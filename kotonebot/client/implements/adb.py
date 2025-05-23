import logging
from typing import cast
from typing_extensions import override

import cv2
import numpy as np
from cv2.typing import MatLike

from ..device import Device
from ..protocol import Commandable, Touchable, Screenshotable

logger = logging.getLogger(__name__)

class AdbImpl(Commandable, Touchable, Screenshotable):
    def __init__(self, device: Device):
        self.device = device
        self.adb = device.adb

    @override
    def launch_app(self, package_name: str) -> None:
        self.adb.shell(f"monkey -p {package_name} 1")

    @override
    def current_package(self) -> str | None:
        # https://blog.csdn.net/guangdeshishe/article/details/117154406
        result_text = self.adb.shell('dumpsys activity top | grep ACTIVITY | tail -n 1')
        logger.debug(f"adb returned: {result_text}")
        if not isinstance(result_text, str):
            logger.error(f"Invalid result_text: {result_text}")
            return None
        result_text = result_text.strip()
        if result_text == '':
            logger.error("No current package found")
            return None
        _, activity, *_ = result_text.split(' ')
        package = activity.split('/')[0]
        return package

    @override
    def detect_orientation(self):
        # 判断方向：https://stackoverflow.com/questions/10040624/check-if-device-is-landscape-via-adb
        # 但是上面这种方法不准确
        # 因此这里直接通过截图判断方向
        img = self.screenshot()
        if img.shape[0] > img.shape[1]:
            return 'portrait'
        return 'landscape'
    
    @property
    def screen_size(self) -> tuple[int, int]:
        ret = cast(str, self.adb.shell("wm size")).strip('Physical size: ')
        spiltted = tuple(map(int, ret.split("x")))
        landscape = self.device.orientation == 'landscape'
        spiltted = tuple(sorted(spiltted, reverse=landscape))
        if len(spiltted) != 2:
            raise ValueError(f"Invalid screen size: {ret}")
        return spiltted

    def screenshot(self) -> MatLike:
        return cv2.cvtColor(np.array(self.adb.screenshot()), cv2.COLOR_RGB2BGR)

    def click(self, x: int, y: int) -> None:
        self.adb.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        if duration is not None:
            logger.warning("Swipe duration is not supported with AdbDevice. Ignoring duration.")
        self.adb.shell(f"input touchscreen swipe {x1} {y1} {x2} {y2}")
