"""构图片段：封装由多个 Node 组成的子图，只暴露入口和出口。"""

from dataclasses import dataclass

from .pipeline import ConnectionExpression, Node, connect


@dataclass(frozen=True)
class Fragment:
    """构图片段：封装由多个 Node 组成的子图，只暴露入口和出口。

    Fragment 不拥有运行时状态，不出现在最终 Pipeline 中。
    它只是构图期的语法糖，连接时会将 Fragment 展开为纯 Node。
    """

    entry: Node
    exit: Node

    @property
    def _connect_head(self) -> Node:
        """返回连接入口（自身 entry）。"""
        return self.entry

    @property
    def _connect_tails(self) -> list[Node]:
        """返回连接尾部（自身 exit）。"""
        return [self.exit]

    def __rshift__(self, target: object) -> ConnectionExpression:
        """连接 fragment.exit 到 target，返回以 entry 为入口的连接表达式。

        :param target: Node、Fragment、连接表达式、列表或元组。
        :returns: 连接表达式（入口为 ``self.entry``），供外层 ``_normalize_candidates``
            提取入口并继续链式连接。
        :raises PipelineGraphFrozenError: 末端或目标已冻结时抛出。
        :raises ValueError: 候选列表包含重复项时抛出。
        :raises TypeError: target 类型不支持时抛出。
        """
        return connect(self.entry, [self.exit], target)
