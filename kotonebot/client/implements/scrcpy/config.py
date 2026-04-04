from dataclasses import dataclass, field
from typing import Literal

from ...host.protocol import AdbHostConfig


CleanupStrategy = Literal['owned_only', 'aggressive']


@dataclass(slots=True)
class VirtualDisplayConfig:
    enabled: bool = True
    """是否启用虚拟显示器。"""
    reuse_existing: bool = True
    """
    是否优先复用已有虚拟显示器。

    若启用，且设备上已存在一个与配置完全匹配的虚拟显示器，则会复用该显示器而非创建新显示器。
    匹配条件包括：尺寸、包名。
    """
    width: int | None = None
    """虚拟显示器宽度。"""
    height: int | None = None
    """虚拟显示器高度。"""
    dpi: int | None = None
    """虚拟显示器 DPI。"""
    destroy_content: bool | None = None
    """关闭时是否销毁虚拟显示器。"""
    system_decorations: bool | None = None
    """是否启用系统装饰。"""
    launch_package: str | None = None
    """创建显示器后自动启动的 APP。"""


@dataclass(slots=True, kw_only=True)
class ScrcpyConfig(AdbHostConfig):
    server_jar_path: str
    """scrcpy server jar 的本地路径。"""
    server_version: str
    """scrcpy server 版本号。"""
    device_serial: str | None = None
    """目标设备序列号。"""
    video: bool = True
    """是否启用视频流。"""
    audio: bool = False
    """是否启用音频流。"""
    control: bool = True
    """是否启用控制。"""
    video_codec: Literal['h264', 'h265'] = 'h264'
    """视频编码格式。"""
    max_size: int | None = None
    """视频最大边长。"""
    video_bit_rate: int | None = None
    """视频码率。"""
    log_level: Literal['verbose', 'debug', 'info', 'warn', 'error'] = 'info'
    """服务端日志级别。"""
    scid: int | None = None
    """scrcpy 会话标识。留空将自动生成。"""
    cleanup_strategy: CleanupStrategy = 'owned_only'
    """
    启动前的清理策略。

    * owned_only：只清理由 kotonebot 启动的 scrcpy 实例
    * aggressive：清理所有 scrcpy 实例
    """
    virtual_display: VirtualDisplayConfig | None = None
    """虚拟显示器配置。为空表示不创建虚拟显示器。"""
    extra_args: list[str] = field(default_factory=list)
    """
    额外传给 scrcpy server 的参数。

    这里传递的参数会覆盖 ScrcpyConfig 中的相关配置。
    """
