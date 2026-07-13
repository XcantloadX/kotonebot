from kotonebot.devtools.errors import NotFoundError

from .corpus import MetaCorpus
from ..diagnostics.codes import (
    META_VARIANT_INVALID,
)
from ..diagnostics.models import Diagnostic
from .models import DefinitionModel
from .resolver import DefinitionRef, group_prefab_definitions_by_name


def _policy_for_variant(definition: DefinitionModel, variant: str) -> str | None:
    if definition.variant_policy is None:
        return None
    return definition.variant_policy.get(variant)


def validate_meta_corpus(
    corpus: MetaCorpus,
    *,
    resource_variants: list[str] | None = None,
    base_variant: str | None = None,
    variant_configured: bool = False,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    refs: list[DefinitionRef] = []
    doc_by_path = {doc.meta_path: doc for doc in corpus.docs}

    # 第一阶段：逐条 definition 做局部校验（不依赖同名分组信息）。
    for doc in corpus.docs:
        for definition_id, definition in doc.data.definitions.items():
            definition_range = doc.ranges.of_definition(definition_id)
            refs.append(
                DefinitionRef(
                    meta_path=doc.meta_path,
                    definition_id=definition_id,
                    definition=definition,
                    line=definition_range.line,
                    column=definition_range.column,
                    end_line=definition_range.end_line,
                    end_column=definition_range.end_column,
                )
            )
            variant = definition.variant
            if variant is None:
                if definition.type == "prefab" and variant_configured:
                    if definition.variant_policy is None:
                        diagnostics.append(
                            Diagnostic(
                                code=META_VARIANT_INVALID.code,
                                message=f"base prefab requires variant_policy in meta v3: {definition.name}",
                                meta_path=doc.meta_path,
                                severity="error",
                                definition_id=definition_id,
                                field_path=f"definitions.{definition_id}.variant_policy",
                                line=definition_range.line,
                                column=definition_range.column,
                                end_line=definition_range.end_line,
                                end_column=definition_range.end_column,
                            )
                        )
                    elif resource_variants is not None:
                        missing_policy_variants = [
                            item
                            for item in resource_variants
                            if (base_variant is None or item != base_variant)
                            and item not in definition.variant_policy
                        ]
                        if missing_policy_variants:
                            diagnostics.append(
                                Diagnostic(
                                    code=META_VARIANT_INVALID.code,
                                    message=(
                                        "base prefab variant_policy is missing configured variants: "
                                        f"{definition.name}; missing={', '.join(missing_policy_variants)}"
                                    ),
                                    meta_path=doc.meta_path,
                                    severity="error",
                                    definition_id=definition_id,
                                    field_path=f"definitions.{definition_id}.variant_policy",
                                    line=definition_range.line,
                                    column=definition_range.column,
                                    end_line=definition_range.end_line,
                                    end_column=definition_range.end_column,
                                )
                            )
                continue
            # 规则：variant 字段只允许出现在 prefab definition 上。
            if definition.type != "prefab":
                diagnostics.append(
                    Diagnostic(
                        code=META_VARIANT_INVALID.code,
                        message=f"variant is only allowed for prefab: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                        line=definition_range.line,
                        column=definition_range.column,
                        end_line=definition_range.end_line,
                        end_column=definition_range.end_column,
                    )
                )
                continue
            # 规则：variant prefab 必须声明 name（用于和 base prefab 按名称分组）。
            if definition.name is None:
                diagnostics.append(
                    Diagnostic(
                        code=META_VARIANT_INVALID.code,
                        message=f"variant definition requires name: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                        line=definition_range.line,
                        column=definition_range.column,
                        end_line=definition_range.end_line,
                        end_column=definition_range.end_column,
                    )
                )
                continue
            # 规则：variant 值必须在项目配置的 resource_variants 中。
            if resource_variants is not None and variant not in resource_variants:
                field_range = doc.ranges.of_field(definition_id, "variant")
                diagnostics.append(
                    Diagnostic(
                        code=META_VARIANT_INVALID.code,
                        message=f"variant '{variant}' is not declared in resource_variants: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                        line=field_range.line,
                        column=field_range.column,
                        end_line=field_range.end_line,
                        end_column=field_range.end_column,
                    )
                )
                continue
            # 规则：variant 值不能等于项目配置的 base variant。
            if base_variant is not None and variant == base_variant:
                field_range = doc.ranges.of_field(definition_id, "variant")
                diagnostics.append(
                    Diagnostic(
                        code=META_VARIANT_INVALID.code,
                        message=f"variant '{variant}' must not be equal to base variant: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                        line=field_range.line,
                        column=field_range.column,
                        end_line=field_range.end_line,
                        end_column=field_range.end_column,
                    )
                )

    # 第二阶段：按 prefab name 分组，做跨 definition 校验。
    grouped: dict[str, dict[str | None, DefinitionRef]] = {}
    for ref in refs:
        definition = ref.definition
        if definition.type != "prefab" or definition.name is None:
            continue
        name = definition.name
        variant = definition.variant
        group = grouped.setdefault(name, {})
        # 规则：同一个 name 下，(name, variant) 组合必须唯一。
        if variant in group:
            other = group[variant]
            diagnostics.append(
                Diagnostic(
                    code=META_VARIANT_INVALID.code,
                    message=(
                        f"duplicate prefab (name, variant): {name}, {variant}; "
                        f"{other.meta_path}::{other.definition_id}, {ref.meta_path}::{ref.definition_id}"
                    ),
                    meta_path=ref.meta_path,
                    definition_id=ref.definition_id,
                    line=ref.line,
                    column=ref.column,
                    end_line=ref.end_line,
                    end_column=ref.end_column,
                )
            )
            continue
        group[variant] = ref

    for name, group in grouped.items():
        has_variant = any(v is not None for v in group.keys())
        base_ref = group.get(None)
        if (
            resource_variants is not None
            and base_ref is not None
            and base_ref.definition.type == "prefab"
            and base_ref.definition.variant_policy is not None
        ):
            for configured_variant in resource_variants:
                if base_variant is not None and configured_variant == base_variant:
                    continue
                policy = _policy_for_variant(base_ref.definition, configured_variant)
                if policy is None:
                    continue
                has_explicit_variant = configured_variant in group
                if policy == "require" and not has_explicit_variant:
                    base_doc = doc_by_path.get(base_ref.meta_path)
                    if base_doc is None:
                        raise NotFoundError(f"Document not found: {base_ref.meta_path}")
                    field_range = base_doc.ranges.of_field(base_ref.definition_id, "variant_policy")
                    diagnostics.append(
                        Diagnostic(
                            code=META_VARIANT_INVALID.code,
                            message=(
                                "variant_policy=require requires explicit variant definition: "
                                f"{name}#{configured_variant}"
                            ),
                            meta_path=base_ref.meta_path,
                            severity="error",
                            definition_id=base_ref.definition_id,
                            field_path=f"definitions.{base_ref.definition_id}.variant_policy",
                            line=field_range.line,
                            column=field_range.column,
                            end_line=field_range.end_line,
                            end_column=field_range.end_column,
                        )
                    )
                elif policy == "exclude" and has_explicit_variant:
                    ref = group[configured_variant]
                    diagnostics.append(
                        Diagnostic(
                            code=META_VARIANT_INVALID.code,
                            message=(
                                "variant_policy=exclude forbids explicit variant definition: "
                                f"{name}#{configured_variant}"
                            ),
                            meta_path=ref.meta_path,
                            severity="error",
                            definition_id=ref.definition_id,
                            line=ref.line,
                            column=ref.column,
                            end_line=ref.end_line,
                            end_column=ref.end_column,
                        )
                    )
        if not has_variant:
            continue
        # 规则：只要存在任意 variant prefab，就必须有对应 base prefab（variant=None）。
        if None not in group:
            first_variant = next(ref for variant, ref in group.items() if variant is not None)
            diagnostics.append(
                Diagnostic(
                    code=META_VARIANT_INVALID.code,
                    message=f"variant prefab requires base definition: {name}",
                    meta_path=first_variant.meta_path,
                    definition_id=first_variant.definition_id,
                    line=first_variant.line,
                    column=first_variant.column,
                    end_line=first_variant.end_line,
                    end_column=first_variant.end_column,
                )
            )

    return diagnostics


def collect_variant_groups(corpus: MetaCorpus) -> dict[str, dict[str | None, DefinitionRef]]:
    refs: list[DefinitionRef] = []
    for doc in corpus.docs:
        for definition_id, definition in doc.data.definitions.items():
            definition_range = doc.ranges.of_definition(definition_id)
            refs.append(
                DefinitionRef(
                    meta_path=doc.meta_path,
                    definition_id=definition_id,
                    definition=definition,
                    line=definition_range.line,
                    column=definition_range.column,
                    end_line=definition_range.end_line,
                    end_column=definition_range.end_column,
                )
            )
    return group_prefab_definitions_by_name(refs)
