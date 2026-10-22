"""Maa 原生 stdout/stderr 被动捕获，转入 Python logging。"""

import ctypes
import locale
import logging
import re
import sys
import threading
from ctypes import wintypes

logger = logging.getLogger(__name__)

NATIVE_LOGGER_NAME = 'kotonebot.client.maa_backend.native'
"""转发 Maa 原生输出的目标 logger 名称。"""

native_logger = logging.getLogger(NATIVE_LOGGER_NAME)
"""接收 Maa 原生输出行的 logger。"""

_LEVEL_RE: re.Pattern[str] = re.compile(r'^\[[^\]]*\]\[(FTL|ERR|WRN|INF|DBG|TRC)\]')
"""匹配 Maa 原生日志行头的级别标记，如 ``[2026-10-07 18:27:49][INF]``。"""

_ANSI_RE: re.Pattern[str] = re.compile(r'\x1b\[[0-9;]*m')
"""匹配 Maa 原生 stdout 着色用的 ANSI 转义序列。"""

_BUFFER_SIZE = 4096
"""后台线程单次 ReadFile 读取的缓冲区大小（字节）。"""

_STD_OUTPUT_HANDLE = -11
"""GetStdHandle / SetStdHandle 的标准输出句柄 ID。"""

_STD_ERROR_HANDLE = -12
"""GetStdHandle / SetStdHandle 的标准错误句柄 ID。"""


class _SecurityAttributes(ctypes.Structure):
    """CreatePipe 用的安全属性，句柄显式设为不可继承。"""

    _fields_ = [
        ('nLength', wintypes.DWORD),  # 结构体大小
        ('lpSecurityDescriptor', wintypes.LPVOID),  # 安全描述符，None 表示默认
        ('bInheritHandle', wintypes.BOOL),  # 是否可被子进程继承，固定 False
    ]


_lock = threading.Lock()
_capturing = False
"""收集线程是否已启动（进程级幂等标志）。"""

_redirected = False
"""进程级句柄当前是否被换成管道（start/restore 配对之间的窗口）。"""

_original_stdout: wintypes.HANDLE | None = None
"""start 时快照的原始进程级 stdout 句柄，用于 restore 时还原。"""

_original_stderr: wintypes.HANDLE | None = None
"""start 时快照的原始进程级 stderr 句柄，用于 restore 时还原。"""


def _level_for_code(code: str) -> int:
    """把 Maa 原生级别标记映射为 logging 级别，未知标记一律按 DEBUG 处理。

    :param code: 原生级别标记，如 ``"INF"``。
    :returns: 对应的 logging 级别。
    """
    match code:
        case 'FTL':
            return logging.CRITICAL
        case 'ERR':
            return logging.ERROR
        case 'WRN':
            return logging.WARNING
        case 'INF':
            return logging.INFO
        case _:
            return logging.DEBUG


def _strip_ansi(line: str) -> str:
    """去掉行内的 ANSI 着色转义序列。

    :param line: 原生输出行。
    :returns: 去掉转义序列后的行。
    """
    return _ANSI_RE.sub('', line)


def _decode_line(raw: bytes) -> str | None:
    """解码一行原生输出字节。

    Maa 原生经 ``utf8_to_crt`` 写控制台，中文 Windows 下多为 GBK，直接按
    UTF-8 解码会失败；此时改用控制台编码再试一次。两次都失败返回 None，
    调用方负责告警并丢行。

    :param raw: 不含换行符的单行字节。
    :returns: 解码后的字符串，无法解码时返回 None。
    """
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        pass
    console_encoding = locale.getpreferredencoding(False)
    if console_encoding.lower().replace('_', '-') in ('utf-8', 'utf8'):
        return None
    try:
        return raw.decode(console_encoding)
    except (UnicodeDecodeError, LookupError):
        return None


def _emit_line(line: str) -> None:
    """把一行原生输出按级别转发到 native logger。

    带 Maa 原生行头（``[时间][LVL]…``）的按标记映射级别；无前缀的 raw 行
    （如设备端 agent 回显）一律记 DEBUG。整行原文保留，便于排查。

    :param line: 已解码去色的单行文本。
    """
    matched = _LEVEL_RE.match(line)
    if matched is None:
        native_logger.debug(line)
        return
    native_logger.log(_level_for_code(matched.group(1)), line)


def _pop_complete_lines(buffer: bytearray) -> list[bytes]:
    """从累积字节中取出全部完整行（不含换行符），残缺尾部留在 buffer 内。

    :param buffer: 累积的原生输出字节，会被原地消费掉完整行部分。
    :returns: 取出的完整行字节列表。
    """
    lines: list[bytes] = []
    while True:
        index = buffer.find(b'\n')
        if index < 0:
            return lines
        lines.append(bytes(buffer[:index].rstrip(b'\r')))
        del buffer[: index + 1]


def _configure_kernel32() -> ctypes.WinDLL:
    """获取 kernel32 并声明用到的函数原型，保证 ctypes 类型安全。

    :returns: 已声明原型的 kernel32 库对象。
    """
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.CreatePipe.argtypes = [
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(wintypes.HANDLE),
        ctypes.POINTER(_SecurityAttributes),
        wintypes.DWORD,
    ]
    kernel32.CreatePipe.restype = wintypes.BOOL
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.SetStdHandle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
    kernel32.SetStdHandle.restype = wintypes.BOOL
    kernel32.ReadFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    kernel32.ReadFile.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    return kernel32


def _reader_loop(kernel32: ctypes.WinDLL, read_handle: wintypes.HANDLE) -> None:
    """后台线程主循环：持续排空管道，按行解码后转入 logging。

    读端只在进程退出时失效；ReadFile 失败即记 warning 后退出，不抛异常。

    :param kernel32: 已声明原型的 kernel32 库对象。
    :param read_handle: 匿名管道读端句柄。
    """
    buf = ctypes.create_string_buffer(_BUFFER_SIZE)
    nread = wintypes.DWORD(0)
    pending = bytearray()
    while True:
        ok = kernel32.ReadFile(read_handle, buf, _BUFFER_SIZE, ctypes.byref(nread), None)
        if not ok or nread.value == 0:
            logger.warning('Maa native stdout pipe closed, capture thread exiting.')
            return
        pending += buf.raw[: nread.value]
        for raw in _pop_complete_lines(pending):
            text = _decode_line(raw)
            if text is None:
                # 个别字节无法解码只丢该行，不断开整个收集循环。
                logger.warning('Dropped undecodable Maa native log bytes: %r.', raw)
                continue
            _emit_line(_strip_ansi(text))


def start_native_stdout_capture() -> bool:
    """把进程级 stdout/stderr 重定向到匿名管道，开始收集 Maa 原生输出。

    MSVC CRT 的 DLL 在加载时用 ``GetStdHandle`` 快照标准句柄，因此调用方
    必须在 Maa 动态库加载**之前**调用本函数，加载完成后调
    :func:`restore_process_std_handles` 还原（DLL 的快照继续指向管道，
    收集线程常驻进程生命期）。重复调用直接返回 True。

    本函数是纯观测手段：重定向失败只记 warning 并返回 False，不阻断调用方
    的动态库加载流程。

    :returns: 收集已生效时返回 True；非 Windows 或重定向失败时返回 False。
    """
    global _capturing, _redirected, _original_stdout, _original_stderr
    with _lock:
        if _capturing:
            return True
        if sys.platform != 'win32':
            logger.warning(
                'Maa native stdout capture is only supported on Windows, skipped.'
            )
            return False
        kernel32 = _configure_kernel32()
        security = _SecurityAttributes()
        security.nLength = ctypes.sizeof(_SecurityAttributes)
        security.lpSecurityDescriptor = None
        security.bInheritHandle = False
        read_handle = wintypes.HANDLE()
        write_handle = wintypes.HANDLE()
        if not kernel32.CreatePipe(
            ctypes.byref(read_handle), ctypes.byref(write_handle),
            ctypes.byref(security), 0,
        ):
            logger.warning(
                'Failed to create pipe for Maa native stdout capture: %s.',
                ctypes.WinError(ctypes.get_last_error()),
            )
            return False
        original_stdout = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        original_stderr = kernel32.GetStdHandle(_STD_ERROR_HANDLE)
        if not kernel32.SetStdHandle(_STD_OUTPUT_HANDLE, write_handle):
            kernel32.CloseHandle(read_handle)
            kernel32.CloseHandle(write_handle)
            logger.warning(
                'Failed to redirect stdout for Maa native capture: %s.',
                ctypes.WinError(ctypes.get_last_error()),
            )
            return False
        if not kernel32.SetStdHandle(_STD_ERROR_HANDLE, write_handle):
            kernel32.SetStdHandle(_STD_OUTPUT_HANDLE, original_stdout)
            kernel32.CloseHandle(read_handle)
            kernel32.CloseHandle(write_handle)
            logger.warning(
                'Failed to redirect stderr for Maa native capture: %s.',
                ctypes.WinError(ctypes.get_last_error()),
            )
            return False
        thread = threading.Thread(
            target=_reader_loop,
            args=(kernel32, read_handle),
            name='kotonebot-maa-native-stdout',
            daemon=True,
        )
        thread.start()
        _original_stdout = original_stdout
        _original_stderr = original_stderr
        _capturing = True
        _redirected = True
        logger.debug('Maa native stdout capture started.')
        return True


def restore_process_std_handles() -> None:
    """还原进程级 stdout/stderr 句柄。

    管道写端保持打开（Maa DLL 的快照继续有效），后台收集线程继续运行；
    因此还原后 DLL 的原生输出仍会进入 logging，只是新 spawn 的子进程与
    宿主控制台不再受影响。未 start 或已还原时直接返回。

    :returns: 无返回值。
    """
    global _redirected, _original_stdout, _original_stderr
    with _lock:
        if not _redirected:
            return
        kernel32 = _configure_kernel32()
        if _original_stdout is not None:
            kernel32.SetStdHandle(_STD_OUTPUT_HANDLE, _original_stdout)
            _original_stdout = None
        if _original_stderr is not None:
            kernel32.SetStdHandle(_STD_ERROR_HANDLE, _original_stderr)
            _original_stderr = None
        _redirected = False
        logger.debug('Process std handles restored, Maa native capture keeps running.')
