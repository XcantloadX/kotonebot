import logging
from typing_extensions import deprecated
from typing import Callable, Literal, overload

import cv2
import numpy as np
from adbutils import adb
from cv2.typing import MatLike
from adbutils._device import AdbDevice as AdbUtilsDevice

from ..backend.debug import result
from ..errors import UnscalableResolutionError
from kotonebot.backend.core import HintBox
from kotonebot.primitives import Rect, Point, is_point
from .protocol import ClickableObjectProtocol, Commandable, Touchable, Screenshotable, AndroidCommandable, WindowsCommandable

logger = logging.getLogger(__name__)

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


class PinContextManager:
    def __init__(self, device: 'Device'):
        self.device = device
        self.old_hook = device.screenshot_hook_before
        self.memo = None

    def __hook(self) -> MatLike:
        if self.memo is None:
            self.memo = self.device.screenshot_raw()
        return self.memo

    def __enter__(self):
        self.device.screenshot_hook_before = self.__hook
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.device.screenshot_hook_before = self.old_hook

    def update(self) -> None:
        """
        更新记住的截图
        """
        self.memo = self.device.screenshot_raw()

class Device:
    def __init__(self, platform: str = 'unknown') -> None:
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

        self.platform: str = platform
        """
        设备平台名称。
        """
        self.target_resolution: tuple[int, int] | None = None
        """
        目标分辨率。
        
        若设置，则在截图、点击、滑动等时会缩放到目标分辨率。
        仅支持等比例缩放，若无法等比例缩放，则会抛出异常 `UnscalableResolutionError`。
        """
        self.match_rotation: bool = True
        """
        分辨率缩放是否自动匹配旋转。

        当目标与真实分辨率的宽高比不一致时，是否允许通过旋转（交换宽高）后再进行匹配。
        为 True 则忽略方向差异，只要宽高比一致就视为可缩放；False 则必须匹配旋转。

        例如，当目标分辨率为 1920x1080，而真实分辨率为 1080x1920 时，
        ``match_rotation`` 为 True 则认为可以缩放，为 False 则会抛出异常。
        """
        self.aspect_ratio_tolerance: float = 0.1
        """
        宽高比容差阈值。

        判断两分辨率宽高比差异是否接受的阈值。
        该值越小，对比例一致性的要求越严格。
        默认为 0.1（即 10% 容差）。
        """
    
    @property
    def adb(self) -> AdbUtilsDevice:
        if self._adb is None:
            raise ValueError("AdbClient is not connected")
        return self._adb

    @adb.setter
    def adb(self, value: AdbUtilsDevice) -> None:
        self._adb = value

    def _scale_pos_real_to_target(self, real_x: int, real_y: int) -> tuple[int, int]:
        """将真实屏幕坐标缩放到目标逻辑坐标"""
        if self.target_resolution is None:
            return real_x, real_y
        
        real_w, real_h = self.screen_size
        target_w, target_h = self.target_resolution

        # 校验分辨率是否可缩放
        self._assert_scalable((real_w, real_h), (target_w, target_h))

        scale_w = target_w / real_w
        scale_h = target_h / real_h
        
        return int(real_x * scale_w), int(real_y * scale_h)

    def _scale_pos_target_to_real(self, target_x: int, target_y: int) -> tuple[int, int]:
        """将目标逻辑坐标缩放到真实屏幕坐标"""
        if self.target_resolution is None:
            return target_x, target_y # 输入坐标已是真实坐标
        
        real_w, real_h = self.screen_size
        target_w, target_h = self.target_resolution

        # 校验分辨率是否可缩放
        self._assert_scalable((real_w, real_h), (target_w, target_h))

        scale_to_real_w = real_w / target_w
        scale_to_real_h = real_h / target_h
        
        return int(target_x * scale_to_real_w), int(target_y * scale_to_real_h)

    def __scale_image (self, img: MatLike) -> MatLike:
        if self.target_resolution is None:
            return img

        target_w, target_h = self.target_resolution
        h, w = img.shape[:2]

        # 若宽高比不兼容直接抛异常
        self._assert_scalable((w, h), (target_w, target_h))



        return cv2.resize(img, self.target_resolution)

    @overload
    def click(self) -> None:
        """
        点击上次 `image` 对象或 `ocr` 对象的寻找结果（仅包括返回单个结果的函数）。
        （不包括 `image.raw()` 和 `ocr.raw()` 的结果。）

        如果没有上次寻找结果或上次寻找结果为空，会抛出异常 ValueError。
        """
        ...

    @overload
    def click(self, x: int, y: int) -> None:
        """
        点击屏幕上的某个点
        """
        ...

    @overload
    def click(self, point: Point) -> None:
        """
        点击屏幕上的某个点
        """
        ...
    
    @overload
    def click(self, rect: Rect) -> None:
        """
        从屏幕上的某个矩形区域随机选择一个点并点击
        """
        ...

    @overload
    def click(self, clickable: ClickableObjectProtocol) -> None:
        """
        点击屏幕上的某个可点击对象
        """
        ...

    def click(self, *args, **kwargs) -> None:
        arg1 = args[0] if len(args) > 0 else None
        arg2 = args[1] if len(args) > 1 else None
        if arg1 is None:
            self.__click_last()
        elif isinstance(arg1, Rect):
            self.__click_rect(arg1)
        elif is_point(arg1):
            self.__click_point_tuple(arg1)
        elif isinstance(arg1, int) and isinstance(arg2, int):
            self.__click_point(arg1, arg2)
        elif isinstance(arg1, ClickableObjectProtocol):
            self.__click_clickable(arg1)
        else:
            raise ValueError(f"Invalid arguments: {arg1}, {arg2}")

    def __click_last(self) -> None:
        if self.last_find is None:
            raise ValueError("No last find result. Make sure you are not calling the 'raw' functions.")
        self.click(self.last_find)

    def __click_rect(self, rect: Rect) -> None:
        # 从矩形中心的 60% 内部随机选择一点
        x = rect.x1 + rect.w // 2 + np.random.randint(-int(rect.w * 0.3), int(rect.w * 0.3))
        y = rect.y1 + rect.h // 2 + np.random.randint(-int(rect.h * 0.3), int(rect.h * 0.3))
        x = int(x)
        y = int(y)
        self.click(x, y)

    def __click_point(self, x: int, y: int) -> None:
        for hook in self.click_hooks_before:
            logger.debug(f"Executing click hook before: ({x}, {y})")
            x, y = hook(x, y)
            logger.debug(f"Click hook before result: ({x}, {y})")
        if self.target_resolution is not None:
            # 输入坐标为逻辑坐标，需要转换为真实坐标
            real_x, real_y = self._scale_pos_target_to_real(x, y)
        else:
            real_x, real_y = x, y
        logger.debug(f"Click: {x}, {y}%s", f"(Physical: {real_x}, {real_y})" if self.target_resolution is not None else "")
        from ..backend.context import ContextStackVars
        if ContextStackVars.current() is not None:
            image = ContextStackVars.ensure_current()._screenshot
        else:
            image = np.array([])
        if image is not None and image.size > 0:
            cv2.circle(image, (x, y), 10, (0, 0, 255), -1)
            message = f"Point: ({x}, {y})"
            if self.target_resolution is not None:
                message += f" physical: ({real_x}, {real_y})"
            result("device.click", image, message)
        self._touch.click(real_x, real_y)

    def __click_point_tuple(self, point: Point) -> None:
        self.click(point[0], point[1])

    def __click_clickable(self, clickable: ClickableObjectProtocol) -> None:
        self.click(clickable.rect)

    def click_center(self) -> None:
        """
        点击屏幕中心。
        
        此方法会受到 `self.orientation` 的影响。
        调用前确保 `orientation` 属性与设备方向一致，
        否则点击位置会不正确。
        """
        x, y = self.screen_size[0] // 2, self.screen_size[1] // 2
        self.click(x, y)
    
    @overload
    def double_click(self, x: int, y: int, interval: float = 0.4) -> None:
        """
        双击屏幕上的某个点
        """
        ...

    @overload
    def double_click(self, rect: Rect, interval: float = 0.4) -> None:
        """
        双击屏幕上的某个矩形区域
        """
        ...
    
    @overload
    def double_click(self, clickable: ClickableObjectProtocol, interval: float = 0.4) -> None:
        """
        双击屏幕上的某个可点击对象
        """
        ...
    
    def double_click(self, *args, **kwargs) -> None:
        from kotonebot import sleep
        arg0 = args[0]
        if isinstance(arg0, Rect) or isinstance(arg0, ClickableObjectProtocol):
            rect = arg0
            interval = kwargs.get('interval', 0.4)
            self.click(rect)
            sleep(interval)
            self.click(rect)
        else:
            x = args[0]
            y = args[1]
            interval = kwargs.get('interval', 0.4)
            self.click(x, y)
            sleep(interval)
            self.click(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None) -> None:
        """
        滑动屏幕
        """
        if self.target_resolution is not None:
            # 输入坐标为逻辑坐标，需要转换为真实坐标
            x1, y1 = self._scale_pos_target_to_real(x1, y1)
            x2, y2 = self._scale_pos_target_to_real(x2, y2)
        self._touch.swipe(x1, y1, x2, y2, duration)

    def swipe_scaled(self, x1: float, y1: float, x2: float, y2: float, duration: float|None = None) -> None:
        """
        滑动屏幕，参数为屏幕坐标的百分比

        :param x1: 起始点 x 坐标百分比。范围 [0, 1]
        :param y1: 起始点 y 坐标百分比。范围 [0, 1]
        :param x2: 结束点 x 坐标百分比。范围 [0, 1]
        :param y2: 结束点 y 坐标百分比。范围 [0, 1]
        :param duration: 滑动持续时间，单位秒。None 表示使用默认值。
        """
        w, h = self.screen_size
        self.swipe(int(w * x1), int(h * y1), int(w * x2), int(h * y2), duration)
    
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
        if self.screenshot_hook_after is not None:
            img = self.screenshot_hook_after(img)
        img = self.__scale_image(img)
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

    @deprecated('改用 @task/@action 装饰器中的 screenshot_mode 参数')
    def pinned(self) -> PinContextManager:
        """
        记住下次截图结果，并将截图调整为手动挡。
        之后截图都会返回记住的数据，节省重复截图时间。

        调用返回对象中的 PinContextManager.update() 可以立刻更新记住的截图。
        """
        return PinContextManager(self)

    @property
    def screen_size(self) -> tuple[int, int]:
        """
        屏幕尺寸。格式为 `(width, height)`。
        
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

    # ------------------------------------------------------------------
    # 分辨率处理工具函数
    # ------------------------------------------------------------------

    def _aspect_ratio_compatible(self, src_size: tuple[int, int], tgt_size: tuple[int, int]) -> bool:
        """判断两个尺寸在宽高比意义上是否兼容

        若 ``self.match_rotation`` 为 True，忽略方向（长边/短边）进行比较。
        判断标准由 ``self.aspect_ratio_tolerance`` 决定（默认 0.1）。
        """
        src_w, src_h = src_size
        tgt_w, tgt_h = tgt_size

        # 尺寸必须为正
        if src_w <= 0 or src_h <= 0:
            raise ValueError(f"Source size dimensions must be positive for scaling: {src_size}")
        if tgt_w <= 0 or tgt_h <= 0:
            raise ValueError(f"Target size dimensions must be positive for scaling: {tgt_size}")

        tolerant = self.aspect_ratio_tolerance

        # 直接比较宽高比
        if abs((tgt_w / src_w) - (tgt_h / src_h)) <= tolerant:
            return True

        # 尝试忽略方向差异
        if self.match_rotation:
            ratio_src = max(src_w, src_h) / min(src_w, src_h)
            ratio_tgt = max(tgt_w, tgt_h) / min(tgt_w, tgt_h)
            return abs(ratio_src - ratio_tgt) <= tolerant

        return False

    def _assert_scalable(self, src_size: tuple[int, int], tgt_size: tuple[int, int]) -> None:
        """若 ``src_size`` 与 ``tgt_size`` 的宽高比不兼容，则抛出 ``UnscalableResolutionError``"""
        if not self._aspect_ratio_compatible(src_size, tgt_size):
            raise UnscalableResolutionError(tgt_size, src_size)


class AndroidDevice(Device):
    def __init__(self, adb_connection: AdbUtilsDevice | None = None) -> None:
        super().__init__('android')
        self._adb: AdbUtilsDevice | None = adb_connection
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

        
if __name__ == "__main__":
    from kotonebot.client.implements.adb import AdbImpl
    from kotonebot.client.implements.adb_raw import AdbRawImpl
    from .implements.uiautomator2 import UiAutomator2Impl
    print("server version:", adb.server_version())
    adb.connect("127.0.0.1:5555")
    print("devices:", adb.device_list())
    d = adb.device_list()[-1]
    d.shell("dumpsys activity top | grep ACTIVITY | tail -n 1")
    dd = AndroidDevice(d)
    adb_imp = AdbRawImpl(d)
    dd._touch = adb_imp
    dd._screenshot = adb_imp
    dd.commands = adb_imp
    # dd._screenshot = MinicapScreenshotImpl(dd)
    # dd._screenshot = UiAutomator2Impl(dd)

    # 实时展示画面
    import cv2
    import numpy as np
    import time
    last_time = time.time()
    while True:
        start_time = time.time()
        img = dd.screenshot()
        # 50% 缩放
        img = cv2.resize(img, (img.shape[1] // 2, img.shape[0] // 2))
        
        # 计算帧间隔
        interval = start_time - last_time
        fps = 1 / interval if interval > 0 else 0
        last_time = start_time
        
        # 获取当前时间和帧率信息
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        fps_text = f"FPS: {fps:.1f} {interval*1000:.1f}ms"
        
        # 在图像上绘制信息
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, current_time, (10, 30), font, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        cv2.putText(img, fps_text, (10, 60), font, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
        
        cv2.imshow("screen", img)
        cv2.waitKey(1)