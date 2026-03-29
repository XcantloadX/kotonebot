from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


VariantPolicy: TypeAlias = Literal["inherit", "require", "exclude"]


class DefinitionV3Model(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    type: str | None = None
    name: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    description: str | None = None
    prefab_id: str | None = None
    variant: str | None = None
    variant_policy: dict[str, VariantPolicy] | None = None
    props: dict[str, Any] | None = None


class MetaV3Model(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    version: Literal[3]
    definitions: dict[str, DefinitionV3Model]


DefinitionModel: TypeAlias = DefinitionV3Model
MetaModel: TypeAlias = MetaV3Model
