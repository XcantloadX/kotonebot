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
    options: T
    """下游脚本储存的具体数据。"""


class RootConfig(ConfigBaseModel, Generic[T]):
    version: int = 1
    """配置版本。"""
    user_configs: list[UserConfig[T]] = []
    """用户配置。"""

