from pydantic import BaseModel, Field

from .corpus import MetaCorpus
from .models import DefinitionModel
from .resolver import ResolvedPrefabVariants


DefinitionKey = tuple[str, str]


class ResolvedDefinition(BaseModel):
    key: DefinitionKey
    meta_path: str
    image_path: str
    definition_id: str
    definition: DefinitionModel
    merged_definition: DefinitionModel
    base_ref: DefinitionKey | None = None
    variant_refs: list[DefinitionKey] = Field(default_factory=list)


class ResolvedDocsGraph(BaseModel):
    definitions: dict[DefinitionKey, ResolvedDefinition] = Field(default_factory=dict)
    by_name: dict[str, list[DefinitionKey]] = Field(default_factory=dict)
    prefab_groups: dict[str, ResolvedPrefabVariants] = Field(default_factory=dict)


def build_docs_graph(
    corpus: MetaCorpus,
    *,
    prefab_groups: dict[str, ResolvedPrefabVariants] | None = None,
) -> ResolvedDocsGraph:
    graph = ResolvedDocsGraph()
    groups = prefab_groups or {}

    for doc in corpus.docs:
        for definition_id, definition in doc.data.definitions.items():
            key = (doc.meta_path, definition_id)
            graph.definitions[key] = ResolvedDefinition(
                key=key,
                meta_path=doc.meta_path,
                image_path=doc.image_path,
                definition_id=definition_id,
                definition=definition,
                merged_definition=definition,
            )
            if definition.name is not None:
                graph.by_name.setdefault(definition.name, []).append(key)

    graph.prefab_groups = groups
    for group in groups.values():
        base_key: DefinitionKey = (group.base.meta_path, group.base.definition_id)
        base_node = graph.definitions[base_key]
        base_node.merged_definition = group.merged[""]

        variant_keys: list[DefinitionKey] = []
        for variant, variant_ref in group.variants.items():
            vkey = (variant_ref.meta_path, variant_ref.definition_id)
            variant_keys.append(vkey)
            variant_node = graph.definitions[vkey]
            variant_node.base_ref = base_key
            variant_node.merged_definition = group.merged[variant]
        base_node.variant_refs = variant_keys

    return graph
