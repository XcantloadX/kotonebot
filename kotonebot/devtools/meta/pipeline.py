"""# kotonebot.devtools.meta.pipeline

本模块定义了从元数据文件构建 `MetaState` 的流程。
构建流程是：corpus -> validate -> graph。
其中，corpus 是从元数据文件读入的原始文档内容，graph 是解析元数据中的引用关系后构建的文档图。
"""
from .corpus import build_corpus_from_meta_paths
from .diagnostic import Diagnostic
from .graph import build_docs_graph
from .state import MetaState
from .validator import collect_variant_groups, validate_meta_corpus
from .resolver import resolve_prefab_variant_groups


def build_meta_state(
    *,
    meta_paths: list[str],
    resource_variants: list[str] | None = None,
) -> MetaState:
    corpus, parse_diagnostics = build_corpus_from_meta_paths(meta_paths)
    diagnostics: list[Diagnostic] = list(parse_diagnostics)
    diagnostics.extend(
        validate_meta_corpus(
            corpus,
            resource_variants=resource_variants,
        )
    )
    # 仅当不存在错误时才解析 prefab_groups
    if diagnostics:
        docs_graph = build_docs_graph(corpus, prefab_groups={})
    else:
        grouped = collect_variant_groups(corpus)
        resolved = resolve_prefab_variant_groups(
            grouped,
            resource_variants=resource_variants,
        )
        docs_graph = build_docs_graph(corpus, prefab_groups=resolved)
    return MetaState(
        docs_graph=docs_graph,
        diagnostics=diagnostics,
    )
