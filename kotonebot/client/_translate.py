"""设备底层异常到连接异常的统一转译。"""

import logging
import re

from kotonebot.client.implements.nemu_ipc.nemu_ipc import (
    NemuIpcDisplayNotFoundError,
    NemuIpcError,
)
from kotonebot.errors import (
    DeviceConnectRefusedError,
    DeviceConnectTimeoutError,
    DeviceConnectionError,
    DeviceNotReadyError,
)

logger = logging.getLogger(__name__)

_ADDR_PATTERN = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}:\d+")
"""从错误文本中提取 `ip:port` 的正则。"""


def _extract_addr(message: str) -> str:
    """从错误文本中提取设备地址。

    :param message: 原始错误文本。
    :returns: 命中的第一个 `ip:port`；未命中时返回空字符串。
    """
    matched = _ADDR_PATTERN.search(message)
    if matched is None:
        return ""
    return matched.group(0)


def translate_device_error(error: Exception) -> DeviceConnectionError | None:
    """将底层实现抛出的异常转译为设备连接异常。

    已是连接异常时直接透传；与连接无关时返回 None，调用方应原样抛出。

    :param error: 底层实现抛出的原始异常。
    :returns: 转译后的连接异常；与连接无关时返回 None。
    """
    # 已经是连接异常，直接透传，保持原有子类与调用链
    if isinstance(error, DeviceConnectionError):
        return error
    # 目标应用未启动导致的 display_id 缺失属于可预期的运行态条件，不是连接抖动
    if isinstance(error, NemuIpcDisplayNotFoundError):
        return None
    if isinstance(error, NemuIpcError):
        return DeviceNotReadyError(str(error))
    # adbutils 为可选依赖，沿用 device_operation 的懒加载惯例
    try:
        from adbutils import AdbTimeout
        from adbutils.errors import AdbError
    except ImportError:
        pass
    else:
        if isinstance(error, AdbTimeout):
            return DeviceConnectTimeoutError()
        if isinstance(error, AdbError):
            # AdbError 默认为瞬态连接故障，不再按关键词白名单过滤
            return DeviceNotReadyError(str(error))
    if isinstance(error, ConnectionRefusedError):
        return DeviceConnectRefusedError(_extract_addr(str(error)))
    if isinstance(error, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)):
        return DeviceNotReadyError(str(error))
    if isinstance(error, ValueError):
        message = str(error)
        if "cannot connect to" in message:
            # 例如 ValueError("cannot connect to 127.0.0.1:5555: 由于目标计算机积极拒绝，无法连接。 (10061)")
            return DeviceConnectRefusedError(_extract_addr(message))
        if "Device" in message and "not found" in message:
            # 例如 AdbError("device '127.0.0.1:5555' not found")
            return DeviceNotReadyError(message)
        return None
    return None
