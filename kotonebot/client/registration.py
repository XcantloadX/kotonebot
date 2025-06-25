from dataclasses import dataclass
from typing import TypeVar, Callable, Dict, Type, Any, overload, Literal, cast, TYPE_CHECKING

from ..errors import KotonebotError
from .device import Device
if TYPE_CHECKING:
    from .implements.adb import AdbImplConfig
    from .implements.remote_windows import RemoteWindowsImplConfig
    from .implements.windows import WindowsImplConfig
    from .implements.nemu_ipc import NemuIpcImplConfig

AdbBasedImpl = Literal['adb', 'adb_raw', 'uiautomator2']
DeviceImpl = str | AdbBasedImpl | Literal['windows', 'remote_windows', 'nemu_ipc']

# --- 核心类型定义 ---

class ImplRegistrationError(KotonebotError):
    """与 impl 注册相关的错误"""
    pass

@dataclass
class ImplConfig:
    """所有设备实现配置模型的名义上的基类，便于类型约束。"""
    pass
