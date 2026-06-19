# ruff: noqa: E402
from kotonebot.util import windows_only, require_windows

import ctypes
from typing import TYPE_CHECKING, Literal
from dataclasses import dataclass, field

import cv2
import numpy as np
from cv2.typing import MatLike

from ...device import Device
from ...protocol import Touchable, Screenshotable, Lifecycle, SimpleInputDriver
from ...registration import ImplConfig
from kotonebot.interop.window import WindowQuery, WindowSession
from kotonebot.interop.window.windows import WindowsWindow
from kotonebot.interop.win import mouse as win_mouse
from kotonebot.interop.win._mouse import AnimationParams
from kotonebot.primitives import Point

if TYPE_CHECKING:
    import win32ui
    import win32gui
else:
    win32ui = None
    win32gui = None

def _load_deps():
    """WindowsNativeImpl 专用的依赖加载函数，不依赖 `ahk` 包。"""
    global win32ui, win32gui
    if win32ui is not None and win32gui is not None:
        return
    require_windows('"WindowsNativeImpl" implementation')
    import win32ui as _win32ui
    import win32gui as _win32gui
    win32ui = _win32ui
    win32gui = _win32gui

# 1. 定义配置模型
@dataclass
class WindowsNativeImplConfig(ImplConfig):
    window_query: WindowQuery
    avoid_border_click: bool = True
    """点击坐标为 (0, *) 或 (*, 0) 时，是否自动偏移 1~2 像素以避免点到窗口边框。默认开启。"""
    click_animation: AnimationParams = field(default_factory=AnimationParams)
    """点击前移动鼠标到目标位置时使用的动画参数，详见 :class:`~kotonebot.interop.win.AnimationParams`。

    默认为空字典，即瞬间跳转到目标位置（不做动画）。
    """
    swipe_animation: AnimationParams = field(default_factory=AnimationParams)
    """swipe（拖拽）操作默认使用的动画参数，详见 :class:`~kotonebot.interop.win.AnimationParams`。

    若调用 :meth:`WindowsNativeImpl.swipe` 时显式传入了 `duration`，
    则该值会覆盖此处配置的 `duration`/`speed`。
    """

@windows_only('"WindowsNativeImpl" implementation')
class WindowsNativeImpl(Touchable, Screenshotable, Lifecycle, SimpleInputDriver):
    """基于 win32 API 与 `mouse` 库的 Windows 实现，不依赖 AHK。

    与 :class:`~kotonebot.client.implements.windows.windows.WindowsImpl` 相比，
    不提供全局热键（暂停/恢复、停止）与消息框提示功能。
    """
    def __init__(
        self,
        device: Device,
        window_query: WindowQuery,
        *,
        avoid_border_click: bool = True,
        click_animation: AnimationParams | None = None,
        swipe_animation: AnimationParams | None = None,
    ):
        _load_deps()
        self._window_session = WindowSession(window_query)
        self.device = device
        self._started = False
        self.avoid_border_click = avoid_border_click
        self.click_animation: AnimationParams = click_animation or {}
        self.swipe_animation: AnimationParams = swipe_animation or {}

        # 设置 DPI aware，否则高缩放显示器上返回的坐标会错误
        ctypes.windll.user32.SetProcessDPIAware()

    def start(self) -> None:
        if self._started:
            raise RuntimeError("WindowsNativeImpl lifecycle is already started.")
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._started = False

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("WindowsNativeImpl lifecycle is not started.")

    def _window(self) -> WindowsWindow:
        w = self._window_session.get_window()
        if not isinstance(w, WindowsWindow):
            raise TypeError(f"Expected WindowsWindow, got {type(w).__name__}")
        return w

    def _ensure_active(self) -> None:
        """若窗口不是前台窗口，则激活之。"""
        window = self._window()
        if not window.win32_window.is_active():
            window.activate()

    def __client_rect(self) -> tuple[int, int, int, int]:
        """获取 Client 区域屏幕坐标"""
        hwnd = self._window().hwnd
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
        return client_left, client_top, client_right, client_bottom

    def _client_to_screen(self, x: int, y: int) -> tuple[int, int]:
        """将 Client 区域相对坐标转换为屏幕绝对坐标"""
        client_left, client_top, _, _ = self.__client_rect()
        return client_left + x, client_top + y

    def screenshot(self) -> MatLike:
        self._require_started()
        self._ensure_active()
        hwnd = self._window().hwnd

        # TODO: 需要检查下面这些 WinAPI 的返回结果
        # 获取整个窗口的坐标
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bot - top

        # 获取客户区域的坐标
        client_left, client_top, client_right, client_bot = self.__client_rect()

        # 获取整个屏幕的截图
        hwndDC = win32gui.GetWindowDC(0)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)

        saveDC.SelectObject(saveBitMap)

        # 截图整个屏幕
        ctypes.windll.gdi32.BitBlt(saveDC.GetSafeHdc(), 0, 0, w, h, mfcDC.GetSafeHdc(), left, top, 0x00CC0020)

        # 将截图转换为OpenCV格式
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = np.frombuffer(bmpstr, dtype=np.uint8)
        im = im.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

        # 裁剪出客户区域
        cropped_im = im[client_top - top:client_bot - top, client_left - left:client_right - left]

        # 释放资源
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        # 将 RGBA 转换为 RGB
        cropped_im = cv2.cvtColor(cropped_im, cv2.COLOR_RGBA2RGB)
        return cropped_im

    @property
    def screen_size(self) -> tuple[int, int]:
        self._require_started()
        left, top, right, bot = self.__client_rect()
        w = right - left
        h = bot - top
        return w, h

    def detect_orientation(self) -> None | Literal['portrait'] | Literal['landscape']:
        self._require_started()
        bounds = self._window().get_bounds()
        if bounds is None:
            return None
        w, h = bounds.w, bounds.h
        if w > h:
            return 'landscape'
        else:
            return 'portrait'

    def click(self, x: int, y: int) -> None:
        self._require_started()
        # (0, 0) 很可能会点到窗口边框上
        if self.avoid_border_click:
            if x == 0:
                x = 2
            if y == 0:
                y = 2
        self._ensure_active()
        screen_x, screen_y = self._client_to_screen(x, y)
        if self.click_animation:
            target = Point(screen_x, screen_y)
            for p in win_mouse.do_tween(win_mouse.get_pos(), target, self.click_animation):
                win_mouse.set_pos(p)
        else:
            win_mouse.set_pos(screen_x, screen_y)
        win_mouse.click('left')

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        self._require_started()
        self._ensure_active()
        start_x, start_y = self._client_to_screen(x1, y1)
        end_x, end_y = self._client_to_screen(x2, y2)
        params: AnimationParams = AnimationParams(**self.swipe_animation)
        if duration is not None:
            params['duration'] = duration
            params.pop('speed', None)
        win_mouse.drag(Point(start_x, start_y), Point(end_x, end_y), button='left', **params)

if __name__ == '__main__':
    from ...device import Device
    device = Device()
    from kotonebot.interop.window import WindowQuery
    impl = WindowsNativeImpl(device, window_query=WindowQuery(title_contains='gakumas'))
    device._screenshot = impl
    device._touch = impl
    impl.start()
    device.swipe_scaled(0.5, 0.8, 0.5, 0.2)
