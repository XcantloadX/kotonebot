from enum import Enum
from typing import Literal

from .implements.adb import AdbImpl
from .implements.adb_raw import AdbRawImpl
from .implements.windows import WindowsImpl
from .implements.remote_windows import RemoteWindowsImpl
from .implements.uiautomator2 import UiAutomator2Impl
from .device import Device, AndroidDevice, WindowsDevice

from adbutils import adb

DeviceImpl = Literal['adb', 'adb_raw', 'uiautomator2', 'windows', 'remote_windows']

def create_device(
    addr: str,
    impl: DeviceImpl,
) -> Device:
    if impl in ['adb', 'adb_raw', 'uiautomator2']:
        result = adb.connect(addr)
        if 'cannot connect to' in result:
            raise ValueError(result)
        d = [d for d in adb.device_list() if d.serial == addr]
        if len(d) == 0:
            raise ValueError(f"Device {addr} not found")
        d = d[0]
        device = AndroidDevice(d)
        if impl == 'adb':
            device._command = AdbImpl(device)
            device._touch = AdbImpl(device)
            device._screenshot = AdbImpl(device)
        elif impl == 'adb_raw':
            device._command = AdbRawImpl(device)
            device._touch = AdbRawImpl(device)
            device._screenshot = AdbRawImpl(device)
        elif impl == 'uiautomator2':
            device._command = UiAutomator2Impl(device)
            device._touch = UiAutomator2Impl(device)
            device._screenshot = UiAutomator2Impl(device)
    elif impl == 'windows':
        device = WindowsDevice()
        device._touch = WindowsImpl(device)
        device._screenshot = WindowsImpl(device)
    elif impl == 'remote_windows':
        # For remote_windows, addr should be in the format 'host:port'
        if ':' not in addr:
            raise ValueError(f"Invalid address format for remote_windows: {addr}. Expected format: 'host:port'")
        host, port_str = addr.split(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port in address: {port_str}")

        device = WindowsDevice()
        remote_impl = RemoteWindowsImpl(device, host, port)
        device._touch = remote_impl
        device._screenshot = remote_impl
    return device
