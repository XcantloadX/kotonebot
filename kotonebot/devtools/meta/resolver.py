from pydantic import BaseModel

from kotonebot.devtools.errors import ValidationError

from .models import DefinitionModel, DefinitionV3Model, VariantPolicy


class DefinitionRef(BaseModel):
    meta_path: str
    definition_id: str
    definition: DefinitionModel
    line: int
    column: int
    end_line: int
    end_column: int


class ResolvedPrefabVariants(BaseModel):
    name: str
    base: DefinitionRef
    variants: dict[str, DefinitionRef]
    merged: dict[str, DefinitionModel]


def _policy_for_variant(base: DefinitionModel, variant: str) -> VariantPolicy:
    if base.variant_policy is None:
        return "require"
    return base.variant_policy.get(variant, "require")


def merge_prefab_definition(base: DefinitionModel, override: DefinitionModel) -> DefinitionModel:
    if base.type != "prefab" or override.type != "prefab":
        raise ValidationError("merge_prefab_definition requires prefab definitions")
    if base.name != override.name:
        raise ValidationError("merge_prefab_definition requires same name")

    base_props = base.props or {}
    override_props = override.props or {}
    merged_props = dict(base_props)
    merged_props.update(override_props)

    return DefinitionV3Model(
        type="prefab",
        name=override.name,
        displayName=override.display_name if override.display_name is not None else base.display_name,
        description=override.description if override.description is not None else base.description,
        prefab_id=override.prefab_id if override.prefab_id is not None else base.prefab_id,
        variant=override.variant,
        variant_policy=override.variant_policy if override.variant_policy is not None else base.variant_policy,
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
            raise ValidationError(f"duplicate prefab (name, variant) group entry: {key}, {variant}")
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
        base = group.get(None)
        if not variant_keys:
            if base is None:
                continue

        if base is None:
            raise ValidationError(f"variant prefab requires base definition: {name}")
        if base.definition.type != "prefab":
            raise ValidationError(f"variant prefab base must be prefab: {name}")

        typed_variants: dict[str, DefinitionRef] = {}
        for variant in sorted(variant_keys):
            ref = group[variant]
            if ref.definition.type != "prefab":
                raise ValidationError(f"variant prefab must be prefab: {name}#{variant}")
            typed_variants[variant] = ref

        merged: dict[str, DefinitionModel] = {}
        merged[""] = base.definition
        expected_variants = resource_variants if resource_variants is not None else list(typed_variants.keys())
        for variant in expected_variants:
            if variant in typed_variants:
                merged[variant] = merge_prefab_definition(base.definition, typed_variants[variant].definition)
            else:
                policy = _policy_for_variant(base.definition, variant)
                if policy == "exclude":
                    continue
                if policy == "require":
                    continue
                merged[variant] = merge_prefab_definition(
                    base.definition,
                    DefinitionV3Model(
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
