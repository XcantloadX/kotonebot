from abc import ABC
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias, TypeGuard, get_args
from typing_extensions import assert_never

try:
    from adbutils import adb
    from adbutils._device import AdbDevice
except ImportError as _e:
    from kotonebot.errors import MissingDependencyError
    raise MissingDependencyError(_e, 'android')
from kotonebot import logging
from kotonebot.client.device import AndroidDevice
from .protocol import AdbHostConfig, Device

logger = logging.getLogger(__name__)
AdbRecipes = Literal['adb', 'uiautomator2']

def is_adb_recipe(recipe: Any) -> TypeGuard[AdbRecipes]:
    return recipe in get_args(AdbRecipes)


@dataclass(frozen=True, slots=True)
class AdbTargetTcpip:
    serial: str
    addr: str
    connect: bool
    disconnect: bool
    timeout: float = 180


@dataclass(frozen=True, slots=True)
class AdbTargetUsb:
    serial: str
    timeout: float = 180


AdbTarget: TypeAlias = AdbTargetTcpip | AdbTargetUsb

def connect_adb(
    target: AdbTarget
) -> AdbDevice:
    """
    创建 ADB 连接。
    """
    if isinstance(target, AdbTargetTcpip):
        if target.disconnect:
            logger.debug('adb disconnect %s', target.addr)
            adb.disconnect(target.addr)
        else:
            logger.debug('Skip adb disconnect.')
        if target.connect:
            logger.debug('adb connect %s', target.addr)
            result = adb.connect(target.addr)
            if 'cannot connect to' in result:
                raise ValueError(result)
        else:
            logger.debug('Skip adb connect.')
    logger.debug('adb wait for %s', target.serial)
    adb.wait_for(target.serial, timeout=target.timeout)
    devices = adb.device_list()
    logger.debug('adb device_list: %s', devices)
    d = [d for d in devices if d.serial == target.serial]
    if len(d) == 0:
        raise ValueError(f"Device {target.serial} not found")
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
        self.adb_port: int | None
        self.adb_name: str | None
        self.adb_serial: str | None

    def _adb_target(self, timeout: float, *, connect: bool, disconnect: bool) -> AdbTarget:
        if self.adb_port is not None:
            addr = f'{self.adb_ip}:{self.adb_port}'
            serial = self.adb_serial or self.adb_name or addr
            return AdbTargetTcpip(
                serial=serial,
                addr=addr,
                connect=connect,
                disconnect=disconnect,
                timeout=timeout,
            )

        serial = self.adb_serial
        if serial is None:
            raise ValueError("Neither adb_serial nor adb_port is set.")
        if connect or disconnect:
            raise ValueError("adb_port is required when connect/disconnect is enabled.")
        return AdbTargetUsb(
            serial=serial,
            timeout=timeout,
        )
    
    def create_device(self, recipe: AdbRecipes, config: AdbHostConfig, *, connect: bool = True, disconnect: bool = True) -> Device:
        """
        创建 ADB 设备。

        :param recipe: 连接方式配方名称。
        :param config: ADB 配置。
        :param connect: 创建设备实例前，是否连接 ADB（执行 adb connect）。
        :param disconnect: 创建设备实例前，是否先断开已有 ADB 连接（执行 adb disconnect）。
        """
        target = self._adb_target(config.timeout, connect=connect, disconnect=disconnect)
        connection = connect_adb(target)
        d = AndroidDevice(connection)
        match recipe:
            case 'adb':
                from kotonebot.client.implements.adb import AdbImpl
                impl = AdbImpl(connection)
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
