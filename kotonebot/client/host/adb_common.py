from abc import ABC
from typing import Any, Literal, TypeGuard, TypeVar, get_args
from typing_extensions import assert_never

from adbutils import adb
from adbutils._device import AdbDevice
from kotonebot import logging
from kotonebot.client.device import AndroidDevice
from .protocol import Instance, AdbHostConfig, Device

logger = logging.getLogger(__name__)
AdbRecipes = Literal['adb', 'adb_raw', 'uiautomator2']

def is_adb_recipe(recipe: Any) -> TypeGuard[AdbRecipes]:
    return recipe in get_args(AdbRecipes)

def connect_adb(
    ip: str,
    port: int,
    connect: bool = True,
    disconnect: bool = True,
    timeout: float = 180,
    device_serial: str | None = None
) -> AdbDevice:
    """
    创建 ADB 连接。
    """
    if disconnect:
        logger.debug('adb disconnect %s:%d', ip, port)
        adb.disconnect(f'{ip}:{port}')
    if connect:
        logger.debug('adb connect %s:%d', ip, port)
        result = adb.connect(f'{ip}:{port}')
        if 'cannot connect to' in result:
            raise ValueError(result)
    serial = device_serial or f'{ip}:{port}'
    logger.debug('adb wait for %s', serial)
    adb.wait_for(serial, timeout=timeout)
    devices = adb.device_list()
    logger.debug('adb device_list: %s', devices)
    d = [d for d in devices if d.serial == serial]
    if len(d) == 0:
        raise ValueError(f"Device {serial} not found")
    d = d[0]
    return d

class CommonAdbCreateDeviceMixin(ABC):
    """
    通用 ADB 创建设备的 Mixin。
    该 Mixin 定义了创建 ADB 设备的通用接口。
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # 下面的属性只是为了让类型检查通过，无实际实现
        self.adb_ip: str
        self.adb_port: int
        self.adb_name: str
    
    def create_device(self, recipe: AdbRecipes, config: AdbHostConfig) -> Device:
        """
        创建 ADB 设备。
        """
        connection = connect_adb(
            self.adb_ip,
            self.adb_port,
            connect=True,
            disconnect=True,
            timeout=config.timeout,
            device_serial=self.adb_name
        )
        d = AndroidDevice(connection)
        match recipe:
            case 'adb':
                from kotonebot.client.implements.adb import AdbImpl
                impl = AdbImpl(connection)
                d._screenshot = impl
                d._touch = impl
                d.commands = impl
            case 'adb_raw':
                from kotonebot.client.implements.adb_raw import AdbRawImpl
                impl = AdbRawImpl(connection)
                d._screenshot = impl
                d._touch = impl
                d.commands = impl
            case 'uiautomator2':
                from kotonebot.client.implements.uiautomator2 import UiAutomator2Impl
                from kotonebot.client.implements.adb import AdbImpl
                impl = UiAutomator2Impl(connection)
                d._screenshot = impl
                d._touch = impl
                d.commands = AdbImpl(connection)
            case _:
                assert_never(f'Unsupported ADB recipe: {recipe}')
        return d
