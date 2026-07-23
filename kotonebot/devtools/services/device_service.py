"""ADB 设备操作服务。

从 RestApiLogic 提取，封装设备列表查询和截图功能。
"""

import logging
import time

import cv2
import numpy as np

from kotonebot.devtools.path_utils import CACHE_DEVICE_CAPTURES, to_rel
from kotonebot.devtools.project.project import Project
from .types import DeviceInfo, DeviceListResult, DeviceScreenshotResult


class DeviceService:
    """ADB 设备操作服务。"""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.pyproject_root = project.pyproject_root
        self.capture_cache_root = project.pyproject_root / CACHE_DEVICE_CAPTURES

    def list_adb_devices(self) -> DeviceListResult:
        """列出已连接的 ADB 设备。

        :returns: 设备列表结果
        """
        try:
            from adbutils import adb
        except ImportError:
            return DeviceListResult(devices=[], error="adbutils not installed. Please install it with: pip install adbutils")

        devices = []
        for d in adb.device_list():
            serial = d.serial
            state = d.get_state()
            name = f"{serial} ({state})"
            devices.append(DeviceInfo(serial=serial, state=state, name=name))
        return DeviceListResult(devices=devices)

    def capture_screenshot(self, serial: str, display_id: int | None = None) -> DeviceScreenshotResult:
        """截取设备屏幕。

        :param serial: 设备序列号
        :param display_id: 显示 ID（可选）
        :returns: 截图结果
        """
        try:
            from adbutils import adb, AdbDevice
            from adbutils.errors import AdbError
        except ImportError:
            return DeviceScreenshotResult(success=False, error="adbutils not installed. Please install it with: pip install adbutils")

        try:
            device: AdbDevice | None = None
            for d in adb.device_list():
                if d.serial == serial:
                    device = d
                    break

            if device is None:
                return DeviceScreenshotResult(success=False, error=f"Device '{serial}' not found")

            state = device.get_state()
            if state != "device":
                return DeviceScreenshotResult(success=False, error=f"Device '{serial}' is not available (state: {state})")

            image = device.screenshot(display_id=display_id, error_ok=False)
            bgr_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

            self.capture_cache_root.mkdir(parents=True, exist_ok=True)

            timestamp = int(time.time() * 1000)
            filename = f"capture_{serial.replace(':', '_')}_{timestamp}.png"
            temp_path = self.capture_cache_root / filename

            cv2.imwrite(str(temp_path), bgr_image)

            root = self.pyproject_root
            rel_path = to_rel(temp_path, root)
            return DeviceScreenshotResult(success=True, imagePath=rel_path)
        except AdbError as e:
            return DeviceScreenshotResult(success=False, error=f"ADB error: {str(e)}")
        except Exception as e:
            logging.exception("Error capturing device screenshot")
            return DeviceScreenshotResult(success=False, error=str(e))
