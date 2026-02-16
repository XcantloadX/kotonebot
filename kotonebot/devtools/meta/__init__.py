from .corpus import MetaCorpus, ParsedMetaDoc, build_corpus_from_meta_paths
from ..diagnostics.models import Diagnostic, Severity
from .graph import DefinitionKey, ResolvedDefinition, ResolvedDocsGraph, build_docs_graph
from .models import DefinitionV2Model, MetaV2Model
from .parser import parse_meta_file
from .pipeline import build_meta_state
from .projections import IndexingProjection, build_indexing_projection, build_variant_projection_for_resgen
from .scanner import MetaFileRef, scan_meta_files
from .state import MetaState
from .validator import collect_variant_groups, validate_meta_corpus
from .resolver import (
    DefinitionRef,
    ResolvedPrefabVariants,
    group_prefab_definitions_by_name,
    merge_prefab_definition,
    resolve_prefab_variant_groups,
)

__all__ = [
    "DefinitionKey",
    "Diagnostic",
    "Severity",
    "ResolvedDefinition",
    "ResolvedDocsGraph",
    "MetaCorpus",
    "MetaState",
    "ParsedMetaDoc",
    "build_corpus_from_meta_paths",
    "build_docs_graph",
    "build_meta_state",
    "DefinitionV2Model",
    "MetaFileRef",
    "MetaV2Model",
    "parse_meta_file",
    "scan_meta_files",
    "validate_meta_corpus",
    "collect_variant_groups",
    "IndexingProjection",
    "build_indexing_projection",
    "build_variant_projection_for_resgen",
    "DefinitionRef",
    "ResolvedPrefabVariants",
    "group_prefab_definitions_by_name",
    "merge_prefab_definition",
    "resolve_prefab_variant_groups",
]
