from dataclasses import dataclass

from .diagnostic import Diagnostic
from .graph import ResolvedDocsGraph


@dataclass(slots=True)
class MetaState:
    docs_graph: ResolvedDocsGraph
    diagnostics: list[Diagnostic]
