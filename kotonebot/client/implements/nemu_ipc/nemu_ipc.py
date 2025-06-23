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
from ...registration import register_impl, ImplConfig
from .external_renderer_ipc import ExternalRendererIpc

logger = logging.getLogger(__name__)


class NemuIpcIncompatible(Exception):
    """MuMu12 版本过低或 dll 不兼容"""
    pass


class NemuIpcError(Exception):
    """调用 IPC 过程中发生错误"""
    pass


@dataclass
class NemuIpcImplConfig(ImplConfig):
    """nemu_ipc 设备实现的配置模型"""
    mumu_shell_folder: str
    instance_id: int


class NemuIpcImpl(Touchable, Screenshotable):
    """
    利用 MuMu12 提供的 external_renderer_ipc.dll 进行截图与触摸控制。
    """

    def __init__(self, device: Device, config: NemuIpcImplConfig):
        self.device = device
        self.config = config
        self.__width: int = 0
        self.__height: int = 0
        self.__connected: bool = False
        self._connect_id: int = 0
        self.display_id: int = 0
        """
        显示器 ID。`0` 表示主显示器。
        
        如果没有启用「后台保活」功能，一般为主显示器。
        """
        self.nemu_folder = os.path.abspath(os.path.join(config.mumu_shell_folder, os.pardir))

        # --------------------------- DLL 封装 ---------------------------
        self._ipc = ExternalRendererIpc(config.mumu_shell_folder)
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

        # 确保分辨率已知
        _ = self.screen_size

        length = self.__width * self.__height * 4 # RGBA
        buf_type = ctypes.c_ubyte * length
        buffer = buf_type()

        w_ptr = ctypes.pointer(ctypes.c_int(self.__width))
        h_ptr = ctypes.pointer(ctypes.c_int(self.__height))

        ret = self._ipc.capture_display(
            self._connect_id,
            self.display_id,
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
            self.display_id,
            0,
            ctypes.cast(w_ptr, ctypes.c_void_p),
            ctypes.cast(h_ptr, ctypes.c_void_p),
            ctypes.c_void_p(),
        )
        if ret != 0:
            raise NemuIpcError(f"nemu_capture_display 查询分辨率失败，错误码={ret}")

        self.__width = w_ptr.contents.value
        self.__height = h_ptr.contents.value
        logger.debug("Parsed resolution %dx%d", self.__width, self.__height)

    # ------------------------------------------------------------------
    # Touchable 接口实现
    # ------------------------------------------------------------------
    @override
    def click(self, x: int, y: int) -> None:
        self._ensure_connected()
        self._ipc.input_touch_down(self._connect_id, self.display_id, x, y)
        sleep(0.01)
        self._ipc.input_touch_up(self._connect_id, self.display_id)

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
        xs = np.linspace(x1, x2, steps, dtype=int)
        ys = np.linspace(y1, y2, steps, dtype=int)

        # 按下第一点
        self._ipc.input_touch_down(self._connect_id, self.display_id, xs[0], ys[0])
        sleep(0.01)
        # 中间移动
        for px, py in zip(xs[1:-1], ys[1:-1]):
            self._ipc.input_touch_down(self._connect_id, self.display_id, px, py)
            sleep(0.01)

        # 最终抬起
        self._ipc.input_touch_up(self._connect_id, self.display_id)
        sleep(0.01)

# ------------------------------------------------------------------
# 工厂方法
# ------------------------------------------------------------------
@register_impl("nemu_ipc", config_model=NemuIpcImplConfig)
def create_nemu_ipc_device(config: NemuIpcImplConfig):
    """创建一个 AndroidDevice，并挂载 NemuIpcImpl。"""
    device = AndroidDevice()
    impl = NemuIpcImpl(device, config)
    device._touch = impl
    device._screenshot = impl
    return device 