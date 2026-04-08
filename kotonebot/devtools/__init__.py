from importlib import import_module
from typing import TYPE_CHECKING

from .project.schema import EditorMetadata

if TYPE_CHECKING:
    from .resgen import (
        BasicSpriteParser,
        ClassNode,
        CodeWriter,
        DocstringPolicy,
        EntityGenerator,
        ImageProcessor,
        KotoneV1Parser,
        ParserRegistry,
        PathPolicy,
        RenderContext,
        RendererRegistry,
        ResourceNode,
        ResourceRenderer,
        SchemaParser,
        StandardGenerator,
        build_class_tree,
        to_camel_case,
        unify_path,
    )

_RESGEN_EXPORTS = [
    # core
    "CodeWriter",
    "ResourceNode",
    "ClassNode",
    "SchemaParser",

    # generator
    "StandardGenerator",
    "EntityGenerator",
    "RenderContext",
    "PathPolicy",
    "DocstringPolicy",
    "ResourceRenderer",
    "RendererRegistry",

    # parsers
    "ParserRegistry",
    "KotoneV1Parser",
    "BasicSpriteParser",

    # utils
    "to_camel_case",
    "unify_path",
    "build_class_tree",
    "ImageProcessor",
]

__all__ = _RESGEN_EXPORTS + ["EditorMetadata"]


def __getattr__(name: str):
    if name == "EditorMetadata":
        return EditorMetadata
    if name in _RESGEN_EXPORTS:
        module = import_module(".resgen", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
