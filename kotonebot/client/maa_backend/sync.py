"""基于 Maa Controller 的同步调用封装。"""

import logging

from cv2.typing import MatLike

from kotonebot.errors import MissingDependencyError

try:
    from maa.controller import Controller
except ImportError as _e:
    raise MissingDependencyError(_e, 'maa') from _e

from .errors import MaaJobFailedError

logger = logging.getLogger(__name__)


class MaaSyncController:
    """将 Maa 异步 Controller 转为同步调用的外观类。

    Maa 的 ``post_*`` 接口均为异步，返回 ``Job`` 句柄；
    本类对每个操作执行 ``post_*().wait()`` 并在失败时抛出
    :class:`~kotonebot.client.maa_backend.errors.MaaJobFailedError`。

    :param controller: 已构造的 Maa 控制器实例。
    :param address: 目标设备地址，仅用于异常信息与日志。
    """

    def __init__(self, controller: Controller, address: str = '') -> None:
        if not isinstance(controller, Controller):
            raise TypeError(
                'controller must be an instance of maa.controller.Controller, '
                f'got {type(controller).__name__}.'
            )
        self._controller: Controller = controller
        self._address: str = address

    @property
    def controller(self) -> Controller:
        """底层 Maa 控制器实例。"""
        return self._controller

    @property
    def address(self) -> str:
        """目标设备地址。"""
        return self._address

    def connect(self) -> None:
        """连接设备。

        :raises MaaJobFailedError: 连接任务失败时抛出。
        """
        logger.debug('Maa post_connection (address=%s).', self._address)
        job = self._controller.post_connection()
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('connect', self._address)
        logger.debug('Maa controller connected (address=%s).', self._address)

    def screencap(self) -> MatLike:
        """截取一帧屏幕并同步返回。

        :returns: BGR 格式的截图数据。
        :raises MaaJobFailedError: 截图任务失败或返回空图像时抛出。
        """
        job = self._controller.post_screencap()
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('screencap', self._address)
        image = job.get()
        if image.size == 0:
            raise MaaJobFailedError('screencap', self._address)
        return image

    def click(self, x: int, y: int) -> None:
        """在指定坐标执行点击。

        :param x: 横坐标。
        :param y: 纵坐标。
        :raises ValueError: 坐标为负数时抛出。
        :raises MaaJobFailedError: 点击任务失败时抛出。
        """
        if x < 0 or y < 0:
            raise ValueError(f'Click coordinates must not be negative, got x={x} y={y}.')
        job = self._controller.post_click(x, y)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('click', self._address)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        """从起点滑动到终点。

        :param x1: 起点横坐标。
        :param y1: 起点纵坐标。
        :param x2: 终点横坐标。
        :param y2: 终点纵坐标。
        :param duration_ms: 滑动持续时间，单位毫秒，必须为正数。
        :raises ValueError: 坐标为负数或时长非正数时抛出。
        :raises MaaJobFailedError: 滑动任务失败时抛出。
        """
        if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
            raise ValueError(
                f'Swipe coordinates must not be negative, got ({x1}, {y1}) -> ({x2}, {y2}).'
            )
        if duration_ms <= 0:
            raise ValueError(f'Swipe duration must be positive (ms), got {duration_ms}.')
        logger.debug(
            'Maa post_swipe (%d, %d) -> (%d, %d) duration=%dms (address=%s).',
            x1, y1, x2, y2, duration_ms, self._address,
        )
        job = self._controller.post_swipe(x1, y1, x2, y2, duration_ms)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('swipe', self._address)

    def touch_down(self, x: int, y: int, contact: int = 0) -> None:
        """按下指定触点。

        供触控适配器实现 ``TouchDriver`` 原语使用。

        :param x: 横坐标。
        :param y: 纵坐标。
        :param contact: 触点编号。
        :raises ValueError: 坐标为负数或触点编号为负数时抛出。
        :raises MaaJobFailedError: 任务失败时抛出。
        """
        if x < 0 or y < 0:
            raise ValueError(f'Touch coordinates must not be negative, got x={x} y={y}.')
        if contact < 0:
            raise ValueError(f'Contact id must not be negative, got {contact}.')
        job = self._controller.post_touch_down(x, y, contact)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('touch_down', self._address)

    def touch_move(self, x: int, y: int, contact: int = 0) -> None:
        """移动指定触点。

        供触控适配器实现 ``TouchDriver`` 原语使用。

        :param x: 横坐标。
        :param y: 纵坐标。
        :param contact: 触点编号。
        :raises ValueError: 坐标为负数或触点编号为负数时抛出。
        :raises MaaJobFailedError: 任务失败时抛出。
        """
        if x < 0 or y < 0:
            raise ValueError(f'Touch coordinates must not be negative, got x={x} y={y}.')
        if contact < 0:
            raise ValueError(f'Contact id must not be negative, got {contact}.')
        job = self._controller.post_touch_move(x, y, contact)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('touch_move', self._address)

    def touch_up(self, contact: int = 0) -> None:
        """抬起指定触点。

        供触控适配器实现 ``TouchDriver`` 原语使用。

        :param contact: 触点编号。
        :raises ValueError: 触点编号为负数时抛出。
        :raises MaaJobFailedError: 任务失败时抛出。
        """
        if contact < 0:
            raise ValueError(f'Contact id must not be negative, got {contact}.')
        job = self._controller.post_touch_up(contact)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('touch_up', self._address)

    def key(self, key: int) -> None:
        """单击指定键码对应的按键。

        :param key: 按键键码（ADB 控制器为 Android 键码，Win32 控制器为 Win32 虚拟键码）。
        :raises MaaJobFailedError: 按键任务失败时抛出。
        """
        job = self._controller.post_click_key(key)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('key', self._address)

    def key_down(self, key: int) -> None:
        """按下指定键码对应的按键。

        供键盘适配器实现 ``KeyboardDriver`` 原语使用。

        :param key: 按键键码。
        :raises MaaJobFailedError: 按键任务失败时抛出。
        """
        job = self._controller.post_key_down(key)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('key_down', self._address)

    def key_up(self, key: int) -> None:
        """抬起指定键码对应的按键。

        供键盘适配器实现 ``KeyboardDriver`` 原语使用。

        :param key: 按键键码。
        :raises MaaJobFailedError: 按键任务失败时抛出。
        """
        job = self._controller.post_key_up(key)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('key_up', self._address)

    def input_text(self, text: str) -> None:
        """输入一段文本。

        :param text: 待输入的文本，不允许为空。
        :raises ValueError: 文本为空时抛出。
        :raises MaaJobFailedError: 输入任务失败时抛出。
        """
        if not text:
            raise ValueError('Input text must not be empty.')
        logger.debug('Maa post_input_text len=%d (address=%s).', len(text), self._address)
        job = self._controller.post_input_text(text)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('input_text', self._address)

    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        """滚动滚轮。

        :param dx: 水平滚动量。
        :param dy: 垂直滚动量。
        :raises MaaJobFailedError: 滚动任务失败时抛出。
        """
        job = self._controller.post_scroll(dx, dy)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('scroll', self._address)

    def start_app(self, intent: str) -> None:
        """启动应用。

        供 Android 适配器实现 ``launch_app`` 使用。

        :param intent: 启动目标（ADB 控制器为包名或 Activity）。
        :raises ValueError: 启动目标为空时抛出。
        :raises MaaJobFailedError: 启动任务失败时抛出。
        """
        if not intent:
            raise ValueError('App launch target must not be empty.')
        job = self._controller.post_start_app(intent)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('start_app', self._address)

    def shell(self, cmd: str, timeout_ms: int = 20000) -> str:
        """执行 shell 命令（仅 ADB 控制器支持）。

        供 Android 适配器实现 ``adb_shell`` 使用。

        :param cmd: shell 命令，不允许为空。
        :param timeout_ms: 超时时间，单位毫秒。
        :returns: shell 命令输出。
        :raises ValueError: 命令为空时抛出。
        :raises MaaJobFailedError: 命令任务失败时抛出。
        """
        if not cmd:
            raise ValueError('Shell command must not be empty.')
        job = self._controller.post_shell(cmd, timeout_ms)
        job.wait()
        if not job.succeeded:
            raise MaaJobFailedError('shell', self._address)
        return job.get()
