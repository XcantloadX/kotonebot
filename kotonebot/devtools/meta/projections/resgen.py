from __future__ import annotations

from dataclasses import dataclass

from ..pipeline import build_meta_state


@dataclass(slots=True)
class ResgenVariantProjection:
    variant_group_by_base_key: dict[tuple[str, str], object]
    variant_skip_keys: set[tuple[str, str]]


def build_variant_projection_for_resgen(
    *,
    meta_files: list[str],
    resource_variants: list[str],
) -> ResgenVariantProjection:
    state = build_meta_state(
        meta_paths=meta_files,
        resource_variants=resource_variants,
    )
    if state.diagnostics:
        raise ValueError(state.diagnostics[0].message)

    by_base_key: dict[tuple[str, str], object] = {}
    skip_keys: set[tuple[str, str]] = set()
    for group in state.docs_graph.prefab_groups.values():
        by_base_key[(group.base.meta_path.lower(), group.base.definition_id)] = group
        for ref in group.variants.values():
            skip_keys.add((ref.meta_path.lower(), ref.definition_id))

    return ResgenVariantProjection(
        variant_group_by_base_key=by_base_key,
        variant_skip_keys=skip_keys,
    )
