import threading
from typing import Callable, Literal, overload, TYPE_CHECKING

from cv2.typing import MatLike
from typing_extensions import deprecated


if TYPE_CHECKING:
    from adbutils._device import AdbDevice as AdbUtilsDevice

from kotonebot import logging
from kotonebot._utils import match_types
from .scaler import AbstractScaler
from kotonebot.config.config import conf
from kotonebot.primitives.geometry import Size
from kotonebot.client.input import InputManager
from kotonebot.primitives import Rect, Point
from functools import wraps
from kotonebot.errors import (
    CapabilityNotSupportedError, DeviceAlreadyStartedError, DeviceThreadMismatchError,
    DeviceConnectionError, DeviceNotReadyError, DeviceConnectRefusedError, DeviceConnectTimeoutError,
)
from .protocol import ClickableObjectProtocol, Commandable, MultiTouchable, Touchable, Screenshotable, AndroidCommandable, WindowsCommandable, Lifecycle

logger = logging.getLogger(__name__)
LogLevel = Literal['info', 'debug', 'verbose', 'silent']
CommandComponent = Commandable | AndroidCommandable | WindowsCommandable

def device_operation(func):
    """
    标记一个方法为设备操作。

    将底层 impl 抛出的连接相关异常（AdbError、AdbTimeout、socket 异常等）
    统一转译为 DeviceConnectionError 子类，使调用方无需感知底层库细节。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DeviceConnectionError:
            raise
        except (ConnectionAbortedError, ConnectionResetError) as e:
            raise DeviceNotReadyError(str(e)) from e
        except ConnectionRefusedError as e:
            raise DeviceConnectRefusedError('', e) from e
        except Exception as e:
            msg = str(e)
            try:
                from adbutils import AdbTimeout
                from adbutils.errors import AdbError
                if isinstance(e, AdbTimeout):
                    raise DeviceConnectTimeoutError() from e
                if isinstance(e, AdbError):
                    if any(k in msg for k in ('offline', 'closed', 'not found', 'screencap error')):
                        raise DeviceNotReadyError(msg) from e
            except ImportError:
                pass
            raise
    return wrapper


class HookContextManager:
    def __init__(self, device: 'Device', func: Callable[[MatLike], MatLike]):
        self.device = device
        self.func = func
        self.old_func = device.screenshot_hook_after

    def __enter__(self):
        self.device.screenshot_hook_after = self.func
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.device.screenshot_hook_after = self.old_func

class Device:
    def __init__(self, platform: str = 'unknown', scaler: AbstractScaler | None = None) -> None:
        self.screenshot_hook_after: Callable[[MatLike], MatLike] | None = None
        """截图后调用的函数"""
        self.screenshot_hook_before: Callable[[], MatLike | None] | None = None
        """截图前调用的函数。返回修改后的截图。"""
        self.click_hooks_before: list[Callable[[int, int], tuple[int, int]]] = []
        """点击前调用的函数。返回修改后的点击坐标。"""
        self.last_find: Rect | ClickableObjectProtocol | None = None
        """上次 image 对象或 ocr 对象的寻找结果"""
        self.orientation: Literal['portrait', 'landscape'] = 'portrait'
        """
        设备当前方向。默认为竖屏。注意此属性并非用于检测设备方向。
        如果需要检测设备方向，请使用 `self.detect_orientation()` 方法。

        横屏时为 'landscape'，竖屏时为 'portrait'。
        """

        self._touch: Touchable
        """已弃用，使用输入控制器接口替代。"""
        self._screenshot: Screenshotable
        self._multitouch: MultiTouchable | None = None
        """已弃用，使用输入控制器接口替代。"""
        self.input: InputManager
        """输入控制器接口，包含触摸、鼠标、键盘等输入方式。"""

        self.platform: str = platform
        """
        设备平台名称。
        """
        self.log_level: LogLevel = 'debug'
        """默认日志级别。"""
    
        self._scaler = scaler or conf().device.default_scaler_factory()
        self._scaler_initialized = False
        self._lifecycle_started = False
        """是否已启动生命周期。

        此变量用于标识 components（touchable、screenshotable 等）是否已启动。
        """
        self._lifecycle_thread: threading.Thread | None = None
        """当前 Device 生命周期启动时所处的线程。"""

    @property
    def scaler(self) -> AbstractScaler:
        # TODO: 应该要有一种更好的方式，把从延迟初始化的 _screenshot 中获取到屏幕大小，以初始化 scaler 的逻辑放到更合适的位置。
        if not self._scaler.physical_resolution:
            self._scaler.logic_resolution = conf().device.default_logic_resolution
            self._scaler.physical_resolution = Size(*self._screenshot.screen_size)
            self._scaler_initialized = True
        return self._scaler

    @property
    @deprecated('Use input controllers instead.')
    def touch(self) -> Touchable:
        """
        触摸接口。
        """
        return self._touch
    
    @property
    def screenshotable(self) -> Screenshotable:
        """
        截图接口。
        """
        return self._screenshot

    @property
    @deprecated('Use input controllers instead.')
    def multi_touch(self) -> MultiTouchable:
        """
        多点触控接口。
        
        :raises CapabilityNotSupportedError: 如果当前设备实现不支持多点触控，则抛出异常。
        """
        if not self._multitouch:
            raise CapabilityNotSupportedError("multi_touch")
        return self._multitouch

    @deprecated('Use setup(components=[...]) instead.')
    @overload
    def setup(self,
        *,
        screenshot: Screenshotable,
        touch: Touchable,
        commands: CommandComponent | None = None,
        scaler: AbstractScaler | None = None,
        multitouch: MultiTouchable | None = None,
    ) -> None:
        ...

    @overload
    def setup(self, components: list[object], *, scaler: AbstractScaler | None = None) -> None:
        ...

    def setup(self,
        components: list[object] | None = None,
        *,
        screenshot: Screenshotable | None = None,
        touch: Touchable | None = None,
        commands: CommandComponent | None = None,
        scaler: AbstractScaler | None = None,
        multitouch: MultiTouchable | None = None,
    ) -> None:
        if scaler is not None:
            self._scaler = scaler

        if components is not None:
            resolved_screenshot: Screenshotable | None = None
            resolved_touch: Touchable | None = None
            resolved_multitouch: MultiTouchable | None = None
            resolved_commands: CommandComponent | None = None

            for component in components:
                if resolved_screenshot is None and isinstance(component, Screenshotable):
                    resolved_screenshot = component
                if resolved_multitouch is None and isinstance(component, MultiTouchable):
                    resolved_multitouch = component
                if resolved_touch is None and isinstance(component, Touchable):
                    resolved_touch = component
                if (
                    resolved_commands is None and
                    (
                        isinstance(component, Commandable) or
                        isinstance(component, AndroidCommandable) or
                        isinstance(component, WindowsCommandable)
                    )
                ):
                    resolved_commands = component

            if resolved_screenshot is None:
                raise ValueError("No Screenshotable component found")
            if resolved_touch is None:
                raise ValueError("No Touchable component found")

            self._screenshot = resolved_screenshot
            self._touch = resolved_touch
            self._multitouch = resolved_multitouch
            self.commands = resolved_commands
            self.input = InputManager(self._scaler, components)
            return

        if screenshot is None or touch is None:
            raise ValueError("screenshot and touch are required")

        self._screenshot = screenshot
        self._touch = touch
        self._multitouch = multitouch
        self.commands = commands
        legacy_components: list[object] = [screenshot, touch]
        if multitouch is not None:
            legacy_components.append(multitouch)
        if commands is not None:
            legacy_components.append(commands)
        self.input = InputManager(self._scaler, legacy_components)

    def _lifecycle_components(self) -> list[Lifecycle]:
        components: list[Lifecycle] = []
        component_ids: set[int] = set()
        for item in (self._screenshot, self._touch, self._multitouch, getattr(self, 'commands', None)):
            if item is None:
                continue
            if not isinstance(item, Lifecycle):
                continue
            item_id = id(item)
            if item_id in component_ids:
                continue
            component_ids.add(item_id)
            components.append(item)
        return components

    @device_operation
    def start(self) -> None:
        """启动设备并初始化组件。
        
        :meth:`start` 与 :meth:`stop` 必须在同一线程中调用，否则会抛出异常。

        :raises DeviceAlreadyStartedError: 如果设备生命周期已经启动，则抛出异常。
        """
        if self._lifecycle_started:
            raise DeviceAlreadyStartedError()
        self._lifecycle_thread = threading.current_thread()
        components = self._lifecycle_components()
        started_components: list[Lifecycle] = []
        try:
            for component in components:
                component.start()
                started_components.append(component)
        except Exception:
            for component in reversed(started_components):
                component.stop()
            self._lifecycle_thread = None
            raise
        self._lifecycle_started = True

    @device_operation
    def stop(self) -> None:
        """停止设备并清理组件。

        如果设备生命周期未启动，则此方法不会执行任何操作。

        :meth:`start` 与 :meth:`stop` 必须在同一线程中调用，否则会抛出异常。

        :raises DeviceThreadMismatchError: 如果当前线程与启动生命周期的线程不匹配，则抛出异常。
        """
        if not self._lifecycle_started:
            return
        current_thread = threading.current_thread()
        if self._lifecycle_thread is not current_thread:
            owner_thread_name = self._lifecycle_thread.name if self._lifecycle_thread is not None else 'unknown'
            raise DeviceThreadMismatchError(
                action='stop',
                owner_thread=owner_thread_name,
                current_thread=current_thread.name,
            )
        components = self._lifecycle_components()
        try:
            for component in reversed(components):
                component.stop()
        finally:
            self._lifecycle_started = False
            self._lifecycle_thread = None

    def __log(self, message: str, level: LogLevel | None = None, *args):
        """以指定的日志级别输出日志。

        :param message: 要输出的日志信息。
        :param level: 要使用的日志级别。可以是 'info', 'debug', 'verbose', 'silent' 中的一个，或者是 None。
                       如果为 None，则使用实例的 `log_level` 属性。
        """
        effective_level = level if level is not None else self.log_level

        if effective_level == 'info':
            logger.info(message, *args)
        elif effective_level == 'debug':
            logger.debug(message, *args)
        elif effective_level == 'verbose':
            logger.verbose(message, *args)
        elif effective_level == 'silent':
            pass # Do nothing

    @deprecated('Exciplicitly store the last find result and use click with the result as argument instead.')
    @overload
    def click(self, *, log: "LogLevel | None" = None) -> None:
        """
        点击上次 `image` 对象或 `ocr` 对象的寻找结果（仅包括返回单个结果的函数）。
        （不包括 `image.raw()` 和 `ocr.raw()` 的结果。）

        如果没有上次寻找结果或上次寻找结果为空，会抛出异常 ValueError。
        """
        ...

    @overload
    def click(self, x: int, y: int, *, log: "LogLevel | None" = None) -> None:
        """
        点击屏幕上的某个点
        """
        ...

    @overload
    def click(self, point: Point, *, log: "LogLevel | None" = None) -> None:
        """
        点击屏幕上的某个点
        """
        ...
    
    @overload
    def click(self, rect: Rect, *, log: "LogLevel | None" = None) -> None:
        """
        点击矩形区域的中心位置
        """
        ...

    @overload
    def click(self, clickable: ClickableObjectProtocol, *, log: "LogLevel | None" = None) -> None:
        """
        点击可点击对象的中心位置
        """
        ...

    @device_operation
    def click(self, *args, **kwargs) -> None:
        log: LogLevel | None = kwargs.pop('log', None)
        if match_types(args, {}, exact=True):
            target: Rect | ClickableObjectProtocol = self.__click_last_target()
            self.click(target, log=log)
            return
        if len(args) == 1 and isinstance(args[0], Rect):
            rect = args[0]
            x = rect.x1 + rect.w // 2
            y = rect.y1 + rect.h // 2
            point = Point(int(x), int(y))
            self.click(point, log=log)
            return
        if len(args) == 1 and isinstance(args[0], ClickableObjectProtocol):
            self.click(args[0].rect, log=log)
            return

        point = self.__solve_click_point(*args)
        x, y = point.x, point.y
        for hook in self.click_hooks_before:
            logger.debug(f"Executing click hook before: ({x}, {y})")
            x, y = hook(x, y)
            logger.debug(f"Click hook before result: ({x}, {y})")
        if self.input.capabilities.pointer:
            self.input.tap(x, y, log=log)
            return
        real_x, real_y = self.scaler.logic_to_physical((x, y))
        self._touch.click(int(real_x), int(real_y))

    def __click_last_target(self) -> Rect | ClickableObjectProtocol:
        if self.last_find is None:
            raise ValueError("No last find result. Make sure you are not calling the 'raw' functions.")
        return self.last_find

    def __solve_click_point(self, *args) -> Point:
        if len(args) == 1 and isinstance(args[0], Point):
            return args[0]
        if (
            len(args) == 1 and
            isinstance(args[0], (tuple, list)) and
            len(args[0]) == 2 and
            all(isinstance(v, int) for v in args[0])
        ):
            x, y = args[0]
            return Point(x, y)
        if len(args) == 2 and isinstance(args[0], int) and isinstance(args[1], int):
            x = args[0]
            y = args[1]
            return Point(x, y)
        raise ValueError(f"Invalid arguments: {args}")

    def click_center(self, *, log: "LogLevel | None" = None) -> None:
        """
        点击屏幕中心。
        
        此方法会受到 `self.orientation` 的影响。
        调用前确保 `orientation` 属性与设备方向一致，
        否则点击位置会不正确。
        """
        size = self.scaler.physical_to_logic(self.screen_size)
        x, y = size[0] // 2, size[1] // 2
        self.click(x, y, log=log)
    
    @overload
    def double_click(self, x: int, y: int, interval: float = 0.4, *, log: "LogLevel | None" = None) -> None:
        """
        双击屏幕上的某个点
        """
        ...

    @overload
    def double_click(self, rect: Rect, interval: float = 0.4, *, log: "LogLevel | None" = None) -> None:
        """
        双击矩形区域的中心位置
        """
        ...
    
    @overload
    def double_click(self, clickable: ClickableObjectProtocol, interval: float = 0.4, *, log: "LogLevel | None" = None) -> None:
        """
        双击可点击对象的中心位置
        """
        ...
    
    def double_click(self, *args, **kwargs) -> None:
        from kotonebot import sleep

        log = kwargs.get('log', None)
        interval = kwargs.get('interval', 0.4)

        if match_types(args, {}, exact=True):
            target = self.__click_last_target()
            self.double_click(target, interval=interval, log=log)
            return
        self.click(*args, log=log)
        sleep(interval)
        self.click(*args, log=log)

    @device_operation
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None, *, log: "LogLevel | None" = None) -> None:
        """
        滑动屏幕
        """
        if self.input.capabilities.pointer:
            self.input.drag(x1, y1, x2, y2, duration=duration, log=log)
            return
        real_pos1 = self.scaler.logic_to_physical((x1, y1))
        real_x1, real_y1 = int(real_pos1[0]), int(real_pos1[1])
        real_pos2 = self.scaler.logic_to_physical((x2, y2))
        real_x2, real_y2 = int(real_pos2[0]), int(real_pos2[1])
        self._touch.swipe(real_x1, real_y1, real_x2, real_y2, duration)

    @deprecated('Use input controllers instead.')
    def swipe_scaled(self, x1: float, y1: float, x2: float, y2: float, duration: float|None = None, *, log: "LogLevel | None" = None) -> None:
        """
        滑动屏幕，参数为屏幕坐标的百分比。

        如果设置了 `self.target_resolution`，则参数为逻辑坐标百分比。
        否则为真实坐标百分比。

        :param x1: 起始点 x 坐标百分比。范围 [0, 1]
        :param y1: 起始点 y 坐标百分比。范围 [0, 1]
        :param x2: 结束点 x 坐标百分比。范围 [0, 1]
        :param y2: 结束点 y 坐标百分比。范围 [0, 1]
        :param duration: 滑动持续时间，单位秒。None 表示使用默认值。
        """
        w, h = self.scaler.physical_to_logic(self.screen_size)
        self.swipe(int(w * x1), int(h * y1), int(w * x2), int(h * y2), duration, log=log)
    
    @device_operation
    def screenshot(self) -> MatLike:
        """
        截图
        """
        if self.screenshot_hook_before is not None:
            logger.debug("execute screenshot hook before")
            img = self.screenshot_hook_before()
            if img is not None:
                logger.debug("screenshot hook before returned image")
                return img
        img = self.screenshot_raw()
        img = self.scaler.transform_screenshot(img)
        if self.screenshot_hook_after is not None:
            img = self.screenshot_hook_after(img)
        return img

    @device_operation
    def screenshot_raw(self) -> MatLike:
        """
        截图，不调用任何 Hook。
        """
        return self._screenshot.screenshot()

    def hook(self, func: Callable[[MatLike], MatLike]) -> HookContextManager:
        """
        注册 Hook，在截图前将会调用此函数，对截图进行处理
        """
        return HookContextManager(self, func)

    @device_operation
    def _get_screen_size(self) -> tuple[int, int]:
        size = self._screenshot.screen_size
        if self.orientation == 'landscape':
            size = sorted(size, reverse=True)
        else:
            size = sorted(size, reverse=False)
        return size[0], size[1]

    @property
    def screen_size(self) -> tuple[int, int]:
        """
        真实屏幕尺寸。格式为 `(width, height)`。

        **注意**： 此属性返回的分辨率会随设备方向变化。
        如果 `self.orientation` 为 `landscape`，则返回的分辨率是横屏下的分辨率，
        否则返回竖屏下的分辨率。

        `self.orientation` 属性默认为竖屏。如果需要自动检测，
        调用 `self.detect_orientation()` 方法。
        如果已知方向，也可以直接设置 `self.orientation` 属性。

        即使设置了 `self.target_resolution`，返回的分辨率仍然是真实分辨率。
        """
        return self._get_screen_size()

    @device_operation
    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        """
        检测当前设备方向并设置 `self.orientation` 属性。

        :return: 检测到的方向，如果无法检测到则返回 None。
        """
        return self._screenshot.detect_orientation()


class AndroidDevice(Device):
    def __init__(self, adb_connection: 'AdbUtilsDevice | None' = None) -> None:
        super().__init__('android')
        self._adb: 'AdbUtilsDevice | None' = adb_connection
        self.commands: AndroidCommandable
        
    @device_operation
    def current_package(self) -> str | None:
        """
        获取前台 APP 的包名。

        :return: 前台 APP 的包名。如果获取失败，则返回 None。
        :raises NotImplementedError: 如果设备不支持此功能。
        """
        ret = self.commands.current_package()
        logger.debug("current_package: %s", ret)
        return ret

    @device_operation
    def launch_app(self, package_name: str) -> None:
        """
        根据包名启动 app
        """
        self.commands.launch_app(package_name)
    

class WindowsDevice(Device):
    def __init__(self) -> None:
        super().__init__('windows')
        self.commands: WindowsCommandable


class MacOSDevice(Device):
    def __init__(self) -> None:
        super().__init__('macos')
