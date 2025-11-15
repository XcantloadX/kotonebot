import math
import time
from typing import Callable, Literal, TypedDict, overload, Tuple

import mouse
from typing_extensions import Unpack

from kotonebot.primitives import Point

MouseButton = Literal['left', 'right', 'middle']
TweenFunc = Callable[[float], float]
Tween = Literal['linear', 'ease_in', 'ease_out', 'ease_in_out'] | TweenFunc

# https://stackoverflow.com/a/76554895
def high_precision_sleep(duration):
    start_time = time.perf_counter()
    while True:
        elapsed_time = time.perf_counter() - start_time
        remaining_time = duration - elapsed_time
        if remaining_time <= 0:
            break
        if remaining_time > 0.02:  # Sleep for 5ms if remaining time is greater
            time.sleep(max(remaining_time/2, 0.0001))  # Sleep for the remaining time or minimum sleep interval
        else:
            pass

class AnimationParams(TypedDict, total=False):
    duration: float
    """动画持续时间，单位为秒。

    动画实际持续时间可能会略大于此值，具体取决于系统以及 delay_func 的实现。
    """
    speed: float
    """动画速度，单位为像素/秒。"""
    steps: int
    """动画步数。"""
    tween: Tween
    """插值函数。

    可选 'linear', 'ease_in', 'ease_out', 'ease_in_out'，默认为 'ease_in_out'。
    也可以是一个函数，其输入为动画进度，输出为动画值。
    """
    delay_func: Callable[[float], None] | None
    """延时函数。默认为 time.sleep。

    可选，如果提供了此参数，则会在每个动画点之间调用此函数。
    """
    user_interrupt: Callable[[], bool | None] | Literal[True] | None
    """可选，用户中断函数，默认为 None。

    若提供此参数，那么在动画执行时会检测用户输入，如果用户尝试移动鼠标，
    会自动终止动画（传入 True）或调用此函数（传入 Callable，根据返回值决定是否继续）。
    """
    user_interrupt_threshold: float | None
    """可选，用户中断阈值，单位为像素，默认为 None，表示使用全局参数。

    如果提供此参数，则在检测用户中断时，仅当移动鼠标的距离大于此值时才会触发终止。
    """

default_speed = 3000
animation_args: AnimationParams = {
    'steps': 100,
    'tween': 'ease_in_out',
    'delay_func': high_precision_sleep,
    'user_interrupt': None,
    'user_interrupt_threshold': 30,
}
"""全局动画参数。"""

# https://easings.net
def _tween_linear(t: float) -> float:
    return t

def _tween_ease_in(t: float) -> float:
    return t * t

def _tween_ease_out(t: float) -> float:
    return t * (2 - t)

def _tween_ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)

_TWEEN_FUNCTIONS = {
    'linear': _tween_linear,
    'ease_in': _tween_ease_in,
    'ease_out': _tween_ease_out,
    'ease_in_out': _tween_ease_in_out,
}

def _get_animated_points(start_point: Point, end_point: Point, steps: int, tween: Tween):
    if isinstance(tween, str):
        tween_func = _TWEEN_FUNCTIONS.get(tween, _tween_linear)
    else:
        tween_func = tween
    for i in range(steps + 1):
        progress = i / steps
        eased_progress = tween_func(progress)
        x = start_point.x + (end_point.x - start_point.x) * eased_progress
        y = start_point.y + (end_point.y - start_point.y) * eased_progress
        yield Point(int(x), int(y))

def do_tween(start: Point, end: Point, args: AnimationParams, *, skip_first: bool = True):
    """从起点到终点根据输入的动画参数进行插值，并自动进行延时。

    :param start: 开始位置。
    :param end: 结束位置。
    :param args: 动画参数，详见 :class:`.AnimationParams`。
    :param skip_first: 是否跳过第一个点。默认为 True。
    :raises ValueError: 输入的 speed 为非正数时抛出。
    :raises ValueError: 同时提供 speed 与 duration 参数时抛出。
    :return: 一个迭代器，包含所有插值的中间点。
    """
    duration = args.get('duration')
    speed = args.get('speed')
    steps = args.get('steps', animation_args.get('steps'))
    tween = args.get('tween', animation_args.get('tween'))
    delay_func = args.get('delay_func', animation_args.get('delay_func'))
    user_interrupt = args.get('user_interrupt', animation_args.get('user_interrupt'))
    user_interrupt_threshold = args.get('user_interrupt_threshold', animation_args.get('user_interrupt_threshold'))
    assert steps is not None and tween is not None and delay_func is not None

    def _speed_to_duration(speed: float) -> float:
        return math.sqrt((end.x - start.x)**2 + (end.y - start.y)**2) / speed

    if duration is None and speed is not None:
        # 设置了速度，但没有设置时长，则计算时长
        if speed <= 0:
            raise ValueError('speed must be positive')
        duration = _speed_to_duration(speed)
    elif duration is not None and speed is None:
        # 设置了时长，但没有设置速度，则计算速度
        pass
    elif duration is not None and speed is not None:
        # 两个都设置
        raise ValueError('duration and speed cannot be set at the same time')
    else:
        # 两个都没有设置，使用默认速度
        duration = _speed_to_duration(default_speed)

    delay = duration / steps if steps > 0 else 0
    print(duration, steps, delay)
    
    point_iterator = _get_animated_points(start, end, steps, tween)
    if skip_first:
        next(point_iterator, None)

    # 调用函数 (drag/move) 负责设置鼠标位置。
    # 在每次迭代中，我们检查当前鼠标位置是否与我们在“上一次”迭代中生成的位置匹配。
    # 我们无法在此处知道初始鼠标位置，因此我们从第二个点开始检查。
    
    iterator = iter(point_iterator)
    try:
        prev_pos = next(iterator)
        yield prev_pos
        delay_func(delay)
    except StopIteration:
        return

    for pt in iterator:
        # 检测用户中断
        if user_interrupt:
            pos = get_pos()
            should_interrupt = False
            if user_interrupt_threshold is not None:
                if pos.distance_to(prev_pos) > user_interrupt_threshold:
                    should_interrupt = True
            else:
                if pos != prev_pos:
                    should_interrupt = True
            
            if should_interrupt:
                # 鼠标被用户移动，中断动画。
                if user_interrupt is True:
                    return
                if callable(user_interrupt):
                    if not user_interrupt():
                        return
        
        yield pt
        prev_pos = pt
        delay_func(delay)

@overload
def set_pos(p: Point) -> None: 
    """移动光标到指定位置。

    :param p: 坐标，Point 实例。
    """

@overload
def set_pos(p: Tuple[int, int]) -> None:
    """移动光标到指定位置。

    :param p: 坐标，二元 tuple[int, int]。
    """

@overload
def set_pos(p: int, y: int) -> None:
    """移动光标到指定位置。

    :param p: 坐标，x 坐标。
    :param y: 坐标，y 坐标。
    """

def set_pos(p, y: int | None = None):
    if y is None:
        # 可能是 Point 或二元 tuple
        if isinstance(p, Point):
            x = int(p.x)
            y = int(p.y)
        else:
            # 假定为 (x, y)
            _x, _y = p
            x = int(_x)
            y = int(_y)
    else:
        x = int(p)
        y = int(y)

    mouse.move(x, y)


def get_pos() -> Point:
    x, y = mouse.get_position()
    return Point(x, y)


def down(button: MouseButton):
    mouse.press(button)


def up(button: MouseButton):
    mouse.release(button)


def click(button: MouseButton, *, duration: float = 0.1):
    """模拟鼠标点击。
    
    :param button: 必填，鼠标按钮。
    :param duration: 可选，点击持续时间。默认为 0.1。
    """
    down(button)
    time.sleep(duration)
    up(button)


def drag(
    start: Point,
    end: Point,
    *,
    button: MouseButton | None = 'left',
    **kargs: Unpack[AnimationParams],
):
    """模拟鼠标拖拽。
    参数中与动画相关的部分详见 :class:`.AnimationParams`。

    :param start: 必填，起点。
    :param end: 必填，终点。
    :param button: 可选，拖拽使用的鼠标按钮。默认为 `left`。None 表示不按下任何鼠标按钮，相当于只移动光标。
    :param duration: 可选，动画持续时间。
    :param speed: 可选，动画速度。
    :param steps: 可选，动画步数。
    :param tween: 可选，动画曲线。
    :param delay_func: 可选，延时函数。详见 :class:`.AnimationParams`。
    :param user_interrupt: 可选，用户中断函数。详见 :class:`.AnimationParams`。
    :param user_interrupt_threshold: 可选，用户中断阈值。详见 :class:`.AnimationParams`。
    """
    if button:
        set_pos(start)
        time.sleep(0.02)
        down(button)
        time.sleep(0.02)
    
    try:
        for p in do_tween(start, end, kargs):
            set_pos(p)
            pass
    finally:
        if button:
            up(button)

def move(
    start: Point,
    end: Point,
    /,
    **kargs: Unpack[AnimationParams],
):
    """模拟鼠标移动。
    参数中与动画相关的部分详见 :class:`kotonebot.interop.win.AnimationParams`。

    :param start: 必填，起点。
    :param end: 必填，终点。
    :param duration: 可选，动画持续时间。
    :param speed: 可选，动画速度。
    :param steps: 可选，动画步数。
    :param tween: 可选，动画曲线。
    :param delay_func: 可选，延时函数。详见 :class:`.AnimationParams`。
    :param user_interrupt: 可选，用户中断函数。详见 :class:`.AnimationParams`。
    :param user_interrupt_threshold: 可选，用户中断阈值。详见 :class:`.AnimationParams`。
    """
    drag(start, end, button=None, **kargs)

__all__ = [
    'set_pos',
    'get_pos',
    'down',
    'up',
    'click',
    'drag',
    'move',
]