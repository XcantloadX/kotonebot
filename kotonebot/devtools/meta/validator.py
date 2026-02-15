from .corpus import MetaCorpus
from .diagnostic import Diagnostic
from .resolver import DefinitionRef, group_prefab_definitions_by_name


def validate_meta_corpus(
    corpus: MetaCorpus,
    *,
    resource_variants: list[str] | None = None,
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    refs: list[DefinitionRef] = []

    for doc in corpus.docs:
        for definition_id, definition in doc.data.definitions.items():
            refs.append(
                DefinitionRef(
                    meta_path=doc.meta_path,
                    definition_id=definition_id,
                    definition=definition,
                )
            )
            variant = definition.variant
            if variant is None:
                continue
            if definition.type != "prefab":
                diagnostics.append(
                    Diagnostic(
                        code="META_VARIANT_INVALID",
                        message=f"variant is only allowed for prefab: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                    )
                )
                continue
            if definition.name is None:
                diagnostics.append(
                    Diagnostic(
                        code="META_VARIANT_INVALID",
                        message=f"variant definition requires name: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                    )
                )
                continue
            if resource_variants is not None and variant not in resource_variants:
                diagnostics.append(
                    Diagnostic(
                        code="META_VARIANT_INVALID",
                        message=f"variant '{variant}' is not declared in resource_variants: {doc.meta_path}::{definition_id}",
                        meta_path=doc.meta_path,
                        definition_id=definition_id,
                    )
                )

    grouped: dict[str, dict[str | None, DefinitionRef]] = {}
    for ref in refs:
        definition = ref.definition
        if definition.type != "prefab" or definition.name is None:
            continue
        name = definition.name
        variant = definition.variant
        group = grouped.setdefault(name, {})
        if variant in group:
            other = group[variant]
            diagnostics.append(
                Diagnostic(
                    code="META_VARIANT_INVALID",
                    message=(
                        f"duplicate prefab (name, variant): {name}, {variant}; "
                        f"{other.meta_path}::{other.definition_id}, {ref.meta_path}::{ref.definition_id}"
                    ),
                    meta_path=ref.meta_path,
                    definition_id=ref.definition_id,
                )
            )
            continue
        group[variant] = ref

    for name, group in grouped.items():
        has_variant = any(v is not None for v in group.keys())
        if not has_variant:
            continue
        if None not in group:
            first_variant = next(ref for variant, ref in group.items() if variant is not None)
            diagnostics.append(
                Diagnostic(
                    code="META_VARIANT_INVALID",
                    message=f"variant prefab requires base definition: {name}",
                    meta_path=first_variant.meta_path,
                    definition_id=first_variant.definition_id,
                )
            )

    return diagnostics


def collect_variant_groups(corpus: MetaCorpus) -> dict[str, dict[str | None, DefinitionRef]]:
    refs: list[DefinitionRef] = []
    for doc in corpus.docs:
        for definition_id, definition in doc.data.definitions.items():
            refs.append(
                DefinitionRef(
                    meta_path=doc.meta_path,
                    definition_id=definition_id,
                    definition=definition,
                )
            )
    return group_prefab_definitions_by_name(refs)
