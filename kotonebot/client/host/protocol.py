import time
import socket
from typing import Protocol, NamedTuple
from dataclasses import dataclass

from adbutils import adb, AdbTimeout, AdbError
from adbutils._device import AdbDevice

from kotonebot import logging
from kotonebot.util import Countdown, Interval

logger = logging.getLogger(__name__)

def tcp_ping(host: str, port: int, timeout: float = 1.0) -> bool:
    """
    通过 TCP ping 检查主机和端口是否可达。
    
    :param host: 主机名或 IP 地址
    :param port: 端口号
    :param timeout: 超时时间（秒）
    :return: 如果主机和端口可达，则返回 True，否则返回 False
    """
    logger.debug('TCP ping %s:%d...', host, port)
    try:
        with socket.create_connection((host, port), timeout):
            logger.debug('TCP ping %s:%d success.', host, port)
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        logger.debug('TCP ping %s:%d failed.', host, port)
        return False


@dataclass
class Instance:
    id: str
    name: str
    adb_port: int
    adb_ip: str = '127.0.0.1'
    adb_emulator_name: str = 'emulator-5554'

    def start(self):
        raise NotImplementedError()
    
    def stop(self):
        raise NotImplementedError()

    def running(self) -> bool:
        raise NotImplementedError()

    def wait_available(self, timeout: float = 180):
        logger.info('Starting to wait for emulator %s(127.0.0.1:%d) to be available...', self.name, self.adb_port)
        state = 0
        port = self.adb_port
        emulator_name = self.adb_emulator_name
        cd = Countdown(timeout)
        it = Interval(1)
        d: AdbDevice | None = None
        while True:
            if cd.expired():
                raise TimeoutError(f"Emulator {self.name} is not available.")
            it.wait()
            try:
                match state:
                    case 0:
                        logger.debug('Ping emulator %s(127.0.0.1:%d)...', self.name, port)
                        if tcp_ping('127.0.0.1', port):
                            logger.debug('Ping emulator %s(127.0.0.1:%d) success.', self.name, port)
                            state = 1
                    case 1:
                        logger.debug('Connecting to emulator %s(127.0.0.1:%d)...', self.name, port)
                        if adb.connect(f'127.0.0.1:{port}', timeout=0.5):
                            logger.debug('Connect to emulator %s(127.0.0.1:%d) success.', self.name, port)
                            state = 2
                    case 2:
                        logger.debug('Getting device list...')
                        if devices := adb.device_list():
                            logger.debug('Get device list success. devices=%s', devices)
                            # emulator_name 用于适配雷电模拟器
                            # 雷电模拟器启动后，在上方的列表中并不会出现 127.0.0.1:5555，而是 emulator-5554
                            d = next(
                                (d for d in devices if d.serial == f'127.0.0.1:{port}' or d.serial == emulator_name),
                                None
                            )
                            if d:
                                logger.debug('Get target device success. d=%s', d)
                                state = 3
                    case 3:
                        if not d:
                            logger.warning('Device is None.')
                            state = 0
                            continue
                        logger.debug('Waiting for device state...')
                        if d.get_state() == 'device':
                            logger.debug('Device state ready. state=%s', d.get_state())
                            state = 4
                    case 4:
                        logger.debug('Waiting for device boot completed...')
                        if not d:
                            logger.warning('Device is None.')
                            state = 0
                            continue
                        ret = d.shell('getprop sys.boot_completed')
                        if isinstance(ret, str) and ret.strip() == '1':
                            logger.debug('Device boot completed. ret=%s', ret)
                            state = 5
                    case 5:
                        if not d:
                            logger.warning('Device is None.')
                            state = 0
                            continue
                        app = d.app_current()
                        logger.debug('Waiting for launcher... (current=%s)', app)
                        if app and 'launcher' in app.package:
                            logger.info('Emulator %s(127.0.0.1:%d) now is available.', self.name, self.adb_port)
                            state = 6
                    case 6:
                        break
            except (AdbError, AdbTimeout):
                state = 1
                continue
        time.sleep(1)
        logger.info('Emulator %s(127.0.0.1:%d) now is available.', self.name, self.adb_port)


class HostProtocol(Protocol):
    @staticmethod
    def installed() -> bool: ...
    @staticmethod
    def list() -> list[Instance]: ...


if __name__ == '__main__':
    from . import bluestack_global
    from pprint import pprint
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s][%(levelname)s] %(message)s')
    # bluestack_global.
    ins = Instance(id='1', name='test', adb_port=5555)
    ins.wait_available()

    # 
    # while not tcp_ping('127.0.0.1', 16384):
    #     print('waiting for bluestacks to start...')
    
    # while True:
    #     print('connecting to bluestacks...')
    #     try:
    #         adb.connect('127.0.0.1:16384', timeout=0.1)
    #         print('connected to bluestacks')
    #         if d := adb.device_list()[0]:
    #             if d.get_state() == 'device':
    #                 if d.shell('getprop sys.boot_completed').strip() == '1':
    #                     if 'launcher' in d.app_current().package:
    #                         break
    #     except Exception as e:
    #         print(e)
    #     time.sleep(0.5)
    # time.sleep(1)
    # print('bluestacks is ready')
