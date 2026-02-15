from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from kotonebot.devtools.meta import DefinitionV2Model, parse_meta_v2_file

from .diagnostics import make_error
from .models import Diagnostic, IndexedFile, IndexedSymbol


_TOKEN_SPLIT_RE = re.compile(r"[\s._\-]+")
_CAMEL_CASE_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_GEOMETRY_KINDS = ("image", "rect", "point")


def _split_tokens(text: str) -> list[str]:
    raw = _CAMEL_CASE_RE.sub(" ", text)
    tokens = []
    for part in _TOKEN_SPLIT_RE.split(raw):
        part = part.strip().lower()
        if part:
            tokens.append(part)
    return tokens


def _validate_str_or_none(value: Any, field_path: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise ValueError(f"{field_path} must be string or null")


def _validate_geometry(prop_key: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    if kind not in _GEOMETRY_KINDS:
        return None
    if kind in ("rect", "image"):
        for key in ("x1", "y1", "x2", "y2"):
            if key not in value:
                raise ValueError(f"props.{prop_key}.{key} is required for {kind}")
            if not isinstance(value[key], (int, float)):
                raise ValueError(f"props.{prop_key}.{key} must be number")
    if kind == "point":
        for key in ("x", "y"):
            if key not in value:
                raise ValueError(f"props.{prop_key}.{key} is required for point")
            if not isinstance(value[key], (int, float)):
                raise ValueError(f"props.{prop_key}.{key} must be number")
    return value


def _pick_primary_geometry(
    *,
    props: dict[str, Any],
    prefab_id: str | None,
    prefab_schema: dict[str, Any],
) -> tuple[str | None, dict[str, Any] | None]:
    if prefab_id is not None:
        prefab = prefab_schema.get(prefab_id)
        if prefab is not None:
            primary_prop = prefab.get("primary_prop")
            if primary_prop is not None:
                value = props.get(primary_prop)
                if value is None:
                    raise ValueError(f"Primary prop '{primary_prop}' does not exist in props")
                geometry = _validate_geometry(primary_prop, value)
                if geometry is None:
                    raise ValueError(f"Primary prop '{primary_prop}' is not geometry")
                return primary_prop, geometry

    for kind in _GEOMETRY_KINDS:
        for key in sorted(props.keys()):
            geometry = _validate_geometry(key, props[key])
            if geometry is not None and geometry.get("kind") == kind:
                return key, geometry
    return None, None


def parse_meta_file(
    *,
    abs_meta_path: Path,
    meta_path: str,
    image_path: str,
    mtime_ns: int,
    prefab_schema: dict[str, Any],
) -> tuple[IndexedFile, list[IndexedSymbol], list[Diagnostic]]:
    data = parse_meta_v2_file(abs_meta_path)
    definitions = data.definitions

    diagnostics: list[Diagnostic] = []
    symbols: list[IndexedSymbol] = []

    for definition_id in sorted(definitions.keys(), key=lambda x: str(x)):
        definition = definitions[definition_id]
        if not isinstance(definition_id, str) or definition_id == "":
            diagnostics.append(
                make_error(
                    code="INDEX_DEF_ID_INVALID",
                    message="Definition id must be a non-empty string",
                    meta_path=meta_path,
                    definition_id=str(definition_id),
                    field_path="definitions",
                )
            )
            continue
        if not isinstance(definition, DefinitionV2Model):
            diagnostics.append(
                make_error(
                    code="INDEX_DEF_INVALID",
                    message="Definition must be an object",
                    meta_path=meta_path,
                    definition_id=definition_id,
                    field_path=f"definitions.{definition_id}",
                )
            )
            continue

        try:
            type_value = definition.type
            if not isinstance(type_value, str):
                raise ValueError("type must be string")
            props = definition.props
            if not isinstance(props, dict):
                raise ValueError("props must be an object")

            name = _validate_str_or_none(definition.name, "name") or definition_id
            display_name = _validate_str_or_none(definition.display_name, "displayName")
            description = _validate_str_or_none(definition.description, "description")
            prefab_id = _validate_str_or_none(definition.prefab_id, "prefab_id")

            primary_prop_key, primary_geometry = _pick_primary_geometry(
                props=props,
                prefab_id=prefab_id,
                prefab_schema=prefab_schema,
            )

            search_tokens: list[str] = []
            for source in (
                display_name,
                name,
                definition_id,
                prefab_id,
                Path(meta_path).name,
                Path(image_path).name,
            ):
                if source is None:
                    continue
                search_tokens.extend(_split_tokens(source))

            seen: set[str] = set()
            dedup_tokens: list[str] = []
            for token in search_tokens:
                if token not in seen:
                    seen.add(token)
                    dedup_tokens.append(token)

            symbol_key = f"{meta_path}::{definition_id}"
            symbols.append(
                IndexedSymbol(
                    symbol_key=symbol_key,
                    definition_id=definition_id,
                    type=type_value,
                    name=name,
                    display_name=display_name,
                    description=description,
                    prefab_id=prefab_id,
                    meta_path=meta_path,
                    image_path=image_path,
                    primary_prop_key=primary_prop_key,
                    primary_geometry=primary_geometry,
                    search_tokens=dedup_tokens,
                )
            )
        except ValueError as exc:
            diagnostics.append(
                make_error(
                    code="INDEX_DEF_PARSE_ERROR",
                    message=str(exc),
                    meta_path=meta_path,
                    definition_id=definition_id,
                    field_path=f"definitions.{definition_id}",
                )
            )

    indexed_file = IndexedFile(
        image_path=image_path,
        meta_path=meta_path,
        mtime_ns=mtime_ns,
        meta_version=2,
        definition_ids=sorted([symbol.definition_id for symbol in symbols]),
    )
    return indexed_file, symbols, diagnostics
