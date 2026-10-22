"""Maa 连接期方法选择的调试日志采集。"""

import logging
import re
import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from kotonebot.errors import MissingDependencyError

logger = logging.getLogger(__name__)

_FASTEST_RE: re.Pattern[str] = re.compile(r'The fastest method is ([A-Za-z_]+)')
"""匹配 Maa 测速日志中的胜选行，如 ``The fastest method is RawWithGzip [cost=434ms]``。

Maa 日志直接打印内部枚举名（ADB 侧是 `ScreencapAgent.h` Method 枚举，
Win32 侧是 `Win32ControlUnitMgr.h` ScreencapMethod 枚举），无需做数值映射。
"""

def _maa_define():
    """懒导入 Maa 枚举定义，避免无 maa 环境在模块导入期爆炸。"""
    try:
        from maa.define import MaaAdbInputMethodEnum, MaaWin32InputMethodEnum
    except ImportError as _e:
        raise MissingDependencyError(_e, 'maa') from _e
    return MaaAdbInputMethodEnum, MaaWin32InputMethodEnum


def _parse_fastest(log_text: str) -> str | None:
    """从 Maa 日志文本中解析测速胜选者的枚举名，无胜选行时返回 None。"""
    found = _FASTEST_RE.findall(log_text)
    if not found:
        return None
    return found[-1]


def _adb_input_name(input_methods: int) -> str:
    """按 Maa 固定优先级从输入掩码推导实际使用的输入方式。

    Maa `InputAgent::init` 按 Extras > Maatouch > Minitouch > AdbShell 的顺序
    取首个初始化成功的，初始化失败会静默回退到次选（日志不记录），因此此处
    只能反映优先级首选，极少数情况下可能与实际偏离。
    """
    MaaAdbInputMethodEnum, _ = _maa_define()
    for method in (
        MaaAdbInputMethodEnum.EmulatorExtras,
        MaaAdbInputMethodEnum.Maatouch,
        MaaAdbInputMethodEnum.MinitouchAndAdbKey,
        MaaAdbInputMethodEnum.AdbShell,
    ):
        if input_methods & int(method):
            return method.name
    return 'unknown'


def _win32_input_name(value: int | None, *, default: str) -> str:
    """解析 Win32 单选输入方式，None 表示使用 Maa 默认值。"""
    if value is None:
        return default
    _, MaaWin32InputMethodEnum = _maa_define()
    try:
        return MaaWin32InputMethodEnum(int(value)).name
    except ValueError:
        # 调试上报绝不能破坏已成功的连接，未知取值如实记录。
        return f'unknown({value})'


class MaaLogCapture:
    """一次 connect 期 Maa 日志的采集结果。"""

    def __init__(self, text: str) -> None:
        """初始化采集结果。

        :param text: 采集到的 Maa 日志文本，采集失败时为空字符串。
        """
        self._text: str = text
        """采集到的 Maa 日志文本。"""

    def text(self) -> str:
        """返回采集到的 Maa 日志文本。

        :returns: Maa 日志文本，采集失败时为空字符串。
        """
        return self._text


def _read_logs(tmp: str) -> str:
    """读回临时目录中的 Maa 日志，读失败的文件记 warning 后跳过。"""
    texts = []
    for path in sorted(Path(tmp).rglob('*.log')):
        try:
            texts.append(path.read_text(encoding='utf-8'))
        except (OSError, UnicodeDecodeError):
            # 调试采集绝不能破坏已成功的连接。
            logger.warning('Failed to read Maa log file: %s.', path)
    return '\n'.join(texts)


@contextmanager
def capture_maa_logs() -> Generator[MaaLogCapture, None, None]:
    """把 Maa 文件日志重定向到临时目录，仅包裹一次 connect 调用。

    测速日志只在 connect 期间产生，因此 ``sync.connect()`` 必须写在
    with 块内。被包裹代码抛出的异常原样透出，不做任何掩盖；退出时恢复
    日志目录并清理临时目录。

    :returns: 日志采集结果，日志重定向失败时其文本为空字符串。
    """
    try:
        from maa.tasker import Tasker
    except ImportError as _e:
        raise MissingDependencyError(_e, 'maa') from _e
    # 不用 TemporaryDirectory：Maa 进程级复用日志文件句柄，退出时删不掉（Windows 报 32 错误），
    # 用 mkdtemp + ignore_errors 自行清理，残留的空目录由系统 Temp 清理机制回收。
    tmp = tempfile.mkdtemp(prefix='maa-conn-logs-')
    capture = MaaLogCapture('')
    try:
        if not Tasker.set_log_dir(tmp):
            logger.warning('Failed to redirect Maa logs, method selection will be unknown.')
            yield capture
            return
        try:
            yield capture
        finally:
            Tasker.set_log_dir('')
            capture._text = _read_logs(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def report_adb_selection(log_text: str, *, address: str, input_methods: int) -> None:
    """根据采集到的 Maa 日志，以 debug 打印 ADB 控制器实际选用的方式。

    纯上报，不触碰连接。

    :param log_text: :func:`capture_maa_logs` 采集到的 Maa 日志文本。
    :param address: ADB 连接地址，仅用于日志。
    :param input_methods: 传给控制器的输入掩码（已 resolve 后的生效值）。
    """
    fastest = _parse_fastest(log_text)
    logger.debug(
        'Maa ADB controller connected: address=%s screencap=%s input=%s.',
        address,
        fastest if fastest is not None else 'unknown',
        _adb_input_name(input_methods),
    )


def report_win32_selection(
    log_text: str,
    *,
    hwnd: int,
    mouse_method: int | None,
    keyboard_method: int | None,
) -> None:
    """根据采集到的 Maa 日志，以 debug 打印 Win32 控制器实际选用的方式。

    纯上报，不触碰连接。

    :param log_text: :func:`capture_maa_logs` 采集到的 Maa 日志文本。
    :param hwnd: 目标窗口句柄，仅用于日志。
    :param mouse_method: 传给控制器的鼠标方式，None 表示 Maa 默认（Seize）。
    :param keyboard_method: 传给控制器的键盘方式，None 表示 Maa 默认（Seize）。
    """
    fastest = _parse_fastest(log_text)
    logger.debug(
        'Maa Win32 controller connected: hwnd=%d screencap=%s mouse=%s keyboard=%s.',
        hwnd,
        fastest if fastest is not None else 'unknown',
        _win32_input_name(mouse_method, default='Seize'),
        _win32_input_name(keyboard_method, default='Seize'),
    )
