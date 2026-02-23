from pydantic import BaseModel

from ..diagnostics.models import Diagnostic
from .graph import ResolvedDocsGraph


class MetaState(BaseModel):
    docs_graph: ResolvedDocsGraph
    diagnostics: list[Diagnostic]
