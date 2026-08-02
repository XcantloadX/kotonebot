from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable
from contextvars import ContextVar

if TYPE_CHECKING:
    from kotonebot import Loop
    from kotonebot.client.scaler import AbstractScaler
from kotonebot.primitives import Size

@dataclass
class DeviceConfig:
    default_scaler_factory: 'Callable[[], AbstractScaler]'
    """Device 类默认使用缩放方法类的构造器。
    
    构造 Device 实例时，可以在构造方法中指定 scaler。若未指定，则使用此处的默认值。
    默认使用的 scaler 为 :class:`ProportionalScaler`，即等比例缩放。对于非等比例缩放，
    会直接抛出异常。
    """
    default_logic_resolution: Size | None
    """Device 默认逻辑分辨率。
    
    若为 None，则不进行缩放。
    """


@dataclass
class LoopConfig:
    loop_callbacks: 'list[Callable[[Loop], bool]]' = field(default_factory=list)
    """全局 Loop 回调函数。
    
    每次 Loop 循环一次时，都会调用此处的处理函数。
    可以在这里放置一些需要全局处理的内容，如网络错误等。
    """

@dataclass
class Config:
    device: DeviceConfig
    loop: LoopConfig


_global_config: ContextVar[Config | None] = ContextVar('kotonebot_global_config', default=None)

def conf(*, auto_create: bool = True) -> Config:
    """获取全局配置对象。

    :return: 全局配置对象。
    """
    c = _global_config.get()
    if c is None:
        if not auto_create:
            raise RuntimeError('Global config is not set.')
        from kotonebot.client.scaler import ProportionalScaler
        c = Config(
            device=DeviceConfig(
                default_scaler_factory=lambda: ProportionalScaler(),
                default_logic_resolution=None
            ),
            loop=LoopConfig()
        )
        _global_config.set(c)
    return c