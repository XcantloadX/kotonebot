import os
import ctypes
import logging
from dataclasses import dataclass
from time import sleep
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
            display_id = self._ipc.get_display_id(
                self._connect_id,
                self.config.target_package_name,
                self.config.app_index
            )
            # 当程序未启动时，返回值为 -1
            # if display_id == -1:
            #     return None
            if display_id < 0:
                raise NemuIpcError(f"Failed to get display_id for package '{self.config.target_package_name}', error code={display_id}")
            # logger.debug("Real-time display_id=%d for package '%s'", display_id, self.config.target_package_name)
            return display_id

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
            self._query_resolution()
        if self.__width == 0 or self.__height == 0:
            raise NemuIpcError("Screen resolution not obtained, please connect to the emulator first.")
        return self.__width, self.__height

    @override
    def detect_orientation(self):
        if self.__width > self.__height:
            return "landscape"
        if self.__height > self.__width:
            return "portrait"
        return None

    @override
    def screenshot(self) -> MatLike:
        self._ensure_connected()

        # 必须每次都更新分辨率，因为屏幕可能会旋转
        self._query_resolution()

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

    def _query_resolution(self) -> None:
        """调用 capture 接口并返回宽高信息，不取像素数据。"""
        self._ensure_connected()

        w_ptr = ctypes.pointer(ctypes.c_int(0))
        h_ptr = ctypes.pointer(ctypes.c_int(0))
        ret = self._ipc.capture_display(
            self._connect_id,
            self._get_display_id(),
            0,
            ctypes.cast(w_ptr, ctypes.c_void_p),
            ctypes.cast(h_ptr, ctypes.c_void_p),
            ctypes.c_void_p(),
        )
        if ret != 0:
            raise NemuIpcError(f"nemu_capture_display 查询分辨率失败，错误码={ret}")

        self.__width = w_ptr.contents.value
        self.__height = h_ptr.contents.value
        # logger.debug("Parsed resolution %dx%d", self.__width, self.__height)

    # ------------------------------------------------------------------
    # Touchable 接口实现
    # ------------------------------------------------------------------
    def convert_xy(self, x: int, y: int):
        display_id = self._get_display_id()
        if display_id > 0:
            # 在非主显示器上，坐标系原点为右上角，且坐标格式为 (y, x)
            self._query_resolution()
            x = self.width - x
            return y, x
        else:
            return x, y
    
    @override
    def click(self, x: int, y: int) -> None:
        self._ensure_connected()
        display_id = self._get_display_id()
        x, y = self.convert_xy(x, y)
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
        x1, y1 = self.convert_xy(x1, y1)
        x2, y2 = self.convert_xy(x2, y2)

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
        target_package_name='com.bandainamcoent.idolmaster_gakuen',
    ))
    nemu.connect()
    while True:
        nemu.click(0, 0)
