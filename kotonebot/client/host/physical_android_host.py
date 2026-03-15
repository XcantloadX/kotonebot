from typing import Literal
from typing_extensions import override

try:
    from adbutils import adb
except ImportError as _e:
    from kotonebot.errors import MissingDependencyError
    raise MissingDependencyError(_e, 'android')

from kotonebot import logging
from kotonebot.client import Device
from kotonebot.util import Countdown, Interval
from .adb_common import AdbRecipes, CommonAdbCreateDeviceMixin
from .protocol import AdbHostConfig, HostProtocol, Instance

logger = logging.getLogger(__name__)
PhysicalAndroidRecipes = AdbRecipes


class PhysicalAndroidInstance(CommonAdbCreateDeviceMixin, Instance[AdbHostConfig]):
    @override
    def refresh(self):
        ins = PhysicalAndroidHost.query(id=self.id)
        if ins is None:
            raise ValueError(f'Physical Android device "{self.id}" not found.')
        if not isinstance(ins, PhysicalAndroidInstance):
            raise TypeError(f'Expected PhysicalAndroidInstance, got {type(ins)}')
        self.name = ins.name
        self.adb_serial = ins.adb_serial
        self.adb_name = ins.adb_name
        logger.debug('Refreshed physical Android instance: %s', repr(ins))

    @override
    def start(self):
        return

    @override
    def stop(self):
        return

    @override
    def running(self) -> bool:
        if self.adb_serial is None:
            raise ValueError('ADB serial is not set.')
        devices = adb.device_list()
        for d in devices:
            if d.serial == self.adb_serial:
                return d.get_state() == 'device'
        return False

    @override
    def wait_available(self, timeout: float = 180):
        cd = Countdown(timeout)
        it = Interval(1)
        while True:
            if self.running():
                return
            if cd.expired():
                raise TimeoutError(f'Physical Android device "{self.name}" is not available.')
            it.wait()

    @override
    def create_device(self, impl: PhysicalAndroidRecipes, host_config: AdbHostConfig) -> Device:
        if self.adb_serial is None:
            raise ValueError("ADB serial is not set and is required.")
        return super().create_device(impl, host_config, connect=False, disconnect=False)


class PhysicalAndroidHost(HostProtocol[PhysicalAndroidRecipes]):
    @staticmethod
    def installed() -> bool:
        return True

    @staticmethod
    def list() -> list[Instance]:
        instances: list[Instance] = []
        for d in adb.device_list():
            serial = d.serial
            state = d.get_state()
            name = f'{serial} ({state})'
            ins = PhysicalAndroidInstance(
                id=serial,
                name=name,
                adb_serial=serial,
                adb_name=serial,
            )
            instances.append(ins)
        return instances

    @staticmethod
    def query(*, id: str) -> Instance | None:
        for ins in PhysicalAndroidHost.list():
            if ins.id == id:
                return ins
        return None

    @staticmethod
    def recipes() -> 'list[Literal["adb", "uiautomator2"]]':
        return ['adb', 'uiautomator2']
