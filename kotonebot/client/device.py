from typing import Callable, Literal, overload, TYPE_CHECKING

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot.errors import CapabilityNotSupportedError, DeviceAlreadyStartedError

if TYPE_CHECKING:
    from adbutils._device import AdbDevice as AdbUtilsDevice

from kotonebot import logging
from ..backend.debug import result
from kotonebot.primitives import Rect, Point, is_point
from .protocol import ClickableObjectProtocol, Commandable, MultiTouchable, Touchable, Screenshotable, AndroidCommandable, WindowsCommandable, Lifecycle
from .scaler import AbstractScaler
from kotonebot.config.config import conf
from kotonebot.primitives.geometry import Size

logger = logging.getLogger(__name__)
LogLevel = Literal['info', 'debug', 'verbose', 'silent']

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
        self._screenshot: Screenshotable
        self._multitouch: MultiTouchable | None = None

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

    @property
    def scaler(self) -> AbstractScaler:
        # TODO: 应该要有一种更好的方式，把从延迟初始化的 _screenshot 中获取到屏幕大小，以初始化 scaler 的逻辑放到更合适的位置。
        if not self._scaler.physical_resolution:
            self._scaler.logic_resolution = conf().device.default_logic_resolution
            self._scaler.physical_resolution = Size(*self._screenshot.screen_size)
            self._scaler_initialized = True
        return self._scaler

    @property
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
    def multi_touch(self) -> MultiTouchable:
        """
        多点触控接口。
        
        :raises CapabilityNotSupportedError: 如果当前设备实现不支持多点触控，则抛出异常。
        """
        if not self._multitouch:
            raise CapabilityNotSupportedError("multi_touch")
        return self._multitouch

    def setup(self, 
        *, 
        screenshot: Screenshotable,
        touch: Touchable,
        commands: Commandable | None = None,
        scaler: AbstractScaler | None = None,
        multitouch: MultiTouchable | None = None,
    ):
        self._screenshot = screenshot
        self._touch = touch
        self._multitouch = multitouch
        self.commands = commands

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

    def start(self) -> None:
        """启动设备并初始化组件。

        :raises DeviceAlreadyStartedError: 如果设备生命周期已经启动，则抛出异常。
        """
        if self._lifecycle_started:
            raise DeviceAlreadyStartedError()
        components = self._lifecycle_components()
        started_components: list[Lifecycle] = []
        try:
            for component in components:
                component.start()
                started_components.append(component)
        except Exception:
            for component in reversed(started_components):
                component.stop()
            raise
        self._lifecycle_started = True

    def stop(self) -> None:
        """停止设备并清理组件。

        如果设备生命周期未启动，则此方法不会执行任何操作。
        """
        if not self._lifecycle_started:
            return
        components = self._lifecycle_components()
        for component in reversed(components):
            component.stop()
        self._lifecycle_started = False

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
        从屏幕上的某个矩形区域随机选择一个点并点击
        """
        ...

    @overload
    def click(self, clickable: ClickableObjectProtocol, *, log: "LogLevel | None" = None) -> None:
        """
        点击屏幕上的某个可点击对象
        """
        ...

    def click(self, *args, **kwargs) -> None:
        log: LogLevel | None = kwargs.pop('log', None)
        arg1 = args[0] if len(args) > 0 else None
        arg2 = args[1] if len(args) > 1 else None
        if arg1 is None:
            self.__click_last(log=log)
        elif isinstance(arg1, Rect):
            self.__click_rect(arg1, log=log)
        elif is_point(arg1):
            self.__click_point_tuple(arg1, log=log)
        elif isinstance(arg1, int) and isinstance(arg2, int):
            self.__click_point(arg1, arg2, log=log)
        elif isinstance(arg1, ClickableObjectProtocol):
            self.__click_clickable(arg1, log=log)
        else:
            raise ValueError(f"Invalid arguments: {arg1}, {arg2}")

    def __click_last(self, *, log: "LogLevel | None" = None) -> None:
        if self.last_find is None:
            raise ValueError("No last find result. Make sure you are not calling the 'raw' functions.")
        self.click(self.last_find, log=log)

    def __click_rect(self, rect: Rect, *, log: "LogLevel | None" = None) -> None:
        # 从矩形中心的 60% 内部随机选择一点
        x = rect.x1 + rect.w // 2 + np.random.randint(-int(rect.w * 0.3), int(rect.w * 0.3))
        y = rect.y1 + rect.h // 2 + np.random.randint(-int(rect.h * 0.3), int(rect.h * 0.3))
        x = int(x)
        y = int(y)
        self.click(x, y, log=log)

    def __click_point(self, x: int, y: int, *, log: "LogLevel | None" = None) -> None:
        for hook in self.click_hooks_before:
            logger.debug(f"Executing click hook before: ({x}, {y})")
            x, y = hook(x, y)
            logger.debug(f"Click hook before result: ({x}, {y})")
        
        real_pos = self.scaler.logic_to_physical((x, y))
        real_x, real_y = int(real_pos[0]), int(real_pos[1])
        
        log_message = f"Click: {x}, {y}%s"
        log_details = f"(Physical: {real_x}, {real_y})"
        self.__log(log_message, log, log_details)

        from ..backend.context import ContextStackVars
        if ContextStackVars.current() is not None:
            image = ContextStackVars.ensure_current()._screenshot
        else:
            image = np.array([])
        if image is not None and image.size > 0:
            cv2.circle(image, (x, y), 10, (0, 0, 255), -1)
            message = f"Point: ({x}, {y})"
            message += f" physical: ({real_x}, {real_y})"
            result("device.click", image, message)
        self.touch.click(real_x, real_y)

    def __click_point_tuple(self, point: Point, *, log: "LogLevel | None" = None) -> None:
        self.click(point[0], point[1], log=log)

    def __click_clickable(self, clickable: ClickableObjectProtocol, *, log: "LogLevel | None" = None) -> None:
        self.click(clickable.rect, log=log)

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
        双击屏幕上的某个矩形区域
        """
        ...
    
    @overload
    def double_click(self, clickable: ClickableObjectProtocol, interval: float = 0.4, *, log: "LogLevel | None" = None) -> None:
        """
        双击屏幕上的某个可点击对象
        """
        ...
    
    def double_click(self, *args, **kwargs) -> None:
        from kotonebot import sleep
        arg0 = args[0]
        log = kwargs.get('log', None)
        if isinstance(arg0, Rect) or isinstance(arg0, ClickableObjectProtocol):
            rect = arg0
            interval = kwargs.get('interval', 0.4)
            self.click(rect, log=log)
            sleep(interval)
            self.click(rect, log=log)
        else:
            x = args[0]
            y = args[1]
            interval = kwargs.get('interval', 0.4)
            self.click(x, y, log=log)
            sleep(interval)
            self.click(x, y, log=log)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None, *, log: "LogLevel | None" = None) -> None:
        """
        滑动屏幕
        """
        real_pos1 = self.scaler.logic_to_physical((x1, y1))
        real_x1, real_y1 = int(real_pos1[0]), int(real_pos1[1])
        real_pos2 = self.scaler.logic_to_physical((x2, y2))
        real_x2, real_y2 = int(real_pos2[0]), int(real_pos2[1])
        log_message = f"Swipe: from ({x1}, {y1}) to ({x2}, {y2}) (Physical: from ({real_x1}, {real_y1}) to ({real_x2}, {real_y2}))"

        self.__log(log_message, log)

        self.touch.swipe(real_x1, real_y1, real_x2, real_y2, duration)

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
        size = self._screenshot.screen_size
        if self.orientation == 'landscape':
            size = sorted(size, reverse=True)
        else:
            size = sorted(size, reverse=False)
        return size[0], size[1]

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
        
    def current_package(self) -> str | None:
        """
        获取前台 APP 的包名。

        :return: 前台 APP 的包名。如果获取失败，则返回 None。
        :exception: 如果设备不支持此功能，则抛出 NotImplementedError。
        """
        ret = self.commands.current_package()
        logger.debug("current_package: %s", ret)
        return ret

    def launch_app(self, package_name: str) -> None:
        """
        根据包名启动 app
        """
        self.commands.launch_app(package_name)
    

class WindowsDevice(Device):
    def __init__(self) -> None:
        super().__init__('windows')
        self.commands: WindowsCommandable
