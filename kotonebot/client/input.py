from dataclasses import dataclass
from time import sleep
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar, cast
import numpy as np
from typing_extensions import overload

from kotonebot import logging
from kotonebot._utils import match_types
from kotonebot.errors import CapabilityNotSupportedError
from kotonebot.primitives import Point, PointLike, Rect
from .scaler import AbstractScaler
from .protocol import (
    Driver,
    TouchDriver,
    MouseDriver,
    KeyboardDriver,
    SimpleInputDriver,
    ClickableObjectProtocol,
    MouseButton,
)

if TYPE_CHECKING:
    from .device import LogLevel

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InputCapabilities:
    pointer: bool
    mouse: bool
    touch: bool
    keyboard: bool
    max_contacts: int | None

T_Driver = TypeVar('T_Driver', bound=Driver)

class BaseController(Generic[T_Driver]):
    DriverType: ClassVar[type[object]]

    def __init__(self, scaler: AbstractScaler, drivers: list[Driver] | Driver) -> None:
        self.scaler = scaler
        self.driver: T_Driver
        if isinstance(drivers, list):
            self.drivers = drivers
        else:
            self.drivers = [drivers]
        for driver in self.drivers:
            if isinstance(driver, self.DriverType):
                self.driver = cast(T_Driver, driver)
                break
        else:
            raise ValueError("No suitable driver found")

    def _to_physical(self, x: int, y: int) -> tuple[int, int]:
        real_x, real_y = self.scaler.logic_to_physical((x, y))
        return int(real_x), int(real_y)
    
    @overload
    def _solve_point(self, point: Point) -> tuple[int, int]: ...
    @overload
    def _solve_point(self, point: ClickableObjectProtocol) -> tuple[int, int]: ...
    @overload
    def _solve_point(self, point: tuple[int, int]) -> tuple[int, int]: ...
    @overload
    def _solve_point(self, x: int, y: int) -> tuple[int, int]: ...
    def _solve_point(self, *args, **kwargs) -> tuple[int, int]:
        if len(args) == 1 and isinstance(args[0], Point):
            point: Point = args[0]
            return self._to_physical(point.x, point.y)
        elif len(args) == 1 and isinstance(args[0], ClickableObjectProtocol):
            obj: ClickableObjectProtocol = args[0]
            return self._to_physical(obj.rect.center_x, obj.rect.center_y)
        elif (
            len(args) == 1 and
            isinstance(args[0], tuple) and
            len(args[0]) == 2 and
            all(isinstance(v, int) for v in args[0])
        ):
            x, y = args[0]
            return self._to_physical(x, y)
        elif len(args) == 2 and all(isinstance(v, int) for v in args):
            x, y = args
            return self._to_physical(x, y)
        else:
            raise TypeError("Invalid arguments for _solve_point")

    def _log(self, msg: str) -> None:
        logger.debug(msg)


class TouchController(BaseController[TouchDriver]):
    DriverType = TouchDriver

    @overload
    def tap(self, x: int, y: int, *, contact_id: int = 0) -> None:
        """点击指定坐标 x, y。"""
    
    @overload
    def tap(self, point: tuple[int, int], *, contact_id: int = 0) -> None:
        """点击指定坐标 (x, y)。"""

    @overload
    def tap(self, point: Point, *, contact_id: int = 0) -> None:
        """点击指定 Point 对象。"""

    @overload
    def tap(self, clickable: ClickableObjectProtocol, *, contact_id: int = 0) -> None:
        """点击指定可点击对象的中心点。"""

    def tap(self, *args, contact_id: int = 0, **kwargs) -> None:
        point = self._solve_point(*args, **kwargs)
        
        self.driver.touch_down(*point, contact_id=contact_id)
        self.driver.touch_up(*point, contact_id=contact_id)

    @overload
    def double_tap(self, x: int, y: int, *, contact_id: int = 0, interval: float = 0.4) -> None:
        """双击指定坐标 x, y。"""
    @overload
    def double_tap(self, point: PointLike, *, contact_id: int = 0, interval: float = 0.4) -> None:
        """双击指定 Point 对象或可点击对象。"""
    
    def double_tap(self, *args, **kwargs) -> None:
        point = self._solve_point(*args, **kwargs)

        self.driver.touch_down(*point, contact_id=kwargs.get('contact_id', 0))
        self.driver.touch_up(*point, contact_id=kwargs.get('contact_id', 0))
        sleep(kwargs.get('interval', 0.4))
        self.driver.touch_down(*point, contact_id=kwargs.get('contact_id', 0))
        self.driver.touch_up(*point, contact_id=kwargs.get('contact_id', 0))

    @overload
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None, *, contact_id: int = 0) -> None:
        """从坐标 (x1, y1) 滑动到坐标 (x2, y2)。"""
    @overload
    def swipe(self, point1: PointLike, point2: PointLike, duration: float | None = None, *, contact_id: int = 0) -> None:
        """从 point1 滑动到 point2。"""

    def swipe(self, *args, duration: float | None = None, contact_id: int = 0, **kwargs) -> None:
        if len(args) == 4:
            x1, y1, x2, y2 = args
            point1 = self._to_physical(x1, y1)
            point2 = self._to_physical(x2, y2)
        elif len(args) == 2:
            point1 = self._solve_point(args[0])
            point2 = self._solve_point(args[1])
        else:
            raise TypeError("Invalid arguments for swipe")
        
        self.driver.touch_down(*point1, contact_id=contact_id)
        if duration is not None:
            steps = max(int(duration / 0.01), 1)
            for i in range(steps):
                intermediate_x = int(point1[0] + (point2[0] - point1[0]) * (i + 1) / steps)
                intermediate_y = int(point1[1] + (point2[1] - point1[1]) * (i + 1) / steps)
                self.driver.touch_move(intermediate_x, intermediate_y, contact_id=contact_id)
                sleep(0.01)
        else:
            self.driver.touch_move(*point2, contact_id=contact_id)
        self.driver.touch_up(*point2, contact_id=contact_id)


class MouseController(BaseController[MouseDriver]):
    DriverType = MouseDriver

    @overload
    def move(self, x: int, y: int) -> None:
        """移动鼠标到指定坐标 x, y。"""
    @overload
    def move(self, point: PointLike) -> None:
        """移动鼠标到指定 Point 对象或坐标元组。"""
    @overload
    def move(self, clickable: ClickableObjectProtocol) -> None:
        """移动鼠标到指定可点击对象的中心点。"""
    def move(self, *args, **kwargs) -> None:
        point = self._solve_point(*args, **kwargs)
        self.driver.move(*point)

    @overload
    def click(self, x: int, y: int, *, button: MouseButton | None = 'left') -> None:
        """点击指定坐标 x, y。"""
    @overload
    def click(self, point: PointLike, *, button: MouseButton | None = 'left') -> None:
        """点击指定 Point 对象或坐标元组。"""
    @overload
    def click(self, clickable: ClickableObjectProtocol, *, button: MouseButton | None = 'left') -> None:
        """点击指定可点击对象的中心点。"""
    def click(self, *args, button: MouseButton | None = 'left', **kwargs) -> None:
        self.move(*args, **kwargs)
        self.driver.button_down(button)
        self.driver.button_up(button)

    @overload
    def double_click(self, x: int, y: int, *, button: MouseButton | None = 'left', interval: float = 0.4) -> None:
        """双击指定坐标 x, y。"""
    @overload
    def double_click(self, point: PointLike, *, button: MouseButton | None = 'left', interval: float = 0.4) -> None:
        """双击指定 Point 对象或坐标元组。"""
    @overload
    def double_click(self, clickable: ClickableObjectProtocol, *, button: MouseButton | None = 'left', interval: float = 0.4) -> None:
        """双击指定可点击对象的中心点。"""
    def double_click(self, *args, button: MouseButton | None = 'left', interval: float = 0.4, **kwargs) -> None:
        self.click(*args, button=button, **kwargs)
        sleep(interval)
        self.click(*args, button=button, **kwargs)

    @overload
    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float | None = None,
        *,
        button: MouseButton | None = 'left',
    ) -> None:
        """按住鼠标并从坐标 (x1, y1) 拖动到坐标 (x2, y2)。"""
    @overload
    def drag(
        self,
        point1: PointLike,
        point2: PointLike,
        duration: float | None = None,
        *,
        button: MouseButton | None = 'left',
    ) -> None:
        """按住鼠标并从 point1 拖动到 point2。"""
    def drag(self, *args, duration: float | None = None, button: MouseButton | None = 'left', **kwargs) -> None:
        if len(args) == 4:
            x1, y1, x2, y2 = args
            point1 = self._to_physical(x1, y1)
            point2 = self._to_physical(x2, y2)
        elif len(args) == 2:
            point1 = self._solve_point(args[0])
            point2 = self._solve_point(args[1])
        else:
            raise TypeError("Invalid arguments for drag")

        self.driver.move(*point1)
        self.driver.button_down(button)
        if duration is not None:
            steps = max(int(duration / 0.01), 1)
            for i in range(steps):
                intermediate_x = int(point1[0] + (point2[0] - point1[0]) * (i + 1) / steps)
                intermediate_y = int(point1[1] + (point2[1] - point1[1]) * (i + 1) / steps)
                self.driver.move(intermediate_x, intermediate_y)
                sleep(0.01)
        else:
            self.driver.move(*point2)
        self.driver.button_up(button)

    def button_down(self, button: MouseButton | None = 'left') -> None:
        """按下指定鼠标按键。"""
        self.driver.button_down(button)

    def button_up(self, button: MouseButton | None = 'left') -> None:
        """抬起指定鼠标按键。"""
        self.driver.button_up(button)

    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        """滚动鼠标滚轮。dx 为水平滚动量，dy 为垂直滚动量。"""
        self.driver.scroll(dx=dx, dy=dy)


class KeyboardController(BaseController[KeyboardDriver]):
    DriverType = KeyboardDriver

    def key_down(self, key: str) -> None:
        """按下指定按键。"""
        self.driver.key_down(key)

    def key_up(self, key: str) -> None:
        """抬起指定按键。"""
        self.driver.key_up(key)

    def press(self, key: str) -> None:
        """按下并抬起指定按键。"""
        self.driver.key_down(key)
        self.driver.key_up(key)

    def hotkey(self, *keys: str) -> None:
        """依次按下多个按键，并按相反顺序抬起。"""
        if not keys:
            raise ValueError("At least one key is required")
        for key in keys:
            self.driver.key_down(key)
        for key in reversed(keys):
            self.driver.key_up(key)

    def type_text(self, text: str) -> None:
        """输入一段文本。"""
        self.driver.type_text(text)


class SimpleInputController(BaseController[SimpleInputDriver]):
    DriverType = SimpleInputDriver

    @overload
    def tap(self, x: int, y: int) -> None:
        """点击指定坐标 x, y。"""
    @overload
    def tap(self, point: PointLike) -> None:
        """点击指定 Point 对象或坐标元组。"""
    @overload
    def tap(self, clickable: ClickableObjectProtocol) -> None:
        """点击指定可点击对象的中心点。"""
    def tap(self, *args, **kwargs) -> None:
        point = self._solve_point(*args, **kwargs)
        self.driver.click(*point)

    @overload
    def double_tap(self, x: int, y: int, *, interval: float = 0.4) -> None:
        """双击指定坐标 x, y。"""
    @overload
    def double_tap(self, point: PointLike, *, interval: float = 0.4) -> None:
        """双击指定 Point 对象或坐标元组。"""
    @overload
    def double_tap(self, clickable: ClickableObjectProtocol, *, interval: float = 0.4) -> None:
        """双击指定可点击对象的中心点。"""
    def double_tap(self, *args, interval: float = 0.4, **kwargs) -> None:
        self.tap(*args, **kwargs)
        sleep(interval)
        self.tap(*args, **kwargs)

    @overload
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        """从坐标 (x1, y1) 滑动到坐标 (x2, y2)。"""
    @overload
    def swipe(self, point1: PointLike, point2: PointLike, duration: float | None = None) -> None:
        """从 point1 滑动到 point2。"""
    def swipe(self, *args, duration: float | None = None, **kwargs) -> None:
        if len(args) == 4:
            x1, y1, x2, y2 = args
            point1 = self._to_physical(x1, y1)
            point2 = self._to_physical(x2, y2)
        elif len(args) == 2:
            point1 = self._solve_point(args[0])
            point2 = self._solve_point(args[1])
        else:
            raise TypeError("Invalid arguments for swipe")

        self.driver.swipe(*point1, *point2, duration)

    @overload
    def drag(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        """从坐标 (x1, y1) 拖动到坐标 (x2, y2)。"""
    @overload
    def drag(self, point1: PointLike, point2: PointLike, duration: float | None = None) -> None:
        """从 point1 拖动到 point2。"""
    def drag(self, *args, duration: float | None = None, **kwargs) -> None:
        self.swipe(*args, duration=duration, **kwargs)


class InputManager:
    def __init__(self, scaler: AbstractScaler, drivers: list[object]) -> None:
        self.scaler = scaler
        self.drivers = drivers
        self._touch: TouchController | None = None
        self._mouse: MouseController | None = None
        self._keyboard: KeyboardController | None = None
        self._simple: SimpleInputController | None = None
        self._touch_driver: TouchDriver | None = None
        self._mouse_driver: MouseDriver | None = None
        self._keyboard_driver: KeyboardDriver | None = None
        self._simple_driver: SimpleInputDriver | None = None

        for driver in drivers:
            if self._touch_driver is None and isinstance(driver, TouchDriver):
                self._touch_driver = driver
            if self._mouse_driver is None and isinstance(driver, MouseDriver):
                self._mouse_driver = driver
            if self._keyboard_driver is None and isinstance(driver, KeyboardDriver):
                self._keyboard_driver = driver
            if self._simple_driver is None and isinstance(driver, SimpleInputDriver):
                self._simple_driver = driver

        if self._touch_driver is not None:
            self._touch = TouchController(self.scaler, self._touch_driver)
        if self._mouse_driver is not None:
            self._mouse = MouseController(self.scaler, self._mouse_driver)
        if self._keyboard_driver is not None:
            self._keyboard = KeyboardController(self.scaler, self._keyboard_driver)
        if self._simple_driver is not None:
            self._simple = SimpleInputController(self.scaler, self._simple_driver)

    @property
    def touch(self) -> TouchController:
        """触摸控制器。

        :raises CapabilityNotSupportedError: 若当前不支持触摸，抛出此异常。
        """
        if not self._touch:
            raise CapabilityNotSupportedError('InputManager.touch')
        return self._touch
    
    @property
    def mouse(self) -> MouseController:
        """鼠标控制器。

        :raises CapabilityNotSupportedError: 若当前不支持鼠标，抛出此异常。
        """
        if not self._mouse:
            raise CapabilityNotSupportedError('InputManager.mouse')
        return self._mouse
    
    @property
    def keyboard(self) -> KeyboardController:
        """键盘控制器。

        :raises CapabilityNotSupportedError: 若当前不支持键盘，抛出此异常。
        """
        if not self._keyboard:
            raise CapabilityNotSupportedError('InputManager.keyboard')
        return self._keyboard

    @property
    def simple(self) -> SimpleInputController:
        """简单输入控制器。

        :raises CapabilityNotSupportedError: 若当前不支持简单输入，抛出此异常。
        """
        if not self._simple:
            raise CapabilityNotSupportedError('InputManager.simple')
        return self._simple

    @property
    def touch_driver(self) -> TouchDriver:
        """底层触摸实现类。"""
        if not self._touch_driver:
            raise CapabilityNotSupportedError('InputManager.touch_driver')
        return self._touch_driver

    @property
    def mouse_driver(self) -> MouseDriver:
        """底层鼠标实现类。"""
        if not self._mouse_driver:
            raise CapabilityNotSupportedError('InputManager.mouse_driver')
        return self._mouse_driver

    @property
    def keyboard_driver(self) -> KeyboardDriver:
        """底层键盘实现类。"""
        if not self._keyboard_driver:
            raise CapabilityNotSupportedError('InputManager.keyboard_driver')
        return self._keyboard_driver

    @property
    def simple_driver(self) -> SimpleInputDriver:
        """底层简单输入实现类。"""
        if not self._simple_driver:
            raise CapabilityNotSupportedError('InputManager.simple_driver')
        return self._simple_driver
    
    @property
    def capabilities(self) -> InputCapabilities:
        """输入能力信息。"""
        return InputCapabilities(
            pointer=bool(self._mouse_driver or self._touch_driver or self._simple_driver),
            mouse=self._mouse_driver is not None,
            touch=self._touch_driver is not None,
            keyboard=self._keyboard_driver is not None,
            max_contacts=self._touch_driver.max_contacts if self._touch_driver else None
        )

    def _log(self, message: str, level: 'LogLevel | None' = None) -> None:
        effective_level = level or 'debug'
        if effective_level == 'info':
            logger.info(message)
        elif effective_level == 'debug':
            logger.debug(message)
        elif effective_level == 'verbose':
            logger.verbose(message)
        elif effective_level == 'silent':
            return
        else:
            logger.debug(message)

    @overload
    def tap(self, x: int, y: int, *, log: 'LogLevel | None' = None) -> None: ...
    @overload
    def tap(self, point: PointLike, *, log: 'LogLevel | None' = None) -> None: ...
    @overload
    def tap(self, rect: Rect, *, log: 'LogLevel | None' = None) -> None: ...
    @overload
    def tap(self, clickable: ClickableObjectProtocol, *, log: 'LogLevel | None' = None) -> None: ...
    def tap(self, *args, log: 'LogLevel | None' = None, **kwargs) -> None:
        if len(args) == 1 and isinstance(args[0], Rect):
            rect = args[0]
            self._log(f"Tap: {rect}", log)
            x = rect.x1 + rect.w // 2 + np.random.randint(-int(rect.w * 0.3), int(rect.w * 0.3))
            y = rect.y1 + rect.h // 2 + np.random.randint(-int(rect.h * 0.3), int(rect.h * 0.3))
            self.tap(int(x), int(y), log=log, **kwargs)
            return
        self._log(f"Tap: {args}", log)
        if self._simple is not None:
            self.simple.tap(*args, **kwargs)
            return
        if self._touch is not None:
            self.touch.tap(*args, **kwargs)
            return
        if self._mouse is not None:
            self.mouse.click(*args, **kwargs)
            return
        raise CapabilityNotSupportedError('InputManager.tap')

    @overload
    def double_tap(self, x: int, y: int, *, interval: float = 0.4, log: 'LogLevel | None' = None) -> None: ...
    @overload
    def double_tap(self, point: PointLike, *, interval: float = 0.4, log: 'LogLevel | None' = None) -> None: ...
    @overload
    def double_tap(self, rect: Rect, *, interval: float = 0.4, log: 'LogLevel | None' = None) -> None: ...
    @overload
    def double_tap(self, clickable: ClickableObjectProtocol, *, interval: float = 0.4, log: 'LogLevel | None' = None) -> None: ...
    def double_tap(self, *args, log: 'LogLevel | None' = None, **kwargs) -> None:
        if len(args) == 1 and isinstance(args[0], Rect):
            rect = args[0]
            self._log(f"Double tap: {rect}", log)
            self.tap(rect, log=log)
            sleep(kwargs.get('interval', 0.4))
            self.tap(rect, log=log)
            return
        self._log(f"Double tap: {args}", log)
        if self._simple is not None:
            self.simple.double_tap(*args, **kwargs)
            return
        if self._touch is not None:
            self.touch.double_tap(*args, **kwargs)
            return
        if self._mouse is not None:
            self.mouse.double_click(*args, **kwargs)
            return
        raise CapabilityNotSupportedError('InputManager.double_tap')

    @overload
    def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float | None = None,
        *,
        log: 'LogLevel | None' = None,
    ) -> None: ...
    @overload
    def drag(
        self,
        point1: PointLike,
        point2: PointLike,
        duration: float | None = None,
        *,
        log: 'LogLevel | None' = None,
    ) -> None: ...
    def drag(self, *args, duration: float | None = None, log: 'LogLevel | None' = None, **kwargs) -> None:
        self._log(f"Drag: {args}", log)
        if self._simple is not None:
            self.simple.drag(*args, duration=duration, **kwargs)
            return
        if self._touch is not None:
            self.touch.swipe(*args, duration=duration, **kwargs)
            return
        if self._mouse is not None:
            self.mouse.drag(*args, duration=duration, **kwargs)
            return
        raise CapabilityNotSupportedError('InputManager.drag')
