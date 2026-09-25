"""ADB 设备实现。"""

import logging
import re
import struct
from dataclasses import dataclass
from typing import Literal, cast

import cv2
import numpy as np
from cv2.typing import MatLike
from typing_extensions import override

try:
    from adbutils._device import AdbDevice as AdbUtilsDevice
    from adbutils.errors import AdbError
except ImportError as _e:
    from kotonebot.errors import MissingDependencyError
    raise MissingDependencyError(_e, 'android')

from ..protocol import AndroidCommandable, Touchable, Screenshotable, SimpleInputDriver
from ..registration import ImplConfig
from kotonebot.errors import DeviceConnectionError, DeviceNotReadyError

logger = logging.getLogger(__name__)

# 定义配置模型
@dataclass
class AdbImplConfig(ImplConfig):
    addr: str
    connect: bool = True
    disconnect: bool = True
    device_serial: str | None = None
    display_id: int | None = None
    timeout: float = 180

class AdbImpl(AndroidCommandable, Touchable, Screenshotable, SimpleInputDriver):
    def __init__(self, adb_connection: AdbUtilsDevice, display_id: int | None = None):
        self.adb = adb_connection
        self.display_id = display_id

    def _display_context(self) -> str:
        if self.display_id is None:
            return 'default display'
        return f'display_id={self.display_id}'
    
    def _format_message(self, message: str) -> str:
        if self.display_id is None:
            return message
        return f'{message} ({self._display_context()})'

    def _build_input(self, command: str, *args: int | str, source: str | None = None) -> list[str]:
        cmdargs = ['input']
        if source is not None:
            cmdargs.append(source)
        if self.display_id is not None:
            # AOSP shell syntax is: input [<source>] [-d DISPLAY_ID] <command> [<arg>...].
            # Source:
            # https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/input/InputShellCommand.java
            cmdargs.extend(['-d', str(self.display_id)])
        cmdargs.append(command)
        cmdargs.extend(str(arg) for arg in args)
        return cmdargs

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

    def adb_shell(self, cmd: str) -> str:
        """执行 ADB shell 命令"""
        return cast(str, self.adb.shell(cmd))

    def install_apk(self, path: str) -> None:
        """安装 APK 文件"""
        self.adb.install(path)

    @override
    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        """检测当前设备方向。

        通过截图宽高比判断方向。当截图不可用（例如截图数据截断）时
        返回 None，表示无法检测，调用方可跳过方向相关逻辑。

        :returns: 检测到的方向，无法检测时返回 None。
        """
        # 判断方向：https://stackoverflow.com/questions/10040624/check-if-device-is-landscape-via-adb
        # 但是上面这种方法不准确
        # 因此这里直接通过截图判断方向
        try:
            img = self.screenshot()
        except DeviceConnectionError as e:
            # 截图失败属于瞬态故障（例如 screencap 数据截断），不向上传播，
            # 返回 None 让调用方跳过方向判断。
            logger.warning('Skipping orientation detection as screenshot is unavailable: %s', e)
            return None
        if img.shape[0] > img.shape[1]:
            return 'portrait'
        return 'landscape'
    
    @property
    def screen_size(self) -> tuple[int, int]:
        cmdargs = ['wm', 'size']
        if self.display_id is not None:
            # AOSP supports querying a specific display with "wm size -d DISPLAY_ID".
            # Source:
            # https://android.googlesource.com/platform/frameworks/base/+/master/services/core/java/com/android/server/wm/WindowManagerShellCommand.java
            cmdargs.extend(['-d', str(self.display_id)])    
        output = self.adb.shell(cmdargs)
        logger.debug('wm size output for %s: %s', self._display_context(), output)
        text = cast(str, output)
        m = re.search(r'Override\s+size:\s*(\d+)\s*[xX×]\s*(\d+)', text)
        size_source = 'override'
        if not m:
            m = re.search(r'Physical\s+size:\s*(\d+)\s*[xX×]\s*(\d+)', text)
            size_source = 'physical'
        if not m:
            m = re.search(r'(\d+)\s*[xX×]\s*(\d+)', text)
            size_source = 'generic'
        if not m:
            raise ValueError(self._format_message(f"Invalid screen size: {text}"))
        spiltted = (int(m.group(1)), int(m.group(2)))
        logger.debug('wm size picked %s size: %s', size_source, spiltted)
        # 检测当前方向
        orientation = self.detect_orientation()
        landscape = orientation == 'landscape'
        spiltted = tuple(sorted(spiltted, reverse=landscape))
        if len(spiltted) != 2:
            raise ValueError(self._format_message(f"Invalid screen size: {text}"))
        return spiltted

    def screenshot(self) -> MatLike:
        """截取当前屏幕。

        :returns: BGR 格式的截图数据。
        :raises DeviceNotReadyError: 截图数据截断或图片损坏时抛出。
        """
        # adbutils already converts the display index into the SurfaceFlinger display ID
        # required by "screencap -d".
        # Source:
        # https://android.googlesource.com/platform/frameworks/base/+/master/cmds/screencap/screencap.cpp
        try:
            image = self.adb.screenshot(display_id=self.display_id, error_ok=False)
            image.load() # 立刻求值检验图片是否有效
        except AdbError as exc:
            raise AdbError(self._format_message(str(exc))) from exc
        except (OSError, SyntaxError, struct.error) as exc:
            # PIL 解析截断 PNG 时的错误路径：
            # OSError("image file is truncated")
            # SyntaxError("broken PNG file")
            # struct.error("unpack_from requires a buffer of ...")
            logger.warning('ADB screenshot data is truncated, treating device as not ready: %s', exc)
            raise DeviceNotReadyError(self._format_message(str(exc))) from exc
        try:
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        except (ValueError, cv2.error) as exc:
            logger.warning('ADB screenshot conversion failed, treating device as not ready: %s', exc)
            raise DeviceNotReadyError(self._format_message(str(exc))) from exc

    def click(self, x: int, y: int) -> None:
        self.adb.shell(self._build_input('tap', x, y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        if duration is not None:
            logger.warning("Swipe duration is not supported with AdbDevice. Ignoring duration.")
        self.adb.shell(self._build_input('swipe', x1, y1, x2, y2, source='touchscreen'))
