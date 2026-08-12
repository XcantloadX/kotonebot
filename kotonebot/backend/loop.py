import time
from typing import Any, Generic, TypeVar, cast, get_args

from cv2.typing import MatLike

from kotonebot.config.config import conf
from kotonebot import device
from .context import vars

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
        # 执行全局回调
        callbacks = conf().loop.loop_callbacks
        while True:
            did = False
            for cb in callbacks:
                did = cb(self)
                if did:
                    time.sleep(self.interval)
                    self.screenshot = device.screenshot()
                    break
            if not did:
                break

        return self

    def exit(self):
        """
        结束循环。
        """
        self.running = False

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
