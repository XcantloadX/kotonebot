from abc import ABC
from typing import Literal
from typing_extensions import assert_never

from kotonebot import logging
from kotonebot.client.device import WindowsDevice
from .protocol import Device, WindowsHostConfig, RemoteWindowsHostConfig

logger = logging.getLogger(__name__)
WindowsRecipes = Literal['windows', 'remote_windows']

# Windows 相关的配置类型联合
WindowsHostConfigs = WindowsHostConfig | RemoteWindowsHostConfig

class CommonWindowsCreateDeviceMixin(ABC):
    """
    通用 Windows 创建设备的 Mixin。
    该 Mixin 定义了创建 Windows 设备的通用接口。
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
    
    def create_device(self, recipe: WindowsRecipes, config: WindowsHostConfigs) -> Device:
        """
        创建 Windows 设备。
        """
        match recipe:
            case 'windows':
                if not isinstance(config, WindowsHostConfig):
                    raise ValueError(f"Expected WindowsHostConfig for 'windows' recipe, got {type(config)}")
                from kotonebot.client.implements.windows import WindowsImpl
                d = WindowsDevice()
                impl = WindowsImpl(
                    device=d,
                    window_title=config.window_title,
                    ahk_exe_path=config.ahk_exe_path
                )
                d._screenshot = impl
                d._touch = impl
                return d
            case 'remote_windows':
                if not isinstance(config, RemoteWindowsHostConfig):
                    raise ValueError(f"Expected RemoteWindowsHostConfig for 'remote_windows' recipe, got {type(config)}")
                from kotonebot.client.implements.remote_windows import RemoteWindowsImpl
                d = WindowsDevice()
                impl = RemoteWindowsImpl(
                    device=d,
                    host=config.host,
                    port=config.port
                )
                d._screenshot = impl
                d._touch = impl
                return d
            case _:
                assert_never(f'Unsupported Windows recipe: {recipe}')
