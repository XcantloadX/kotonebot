from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from kotonebot.devtools.errors import NotFoundError, ValidationError

from ...indexing.models import IndexedFile, IndexedSymbol
from ...diagnostics.codes import (
    INDEX_DEF_ID_INVALID,
    INDEX_DEF_PARSE_ERROR,
    INDEX_FILE_PARSE_ERROR,
    INDEX_VARIANT_INVALID,
)
from ...diagnostics.models import Diagnostic
from ..corpus import ParsedMetaDoc, build_corpus_from_meta_paths
from ..scanner import MetaFileRef
from ..validator import validate_meta_corpus


_TOKEN_SPLIT_RE = re.compile(r"[\s._\-]+")
_CAMEL_CASE_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_GEOMETRY_KINDS = ("image", "rect", "point")


class IndexingProjection(BaseModel):
    files: dict[str, IndexedFile]
    symbols: dict[str, IndexedSymbol]
    diagnostics: dict[str, list[Diagnostic]]


def _split_tokens(text: str) -> list[str]:
    raw = _CAMEL_CASE_RE.sub(" ", text)
    tokens = []
    for part in _TOKEN_SPLIT_RE.split(raw):
        part = part.strip().lower()
        if part:
            tokens.append(part)
    return tokens


def _validate_geometry(prop_key: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    kind = value.get("kind")
    if kind not in _GEOMETRY_KINDS:
        return None
    if kind in ("rect", "image"):
        for key in ("x1", "y1", "x2", "y2"):
            if key not in value:
                raise ValidationError(f"props.{prop_key}.{key} is required for {kind}")
            if not isinstance(value[key], (int, float)):
                raise ValidationError(f"props.{prop_key}.{key} must be number")
    if kind == "point":
        for key in ("x", "y"):
            if key not in value:
                raise ValidationError(f"props.{prop_key}.{key} is required for point")
            if not isinstance(value[key], (int, float)):
                raise ValidationError(f"props.{prop_key}.{key} must be number")
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
                    raise ValidationError(f"Primary prop '{primary_prop}' does not exist in props")
                geometry = _validate_geometry(primary_prop, value)
                if geometry is None:
                    raise ValidationError(f"Primary prop '{primary_prop}' is not geometry")
                return primary_prop, geometry

    for kind in _GEOMETRY_KINDS:
        for key in sorted(props.keys()):
            geometry = _validate_geometry(key, props[key])
            if geometry is not None and geometry.get("kind") == kind:
                return key, geometry
    return None, None


def _project_symbols_for_doc(
    *,
    doc: ParsedMetaDoc,
    mtime_ns: int,
    prefab_schema: dict[str, Any],
) -> tuple[IndexedFile, list[IndexedSymbol], list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []
    symbols: list[IndexedSymbol] = []

    for definition_id in sorted(doc.data.definitions.keys(), key=lambda x: str(x)):
        definition = doc.data.definitions[definition_id]
        if not isinstance(definition_id, str) or definition_id == "":
            diagnostics.append(
                Diagnostic(
                    code=INDEX_DEF_ID_INVALID.code,
                    severity="error",
                    message="Definition id must be a non-empty string",
                    meta_path=doc.meta_path,
                    definition_id=str(definition_id),
                    field_path="definitions",
                    line=doc.ranges.definitions.line,
                    column=doc.ranges.definitions.column,
                    end_line=doc.ranges.definitions.end_line,
                    end_column=doc.ranges.definitions.end_column,
                )
            )
            continue

        try:
            type_value = definition.type
            if not isinstance(type_value, str):
                raise ValidationError("type must be string")
            props = definition.props
            if not isinstance(props, dict):
                raise ValidationError("props must be an object")

            name = definition.name or definition_id
            display_name = definition.display_name
            description = definition.description
            prefab_id = definition.prefab_id
            variant = definition.variant

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
                Path(doc.meta_path).name,
                Path(doc.image_path).name,
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

            symbol_key = f"{doc.meta_path}::{definition_id}"
            symbols.append(
                IndexedSymbol(
                    symbol_key=symbol_key,
                    definition_id=definition_id,
                    type=type_value,
                    name=name,
                    display_name=display_name,
                    description=description,
                    prefab_id=prefab_id,
                    variant=variant,
                    meta_path=doc.meta_path,
                    image_path=doc.image_path,
                    primary_prop_key=primary_prop_key,
                    primary_geometry=primary_geometry,
                    search_tokens=dedup_tokens,
                )
            )
        except ValueError as exc:
            definition_range = doc.ranges.of_definition(definition_id)
            diagnostics.append(
                Diagnostic(
                    code=INDEX_DEF_PARSE_ERROR.code,
                    severity="error",
                    message=str(exc),
                    meta_path=doc.meta_path,
                    definition_id=definition_id,
                    field_path=f"definitions.{definition_id}",
                    line=definition_range.line,
                    column=definition_range.column,
                    end_line=definition_range.end_line,
                    end_column=definition_range.end_column,
                )
            )

    indexed_file = IndexedFile(
        image_path=doc.image_path,
        meta_path=doc.meta_path,
        mtime_ns=mtime_ns,
        meta_version=doc.data.version,
        definition_ids=sorted([symbol.definition_id for symbol in symbols]),
    )
    return indexed_file, symbols, diagnostics


def build_indexing_projection(
    *,
    meta_refs: list[MetaFileRef],
    prefab_schema: dict[str, Any],
    resource_variants: list[str] | None,
    base_variant: str | None,
    variant_configured: bool = False,
) -> IndexingProjection:
    ref_by_path = {ref.meta_path: ref for ref in meta_refs}
    corpus, parse_diagnostics = build_corpus_from_meta_paths(list(ref_by_path.keys()))

    files: dict[str, IndexedFile] = {}
    symbols: dict[str, IndexedSymbol] = {}
    diagnostics: dict[str, list[Diagnostic]] = {}

    for diag in parse_diagnostics:
        diagnostics.setdefault(diag.meta_path, []).append(
            Diagnostic(
                code=INDEX_FILE_PARSE_ERROR.code,
                severity="error",
                message=diag.message,
                meta_path=diag.meta_path,
                line=diag.line,
                column=diag.column,
                end_line=diag.end_line,
                end_column=diag.end_column,
            )
        )

    for doc in corpus.docs:
        ref = ref_by_path.get(doc.meta_path)
        if ref is None:
            raise NotFoundError(f"Missing file ref for parsed doc: {doc.meta_path}")
        indexed_file, file_symbols, file_diags = _project_symbols_for_doc(
            doc=doc,
            mtime_ns=ref.mtime_ns,
            prefab_schema=prefab_schema,
        )
        files[indexed_file.meta_path] = indexed_file
        if file_diags:
            diagnostics.setdefault(indexed_file.meta_path, []).extend(file_diags)
        for symbol in file_symbols:
            symbols[symbol.symbol_key] = symbol

    variant_diagnostics = validate_meta_corpus(
        corpus,
        resource_variants=resource_variants,
        base_variant=base_variant,
        variant_configured=variant_configured,
    )
    for diag in variant_diagnostics:
        diagnostics.setdefault(diag.meta_path, []).append(
            Diagnostic(
                code=INDEX_VARIANT_INVALID.code,
                severity=diag.severity,
                message=diag.message,
                meta_path=diag.meta_path,
                definition_id=diag.definition_id,
                field_path=diag.field_path or "definitions",
                line=diag.line,
                column=diag.column,
                end_line=diag.end_line,
                end_column=diag.end_column,
            )
        )

    return IndexingProjection(
        files=files,
        symbols=symbols,
        diagnostics=diagnostics,
    )
