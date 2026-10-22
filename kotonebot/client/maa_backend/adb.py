"""基于 Maa AdbController 的 Android 设备适配实现。"""

import logging
from enum import IntEnum
from typing import TYPE_CHECKING, Literal

from cv2.typing import MatLike
from typing_extensions import override

from ..protocol import AndroidCommandable, KeyboardDriver, Screenshotable, TouchDriver
from .sync import MaaSyncController

if TYPE_CHECKING:
    from adbutils._device import AdbDevice as AdbUtilsDevice

logger = logging.getLogger(__name__)

_DEFAULT_SWIPE_DURATION_MS: int = 500
"""swipe 未指定时长时使用的默认持续时间，单位毫秒。"""


class AndroidKeycode(IntEnum):
    """常用 Android 键码。"""

    BACK = 4
    HOME = 3
    MENU = 82
    APP_SWITCH = 187
    ENTER = 66
    ESCAPE = 111
    TAB = 61
    SPACE = 62
    DEL = 67
    DPAD_UP = 19
    DPAD_DOWN = 20
    DPAD_LEFT = 21
    DPAD_RIGHT = 22
    DPAD_CENTER = 23
    VOLUME_UP = 24
    VOLUME_DOWN = 25
    POWER = 26
    SLEEP = 223
    WAKEUP = 224
    SEARCH = 84


def _resolve_android_key(key: str) -> int:
    """将按键名称解析为 Android 键码。

    :param key: 按键名称（不区分大小写），或纯数字键码字符串。
    :returns: Android 键码。
    :raises ValueError: 按键名称为空或不受支持时抛出。
    """
    text = key.strip()
    if not text:
        raise ValueError('Key name must not be empty.')
    if text.isdigit():
        return int(text)
    try:
        return int(AndroidKeycode[text.upper()])
    except KeyError as e:
        valid = ', '.join(sorted(AndroidKeycode.__members__))
        raise ValueError(f'Unsupported Android key name: {key!r}. Supported names: {valid}.') from e


class MaaAdbAdapter(Screenshotable, TouchDriver, KeyboardDriver, AndroidCommandable):
    """基于 Maa AdbController 的 Android 实现。

    截图、触控、键盘与 ADB 命令均经由 :class:`MaaSyncController`
    转发给 Maa；``display_id`` 必须为 None，因为 Maa 无法处理多屏。

    :param sync: Maa 同步控制器。
    :param adb_connection: adbutils 连接，用于 ``install_apk``，不允许为 None。
    :param display_id: 必须为 None，非 None 直接抛错。
    """

    max_contacts: int = 10
    """Maa ADB 多点触控上限。Maa 侧 post_touch_down(x, y, contact) 原生接受触点编号，
    实际生效取决于 Maa 内核协商到的输入法（Minitouch/MaaTouch 支持多点，
    AdbInput 仅单点）。超出上限直接抛错，不静默截断。"""

    MAX_CONTACTS: int = 10
    """触点编号合法上界（contact_id/pointer_id 必须小于此值）。"""

    def __init__(
        self,
        sync: MaaSyncController,
        adb_connection: 'AdbUtilsDevice',
        display_id: int | None = None,
    ) -> None:
        if sync is None:
            raise ValueError('sync must not be None.')
        if adb_connection is None:
            raise ValueError('adb_connection must not be None.')
        if display_id is not None:
            raise ValueError(
                f'Maa AdbController does not support multiple displays (display_id={display_id}), '
                'use the default single display (display_id=None).'
            )
        self._sync: MaaSyncController = sync
        self.adb_connection: 'AdbUtilsDevice' = adb_connection
        """adbutils 连接。"""

    @property
    @override
    def screen_size(self) -> tuple[int, int]:
        """实时截图的宽高，格式为 ``(width, height)``，每次调用都重新截图查询。"""
        frame = self._sync.screencap()
        height, width = int(frame.shape[0]), int(frame.shape[1])
        if width <= 0 or height <= 0:
            raise ValueError(f'Invalid Maa frame size: width={width} height={height}.')
        logger.debug('Maa ADB frame size: width=%d height=%d.', width, height)
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
        """截取当前屏幕。

        :returns: BGR 格式的截图数据。
        """
        return self._sync.screencap()

    @staticmethod
    def _validate_contact(contact_id: int) -> None:
        """校验触点编号，越界直接失败。

        :param contact_id: 触点编号。
        :raises ValueError: 编号越界时。
        """
        if contact_id < 0 or contact_id >= MaaAdbAdapter.MAX_CONTACTS:
            raise ValueError(
                f'contact_id 越界：要求 0 <= id < {MaaAdbAdapter.MAX_CONTACTS}，实际 {contact_id}。'
            )

    @override
    def touch_down(self, x: int, y: int, contact_id: int = 0) -> None:
        """在指定坐标按下触点。

        :param x: 横坐标。
        :param y: 纵坐标。
        :param contact_id: 触点编号。
        """
        self._validate_contact(contact_id)
        self._sync.touch_down(x, y, contact_id)

    @override
    def touch_move(self, x: int, y: int, contact_id: int = 0) -> None:
        """移动触点到指定坐标。

        :param x: 横坐标。
        :param y: 纵坐标。
        :param contact_id: 触点编号。
        """
        self._validate_contact(contact_id)
        self._sync.touch_move(x, y, contact_id)

    @override
    def touch_up(self, x: int, y: int, contact_id: int = 0) -> None:
        """抬起触点。

        Maa 抬起操作仅按触点编号生效，坐标参数会被忽略（协议要求保留）。

        :param x: 横坐标（会被忽略）。
        :param y: 纵坐标（会被忽略）。
        :param contact_id: 触点编号。
        """
        self._validate_contact(contact_id)
        self._sync.touch_up(contact_id)

    def multi_touch_down(self, x: int, y: int, pointer_id: int) -> None:
        """以指定的 pointer_id 按下坐标 (x, y)。

        与 nemu_ipc/scrcpy 的多点语义对齐：pointer_id 从 0 起编号，
        直接映射为 Maa 触点编号。

        :param x: 横坐标。
        :param y: 纵坐标。
        :param pointer_id: 指针编号。
        """
        self._validate_contact(pointer_id)
        self._sync.touch_down(x, y, pointer_id)

    def multi_touch_up(self, x: int, y: int, pointer_id: int) -> None:
        """抬起指定 pointer_id 的触摸点。

        :param x: 横坐标（Maa 抬起时忽略）。
        :param y: 纵坐标（Maa 抬起时忽略）。
        :param pointer_id: 指针编号。
        """
        self._validate_contact(pointer_id)
        self._sync.touch_up(pointer_id)

    def click(self, x: int, y: int) -> None:
        """在指定坐标执行点击。

        :param x: 横坐标。
        :param y: 纵坐标。
        """
        self._sync.click(x, y)

    def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None
    ) -> None:
        """从起点滑动到终点。

        :param x1: 起点横坐标。
        :param y1: 起点纵坐标。
        :param x2: 终点横坐标。
        :param y2: 终点纵坐标。
        :param duration: 滑动时长，单位秒；为 None 时使用默认时长。
        """
        duration_ms = _DEFAULT_SWIPE_DURATION_MS if duration is None else int(duration * 1000)
        self._sync.swipe(x1, y1, x2, y2, duration_ms)

    @override
    def key_down(self, key: str) -> None:
        """按下指定按键。

        :param key: 按键名称，见 :class:`AndroidKeycode`。
        """
        self._sync.key_down(_resolve_android_key(key))

    @override
    def key_up(self, key: str) -> None:
        """抬起指定按键。

        :param key: 按键名称，见 :class:`AndroidKeycode`。
        """
        self._sync.key_up(_resolve_android_key(key))

    @override
    def type_text(self, text: str) -> None:
        """输入一段文本。

        :param text: 待输入的文本。
        """
        self._sync.input_text(text)

    @override
    def launch_app(self, package_name: str) -> None:
        """根据包名启动 app。

        :param package_name: 应用包名。
        """
        self._sync.start_app(package_name)

    @override
    def current_package(self) -> str | None:
        """获取前台 APP 的包名。

        经 ``sync.shell`` 执行 dumpsys 查询并沿用老 AdbImpl 的解析规则，
        查不到时返回 None。

        :returns: 前台包名，查不到时返回 None。
        """
        # https://blog.csdn.net/guangdeshishe/article/details/117154406
        result_text = self._sync.shell('dumpsys activity top | grep ACTIVITY | tail -n 1')
        logger.debug('adb returned: %s', result_text)
        result_text = result_text.strip()
        if result_text == '':
            logger.error('No current package found')
            return None
        _, activity, *_ = result_text.split(' ')
        package = activity.split('/')[0]
        return package

    @override
    def adb_shell(self, cmd: str) -> str:
        """执行 ADB shell 命令。

        :param cmd: shell 命令。
        :returns: shell 命令输出。
        """
        return self._sync.shell(cmd)

    @override
    def install_apk(self, path: str) -> None:
        """安装 APK 文件。

        沿用老 AdbImpl 的实现，经 adbutils 连接安装。

        :param path: APK 文件路径。
        """
        self.adb_connection.install(path)
