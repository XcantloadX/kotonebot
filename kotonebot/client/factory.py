from enum import Enum
from typing import Literal

from .device import Device
from .implements.adb import AdbImpl
from .implements.adb_raw import AdbRawImpl
from .implements.uiautomator2 import UiAutomator2Impl

from adbutils import adb

DeviceImpl = Literal['adb', 'adb_raw', 'uiautomator2']

def create_device(
    addr: str,
    impl: DeviceImpl,
) -> Device:
    adb.connect("127.0.0.1:5555")
    d = [d for d in adb.device_list() if d.serial == addr]
    if len(d) == 0:
        raise ValueError(f"Device {addr} not found")
    d = d[0]
    device = Device(d)
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
    return device
