"""基于 MaaFramework 控制器的设备后端。

本包将 Maa 的 ``AdbController``/``Win32Controller``
封装为 kotonebot 设备协议实现。Maa 相关 import 只出现在本包内；
运行环境缺失 ``maafw`` 包时，导入本包会抛出
:class:`~kotonebot.errors.MissingDependencyError`。
"""

from .adb import MaaAdbAdapter
from .errors import (
    MaaDeviceNotFoundError,
    MaaJobFailedError,
    MaaLibraryLoadError,
    MaaLibraryNotFoundError,
)
from .factory import create_maa_adb, create_maa_win32
from .sync import MaaSyncController
from .win32 import MaaWin32Adapter

from maa.define import (
    MaaAdbInputMethodEnum,
    MaaAdbScreencapMethodEnum,
    MaaWin32InputMethodEnum,
    MaaWin32ScreencapMethodEnum,
)

__all__ = [
    'MaaSyncController',
    'MaaAdbAdapter',
    'MaaWin32Adapter',
    'create_maa_adb',
    'create_maa_win32',
    'MaaDeviceNotFoundError',
    'MaaJobFailedError',
    'MaaLibraryLoadError',
    'MaaLibraryNotFoundError',
    'MaaAdbInputMethodEnum',
    'MaaAdbScreencapMethodEnum',
    'MaaWin32InputMethodEnum',
    'MaaWin32ScreencapMethodEnum',
]
