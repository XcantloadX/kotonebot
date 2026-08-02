"""导出 Pipeline 构图与运行 API。

主路径：函数工厂 + 无参 ``@node`` + ``Pipeline(entry=..., exit=...)``。
自带节点：``builtins``（``ocr`` / ``template_match`` / ``dummy`` 等）。
"""

from .pipeline import (
    ConnectionExpression,
    Node,
    NodeAlreadyWiredError,
    NodeFactory,
    Pipeline,
    PipelineGraphError,
    PipelineGraphFrozenError,
    PipelineRunningError,
    node,
    run_node,
)
from .builtins import (
    AfterMatch,
    click_first,
    dummy,
    ocr,
    prefab,
    resolve_labels,
    template_match,
    sleep,
)
from .fragment import Fragment

__all__ = [
    "AfterMatch",
    "click_first",
    "ConnectionExpression",
    "Fragment",
    "Node",
    "NodeAlreadyWiredError",
    "NodeFactory",
    "Pipeline",
    "PipelineGraphError",
    "PipelineGraphFrozenError",
    "PipelineRunningError",
    "dummy",
    "node",
    "ocr",
    "prefab",
    "resolve_labels",
    "run_node",
    "template_match",
    "sleep",
]
