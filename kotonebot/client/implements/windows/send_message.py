# ruff: noqa: E402
from kotonebot.util import require_windows
require_windows('"WindowsImpl" implementation')

import time
from time import sleep
from typing_extensions import assert_never
from typing import Optional, Literal, TYPE_CHECKING

import win32gui
import win32con

from ...protocol import Touchable, SimpleInputDriver
from kotonebot.interop.win.window import Win32Window
if TYPE_CHECKING:
    from ...device import Device

MouseButton = Literal['left', 'right', 'middle']

def _make_lparam(x: int, y: int) -> int:
    """
    创建 LPARAM 参数，打包 x,y 坐标
    
    :param x: X 坐标
    :param y: Y 坐标
    :returns: 打包的 LPARAM 值
    """
    return (y << 16) | (x & 0xFFFF)


def _make_wparam(button_data: int, wheel_delta: int = 0) -> int:
    """
    创建 WPARAM 参数，用于滚轮消息
    
    :param button_data: 按钮数据
    :param wheel_delta: 滚轮增量
    :returns: 打包的 WPARAM 值
    """
    return (wheel_delta << 16) | (button_data & 0xFFFF)

def _wait_cursor_idle(max_speed: float = 50):
    if max_speed <= 0:
        return
    sample_interval = 0.05
    prev_pos = win32gui.GetCursorPos()
    prev_t = time.monotonic()

    while True:
        sleep(sample_interval)
        cur_pos = win32gui.GetCursorPos()
        cur_t = time.monotonic()

        dx = cur_pos[0] - prev_pos[0]
        dy = cur_pos[1] - prev_pos[1]
        dist = (dx * dx + dy * dy) ** 0.5
        dt = cur_t - prev_t
        speed = dist / dt if dt > 0 else float('inf')
        if speed <= max_speed:
            return

        prev_pos = cur_pos
        prev_t = cur_t

class SendMessageWrapper:
    def __init__(self, window: Win32Window, wait_cursor_idle: float = -1):
        self.window = window
        self.last_pos = (0, 0)
        self.last_pos_set = False
        if wait_cursor_idle == -1:
            self.wait_cursor_idle_speed = 50  # 默认值
        else:
            self.wait_cursor_idle_speed = wait_cursor_idle

    @property
    def hwnd(self) -> int:
        return self.window.hwnd

    def _send_activate(self):
        self.window.post_message(win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
    
    def _align_window(self, target_client_x: int, target_client_y: int) -> bool:
        """
        移动窗口，使得目标客户区坐标对齐到指定的光标位置。
        如果提供 `cursor_pos` 则使用该屏幕坐标（例如预测值），否则使用真实光标位置。
        """
        window_rect = self.window.get_rect()
        if not window_rect:
            return False
        
        cursor_x, cursor_y = win32gui.GetCursorPos()
        # 计算客户区偏移
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(self.hwnd)
        client_screen_left, client_screen_top = win32gui.ClientToScreen(self.hwnd, (client_left, client_top))
        offset_x = client_screen_left - window_rect.x1
        offset_y = client_screen_top - window_rect.y1

        new_window_x = cursor_x - target_client_x - offset_x
        new_window_y = cursor_y - target_client_y - offset_y

        win32gui.SetWindowPos(
            self.hwnd,
            None,
            new_window_x,
            new_window_y,
            window_rect.w,
            window_rect.h,
            win32con.SWP_NOREDRAW | win32con.SWP_NOACTIVATE |
            win32con.SWP_NOZORDER | win32con.SWP_NOCOPYBITS |
            win32con.SWP_NOSENDCHANGING | win32con.SWP_NOOWNERZORDER
        )

        return True
    
    def _send_mouse_button(self, x: int, y: int, button: MouseButton, down: bool) -> bool:
        if down:
            match button:
                case 'left':
                    msg = win32con.WM_LBUTTONDOWN
                    w_param = win32con.MK_LBUTTON
                case 'right':
                    msg = win32con.WM_RBUTTONDOWN
                    w_param = win32con.MK_RBUTTON
                case 'middle':
                    msg = win32con.WM_MBUTTONDOWN
                    w_param = win32con.MK_MBUTTON
                case _:
                    assert_never("Unknown mouse button")
        else:
            match button:
                case 'left':
                    msg = win32con.WM_LBUTTONUP
                    w_param = 0
                case 'right':
                    msg = win32con.WM_RBUTTONUP
                    w_param = 0
                case 'middle':
                    msg = win32con.WM_MBUTTONUP
                    w_param = 0
                case _:
                    assert_never("Unknown mouse button")
        
        l_param = _make_lparam(x, y)
        return self.window.post_message(msg, w_param, l_param)

    def _send_mouse_move(self, x: int, y: int, button: Optional[MouseButton] = None) -> bool:
        """
        发送鼠标移动消息，支持在按键按下时携带对应的 wParam 标志（例如拖拽时带 MK_LBUTTON）。
        """

        if button == 'left':
            w_param = win32con.MK_LBUTTON
        elif button == 'right':
            w_param = win32con.MK_RBUTTON
        elif button == 'middle':
            w_param = win32con.MK_MBUTTON
        else:
            w_param = 0

        l_param = _make_lparam(x, y)
        return self.window.post_message(win32con.WM_MOUSEMOVE, w_param, l_param)

    def mouse_down(self, x: int, y: int, button: MouseButton) -> bool:
        """
        发送鼠标按下消息
        button: 0=左键, 1=右键, 2=中键
        
        :param x: X 坐标
        :param y: Y 坐标
        :param button: 按钮类型，0=左键, 1=右键, 2=中键
        :returns: 操作是否成功
        """
        self._send_activate()
        self._align_window(x, y)
        return self._send_mouse_button(x, y, button, down=True)
    
    def mouse_up(self, x: int, y: int, button: MouseButton) -> bool:
        """
        发送鼠标释放消息
        button: 0=左键, 1=右键, 2=中键
        
        :param x: X 坐标
        :param y: Y 坐标
        :param button: 按钮类型，0=左键, 1=右键, 2=中键
        :returns: 操作是否成功
        """
        self._send_activate()
        self._align_window(x, y)
        return self._send_mouse_button(x, y, button, down=False)
    
    def click(self, x: int, y: int, *, button: MouseButton = 'left') -> bool:
        """
        发送点击事件。
        
        :param x: X 坐标
        :param y: Y 坐标
        :param button: 按钮类型，0=左键, 1=右键, 2=中键
        :returns: 操作是否成功
        """
        # 为避免在一次点击操作中重复激活 -> 先激活一次，然后在 down/up 中禁用额外激活
        self._send_activate()
        _wait_cursor_idle(self.wait_cursor_idle_speed)
        self._align_window(x, y)
        if self._send_mouse_button(x, y, button, down=True):
            return self._send_mouse_button(x, y, button, down=False)
        return False
    
    def keyboard_down(self, key_code: int) -> bool:
        """
        发送键盘按下消息
        
        :param key_code: 虚拟键码，例如 win32con.VK_RETURN 等
        :returns: 操作是否成功
        """
        # 发送激活消息
        self._send_activate()
        
        # 发送 WM_KEYDOWN 消息
        result = self.window.post_message(win32con.WM_KEYDOWN, key_code, 0)
        return result
    
    def keyboard_up(self, key_code: int) -> bool:
        """
        发送键盘释放消息
        
        :param key_code: 虚拟键码，例如 win32con.VK_RETURN 等
        :returns: 操作是否成功
        """
        # 发送激活消息
        self._send_activate()
        return self.window.post_message(win32con.WM_KEYUP, key_code, 0)

    def drag(
        self, 
        x1: int, y1: int, 
        x2: int, y2: int,
        *,
        button: MouseButton = 'left',
        duration: float | None = None
    ) -> bool:
        """
        从指定点拖拽到指定点。

        :param x1: 起始点 X 坐标，相对于客户区。
        :param y1: 起始点 Y 坐标，相对于客户区。
        :param x2: 结束点 X 坐标，相对于客户区。
        :param y2: 结束点 Y 坐标，相对于客户区。
        :param button: 按钮类型，'left'、'right'、'middle'。
        :returns: 操作是否成功
        """
        if duration is None:
            duration = 0.5

        self._send_activate()
        # 将窗口对齐到起点，确保起始客户区坐标与当前光标对齐
        self._align_window(x1, y1)

        # 发送按下
        if not self._send_mouse_button(x1, y1, button, down=True):
            return False

        # 如果 duration 为 0 或负数，直接跳到结束点并释放
        if not duration or duration <= 0:
            # 最后对齐到结束点以保证位置精确
            self._align_window(x2, y2)
            return self._send_mouse_button(x2, y2, button, down=False)

        # 分段发送移动事件，避免直接跳到结束点
        # 使用 60Hz 作为默认帧率，至少 1 步
        fps = 60
        steps = max(1, int(duration * fps))
        interval = duration / steps - (13 / 1000)  # 减去约 13ms 的消息处理时间

        dx = x2 - x1
        dy = y2 - y1

        # 从 1 到 steps（包含终点）进行插值并发送 WM_MOUSEMOVE
        for i in range(1, steps + 1):
            t = i / steps
            xi = int(x1 + dx * t)
            yi = int(y1 + dy * t)
            # 发送移动事件，保留当前按键状态
            self._send_mouse_move(xi, yi, button=button)
            self._align_window(xi, yi)
            if interval > 0:
                sleep(interval)

        # 对齐到结束点并发送释放
        self._align_window(x2, y2)
        return self._send_mouse_button(x2, y2, button, down=False)

    def drag_by(
        self,
        x: int, y: int,
        dx: int, dy: int,
        *,
        button: MouseButton = 'left',
        duration: float | None = None
    ) -> bool:
        end_x = x + dx
        end_y = y + dy
        return self.drag(x, y, end_x, end_y, button=button, duration=duration)

class SendMessageImpl(Touchable, SimpleInputDriver):
    def __init__(self, device: 'Device', window_title: str, *, wait_cursor_idle: float = -1) -> None:
        self.device = device
        window = Win32Window.require_window('title', window_title)
        self.wrapper = SendMessageWrapper(window, wait_cursor_idle)

    def click(self, x: int, y: int) -> None:
        self.wrapper.click(x, y, button='left')
    
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        ret = self.wrapper.drag(x1, y1, x2, y2, button='left', duration=duration)
        if not ret:
            raise RuntimeError('Swipe operation failed')
        

if __name__ == '__main__':
    # impl = SendMessageImpl(None, window_title='gakumas') # type: ignore
    # impl.click(0, 0)

    while True:
        _wait_cursor_idle()
        print("Cursor idle detected")
