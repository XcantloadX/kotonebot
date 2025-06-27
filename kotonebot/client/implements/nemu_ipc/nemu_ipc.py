import os
import ctypes
import logging
import time
from dataclasses import dataclass
from time import sleep
from typing import Literal
from typing_extensions import override

import cv2
import numpy as np
from cv2.typing import MatLike

from ...device import AndroidDevice, Device
from ...protocol import Touchable, Screenshotable
from ...registration import ImplConfig
from .external_renderer_ipc import ExternalRendererIpc
from kotonebot.errors import KotonebotError

logger = logging.getLogger(__name__)


class NemuIpcIncompatible(Exception):
    """MuMu12 版本过低或 dll 不兼容"""
    pass


class NemuIpcError(KotonebotError):
    """调用 IPC 过程中发生错误"""
    pass


@dataclass
class NemuIpcImplConfig(ImplConfig):
    """nemu_ipc 能力的配置模型。"""
    nemu_folder: str
    r"""MuMu12 根目录（如 F:\Apps\Netease\MuMuPlayer-12.0）。"""
    instance_id: int
    """模拟器实例 ID。"""
    display_id: int | None = 0
    """目标显示器 ID，默认为 0（主显示器）。若为 None 且设置了 target_package_name，则自动获取对应的 display_id。"""
    target_package_name: str | None = None
    """目标应用包名，用于自动获取 display_id。"""
    app_index: int = 0
    """多开应用索引，传给 get_display_id 方法。"""
    wait_package_timeout: float = 60  # 单位秒，-1 表示永远等待，0 表示不等待，立即抛出异常
    wait_package_interval: float = 0.1  # 单位秒


class NemuIpcImpl(Touchable, Screenshotable):
    """
    利用 MuMu12 提供的 external_renderer_ipc.dll 进行截图与触摸控制。
    """

    def __init__(self, config: NemuIpcImplConfig):
        self.config = config
        self.__width: int = 0
        self.__height: int = 0
        self.__connected: bool = False
        self._connect_id: int = 0
        self.nemu_folder = config.nemu_folder

        # --------------------------- DLL 封装 ---------------------------
        self._ipc = ExternalRendererIpc(config.nemu_folder)
        logger.info("ExternalRendererIpc initialized and DLL loaded")

    @property
    def width(self) -> int:
        """
        屏幕宽度。
        
        若为 0，表示未连接或未获取到分辨率。
        """
        return self.__width
    
    @property
    def height(self) -> int:
        """
        屏幕高度。
        
        若为 0，表示未连接或未获取到分辨率。
        """
        return self.__height
    
    @property
    def connected(self) -> bool:
        """是否已连接。"""
        return self.__connected

    # ------------------------------------------------------------------
    # 基础控制
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> None:
        if not self.__connected:
            self.connect()

    def _get_display_id(self) -> int:
        """获取有效的 display_id。"""
        # 如果配置中直接指定了 display_id，直接返回
        if self.config.display_id is not None:
            return self.config.display_id

        # 如果设置了 target_package_name，实时获取 display_id
        if self.config.target_package_name:
            self._ensure_connected()

            timeout = self.config.wait_package_timeout
            interval = self.config.wait_package_interval
            if timeout == -1:
                timeout = float('inf')
            start_time = time.time()
            while True:
                display_id = self._ipc.get_display_id(
                    self._connect_id,
                    self.config.target_package_name,
                    self.config.app_index
                )
                if display_id >= 0:
                    return display_id
                elif display_id == -1:
                    # 可以继续等
                    pass
                else:
                    # 未知错误
                    raise NemuIpcError(f"Failed to get display_id for package '{self.config.target_package_name}', error code={display_id}")
                if time.time() - start_time > timeout:
                    break
                sleep(interval)
            
            raise NemuIpcError(f"Failed to get display_id for package '{self.config.target_package_name}' within {timeout}s")

        # 如果都没有设置，抛出错误
        raise NemuIpcError("display_id is None and target_package_name is not set. Please set display_id or target_package_name in config.")

    def connect(self) -> None:
        """连接模拟器。"""
        if self.__connected:
            return

        connect_id = self._ipc.connect(self.nemu_folder, self.config.instance_id)
        if connect_id == 0:
            raise NemuIpcError("nemu_connect failed, please check if the emulator is running and the instance ID is correct.")

        self._connect_id = connect_id
        self.__connected = True
        logger.debug("NemuIpc connected, connect_id=%d", connect_id)

    def disconnect(self) -> None:
        """断开连接。"""
        if not self.__connected:
            return
        self._ipc.disconnect(self._connect_id)
        self.__connected = False
        self._connect_id = 0
        logger.debug("NemuIpc disconnected.")

    # ------------------------------------------------------------------
    # Screenshotable 接口实现
    # ------------------------------------------------------------------
    @property
    def screen_size(self) -> tuple[int, int]:
        """获取屏幕分辨率。"""
        if self.__width == 0 or self.__height == 0:
            self._refresh_resolution()
        if self.__width == 0 or self.__height == 0:
            raise NemuIpcError("Screen resolution not obtained, please connect to the emulator first.")
        return self.__width, self.__height

    @override
    def detect_orientation(self):
        return self.get_display_orientation(self._get_display_id())

    def get_display_orientation(self, display_id: int = 0) -> Literal['portrait', 'landscape'] | None:
        """获取指定显示屏的方向。"""
        width, height = self.query_resolution(display_id)
        if width > height:
            return "landscape"
        if height > width:
            return "portrait"
        return None

    @override
    def screenshot(self) -> MatLike:
        self._ensure_connected()

        # 必须每次都更新分辨率，因为屏幕可能会旋转
        self._refresh_resolution()

        length = self.__width * self.__height * 4 # RGBA
        buf_type = ctypes.c_ubyte * length
        buffer = buf_type()

        w_ptr = ctypes.pointer(ctypes.c_int(self.__width))
        h_ptr = ctypes.pointer(ctypes.c_int(self.__height))

        ret = self._ipc.capture_display(
            self._connect_id,
            self._get_display_id(),
            length,
            ctypes.cast(w_ptr, ctypes.c_void_p),
            ctypes.cast(h_ptr, ctypes.c_void_p),
            ctypes.cast(buffer, ctypes.c_void_p),
        )
        if ret != 0:
            raise NemuIpcError(f"nemu_capture_display screenshot failed, error code={ret}")

        # 读入并转换数据
        img = np.ctypeslib.as_array(buffer).reshape((self.__height, self.__width, 4))
        # RGBA -> BGR
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        cv2.flip(img, 0, dst=img)
        return img

    # --------------------------- 内部工具 -----------------------------

    def _refresh_resolution(self) -> None:
        """刷新分辨率信息。"""
        display_id = self._get_display_id()
        self.__width, self.__height = self.query_resolution(display_id)

    def query_resolution(self, display_id: int = 0) -> tuple[int, int]:
        """
        查询指定显示屏的分辨率。
        
        :param display_id: 显示屏 ID。
        :return: 分辨率 (width, height)。
        :raise NemuIpcError: 查询失败。
        """
        self._ensure_connected()

        w_ptr = ctypes.pointer(ctypes.c_int(0))
        h_ptr = ctypes.pointer(ctypes.c_int(0))
        ret = self._ipc.capture_display(
            self._connect_id,
            display_id,
            0,
            ctypes.cast(w_ptr, ctypes.c_void_p),
            ctypes.cast(h_ptr, ctypes.c_void_p),
            ctypes.c_void_p(),
        )
        if ret != 0:
            raise NemuIpcError(f"Call nemu_capture_display failed. Return value={ret}")

        return w_ptr.contents.value, h_ptr.contents.value

    # ------------------------------------------------------------------
    # Touchable 接口实现
    # ------------------------------------------------------------------
    def __convert_pos(self, x: int, y: int) -> tuple[int, int]:
        # Android 显示屏有两套坐标：逻辑坐标与物理坐标。
        # 逻辑坐标原点始终是画面左上角，而物理坐标原点则始终是显示屏的左上角。
        # 如果屏幕画面旋转，会导致两个坐标的原点不同，坐标也不同。
        # ========
        # 这里传给 MuMu 的是逻辑坐标，ExternalRendererIpc DLL 内部会
        # 自动判断旋转，并转换为物理坐标。但是这部分有个 bug：
        # 旋转没有考虑到多显示器，只是以主显示器为准，若两个显示器旋转不一致，
        # 会导致错误地转换坐标。因此需要在 Python 层面 workaround 这个问题。
        # 通过判断主显示器与当前显示器的旋转，将坐标进行预转换，抵消 DLL 层的错误转换。
        display_id = self._get_display_id()
        if display_id == 0:
            return x, y
        else:
            primary = self.get_display_orientation(0)
            primary_size = self.query_resolution(0)
            current = self.get_display_orientation(display_id)
            if primary == current:
                return x, y
            else:
                # 如果旋转不一致，视为顺时针旋转了 90°
                # 因此我们要提前逆时针旋转 90°
                self._refresh_resolution()
                x, y = y, primary_size[1] - x
                return x, y
    
    @override
    def click(self, x: int, y: int) -> None:
        self._ensure_connected()
        display_id = self._get_display_id()
        x, y = self.__convert_pos(x, y)
        self._ipc.input_touch_down(self._connect_id, display_id, x, y)
        sleep(0.01)
        self._ipc.input_touch_up(self._connect_id, display_id)

    @override
    def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float | None = None,
    ) -> None:
        self._ensure_connected()

        duration = duration or 0.3
        steps = max(int(duration / 0.01), 2)
        display_id = self._get_display_id()
        x1, y1 = self.__convert_pos(x1, y1)
        x2, y2 = self.__convert_pos(x2, y2)

        xs = np.linspace(x1, x2, steps, dtype=int)
        ys = np.linspace(y1, y2, steps, dtype=int)

        # 按下第一点
        self._ipc.input_touch_down(self._connect_id, display_id, xs[0], ys[0])
        sleep(0.01)
        # 中间移动
        for px, py in zip(xs[1:-1], ys[1:-1]):
            self._ipc.input_touch_down(self._connect_id, display_id, px, py)
            sleep(0.01)

        # 最终抬起
        self._ipc.input_touch_up(self._connect_id, display_id)
        sleep(0.01)
        
if __name__ == '__main__':
    nemu = NemuIpcImpl(NemuIpcImplConfig(
        r'F:\Apps\Netease\MuMuPlayer-12.0', 0, None,
        target_package_name='com.android.chrome',
    ))
    nemu.connect()
    # while True:
    #     nemu.click(0, 0)
    nemu.click(100, 100)
    nemu.click(100*3, 100)
    nemu.click(100*3, 100*3)
