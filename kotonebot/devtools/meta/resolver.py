from dataclasses import dataclass

from .models import DefinitionV2Model


@dataclass(slots=True)
class DefinitionRef:
    meta_path: str
    definition_id: str
    definition: DefinitionV2Model


@dataclass(slots=True)
class ResolvedPrefabVariants:
    name: str
    base: DefinitionRef
    variants: dict[str, DefinitionRef]
    merged: dict[str, DefinitionV2Model]


def merge_prefab_definition(base: DefinitionV2Model, override: DefinitionV2Model) -> DefinitionV2Model:
    if base.type != "prefab" or override.type != "prefab":
        raise ValueError("merge_prefab_definition requires prefab definitions")
    if base.name != override.name:
        raise ValueError("merge_prefab_definition requires same name")

    base_props = base.props or {}
    override_props = override.props or {}
    merged_props = dict(base_props)
    merged_props.update(override_props)

    return DefinitionV2Model(
        type="prefab",
        name=override.name,
        displayName=override.display_name if override.display_name is not None else base.display_name,
        description=override.description if override.description is not None else base.description,
        prefab_id=override.prefab_id if override.prefab_id is not None else base.prefab_id,
        variant=override.variant,
        props=merged_props,
    )


def group_prefab_definitions_by_name(
    refs: list[DefinitionRef],
) -> dict[str, dict[str | None, DefinitionRef]]:
    groups: dict[str, dict[str | None, DefinitionRef]] = {}
    for ref in refs:
        definition = ref.definition
        if definition.type != "prefab" or definition.name is None:
            continue

        key = definition.name
        group = groups.setdefault(key, {})
        variant = definition.variant
        if variant in group:
            raise ValueError(f"duplicate prefab (name, variant) group entry: {key}, {variant}")
        group[variant] = ref
    return groups


def resolve_prefab_variant_groups(
    groups: dict[str, dict[str | None, DefinitionRef]],
    *,
    resource_variants: list[str] | None = None,
) -> dict[str, ResolvedPrefabVariants]:
    resolved: dict[str, ResolvedPrefabVariants] = {}
    for name, group in groups.items():
        variant_keys = [k for k in group.keys() if k is not None]
        if not variant_keys:
            continue

        base = group.get(None)
        if base is None:
            raise ValueError(f"variant prefab requires base definition: {name}")
        if base.definition.type != "prefab":
            raise ValueError(f"variant prefab base must be prefab: {name}")

        typed_variants: dict[str, DefinitionRef] = {}
        for variant in sorted(variant_keys):
            ref = group[variant]
            if ref.definition.type != "prefab":
                raise ValueError(f"variant prefab must be prefab: {name}#{variant}")
            typed_variants[variant] = ref

        merged: dict[str, DefinitionV2Model] = {}
        merged[""] = base.definition
        expected_variants = resource_variants if resource_variants is not None else list(typed_variants.keys())
        for variant in expected_variants:
            if variant in typed_variants:
                merged[variant] = merge_prefab_definition(base.definition, typed_variants[variant].definition)
            else:
                merged[variant] = merge_prefab_definition(
                    base.definition,
                    DefinitionV2Model(
                        type="prefab",
                        name=base.definition.name,
                        variant=variant,
                        props={},
                    ),
                )

        resolved[name] = ResolvedPrefabVariants(
            name=name,
            base=base,
            variants=typed_variants,
            merged=merged,
        )

    return resolved
