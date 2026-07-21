from importlib import import_module
from typing import TYPE_CHECKING

from .codegen import (
    DocstringPolicy,
    EntityGenerator,
    PathPolicy,
    RenderContext,
    RendererRegistry,
    ResourceRenderer,
    StandardGenerator,
)
from .core import (
    ClassNode,
    CodeWriter,
    ResourceNode,
    SchemaParser,
)
from .parsers import (
    KotoneV1Parser,
    ParserRegistry,
)
from .utils import (
    ImageProcessor,
    build_class_tree,
    to_camel_case,
    unify_path,
)

if TYPE_CHECKING:
    from .runner import ResgenGenerateResult, generate_resources

_RUNNER_EXPORTS = [
    "ResgenGenerateResult",
    "generate_resources",
]

__all__ = [
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

    # runner
    "ResgenGenerateResult",
    "generate_resources",

    # utils
    "to_camel_case",
    "unify_path",
    "build_class_tree",
    "ImageProcessor",
]


def __getattr__(name: str):
    if name in _RUNNER_EXPORTS:
        module = import_module(".runner", __name__)
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
