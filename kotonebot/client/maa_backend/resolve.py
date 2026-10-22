"""Maa 控制器构造参数解析。"""

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from kotonebot.errors import MissingDependencyError

from .errors import MaaDeviceNotFoundError

try:
    from maa.toolkit import Toolkit
except ImportError as _e:
    raise MissingDependencyError(_e, 'maa') from _e

if TYPE_CHECKING:
    from kotonebot.client.host.adb_common import AdbTarget
from kotonebot.interop.window import WindowManager, WindowQuery

logger = logging.getLogger(__name__)


class AdbExtraConfig(BaseModel):
    """Maa ADB 附加配置，原样透传给 ``AdbController``。"""

    model_config = ConfigDict(extra='allow')


class AdbConnectionParams(BaseModel):
    """构造 ``AdbController`` 所需的五元组参数。"""

    adb_path: str = Field(description='adb 可执行文件路径。')
    address: str = Field(description='设备连接地址。')
    screencap_methods: int = Field(description='截图方式位掩码。')
    input_methods: int = Field(description='输入方式位掩码。')
    config: AdbExtraConfig = Field(description='Maa 附加配置。')


def _target_address(target: 'AdbTarget') -> str:
    """提取目标对应的 Maa 连接地址。

    :param target: ADB 连接目标。
    :returns: TCP 目标返回 ``addr``，USB 目标返回 ``serial``。
    """
    from kotonebot.client.host.adb_common import AdbTargetTcpip

    if isinstance(target, AdbTargetTcpip):
        return target.addr
    return target.serial


def resolve_adb(target: 'AdbTarget') -> AdbConnectionParams:
    """解析 ADB 目标为 ``AdbController`` 构造参数。

    仅在 ``Toolkit.find_adb_devices`` 结果中按同 ``address`` 命中；
    未命中直接抛错，不做掩码回退。

    :param target: ADB 连接目标。
    :returns: 构造 ``AdbController`` 所需的五元组参数。
    :raises MaaDeviceNotFoundError: 地址不在 Maa 已知设备中时抛出。
    """
    address = _target_address(target)
    logger.debug('Resolving Maa ADB params for address=%s.', address)
    devices = Toolkit.find_adb_devices()
    for device in devices:
        if device.address == address:
            logger.debug(
                'Hit Maa known device: name=%s address=%s.', device.name, device.address
            )
            return AdbConnectionParams(
                adb_path=str(device.adb_path),
                address=device.address,
                screencap_methods=int(device.screencap_methods),
                input_methods=int(device.input_methods),
                config=AdbExtraConfig.model_validate(device.config),
            )
    raise MaaDeviceNotFoundError(address)


def resolve_hwnd(query: WindowQuery) -> int:
    """解析窗口查询条件为 Win32 窗口句柄。

    :param query: 窗口查询条件。
    :returns: 匹配窗口的句柄。
    :raises TypeError: 查到的窗口标识不是整数句柄时抛出。
    :raises WindowNotFoundError: 未找到匹配窗口时抛出。
    """
    window = WindowManager.default().find_one(query)
    raw_id = window.id
    if isinstance(raw_id, bool) or not isinstance(raw_id, int):
        raise TypeError(
            'Win32 window id must be an integer hwnd, '
            f'got {type(raw_id).__name__}: {raw_id!r}.'
        )
    logger.debug('Resolved window query %s to hwnd=%d.', query, raw_id)
    return raw_id
