from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adb import AdbImpl, AdbImplConfig
    from .scrcpy import ScrcpyImpl, ScrcpyConfig, VirtualDisplayConfig, ScrcpySession
    from .uiautomator2 import UiAutomator2Impl
    from .windows import WindowsImpl, WindowsImplConfig, WindowsNativeImpl, WindowsNativeImplConfig
    from .nemu_ipc import NemuIpcImpl, NemuIpcImplConfig, ExternalRendererIpc


def _require_windows():
    global WindowsImpl, WindowsImplConfig, WindowsNativeImpl, WindowsNativeImplConfig
    global NemuIpcImpl, NemuIpcImplConfig, ExternalRendererIpc

    from .windows import WindowsImpl, WindowsImplConfig, WindowsNativeImpl, WindowsNativeImplConfig
    from .nemu_ipc import NemuIpcImpl, NemuIpcImplConfig, ExternalRendererIpc

def _require_adb():
    global AdbImpl, AdbImplConfig
    
    from .adb import AdbImpl, AdbImplConfig

def _require_scrcpy():
    global ScrcpyImpl, ScrcpyConfig, VirtualDisplayConfig, ScrcpySession

    from .scrcpy import ScrcpyImpl, ScrcpyConfig, VirtualDisplayConfig, ScrcpySession

def _require_uiautomator2():
    global UiAutomator2Impl
    
    from .uiautomator2 import UiAutomator2Impl

_IMPORT_NAMES = [
    (_require_windows, [
        'WindowsImpl', 'WindowsImplConfig',
        'WindowsNativeImpl', 'WindowsNativeImplConfig',
        'NemuIpcImpl', 'NemuIpcImplConfig', 'ExternalRendererIpc'
    ]),
    (_require_adb, [
        'AdbImpl', 'AdbImplConfig',
    ]),
    (_require_scrcpy, [
        'ScrcpyImpl', 'ScrcpyConfig', 'VirtualDisplayConfig', 'ScrcpySession',
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
    'WindowsNativeImpl', 'WindowsNativeImplConfig',
    'NemuIpcImpl', 'NemuIpcImplConfig', 'ExternalRendererIpc',
    # android
    'AdbImpl', 'AdbImplConfig',
    'ScrcpyImpl', 'ScrcpyConfig', 'VirtualDisplayConfig', 'ScrcpySession',
    'UiAutomator2Impl'
]
