# ruff: noqa: E402
"""基于 win32 BitBlt + AHK 的 Windows 前台截图实现。"""

from kotonebot.util import windows_only, require_windows

import ctypes
from typing import TYPE_CHECKING, Literal
from importlib import resources
from dataclasses import dataclass

import cv2
import numpy as np
from cv2.typing import MatLike

from kotonebot import logging
from kotonebot.errors import WindowsScreenshotError

from ...device import Device
from ...protocol import Touchable, Screenshotable, Lifecycle, SimpleInputDriver
from ...registration import ImplConfig
from kotonebot.interop.window import WindowQuery, WindowSession
from kotonebot.interop.window.windows import WindowsWindow

if TYPE_CHECKING:
    import win32ui
    import win32gui
    from ahk import AHK, MsgBoxIcon
else:
    win32ui = None
    win32gui = None
    AHK = None
    MsgBoxIcon = None

logger = logging.getLogger(__name__)

def _load_deps():
    global win32ui, win32gui, AHK, MsgBoxIcon
    if win32ui is not None and win32gui is not None and AHK is not None and MsgBoxIcon is not None:
        return
    require_windows('"WindowsImpl" implementation')
    import win32ui as _win32ui
    import win32gui as _win32gui
    from ahk import AHK as _AHK, MsgBoxIcon as _MsgBoxIcon
    win32ui = _win32ui
    win32gui = _win32gui
    AHK = _AHK
    MsgBoxIcon = _MsgBoxIcon

# 1. 定义配置模型
@dataclass
class WindowsImplConfig(ImplConfig):
    window_query: WindowQuery
    ahk_exe_path: str

@windows_only('"WindowsImpl" implementation')
class WindowsImpl(Touchable, Screenshotable, Lifecycle, SimpleInputDriver):
    def __init__(self, device: Device, window_query: WindowQuery, ahk_exe_path: str):
        _load_deps()
        self._window_session = WindowSession(window_query)
        self.ahk = AHK(executable_path=ahk_exe_path)
        self.device = device
        self._started = False

        # 设置 DPI aware，否则高缩放显示器上返回的坐标会错误
        ctypes.windll.user32.SetProcessDPIAware()

    # TODO: 这个应该移动到其他地方去
    def _stop_hotkey(self):
        from kotonebot.backend.context.context import vars
        vars.flow.request_interrupt()
        self.ahk.msg_box('任务已停止。', title='琴音小助手', icon=MsgBoxIcon.EXCLAMATION)

    def _toggle_pause_hotkey(self):
        from kotonebot.backend.context.context import vars
        if vars.flow.is_paused:
            self.ahk.msg_box('任务即将恢复。\n关闭此消息框后将会继续执行', title='琴音小助手', icon=MsgBoxIcon.EXCLAMATION)
            vars.flow.request_resume()
        else:
            vars.flow.request_pause()
            self.ahk.msg_box('任务已暂停。\n关闭此消息框后再按一次快捷键恢复执行。', title='琴音小助手', icon=MsgBoxIcon.EXCLAMATION)

    def start(self) -> None:
        if self._started:
            raise RuntimeError("WindowsImpl lifecycle is already started.")
        self.ahk.add_hotkey('^F4', self._toggle_pause_hotkey) # Ctrl+F4 暂停/恢复
        self.ahk.add_hotkey('^F3', self._stop_hotkey)  # Ctrl+F3 停止
        self.ahk.start_hotkeys()
        # 将点击坐标设置为相对 Client
        self.ahk.set_coord_mode('Mouse', 'Client')
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self.ahk.stop_hotkeys()
        self._started = False

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError("WindowsImpl lifecycle is not started.")

    def _window(self) -> WindowsWindow:
        w = self._window_session.get_window()
        if not isinstance(w, WindowsWindow):
            raise TypeError(f"Expected WindowsWindow, got {type(w).__name__}")
        return w

    def _ahk_window_spec(self) -> str:
        return f"ahk_id {self._window().hwnd}"

    def __client_rect(self) -> tuple[int, int, int, int]:
        """获取 Client 区域屏幕坐标"""
        hwnd = self._window().hwnd
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
        return client_left, client_top, client_right, client_bottom

    def __client_to_screen(self, hwnd: int, x: int, y: int) -> tuple[int, int]:
        """将 Client 区域坐标转换为屏幕坐标"""
        return win32gui.ClientToScreen(hwnd, (x, y))

    def screenshot(self) -> MatLike:
        """截取 Client 区域。

        :returns: RGB 格式截图。
        :raises WindowsScreenshotError: GDI 资源创建或截取失败时抛出。
        """
        self._require_started()
        window_spec = self._ahk_window_spec()
        if not self.ahk.win_is_active(window_spec):
            self.ahk.win_activate(window_spec)
        hwnd = self._window().hwnd

        # 获取整个窗口的坐标
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        w = right - left
        h = bot - top

        # 获取客户区域的坐标
        client_left, client_top, client_right, client_bot = self.__client_rect()

        hwnd_dc: int | None = None
        mfc_dc = None
        save_dc = None
        save_bitmap = None
        old_obj = None
        try:
            # 获取整个屏幕的截图
            hwnd_dc = win32gui.GetWindowDC(0)
            if not hwnd_dc:
                logger.error(f'GetWindowDC failed (hwnd={hwnd}, size={w}x{h})')
                raise WindowsScreenshotError(hwnd, w, h, detail='GetWindowDC failed')
            try:
                mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
                save_dc = mfc_dc.CreateCompatibleDC()
                save_bitmap = win32ui.CreateBitmap()
                save_bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
            except Exception as e:
                logger.error(f'Failed to create GDI objects (hwnd={hwnd}, size={w}x{h}): {e}')
                raise WindowsScreenshotError(hwnd, w, h, detail=str(e), cause=e) from e

            old_obj = save_dc.SelectObject(save_bitmap)

            # 截图整个屏幕
            bitblt_ok = ctypes.windll.gdi32.BitBlt(
                save_dc.GetSafeHdc(), 0, 0, w, h, mfc_dc.GetSafeHdc(), left, top, 0x00CC0020
            )
            if not bitblt_ok:
                logger.error(f'BitBlt failed (hwnd={hwnd}, size={w}x{h})')
                raise WindowsScreenshotError(hwnd, w, h, detail='BitBlt failed')

            # 将截图转换为OpenCV格式
            bmpinfo = save_bitmap.GetInfo()
            bmpstr = save_bitmap.GetBitmapBits(True)
            im = np.frombuffer(bmpstr, dtype=np.uint8)
            im = im.reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

            # 裁剪出客户区域
            cropped_im = im[client_top - top:client_bot - top, client_left - left:client_right - left]
            # 将 RGBA 转换为 RGB
            cropped_im = cv2.cvtColor(cropped_im, cv2.COLOR_RGBA2RGB)
            return cropped_im
        except WindowsScreenshotError:
            raise
        except Exception as e:
            logger.error(f'Screenshot failed (hwnd={hwnd}, size={w}x{h}): {e}')
            raise WindowsScreenshotError(hwnd, w, h, detail=str(e), cause=e) from e
        finally:
            # 失败路径也必须释放 GDI 资源，否则句柄耗尽后会持续 CreateCompatibleDC failed
            if save_dc is not None and old_obj is not None:
                try:
                    save_dc.SelectObject(old_obj)
                except Exception as e:
                    logger.warning(f'Failed to restore GDI bitmap (hwnd={hwnd}): {e}')
            if save_bitmap is not None:
                try:
                    win32gui.DeleteObject(save_bitmap.GetHandle())
                except Exception as e:
                    logger.warning(f'Failed to delete GDI bitmap (hwnd={hwnd}): {e}')
            if save_dc is not None:
                try:
                    save_dc.DeleteDC()
                except Exception as e:
                    logger.warning(f'Failed to delete memory DC (hwnd={hwnd}): {e}')
            if mfc_dc is not None:
                try:
                    mfc_dc.DeleteDC()
                except Exception as e:
                    logger.warning(f'Failed to delete window DC (hwnd={hwnd}): {e}')
            if hwnd_dc:
                try:
                    win32gui.ReleaseDC(0, hwnd_dc)
                except Exception as e:
                    logger.warning(f'Failed to release DC (hwnd={hwnd}): {e}')

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
        # x, y = self.__client_to_screen(self.hwnd, x, y)
        # (0, 0) 很可能会点到窗口边框上
        if x == 0:
            x = 2
        if y == 0:
            y = 2
        window_spec = self._ahk_window_spec()
        if not self.ahk.win_is_active(window_spec):
            self.ahk.win_activate(window_spec)
        self.ahk.click(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        self._require_started()
        window_spec = self._ahk_window_spec()
        if not self.ahk.win_is_active(window_spec):
            self.ahk.win_activate(window_spec)
        # TODO: 这个 speed 的单位是什么？
        self.ahk.mouse_drag(x2, y2, from_position=(x1, y1), coord_mode='Client', speed=10)

if __name__ == '__main__':
    from ...device import Device
    device = Device()
    # 在测试环境中直接使用默认路径
    ahk_path = str(resources.files('kaa.res.bin') / 'AutoHotkey.exe')
    from kotonebot.interop.window import WindowQuery
    impl = WindowsImpl(device, window_query=WindowQuery(title_contains='gakumas'), ahk_exe_path=ahk_path)
    device._screenshot = impl
    device._touch = impl
    device.swipe_scaled(0.5, 0.8, 0.5, 0.2)
    # impl.swipe(0, 100, 0, 0)
    # impl.click(100, 100)
    # while True:
    #     im = impl.screenshot()
    #     cv2.imshow('test', im)
    #     cv2.waitKey(1)
