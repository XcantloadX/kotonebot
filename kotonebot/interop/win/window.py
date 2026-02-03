from typing import Literal
from typing_extensions import assert_never

import win32gui
import win32con
import win32api

from kotonebot.primitives import Rect

FindWindowMethod = Literal['title']

class Win32Window:
    def __init__(self, hwnd: int) -> None:
        self.hwnd = hwnd

    @staticmethod
    def find_window(method: FindWindowMethod, title: str) -> 'Win32Window | None':
        """查找窗口。

        :param method: 查找依据。
        :param title: 窗口标题
        :return: 若找到窗口则返回 Win32Window 实例，否则返回 None。
        """
        match method:
            case 'title':
                hwnd = win32gui.FindWindow(None, title)
                if hwnd == 0:
                    return None
                return Win32Window(hwnd)
            case _:
                assert_never(method)
    
    @staticmethod
    def require_window(method: FindWindowMethod, title: str) -> 'Win32Window':
        """查找窗口，未找到则抛出异常。
        
        参数同 :ref:`find_window`。
        """
        window = Win32Window.find_window(method, title)
        if window is None:
            raise RuntimeError(f'Window not found: {title}')
        return window

    def get_rect(self) -> Rect:
        """取得窗口范围"""
        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
        return Rect(left, top, right - left, bottom - top)
    
    def get_client_rect(self) -> Rect:
        """取得窗口客户区域范围"""
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        return Rect(left, top, right - left, bottom - top)
    
    def is_active(self) -> bool:
        """检查窗口是否为前台窗口"""
        active_hwnd = win32gui.GetForegroundWindow()
        return active_hwnd == self.hwnd
    
    def is_minimized(self) -> bool:
        """检查窗口是否最小化"""
        return win32gui.IsIconic(self.hwnd) != 0
    
    def restore(self) -> None:
        """还原最小化的窗口"""
        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)

    def set_position(self, x: int, y: int, *, flags: int | None = None) -> None:
        """
        设置窗口位置。
        
        :param flags: SetWindowPos 的 `flags` 参数。默认参数为 SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE。
        """
        if flags is None:
            flags = win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
        win32gui.SetWindowPos(
            self.hwnd, None, x, y, 0, 0,
            flags
        )
    
    def bring_foreground(self) -> None:
        """将窗口置于前台"""
        win32gui.SetForegroundWindow(self.hwnd)

    def send_message(self, msg: int, wparam: int, lparam: int) -> int:
        return win32gui.SendMessage(self.hwnd, msg, wparam, lparam)
    
    def post_message(self, msg: int, wparam: int, lparam: int) -> bool:
        win32gui.PostMessage(self.hwnd, msg, wparam, lparam)
        return win32api.GetLastError() == 0