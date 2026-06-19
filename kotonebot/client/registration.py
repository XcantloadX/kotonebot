from dataclasses import dataclass
from typing import Literal, TYPE_CHECKING

from ..errors import KotonebotError
if TYPE_CHECKING:
    from .implements.adb import AdbImplConfig
    from .implements.scrcpy import ScrcpyConfig, VirtualDisplayConfig
    from .implements.windows import WindowsImplConfig, WindowsNativeImplConfig
    from .implements.nemu_ipc import NemuIpcImplConfig

AdbBasedImpl = Literal['adb', 'uiautomator2', 'scrcpy']
DeviceImpl = str | AdbBasedImpl | Literal['windows', 'windows_native', 'nemu_ipc']

# --- 核心类型定义 ---

class ImplRegistrationError(KotonebotError):
    """与 impl 注册相关的错误"""
    pass

@dataclass
class ImplConfig:
    """所有设备实现配置模型的名义上的基类，便于类型约束。"""
    pass
