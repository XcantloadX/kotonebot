from typing import TYPE_CHECKING

from .protocol import HostProtocol, Instance, AdbHostConfig, WindowsHostConfig, RemoteWindowsHostConfig
if TYPE_CHECKING:
    from .custom import CustomInstance, create as create_custom
    from .mumu12_host import Mumu12Host, Mumu12Instance, Mumu12V5Host, Mumu12V5Instance
    from .leidian_host import LeidianHost, LeidianInstance
    from .physical_android_host import PhysicalAndroidHost, PhysicalAndroidInstance

def _require_custom():
    global CustomInstance, create_custom
    from .custom import CustomInstance, create as create_custom
    
def _require_mumu12():
    global Mumu12Host, Mumu12Instance, Mumu12V5Host, Mumu12V5Instance
    from .mumu12_host import Mumu12Host, Mumu12Instance, Mumu12V5Host, Mumu12V5Instance
    
def _require_leidian():
    global LeidianHost, LeidianInstance
    from .leidian_host import LeidianHost, LeidianInstance

def _require_physical_android():
    global PhysicalAndroidHost, PhysicalAndroidInstance
    from .physical_android_host import PhysicalAndroidHost, PhysicalAndroidInstance

_IMPORT_NAMES = [
    (_require_custom, ['CustomInstance', 'create_custom']),
    (_require_mumu12, ['Mumu12Host', 'Mumu12Instance', 'Mumu12V5Host', 'Mumu12V5Instance']),
    (_require_leidian, ['LeidianHost', 'LeidianInstance']),
    (_require_physical_android, ['PhysicalAndroidHost', 'PhysicalAndroidInstance']),
]

def __getattr__(name: str):
    for item in _IMPORT_NAMES:
        if name in item[1]:
            item[0]()
            break
    try:
        return globals()[name]
    except KeyError:
        raise AttributeError(name=name)

__all__ = [
    'HostProtocol', 'Instance',
    'AdbHostConfig', 'WindowsHostConfig', 'RemoteWindowsHostConfig',
    'CustomInstance', 'create_custom',
    'Mumu12Host', 'Mumu12Instance', 'Mumu12V5Host', 'Mumu12V5Instance',
    'LeidianHost', 'LeidianInstance',
    'PhysicalAndroidHost', 'PhysicalAndroidInstance',
]
