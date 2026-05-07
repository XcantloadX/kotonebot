from abc import ABC
from typing import Literal
from typing_extensions import assert_never

from kotonebot import logging
from kotonebot.client.device import WindowsDevice
from kotonebot.util import require_windows
from .protocol import Device, WindowsHostConfig

logger = logging.getLogger(__name__)
WindowsRecipes = Literal['windows', 'windows_background']

# Windows 相关的配置类型联合
WindowsHostConfigs = WindowsHostConfig

class CommonWindowsCreateDeviceMixin(ABC):
    """
    通用 Windows 创建设备的 Mixin。
    该 Mixin 定义了创建 Windows 设备的通用接口。
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        require_windows('CommonWindowsCreateDeviceMixin', self.__class__)
    
    def create_device(self, recipe: WindowsRecipes, config: WindowsHostConfigs) -> Device:
        """
        创建 Windows 设备。
        """
        require_windows('CommonWindowsCreateDeviceMixin.create_device', self.__class__)
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
                d.setup(screenshot=impl, touch=impl)
                return d
            case 'windows_background':
                if not isinstance(config, WindowsHostConfig):
                    raise ValueError(f"Expected WindowsHostConfig for 'windows' recipe, got {type(config)}")
                d = WindowsDevice()
                from kotonebot.client.implements.windows.send_message import SendMessageImpl
                from kotonebot.client.implements.windows.print_window import PrintWindowImpl
                d.setup(
                    screenshot=PrintWindowImpl(d, config.window_title),
                    touch=SendMessageImpl(d, config.window_title),
                )
                return d
            case _:
                assert_never(f'Unsupported Windows recipe: {recipe}')
