import uuid
from typing import Generic, TypeVar, Literal

from pydantic import BaseModel, ConfigDict

T = TypeVar('T')

class ConfigBaseModel(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)

class BackendConfig(ConfigBaseModel):
    adb_ip: str = '127.0.0.1'
    """adb 连接的 ip 地址。"""
    adb_port: int = 5555
    """adb 连接的端口。"""
    screenshot_impl: Literal['adb', 'adb_raw', 'uiautomator2'] = 'adb_raw'
    """
    截图方法。暂时推荐使用【adb】截图方式。
    """

class PushConfig(ConfigBaseModel):
    """推送配置。"""

    wx_pusher_enabled: bool = False
    """是否启用 WxPusher 推送。"""
    wx_pusher_app_token: str | None = None
    """WxPusher 的 app token。"""
    wx_pusher_uid: str | None = None
    """WxPusher 的 uid。"""

    free_image_host_key: str | None = None
    """FreeImageHost API key。用于在推送通知时显示图片。"""

class UserConfig(ConfigBaseModel, Generic[T]):
    """用户可以自由添加、删除的配置数据。"""

    name: str = 'default_config'
    """显示名称。通常由用户输入。"""
    id: str = uuid.uuid4().hex
    """唯一标识符。"""
    category: str = 'default'
    """类别。如：'global'、'china'、'asia' 等。"""
    description: str = ''
    """描述。通常由用户输入。"""
    backend: BackendConfig = BackendConfig()
    """后端配置。"""
    keep_screenshots: bool = False
    """
    是否保留截图。
    若启用，则会保存每一张截图到 `dumps` 目录下。启用该选项有助于辅助调试。
    """
    options: T
    """下游脚本储存的具体数据。"""


class RootConfig(ConfigBaseModel, Generic[T]):
    version: int = 1
    """配置版本。"""
    user_configs: list[UserConfig[T]] = []
    """用户配置。"""

