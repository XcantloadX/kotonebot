import socket
import struct
import threading
from typing import Callable

from ...protocol import MouseButton

CONTROL_MSG_INJECT_KEYCODE = 0
CONTROL_MSG_INJECT_TEXT = 1
CONTROL_MSG_INJECT_TOUCH_EVENT = 2
CONTROL_MSG_INJECT_SCROLL_EVENT = 3
CONTROL_MSG_START_APP = 16

ACTION_DOWN = 0
ACTION_UP = 1
ACTION_MOVE = 2
ACTION_HOVER_MOVE = 7

BUTTON_PRIMARY = 1
BUTTON_SECONDARY = 1 << 1
BUTTON_TERTIARY = 1 << 2

META_SHIFT_ON = 0x00000001

SCRCPY_POINTER_ID_MOUSE = (1 << 64) - 1
SCRCPY_POINTER_ID_VIRTUAL_FINGER = (1 << 64) - 3

ANDROID_KEYCODES = {
    'home': 3,
    'back': 4,
    'tab': 61,
    'space': 62,
    'enter': 66,
    'backspace': 67,
    'pageup': 92,
    'pagedown': 93,
    'esc': 111,
    'delete': 112,
    'ctrl': 113,
    'ctrl_left': 113,
    'ctrl_right': 114,
    'shift': 59,
    'shift_left': 59,
    'shift_right': 60,
    'alt': 57,
    'alt_left': 57,
    'alt_right': 58,
    'up': 19,
    'down': 20,
    'left': 21,
    'right': 22,
    'end': 123,
    'meta': 117,
    'meta_left': 117,
    'meta_right': 118,
}
ANDROID_KEYCODES.update({chr(ord('a') + i): 29 + i for i in range(26)})
ANDROID_KEYCODES.update({str(i): 7 + i for i in range(10)})
ANDROID_KEYCODES.update(
    {
        ',': 55,
        '.': 56,
        '-': 69,
        '=': 70,
        '[': 71,
        ']': 72,
        '\\': 73,
        ';': 74,
        "'": 75,
        '/': 76,
        '@': 77,
        '+': 81,
        '`': 68,
    }
)


class ScrcpyControlChannel:
    """负责向 scrcpy server 发送控制消息。"""

    def __init__(self, sock: socket.socket, size_provider: Callable[[], tuple[int, int] | None]) -> None:
        self._sock = sock
        self._size_provider = size_provider
        self._lock = threading.Lock()
        self._mouse_position: tuple[int, int] | None = None
        self._mouse_buttons = 0

    def close(self) -> None:
        """关闭控制通道。"""
        self._sock.close()

    def send_touch_down(self, x: int, y: int, *, contact_id: int = 0) -> None:
        """发送触摸按下事件。"""
        self._send_touch_packet(ACTION_DOWN, x, y, pointer_id=self._touch_pointer_id(contact_id), pressure=1.0)

    def send_touch_move(self, x: int, y: int, *, contact_id: int = 0) -> None:
        """发送触摸移动事件。"""
        self._send_touch_packet(ACTION_MOVE, x, y, pointer_id=self._touch_pointer_id(contact_id), pressure=1.0)

    def send_touch_up(self, x: int, y: int, *, contact_id: int = 0) -> None:
        """发送触摸抬起事件。"""
        self._send_touch_packet(ACTION_UP, x, y, pointer_id=self._touch_pointer_id(contact_id), pressure=0.0)

    def move(self, x: int, y: int) -> None:
        """移动鼠标指针。"""
        self._mouse_position = (x, y)
        action = ACTION_MOVE if self._mouse_buttons else ACTION_HOVER_MOVE
        self._send_touch_packet(
            action,
            x,
            y,
            pointer_id=SCRCPY_POINTER_ID_MOUSE,
            pressure=1.0,
            buttons=self._mouse_buttons,
        )

    def button_down(self, button: MouseButton | None = None) -> None:
        """按下鼠标按键。"""
        x, y = self._mouse_position_or_center()
        button_mask = self._button_mask(button)
        self._mouse_position = (x, y)
        self._mouse_buttons |= button_mask
        self._send_touch_packet(
            ACTION_DOWN,
            x,
            y,
            pointer_id=SCRCPY_POINTER_ID_MOUSE,
            pressure=1.0,
            action_button=button_mask,
            buttons=self._mouse_buttons,
        )

    def button_up(self, button: MouseButton | None = None) -> None:
        """释放鼠标按键。"""
        x, y = self._mouse_position_or_center()
        button_mask = self._button_mask(button)
        self._mouse_buttons &= ~button_mask
        self._mouse_position = (x, y)
        self._send_touch_packet(
            ACTION_UP,
            x,
            y,
            pointer_id=SCRCPY_POINTER_ID_MOUSE,
            pressure=0.0,
            action_button=button_mask,
            buttons=self._mouse_buttons,
        )

    def scroll(self, *, dx: int = 0, dy: int = 0) -> None:
        """发送鼠标滚轮事件。"""
        x, y = self._mouse_position_or_center()
        px, py, width, height = self._position_payload(x, y)
        payload = struct.pack(
            '>BiiHHhhI',
            CONTROL_MSG_INJECT_SCROLL_EVENT,
            px,
            py,
            width,
            height,
            self._encode_scroll_value(dx),
            self._encode_scroll_value(dy),
            self._mouse_buttons,
        )
        self._send(payload)

    def key_down(self, key: str) -> None:
        """发送按键按下事件。"""
        keycode, metastate = self._resolve_key(key)
        self._send(struct.pack('>BBiii', CONTROL_MSG_INJECT_KEYCODE, ACTION_DOWN, keycode, 0, metastate))

    def key_up(self, key: str) -> None:
        """发送按键抬起事件。"""
        keycode, metastate = self._resolve_key(key)
        self._send(struct.pack('>BBiii', CONTROL_MSG_INJECT_KEYCODE, ACTION_UP, keycode, 0, metastate))

    def type_text(self, text: str) -> None:
        """输入一段文本。"""
        data = text.encode('utf-8')
        if len(data) > 300:
            raise ValueError('scrcpy inject text is limited to 300 UTF-8 bytes')
        self._send(struct.pack('>BI', CONTROL_MSG_INJECT_TEXT, len(data)) + data)

    def start_app(self, name: str) -> None:
        """启动指定应用包。"""
        data = name.encode('utf-8')
        if len(data) > 0xFF:
            raise ValueError('virtual_display.launch_package is too long for scrcpy start-app message')
        self._send(struct.pack('>BB', CONTROL_MSG_START_APP, len(data)) + data)

    def _send_touch_packet(
        self,
        action: int,
        x: int,
        y: int,
        *,
        pointer_id: int,
        pressure: float,
        action_button: int = 0,
        buttons: int = 0,
    ) -> None:
        px, py, width, height = self._position_payload(x, y)
        pressure_u16 = min(max(int(round(pressure * 0xFFFF)), 0), 0xFFFF)
        payload = struct.pack(
            '>BBQiiHHHII',
            CONTROL_MSG_INJECT_TOUCH_EVENT,
            action,
            pointer_id,
            px,
            py,
            width,
            height,
            pressure_u16,
            action_button,
            buttons,
        )
        self._send(payload)

    def _send(self, payload: bytes) -> None:
        with self._lock:
            self._sock.sendall(payload)

    def _touch_pointer_id(self, contact_id: int) -> int:
        if contact_id < 0:
            raise ValueError('scrcpy contact_id must be non-negative')
        if contact_id >= SCRCPY_POINTER_ID_VIRTUAL_FINGER:
            raise ValueError('scrcpy contact_id collides with reserved pointer IDs')
        return contact_id

    def _position_payload(self, x: int, y: int) -> tuple[int, int, int, int]:
        size = self._size_provider()
        if size is None:
            raise RuntimeError('Scrcpy video size is not available yet')
        width, height = size
        x = min(max(int(round(x)), 0), width - 1)
        y = min(max(int(round(y)), 0), height - 1)
        return x, y, width, height

    def _mouse_position_or_center(self) -> tuple[int, int]:
        if self._mouse_position is not None:
            return self._mouse_position
        size = self._size_provider()
        if size is None:
            raise RuntimeError('Scrcpy video size is not available yet')
        width, height = size
        return width // 2, height // 2

    def _button_mask(self, button: MouseButton | None) -> int:
        if button in (None, 'left'):
            return BUTTON_PRIMARY
        if button == 'right':
            return BUTTON_SECONDARY
        if button == 'middle':
            return BUTTON_TERTIARY
        raise ValueError(f'Unsupported mouse button: {button}')

    def _encode_scroll_value(self, value: int) -> int:
        clamped = max(-16.0, min(16.0, float(value)))
        if clamped <= -16.0:
            return -0x8000
        if clamped >= 16.0:
            return 0x7FFF
        if clamped < 0:
            return int(round(clamped / 16.0 * 0x8000))
        return int(round(clamped / 16.0 * 0x7FFF))

    def _resolve_key(self, key: str) -> tuple[int, int]:
        if not key:
            raise ValueError('key must not be empty')
        if len(key) == 1:
            if key.isupper() and key.lower() in ANDROID_KEYCODES:
                return ANDROID_KEYCODES[key.lower()], META_SHIFT_ON
            if key in ANDROID_KEYCODES:
                return ANDROID_KEYCODES[key], 0
            if key.lower() in ANDROID_KEYCODES:
                return ANDROID_KEYCODES[key.lower()], 0
        normalized = key.lower()
        if normalized in ANDROID_KEYCODES:
            return ANDROID_KEYCODES[normalized], 0
        raise ValueError(f'Unsupported Android key for scrcpy: {key}')
