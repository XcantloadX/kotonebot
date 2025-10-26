import time
from functools import lru_cache, partial
from typing import Callable, Any, overload, Literal, Generic, TypeVar, cast, get_args, get_origin
from typing_extensions import deprecated

from cv2.typing import MatLike

from kotonebot.util import Interval
from kotonebot import device, image, ocr
from kotonebot.backend.core import Image
from kotonebot.backend.ocr import TextComparator
from kotonebot.client.protocol import ClickableObjectProtocol
from .context import vars

@deprecated('No longer used.')
class LoopAction:
    def __init__(self, loop: 'Loop', func: Callable[[], ClickableObjectProtocol | None]):
        self.loop = loop
        self.func = func
        self.result: ClickableObjectProtocol | None = None

    @property
    def found(self):
        """
        是否找到结果。若父 Loop 未在运行中，则返回 False。
        """
        if not self.loop.running:
            return False
        return bool(self.result)

    def __bool__(self):
        return self.found

    def reset(self):
        """
        重置 LoopAction，以复用此对象。
        """
        self.result = None

    def do(self):
        """
        执行 LoopAction。
        :return: 执行结果。
        """
        if not self.loop.running:
            return
        if self.loop.found_anything:
            # 本轮循环已执行任意操作，因此不需要再继续检测
            return
        self.result = self.func()
        if self.result:
            self.loop.found_anything = True

    def click(self, *, at: tuple[int, int] | None = None):
        """
        点击寻找结果。若结果为空，会跳过执行。

        :return:
        """
        if self.result:
            if at is not None:
                device.click(*at)
            else:
                device.click(self.result)

    def call(self, func: Callable[[ClickableObjectProtocol], Any]):
        pass


class Loop:
    def __init__(
            self,
            *,
            timeout: float = 300,
            interval: float = 0.3,
            auto_screenshot: bool = True,
            skip_first_wait: bool = True
    ):
        self.running = True
        self.found_anything = False
        self.auto_screenshot = auto_screenshot
        """
        是否在每次循环开始时（Loop.tick() 被调用时）截图。
        """
        self.__last_loop: float = -1
        self.interval = interval
        """每次循环后等待的时间。"""
        self.screenshot: MatLike | None = None
        """上次截图时的图像数据。"""
        self.__skip_first_wait = skip_first_wait
        self.__is_first_tick = True

    def __iter__(self):
        self.__is_first_tick = True
        vars.flow.check()
        return self

    def __next__(self):
        if not self.running:
            raise StopIteration
        self.found_anything = False
        self.__last_loop = time.time()
        return self.tick()

    def tick(self):
        if not (self.__is_first_tick and self.__skip_first_wait):
            time.sleep(self.interval)
        self.__is_first_tick = False

        if self.auto_screenshot:
            self.screenshot = device.screenshot()
        self.__last_loop = time.time()
        self.found_anything = False
        return self

    def exit(self):
        """
        结束循环。
        """
        self.running = False

    @overload
    @deprecated('Use plain if statement instead.')
    def when(self, condition: Image) -> LoopAction:
        ...

    @overload
    @deprecated('Use plain if statement instead.')
    def when(self, condition: TextComparator) -> LoopAction:
        ...

    @deprecated('Use plain if statement instead.')
    def when(self, condition: Any):
        """
        判断某个条件是否成立。

        :param condition:
        :return:
        """
        if isinstance(condition, Image):
            func = partial(image.find, condition)
        elif isinstance(condition, TextComparator):
            func = partial(ocr.find, condition)
        else:
            raise ValueError('Invalid condition type.')
        la = LoopAction(self, func)
        la.reset()
        la.do()
        return la

    @deprecated('Use plain if statement instead.')
    def until(self, condition: Any):
        """
        当满足指定条件时，结束循环。

        等价于 ``loop.when(...).call(lambda _: loop.exit())``
        """
        return self.when(condition).call(lambda _: self.exit())

    @deprecated('Use image.find() and device.click() instead.')
    def click_if(self, condition: Any, *, at: tuple[int, int] | None = None):
        """
        检测指定对象是否出现，若出现，点击该对象或指定位置。

        ``click_if()`` 等价于 ``loop.when(...).click(...)``。

        :param condition: 检测目标。
        :param at: 点击位置。若为 None，表示点击找到的目标。
        """
        return self.when(condition).click(at=at)

StateType = TypeVar('StateType')
class StatedLoop(Loop, Generic[StateType]):
    def __init__(
        self,
        states: list[Any] | None = None,
        initial_state: StateType | None = None,
        *,
        timeout: float = 300,
        interval: float = 0.3,
        auto_screenshot: bool = True
    ):
        self.__tmp_states = states
        self.__tmp_initial_state = initial_state
        self.state: StateType
        super().__init__(timeout=timeout, interval=interval, auto_screenshot=auto_screenshot)

    def __iter__(self):
        # __retrive_state_values() 只能在非 __init__ 中调用
        self.__retrive_state_values()
        return super().__iter__()

    def __retrive_state_values(self):
        # HACK: __orig_class__ 是 undocumented 属性
        if not hasattr(self, '__orig_class__'):
            # 如果 Foo 不是以参数化泛型的方式实例化的，可能没有 __orig_class__
            if self.state is None:
                raise ValueError('Either specify `states` or use StatedLoop[Literal[...]] syntax.')
        else:
            generic_type_args = get_args(self.__orig_class__) # type: ignore
            if len(generic_type_args) != 1:
                raise ValueError('StatedLoop must have exactly one generic type argument.')
            state_values = get_args(generic_type_args[0])
            if not state_values:
                raise ValueError('StatedLoop must have at least one state value.')
            self.states = cast(tuple[StateType, ...], state_values)
            self.state = self.__tmp_initial_state or self.states[0]
            return state_values
