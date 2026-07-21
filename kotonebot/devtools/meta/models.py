from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


VariantPolicy: TypeAlias = Literal["inherit", "require", "exclude"]


class DefinitionMultiModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    type: str | None = None
    name: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    description: str | None = None
    prefab_id: str | None = None
    variant: str | None = None
    variant_policy: dict[str, VariantPolicy] | None = None
    props: dict[str, Any] | None = None


class MetaMultiModel(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    version: Literal[3]
    definitions: dict[str, DefinitionMultiModel]


class SingleDefinitionModel(BaseModel):
    """Single 文档中的单个定义。"""

    model_config = ConfigDict(extra="ignore", strict=True)

    type: str | None = None
    """定义类型。"""
    name: str | None = None
    """定义名称（大驼峰）。"""
    display_name: str | None = Field(default=None, alias="displayName")
    """显示名称。"""
    description: str | None = None
    """描述。"""
    props: dict[str, Any] | None = None
    """属性字典。"""


class SingleMetaModel(BaseModel):
    """Single 文档的顶层模型。"""

    model_config = ConfigDict(extra="ignore", strict=True)

    isSimple: Literal[True]
    """是否为 Simple 格式，固定为 True。"""
    definition: SingleDefinitionModel
    """定义内容。"""


DefinitionModel: TypeAlias = DefinitionMultiModel
MetaModel: TypeAlias = MetaMultiModel
