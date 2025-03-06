import subprocess
from psutil import process_iter
from .protocol import HostProtocol, Instance
from typing import Optional, ParamSpec, TypeVar, TypeGuard
from typing_extensions import override

from kotonebot import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')

class CustomInstance(Instance):
    def __init__(self, exe_path: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exe_path: str = exe_path
        self.process: subprocess.Popen | None = None

    @override
    def start(self):
        if self.process:
            logger.warning('Process is already running.')
            return
        logger.info('Starting process "%s"...', self.exe_path)
        self.process = subprocess.Popen(self.exe_path)

    @override
    def stop(self):
        if not self.process:
            logger.warning('Process is not running.')
            return
        logger.info('Stopping process "%s"...', self.process.pid)
        self.process.terminate()
        self.process.wait()
        self.process = None

def _type_check(ins: Instance) -> CustomInstance:
    if not isinstance(ins, CustomInstance):
        raise ValueError(f'Instance {ins} is not a CustomInstance')
    return ins

def create(exe_path: str, adb_ip: str, adb_port: int) -> CustomInstance:
    return CustomInstance(exe_path, id='custom', name='Custom', adb_ip=adb_ip, adb_port=adb_port)


if __name__ == '__main__':
    ins = create(r'C:\Program Files\BlueStacks_nxt\HD-Player.exe', '127.0.0.1', 5555)
    ins.start()
    ins.wait_available()
    input('Press Enter to stop...')
    ins.stop()
