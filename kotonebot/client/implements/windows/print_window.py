# ruff: noqa: E402
"""基于 PrintWindow 的 Windows 后台截图实现。"""

from kotonebot.util import windows_only, require_windows

import ctypes
import ctypes.wintypes as wt
import threading
from typing import TYPE_CHECKING, Literal

import cv2
from cv2.typing import MatLike
import numpy as np

from kotonebot import logging
from kotonebot.errors import WindowsScreenshotError
if TYPE_CHECKING:
    import win32ui
    import win32con
    import win32gui
else:
    win32ui = None
    win32con = None
    win32gui = None

def _load_deps():
    global win32ui, win32con, win32gui
    if win32ui is not None and win32con is not None and win32gui is not None:
        return
    require_windows('"WindowsImpl" implementation')
    import win32ui as _win32ui
    import win32con as _win32con
    import win32gui as _win32gui
    win32ui = _win32ui
    win32con = _win32con
    win32gui = _win32gui

from ...protocol import Screenshotable
from kotonebot.interop.window import WindowQuery, WindowSession
from kotonebot.interop.window.windows import WindowsWindow
if TYPE_CHECKING:
    from ...device import Device

logger = logging.getLogger(__name__)

_GDI_LOCK: threading.Lock = threading.Lock()

PW_CLIENTONLY = 0x1
PW_RENDERFULLCONTENT = 0x2

# TODO: 目前每次截图都会完整创建和销毁 GDI 对象，性能较差，后续可以考虑缓存这些对象以提升性能
# TODO: 需要先支持 Impl 的生命周期管理
def capture_printwindow(hwnd: int) -> MatLike:
    """使用 PrintWindow 截取指定窗口的 Client 区域。

    :param hwnd: 目标窗口句柄。
    :returns: BGR 格式截图。
    :raises WindowsScreenshotError: GDI 资源创建或截取失败时抛出。
    """
    _load_deps()
    # client rect size
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise WindowsScreenshotError(hwnd, width, height, detail='invalid client size')

    hdc: int | None = None
    mfc_dc = None
    mem_dc = None
    bmp = None
    old_obj = None
    # GDI 全程持锁：创建、PrintWindow、取像素、释放必须串行，否则并发下偶发 CreateCompatibleDC failed
    with _GDI_LOCK:
        try:
            hdc = win32gui.GetDC(hwnd)
            if not hdc:
                raise WindowsScreenshotError(hwnd, width, height, detail='GetDC failed')
            # 任一 GDI 调用失败（例如 GDI 句柄耗尽时的 CreateCompatibleDC failed）
            # 都会经由 except 转为 WindowsScreenshotError，finally 负责释放已创建的资源
            try:
                mfc_dc = win32ui.CreateDCFromHandle(hdc)
                mem_dc = mfc_dc.CreateCompatibleDC()
                bmp = win32ui.CreateBitmap()
                bmp.CreateCompatibleBitmap(mfc_dc, width, height)
            except Exception as e:
                logger.error(f'Failed to create GDI objects (hwnd={hwnd}, size={width}x{height}): {e}')
                raise WindowsScreenshotError(hwnd, width, height, detail=str(e), cause=e) from e
            old_obj = mem_dc.SelectObject(bmp)

            flags = PW_CLIENTONLY | PW_RENDERFULLCONTENT
            res = ctypes.windll.user32.PrintWindow(hwnd, mem_dc.GetSafeHdc(), flags)
            if res != 1:
                logger.error(f'PrintWindow failed (hwnd={hwnd}, size={width}x{height}, res={res})')
                raise WindowsScreenshotError(hwnd, width, height, detail=f'PrintWindow failed, res={res}')

            # extract BGRA bits via GetDIBits (pywin32 does not expose BITMAPINFO)
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", wt.DWORD),
                    ("biWidth", wt.LONG),
                    ("biHeight", wt.LONG),
                    ("biPlanes", wt.WORD),
                    ("biBitCount", wt.WORD),
                    ("biCompression", wt.DWORD),
                    ("biSizeImage", wt.DWORD),
                    ("biXPelsPerMeter", wt.LONG),
                    ("biYPelsPerMeter", wt.LONG),
                    ("biClrUsed", wt.DWORD),
                    ("biClrImportant", wt.DWORD),
                ]

            class BITMAPINFO(ctypes.Structure):
                _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wt.DWORD * 3)]

            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = width
            bmi.bmiHeader.biHeight = -height  # top-down
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = win32con.BI_RGB

            buf = bytearray(width * height * 4)
            bits_ok = ctypes.windll.gdi32.GetDIBits(
                mem_dc.GetSafeHdc(),
                bmp.GetHandle(),
                0,
                height,
                ctypes.byref((ctypes.c_ubyte * len(buf)).from_buffer(buf)),
                ctypes.byref(bmi),
                win32con.DIB_RGB_COLORS,
            )
            if bits_ok == 0:
                logger.error(f'GetDIBits failed (hwnd={hwnd}, size={width}x{height})')
                raise WindowsScreenshotError(hwnd, width, height, detail='GetDIBits failed')

            img = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
        except WindowsScreenshotError:
            raise
        except Exception as e:
            logger.error(f'Screenshot failed (hwnd={hwnd}, size={width}x{height}): {e}')
            raise WindowsScreenshotError(hwnd, width, height, detail=str(e), cause=e) from e
        finally:
            # 失败路径也必须释放 GDI 资源，否则句柄耗尽后会持续 CreateCompatibleDC failed
            if mem_dc is not None and old_obj is not None:
                try:
                    mem_dc.SelectObject(old_obj)
                except Exception as e:
                    logger.warning(f'Failed to restore GDI bitmap (hwnd={hwnd}): {e}')
            if bmp is not None:
                try:
                    win32gui.DeleteObject(bmp.GetHandle())
                except Exception as e:
                    logger.warning(f'Failed to delete GDI bitmap (hwnd={hwnd}): {e}')
            if mem_dc is not None:
                try:
                    mem_dc.DeleteDC()
                except Exception as e:
                    logger.warning(f'Failed to delete memory DC (hwnd={hwnd}): {e}')
            if mfc_dc is not None:
                try:
                    mfc_dc.DeleteDC()
                except Exception as e:
                    logger.warning(f'Failed to delete window DC (hwnd={hwnd}): {e}')
            if hdc:
                try:
                    win32gui.ReleaseDC(hwnd, hdc)
                except Exception as e:
                    logger.warning(f'Failed to release DC (hwnd={hwnd}): {e}')


@windows_only('"WindowsImpl" implementation')
class PrintWindowImpl(Screenshotable):
    def __init__(self, device: 'Device', window_query: WindowQuery):
        _load_deps()
        self._window_session = WindowSession(window_query)
        ctypes.windll.user32.SetProcessDPIAware()

    def _window(self) -> WindowsWindow:
        w = self._window_session.get_window()
        if not isinstance(w, WindowsWindow):
            raise TypeError(f"Expected WindowsWindow, got {type(w).__name__}")
        return w

    def __client_rect(self) -> tuple[int, int, int, int]:
        """获取 Client 区域屏幕坐标"""
        hwnd = self._window().hwnd
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
        return client_left, client_top, client_right, client_bottom

    def detect_orientation(self) -> None | Literal['portrait'] | Literal['landscape']:
        rect = self._window().get_bounds()
        if rect is None:
            return None
        if rect.w > rect.h:
            return 'landscape'
        else:
            return 'portrait'

    @property
    def screen_size(self) -> tuple[int, int]:
        left, top, right, bot = self.__client_rect()
        w = right - left
        h = bot - top
        return w, h

    def screenshot(self) -> MatLike:
        window = self._window()
        if window.is_minimized():
            window.restore()
        return capture_printwindow(window.hwnd)

if __name__ == "__main__":
    from kotonebot.interop.window import WindowQuery
    impl = PrintWindowImpl(None, WindowQuery(title_contains="gakumas"))  # type: ignore
    while True:
        img = impl.screenshot()
        cv2.imshow("screenshot", img)
        cv2.waitKey(1)
