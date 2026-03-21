# ruff: noqa: E402
from kotonebot.util import windows_only, require_windows

import ctypes
import ctypes.wintypes as wt
from typing import TYPE_CHECKING, Literal

import cv2
from cv2.typing import MatLike
import numpy as np
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
from kotonebot.interop.win.window import Win32Window
if TYPE_CHECKING:
    from ...device import Device

PW_CLIENTONLY = 0x1
PW_RENDERFULLCONTENT = 0x2

# TODO: 目前每次截图都会完整创建和销毁 GDI 对象，性能较差，后续可以考虑缓存这些对象以提升性能
# TODO: 需要先支持 Impl 的生命周期管理
def capture_printwindow(hwnd: int) -> MatLike:
    _load_deps()
    # client rect size
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width, height = right - left, bottom - top
    if width <= 0 or height <= 0:
        raise RuntimeError("invalid client size")

    hdc = win32gui.GetDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hdc)
    mem_dc = mfc_dc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mfc_dc, width, height)
    mem_dc.SelectObject(bmp)

    flags = PW_CLIENTONLY | PW_RENDERFULLCONTENT
    res = ctypes.windll.user32.PrintWindow(hwnd, mem_dc.GetSafeHdc(), flags)
    if res != 1:
        raise RuntimeError("PrintWindow failed")

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
        raise RuntimeError("GetDIBits failed")

    img = np.frombuffer(buf, dtype=np.uint8).reshape((height, width, 4))
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # cleanup
    win32gui.DeleteObject(bmp.GetHandle())
    mem_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hdc)
    return img


@windows_only('"WindowsImpl" implementation')
class PrintWindowImpl(Screenshotable):
    def __init__(self, device: 'Device', window_title: str):
        _load_deps()
        self.window = Win32Window.require_window('title', window_title)
        ctypes.windll.user32.SetProcessDPIAware()

    def __client_rect(self) -> tuple[int, int, int, int]:
        """获取 Client 区域屏幕坐标"""
        hwnd = self.window.hwnd
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
        return client_left, client_top, client_right, client_bottom

    def detect_orientation(self) -> None | Literal['portrait'] | Literal['landscape']:
        rect = self.window.get_rect()
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
        if self.window.is_minimized():
            self.window.restore()
        return capture_printwindow(self.window.hwnd)

if __name__ == "__main__":
    impl = PrintWindowImpl(None, "gakumas")  # type: ignore
    while True:
        img = impl.screenshot()
        cv2.imshow("screenshot", img)
        cv2.waitKey(1)
