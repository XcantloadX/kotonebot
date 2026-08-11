from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ..diagnostics.models import Diagnostic


class IndexedFile(BaseModel):
    image_path: str
    meta_path: str
    mtime_ns: int
    meta_version: int
    definition_ids: list[str]


class IndexedSymbol(BaseModel):
    symbol_key: str
    definition_id: str
    type: str
    name: str
    display_name: str | None
    description: str | None
    prefab_id: str | None
    variant: str | None
    meta_path: str
    image_path: str
    primary_prop_key: str | None
    primary_geometry: dict[str, Any] | None


class IndexSnapshot(BaseModel):
    index_version: int
    content_hash: str
    files: dict[str, IndexedFile] = Field(default_factory=dict)
    symbols: dict[str, IndexedSymbol] = Field(default_factory=dict)
    diagnostics: dict[str, list[Diagnostic]] = Field(default_factory=dict)
    reverse_refs: dict[str, list[str]] = Field(default_factory=dict)
