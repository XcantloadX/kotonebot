from ctypes import windll
from typing import Literal
from importlib import resources
from functools import cached_property

import cv2
import win32ui
import win32gui
import numpy as np
from ahk import AHK
from cv2.typing import MatLike

from ..device import Device
from ..protocol import Commandable, Touchable, Screenshotable

class WindowsImpl(Touchable, Screenshotable):
    def __init__(self, device: Device):
        self.__hwnd: int | None = None
        # TODO: 硬编码路径
        self.ahk = AHK(executable_path=str(resources.files('kaa.res.bin') / 'AutoHotkey.exe'))
        self.device = device
        self.emergency = False

        # 设置 DPI aware，否则高缩放显示器上返回的坐标会错误
        windll.user32.SetProcessDPIAware()
        def toggle_emergency():
            self.emergency = True
            self.ahk.msg_box('已启用紧急暂停模式')
        self.ahk.add_hotkey('^F4', toggle_emergency)
        self.ahk.start_hotkeys()
        # 将点击坐标设置为相对 Client
        self.ahk.set_coord_mode('Mouse', 'Client')

    @cached_property
    def scale_ratio(self) -> float:
        """
        缩放比例。截图与模拟输入前都会根据这个比例缩放。
        """
        left, _, right, _ = self.__client_rect()
        w = right - left
        return 720 / w

    @property
    def hwnd(self) -> int:
        if self.__hwnd is None:
            self.__hwnd = win32gui.FindWindow(None, 'gakumas')
            if self.__hwnd is None or self.__hwnd == 0:
                raise RuntimeError('Failed to find window')
        return self.__hwnd

    def __client_rect(self) -> tuple[int, int, int, int]:
        """获取 Client 区域屏幕坐标"""
        hwnd = self.hwnd
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(hwnd)
        client_left, client_top = win32gui.ClientToScreen(hwnd, (client_left, client_top))
        client_right, client_bottom = win32gui.ClientToScreen(hwnd, (client_right, client_bottom))
        return client_left, client_top, client_right, client_bottom

    def __client_to_screen(self, hwnd: int, x: int, y: int) -> tuple[int, int]:
        """将 Client 区域坐标转换为屏幕坐标"""
        return win32gui.ClientToScreen(hwnd, (x, y))

    def __wait_not_emergency(self):
        from time import sleep # TODO: 改为 kotonebot.backend.context.sleep
        while self.emergency:
            sleep(0.2)

    def screenshot(self) -> MatLike:
        if not self.ahk.win_is_active('gakumas'):
            self.ahk.win_activate('gakumas')
        hwnd = self.hwnd

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
        result = windll.gdi32.BitBlt(saveDC.GetSafeHdc(), 0, 0, w, h, mfcDC.GetSafeHdc(), left, top, 0x00CC0020)

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
        # 缩放
        cropped_im = cv2.resize(cropped_im, None, fx=self.scale_ratio, fy=self.scale_ratio)
        return cropped_im

    @property
    def screen_size(self) -> tuple[int, int]:
        # 因为截图和点击的坐标都被缩放了，
        # 因此这里只要返回固定值即可
        if self.device.orientation == 'landscape':
            return 1280, 720
        else:
            return 720, 1280

    def detect_orientation(self) -> None | Literal['portrait'] | Literal['landscape']:
        pos = self.ahk.win_get_position('gakumas')
        if pos is None:
            return None
        w, h = pos.width, pos.height
        if w > h:
            return 'landscape'
        else:
            return 'portrait'

    def click(self, x: int, y: int) -> None:
        self.__wait_not_emergency()
        # x, y = self.__client_to_screen(self.hwnd, x, y)
        # (0, 0) 很可能会点到窗口边框上
        if x == 0:
            x = 2
        if y == 0:
            y = 2
        x, y = int(x / self.scale_ratio), int(y / self.scale_ratio)
        if not self.ahk.win_is_active('gakumas'):
            self.ahk.win_activate('gakumas')
        self.ahk.click(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        self.__wait_not_emergency()
        if not self.ahk.win_is_active('gakumas'):
            self.ahk.win_activate('gakumas')
        x1, y1 = int(x1 / self.scale_ratio), int(y1 / self.scale_ratio)
        x2, y2 = int(x2 / self.scale_ratio), int(y2 / self.scale_ratio)
        # TODO: 这个 speed 的单位是什么？
        self.ahk.mouse_drag(x2, y2, from_position=(x1, y1), coord_mode='Client', speed=10)


if __name__ == '__main__':
    from ..device import Device
    from time import sleep
    device = Device()
    impl = WindowsImpl(device)
    device._screenshot = impl
    device._touch = impl
    device.swipe_scaled(0.5, 0.8, 0.5, 0.2)
    # impl.swipe(0, 100, 0, 0)
    # impl.click(100, 100)
    # while True:
    #     im = impl.screenshot()
    #     cv2.imshow('test', im)
    #     cv2.waitKey(1)
