from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..meta.diagnostic import Diagnostic


@dataclass(slots=True)
class IndexedFile:
    image_path: str
    meta_path: str
    mtime_ns: int
    meta_version: int
    definition_ids: list[str]


@dataclass(slots=True)
class IndexedSymbol:
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
    search_tokens: list[str]


@dataclass(slots=True)
class IndexSnapshot:
    index_version: int
    content_hash: str
    files: dict[str, IndexedFile] = field(default_factory=dict)
    symbols: dict[str, IndexedSymbol] = field(default_factory=dict)
    diagnostics: dict[str, list[Diagnostic]] = field(default_factory=dict)
    reverse_refs: dict[str, list[str]] = field(default_factory=dict)
