"""基于 Maa Win32Controller 的 Windows 设备适配实现。"""

import logging
from enum import IntEnum
from typing import Literal

from cv2.typing import MatLike
from typing_extensions import override

from ..protocol import KeyboardDriver, MouseButton, MouseDriver, Screenshotable
from .sync import MaaSyncController

logger = logging.getLogger(__name__)

_DEFAULT_SWIPE_DURATION_MS: int = 500
"""swipe 未指定时长时使用的默认持续时间，单位毫秒。"""


class Win32VirtualKey(IntEnum):
    """常用 Win32 虚拟键码。"""

    BACK = 0x08
    TAB = 0x09
    ENTER = 0x0D
    ESCAPE = 0x1B
    SPACE = 0x20
    END = 0x23
    HOME = 0x24
    LEFT = 0x25
    UP = 0x26
    RIGHT = 0x27
    DOWN = 0x28
    DELETE = 0x2E


def _resolve_win32_key(key: str) -> int:
    """将按键名称解析为 Win32 虚拟键码。

    :param key: 按键名称（不区分大小写），或单个 ASCII 字符，或纯数字键码字符串。
    :returns: Win32 虚拟键码。
    :raises ValueError: 按键名称为空或不受支持时抛出。
    """
    text = key.strip()
    if not text:
        raise ValueError('Key name must not be empty.')
    if text.isdigit():
        return int(text)
    if len(text) == 1:
        code = ord(text.upper())
        if 0x30 <= code <= 0x5A:
            return code
        raise ValueError(f'Unsupported single-character key: {key!r}. Supported: 0-9/A-Z.')
    try:
        return int(Win32VirtualKey[text.upper()])
    except KeyError as e:
        valid = ', '.join(sorted(Win32VirtualKey.__members__))
        raise ValueError(f'Unsupported Win32 key name: {key!r}. Supported names: {valid}.') from e


def _contact_for_button(button: MouseButton | None) -> int:
    """将鼠标按键映射为 Maa Win32 触点编号。

    Maa Win32 控制器约定：0 为左键，1 为右键，2 为中键。

    :param button: 鼠标按键，为 None 时视为左键。
    :returns: 触点编号。
    :raises ValueError: 按键取值非法时抛出。
    """
    if button is None or button == 'left':
        return 0
    if button == 'right':
        return 1
    if button == 'middle':
        return 2
    raise ValueError(f'Unsupported mouse button: {button!r}. Supported: left/right/middle.')


class MaaWin32Adapter(Screenshotable, MouseDriver, KeyboardDriver):
    """基于 Maa Win32Controller 的 Windows 实现。

    鼠标按下/抬起按 Maa 约定映射为触点操作（左 0/右 1/中 2）；
    ``button_down`` 之前必须先调用 ``move`` 确定光标位置。

    :param sync: Maa 同步控制器。
    :param hwnd: 目标窗口句柄，必须为正整数。
    """

    def __init__(self, sync: MaaSyncController, hwnd: int) -> None:
        if sync is None:
            raise ValueError('sync must not be None.')
        if isinstance(hwnd, bool) or not isinstance(hwnd, int) or hwnd <= 0:
            raise ValueError(f'hwnd must be a positive integer, got {hwnd!r}.')
        self._sync: MaaSyncController = sync
        self.hwnd: int = hwnd
        """目标窗口句柄。"""
        self._cursor: tuple[int, int] | None = None
        """最近一次 move 记录的光标位置，未移动过时为 None。"""
        self._pressed_contact: int | None = None
        """当前按下的触点编号，未按下时为 None。"""

    @property
    @override
    def screen_size(self) -> tuple[int, int]:
        """实时截图的宽高，格式为 ``(width, height)``，每次调用都重新截图查询。"""
        frame = self._sync.screencap()
        height, width = int(frame.shape[0]), int(frame.shape[1])
        if width <= 0 or height <= 0:
            raise ValueError(f'Invalid Maa frame size: width={width} height={height}.')
        logger.debug('Maa Win32 frame size: width=%d height=%d.', width, height)
        return (width, height)

    @override
    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        """按实时截图宽高比判断方向。

        :returns: 宽大于高时为 ``'landscape'``，否则为 ``'portrait'``。
        """
        width, height = self.screen_size
        if width > height:
            return 'landscape'
        return 'portrait'

    @override
    def screenshot(self) -> MatLike:
        """截取目标窗口。

        :returns: BGR 格式的截图数据。
        """
        return self._sync.screencap()

    def _require_cursor(self) -> tuple[int, int]:
        """返回已记录的光标位置，未移动过时抛错。

        :returns: 光标位置。
        :raises ValueError: 未调用过 ``move`` 时抛出。
        """
        if self._cursor is None:
            raise ValueError(
                'MaaWin32Adapter.button_down requires move(x, y) to be called first '
                'to set the cursor position.'
            )
        return self._cursor

    @override
    def move(self, x: int, y: int) -> None:
        """将鼠标移动到窗口坐标 (x, y)。

        按下状态下调用时按拖拽语义转发，保持当前按下的触点编号。

        :param x: 横坐标。
        :param y: 纵坐标。
        """
        contact = self._pressed_contact if self._pressed_contact is not None else 0
        self._sync.touch_move(x, y, contact)
        self._cursor = (x, y)

    @override
    def button_down(self, button: MouseButton | None = None) -> None:
        """在当前光标位置按下指定按键。

        :param button: 鼠标按键，默认为左键。
        """
        contact = _contact_for_button(button)
        x, y = self._require_cursor()
        self._sync.touch_down(x, y, contact)
        self._pressed_contact = contact

    @override
    def button_up(self, button: MouseButton | None = None) -> None:
        """在当前光标位置抬起指定按键。

        :param button: 鼠标按键，默认为左键。
        """
        contact = _contact_for_button(button)
        self._sync.touch_up(contact)
        if self._pressed_contact == contact:
            self._pressed_contact = None

    @override
    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        """在当前光标位置滚动。

        :param dx: 水平滚动量。
        :param dy: 垂直滚动量。
        """
        self._sync.scroll(dx, dy)

    def click(self, x: int, y: int) -> None:
        """在窗口坐标 (x, y) 处执行左键单击。

        :param x: 横坐标。
        :param y: 纵坐标。
        """
        self._sync.click(x, y)
        self._cursor = (x, y)

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None
    ) -> None:
        """从窗口坐标 (x1, y1) 拖拽到 (x2, y2)。

        :param x1: 起点横坐标。
        :param y1: 起点纵坐标。
        :param x2: 终点横坐标。
        :param y2: 终点纵坐标。
        :param duration: 拖拽时长，单位秒；为 None 时使用默认时长。
        """
        duration_ms = _DEFAULT_SWIPE_DURATION_MS if duration is None else int(duration * 1000)
        self._sync.swipe(x1, y1, x2, y2, duration_ms)
        self._cursor = (x2, y2)

    @override
    def key_down(self, key: str) -> None:
        """按下指定按键。

        :param key: 按键名称，见 :class:`Win32VirtualKey`。
        """
        self._sync.key_down(_resolve_win32_key(key))

    @override
    def key_up(self, key: str) -> None:
        """抬起指定按键。

        :param key: 按键名称，见 :class:`Win32VirtualKey`。
        """
        self._sync.key_up(_resolve_win32_key(key))

    @override
    def type_text(self, text: str) -> None:
        """输入一段文本。

        :param text: 待输入的文本。
        """
        self._sync.input_text(text)
