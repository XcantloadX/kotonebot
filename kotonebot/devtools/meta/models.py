from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DefinitionV2Model(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    type: str | None = None
    name: str | None = None
    display_name: str | None = Field(default=None, alias="displayName")
    description: str | None = None
    prefab_id: str | None = None
    variant: str | None = None
    props: dict[str, Any] | None = None


class MetaV2Model(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)

    version: Literal[2]
    definitions: dict[str, DefinitionV2Model]
