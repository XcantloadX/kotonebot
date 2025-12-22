from typing import TYPE_CHECKING
from kotonebot.util import is_windows, require_windows

if TYPE_CHECKING:
    from .adb import AdbImpl, AdbImplConfig
    from .uiautomator2 import UiAutomator2Impl
    from .windows import WindowsImpl, WindowsImplConfig
    from .remote_windows import RemoteWindowsImpl, RemoteWindowsImplConfig, RemoteWindowsServer
    from .nemu_ipc import NemuIpcImpl, NemuIpcImplConfig, ExternalRendererIpc


def _require_windows():
    global WindowsImpl, WindowsImplConfig
    global RemoteWindowsImpl, RemoteWindowsImplConfig, RemoteWindowsServer
    global NemuIpcImpl, NemuIpcImplConfig, ExternalRendererIpc
    
    if not is_windows():
        require_windows('"windows", "remote_windows" and "nemu_ipc" implementations')
    from .windows import WindowsImpl, WindowsImplConfig
    from .remote_windows import RemoteWindowsImpl, RemoteWindowsImplConfig, RemoteWindowsServer
    from .nemu_ipc import NemuIpcImpl, NemuIpcImplConfig, ExternalRendererIpc

def _require_adb():
    global AdbImpl, AdbImplConfig
    
    from .adb import AdbImpl, AdbImplConfig

def _require_uiautomator2():
    global UiAutomator2Impl
    
    from .uiautomator2 import UiAutomator2Impl

_IMPORT_NAMES = [
    (_require_windows, [
        'WindowsImpl', 'WindowsImplConfig',
        'RemoteWindowsImpl', 'RemoteWindowsImplConfig', 'RemoteWindowsServer',
        'NemuIpcImpl', 'NemuIpcImplConfig', 'ExternalRendererIpc'
    ]),
    (_require_adb, [
        'AdbImpl', 'AdbImplConfig',
    ]),
    (_require_uiautomator2, [
        'UiAutomator2Impl'
    ]),
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
    # windows
    'WindowsImpl', 'WindowsImplConfig',
    'RemoteWindowsImpl', 'RemoteWindowsImplConfig', 'RemoteWindowsServer',
    'NemuIpcImpl', 'NemuIpcImplConfig', 'ExternalRendererIpc',
    # android
    'AdbImpl', 'AdbImplConfig',
    'UiAutomator2Impl'
]