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
    *,
    connect: bool = True,
    device_serial: str | None = None
) -> Device:
    """
    根据指定的实现方式创建 Device 实例。
    
    :param addr: 设备地址，如 `127.0.0.1:5555`。
        仅当通过无线方式连接 Android 设备，或者使用 `remote_windows` 时有效。
    :param impl: 实现方式。
    :param connect: 是否在创建时连接设备，默认为 True。
        仅对 ADB-based 的实现方式有效。
    :param device_serial: 设备序列号，默认为 None。
        若为非 None，则当存在多个设备时通过该值判断是否为目标设备。
        仅对 ADB-based 的实现方式有效。
    """
    if impl in ['adb', 'adb_raw', 'uiautomator2']:
        if connect:
            result = adb.connect(addr)
            if 'cannot connect to' in result:
                raise ValueError(result)
        serial = device_serial or addr
        d = [d for d in adb.device_list() if d.serial == serial]
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
