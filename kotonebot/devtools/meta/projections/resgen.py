from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ...diagnostics.models import Diagnostic
from ..pipeline import build_meta_state
from ..resolver import ResolvedPrefabVariants


class ResgenVariantProjection(BaseModel):
    variant_group_by_base_key: dict[tuple[str, str], ResolvedPrefabVariants]
    variant_skip_keys: set[tuple[str, str]]
    diagnostics: list[Diagnostic]


def _normalize_meta_path(path: str) -> str:
    return Path(path).resolve().as_posix().lower()


def build_variant_projection_for_resgen(
    *,
    meta_files: list[str],
    resource_variants: list[str],
    base_variant: str | None,
) -> ResgenVariantProjection:
    state = build_meta_state(
        meta_paths=meta_files,
        resource_variants=resource_variants,
        base_variant=base_variant,
        variant_configured=True,
    )
    by_base_key: dict[tuple[str, str], ResolvedPrefabVariants] = {}
    skip_keys: set[tuple[str, str]] = set()
    for group in state.docs_graph.prefab_groups.values():
        by_base_key[(_normalize_meta_path(group.base.meta_path), group.base.definition_id)] = group
        for ref in group.variants.values():
            skip_keys.add((_normalize_meta_path(ref.meta_path), ref.definition_id))

    return ResgenVariantProjection(
        variant_group_by_base_key=by_base_key,
        variant_skip_keys=skip_keys,
        diagnostics=state.diagnostics,
    )
