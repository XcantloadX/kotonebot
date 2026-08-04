"""提供以布尔节点和有序候选连接构成的同步 Pipeline。

主路径：在函数内用无参 ``@node`` 定义节点工厂、调用工厂得到 ``Node`` 实例、
用 ``>>`` / ``next`` 连接候选，再 ``return Pipeline(entry=..., exit=...)``。

``@node`` 始终返回 ``NodeFactory``，调用 ``factory()`` 得到 ``Node``。
"""

import inspect
import itertools
import logging
import time
from typing import Callable, Literal, Protocol, Sequence, overload, runtime_checkable

from ..errors import (
    NodeAlreadyWiredError,
    PipelineGraphError,
    PipelineGraphFrozenError,
    PipelineRunningError,
)

logger = logging.getLogger(__name__)

NodeCallback = Callable[[], bool]
CancelCallback = Callable[[], bool]
NodeKind = Literal["function", "template", "ocr", "prefab"]

# 全局计数器，用于自动生成 instance_id
_id_counter = itertools.count(1)

# ---------------------------------------------------------------------------
# Connectable 协议
# ---------------------------------------------------------------------------

@runtime_checkable
class Connectable(Protocol):
    """任何可参与 ``>>`` 连接的对象，暴露入口和尾部节点。

    通过 duck typing 让连接逻辑（``connect`` / ``_normalize_rshift_target``）
    以统一方式处理 ``Node``、``Fragment`` 及未来新类型，
    避免 ``pipeline`` 模块反向依赖 ``fragment`` 模块。
    """

    @property
    def _connect_head(self) -> 'Node': ...

    @property
    def _connect_tails(self) -> 'list[Node]': ...

# ---------------------------------------------------------------------------
# NodeFactory
# ---------------------------------------------------------------------------

class _BoundNodeFactory:
    """绑定到实例的节点工厂，由 ``NodeFactory.__get__`` 返回。"""

    __slots__ = ('_factory', '_instance')

    def __init__(self, factory: 'NodeFactory', instance: object) -> None:
        self._factory = factory
        self._instance = instance

    def __call__(self, *, id: str | None = None, label: str | None = None) -> 'Node':
        """创建绑定到实例的 Node。

        :param id: 实例 ID（instance_id）；未传入时自动生成。
        :param label: 面向用户的节点名称。
        :returns: 新 Node 实例。
        """
        import types
        bound_callback = types.MethodType(self._factory._callback, self._instance)
        return self._factory._make_node(bound_callback, instance_id=id, label=label)


class NodeFactory:
    """节点工厂，始终由 ``@node`` 返回。

    调用 ``factory()`` 生成一个 ``Node`` 实例。
    作为描述符使用时（类属性），提供绑定到实例的工厂。
    """

    def __init__(
        self,
        callback: Callable[..., bool],
        *,
        id: str | None = None,
        label: str | None = None,
        kind: NodeKind = "function",
    ) -> None:
        """初始化节点工厂。

        :param callback: 节点回调。
        :param id: 定义 ID（definition_id）；未传入时根据回调派生。
        :param label: 面向用户的节点名称。
        :param kind: 节点种类元数据。
        :raises TypeError: 回调签名不合法（无法无参调用，或返回标注非 ``bool``）时抛出。
        """
        _validate_node_signature(callback)
        self._callback = callback
        self._definition_id = id or _default_factory_id(callback)
        self._label = label
        self._kind = kind

    def _make_node(
        self,
        callback: NodeCallback,
        *,
        instance_id: str | None = None,
        label: str | None = None,
    ) -> 'Node':
        """创建 Node 实例的底层方法。

        :param callback: 已适配签名的回调。
        :param instance_id: 实例 ID；未传入时由 ``Node`` 自动生成。
        :param label: 面向用户的节点名称。
        :returns: 新 Node 实例。
        """
        return Node(
            callback,
            definition_id=self._definition_id,
            instance_id=instance_id,
            label=label or self._label,
            kind=self._kind,
        )

    def __call__(self, *, id: str | None = None, label: str | None = None) -> 'Node':
        """创建 Node 实例。

        :param id: 实例 ID（instance_id）；未传入时自动生成。
        :param label: 面向用户的节点名称。
        :returns: 新 Node 实例。
        """
        return self._make_node(self._callback, instance_id=id, label=label)

    def __get__(self, instance: object | None, owner: type) -> 'NodeFactory | _BoundNodeFactory':
        """描述符协议：实例访问时返回绑定工厂。"""
        if instance is None:
            return self
        return _BoundNodeFactory(self, instance)


def _default_factory_id(callback: Callable) -> str:
    """为 NodeFactory 生成默认 definition_id。

    优先 ``模块名.qualname``。
    """
    module = getattr(callback, '__module__', None)
    qualname = getattr(callback, '__qualname__', None)
    if isinstance(qualname, str) and qualname:
        if isinstance(module, str) and module and module != 'builtins':
            return f'{module}.{qualname}'
        return qualname
    name = getattr(callback, '__name__', None)
    if isinstance(name, str) and name:
        if isinstance(module, str) and module and module != 'builtins':
            return f'{module}.{name}'
        return name
    return 'node'


def _validate_node_signature(callback: Callable[..., bool]) -> None:
    """校验节点回调签名：必须可无参调用，返回类型标注若存在则必须是 ``bool``。

    实例方法（首个参数名为 ``self`` / ``cls``）的参数在绑定后由解释器注入，
    校验时忽略该参数。无法获取签名（如部分内置可调用对象）时跳过静态校验，
    交由运行期的 ``Node.call`` 兜底。

    :param callback: 节点回调。
    :raises TypeError: 签名不合法时抛出。
    """
    try:
        sig = inspect.signature(callback)
    except (TypeError, ValueError):
        return
    params = list(sig.parameters.values())
    if params and params[0].name in ("self", "cls"):
        params = params[1:]
    for p in params:
        if p.default is inspect.Parameter.empty and p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            raise TypeError(
                f"@node callback '{getattr(callback, '__qualname__', repr(callback))}' "
                "must be callable without arguments"
            )
    return_annotation = sig.return_annotation
    if return_annotation is inspect.Signature.empty:
        return
    if isinstance(return_annotation, str):
        is_bool = return_annotation == "bool"
    else:
        is_bool = return_annotation is bool
    if not is_bool:
        raise TypeError(
            f"@node callback '{getattr(callback, '__qualname__', repr(callback))}' "
            f"must return bool, got annotation {return_annotation!r}"
        )


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class Node:
    """表示返回 ``bool`` 的可执行节点。"""

    _next: list['Node']
    _frozen: bool

    def __init__(
        self,
        callback: NodeCallback,
        *,
        definition_id: str | None = None,
        instance_id: str | None = None,
        label: str | None = None,
        kind: NodeKind = 'function',
    ) -> None:
        """初始化节点。

        :param callback: 无参数且返回布尔值的节点函数。
        :param definition_id: 节点定义 ID（工厂级别标识）；未传入时根据回调派生。
        :param instance_id: 节点实例 ID（图内唯一）；未传入时自动生成。
        :param label: 面向用户的节点名称；默认使用实例 ID。
        :param kind: 节点种类元数据。
        """
        if definition_id is None:
            definition_id = _default_factory_id(callback)
        if instance_id is None:
            instance_id = f"{definition_id}#{next(_id_counter)}"
        self._callback = callback
        self.definition_id = definition_id
        self.instance_id = instance_id
        self.label = label or instance_id
        self.kind = kind
        self._next: list[Node] = []
        self._frozen: bool = False

    @property
    def id(self) -> str:
        """返回节点实例 ID（兼容旧属性）。"""
        return self.instance_id

    def call(self) -> bool:
        """执行节点并严格校验布尔返回值。

        :returns: 节点是否命中或完成。
        :raises TypeError: 节点没有返回 ``bool`` 时抛出。
        """
        result = self._callback()
        if not isinstance(result, bool):
            raise TypeError(
                f"node {self.instance_id} returned {type(result).__name__}; expected bool"
            )
        return result

    def freeze(self) -> None:
        """冻结节点，禁止后续图结构修改。由 Pipeline 在装配完成后调用。"""
        self._frozen = True

    @property
    def _connect_head(self) -> 'Node':
        """返回连接入口（自身）。"""
        return self

    @property
    def _connect_tails(self) -> 'list[Node]':
        """返回连接尾部（自身）。"""
        return [self]

    @property
    def next(self) -> list['Node']:
        """返回按优先级排序的后继候选副本。"""
        return list(self._next)

    @next.setter
    def next(self, value: list['Node']) -> None:
        """设置按优先级排序的后继候选（覆盖语义，不做硬连线检查）。

        :param value: 仅由 Node 组成的列表。
        :raises PipelineGraphFrozenError: 节点已冻结时抛出。
        """
        if self._frozen:
            raise PipelineGraphFrozenError(
                f"node '{self.instance_id}' belongs to a frozen pipeline"
            )
        self._next = list(value)

    def __rshift__(
        self,
        target: 'Connectable | ConnectionExpression | Sequence[Connectable | ConnectionExpression]',
    ) -> 'ConnectionExpression':
        """立即连接右侧候选，并返回保留入口和末端的连接表达式。

        :param target: Node、Fragment、连接表达式、列表或元组。
        :returns: 可继续链式连接的轻量表达式。
        :raises NodeAlreadyWiredError: 本节点已有后继候选时抛出。
        :raises PipelineGraphFrozenError: 节点或任一候选已冻结时抛出。
        :raises TypeError: 右侧候选类型不正确时抛出。
        """
        # Node 独有：冻结状态与 once-only 硬连线检查必须在委托 connect() 前完成，
        # 保证「已冻结 + 已有后继」的节点优先报告冻结而非「已有后继」
        if self._frozen:
            raise PipelineGraphFrozenError(
                f"node '{self.instance_id}' belongs to a frozen pipeline"
            )
        if self._next:
            raise NodeAlreadyWiredError(
                f"node '{self.instance_id}' already has successors; "
                "use 'node.next = [...]' to replace instead of '>>'"
            )
        return connect(self, [self], target)


# ---------------------------------------------------------------------------
# ConnectionExpression
# ---------------------------------------------------------------------------

class ConnectionExpression:
    """保存一段 ``>>`` 连接的入口和当前末端。"""

    __slots__ = ('head', 'tails')

    def __init__(self, *, head: Node, tails: list[Node]) -> None:
        self.head = head
        self.tails = tails

    def __rshift__(
        self,
        target: 'Connectable | ConnectionExpression | Sequence[Connectable | ConnectionExpression]',
    ) -> 'ConnectionExpression':
        """把所有末端连接到右侧候选，并保留原始入口。

        :param target: Node、Fragment、连接表达式、列表或元组。
        :returns: 更新末端后的连接表达式。
        :raises PipelineGraphFrozenError: 任一末端或候选已冻结时抛出。
        :raises ValueError: 候选列表包含重复项时抛出。
        :raises TypeError: 右侧候选类型不正确时抛出。
        """
        # 无 once-only：表达式是临时对象，链式复用是正常用法
        return connect(self.head, list(self.tails), target)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class _RunSchedule:
    """Runner 级轮询、超时与取消配置。"""

    __slots__ = ('interval', 'deadline', 'single_pass', 'cancel')

    def __init__(
        self,
        interval: float,
        deadline: float | None,
        single_pass: bool,
        cancel: CancelCallback | None,
    ) -> None:
        self.interval = interval
        self.deadline = deadline
        self.single_pass = single_pass
        self.cancel = cancel


class Pipeline:
    """同步执行由 Node 构成的有向图。

    ``Pipeline(entry=node, exit=node)``，在工厂函数内
    用无参 ``@node`` 与 ``>>`` / ``.next`` 连好图后返回。
    """

    _entry: Node
    _exit: Node | None
    _running: bool
    _strict: bool

    def __init__(
        self,
        *,
        entry: Node,
        exit: Node | None = None,
        strict: bool = True,
    ) -> None:
        """以已连接的入口 / 出口直接构造。

        :param entry: 入口节点。
        :param exit: 出口节点；必须是叶子（``exit.next`` 为空）。
        :param strict: 严格模式。``True`` 时 exit 必须提供；
            图结构会校验 exit 可达性与叶子合法性。``False`` 时允许无 exit，
            运行时无后继即自然结束。
        :raises PipelineGraphError: 图结构不合法时抛出。
        """
        self._strict = strict
        self._running = False
        self._entry = entry
        self._exit = exit

        # 1. 入口必须是 Node；否则无法进行可达性遍历与结构校验
        if not isinstance(entry, Node):
            raise PipelineGraphError(
                f'pipeline entry must be a Node, got {type(entry).__name__}'
            )

        # 2. 从 entry 遍历可达节点，收集所有权
        reachable = _collect_reachable_nodes(entry)

        # 3. 校验图结构
        _validate_pipeline(entry, exit, reachable, strict)

        # 4. 冻结所有节点
        for n in reachable:
            if n._frozen:
                raise PipelineGraphError(
                    f"node '{n.instance_id}' already belongs to another pipeline"
                )
            n.freeze()

    def run(
        self,
        *,
        interval: float = 0.1,
        timeout: float | None = None,
        cancel: CancelCallback | None = None,
    ) -> bool:
        """从入口运行 Pipeline，直到出口命中；超时与取消仅在全部候选未命中的轮次中生效。

        超时语义：

        - ``timeout=0``：不阻塞轮询；本轮全部候选未命中则返回 ``False``。
        - ``timeout=None``：一直轮询直到完成或 ``cancel``。
        - ``timeout>0``：在截止时间前轮询；截止时间从本调用开始计算，
          仅在全部候选未命中的轮次中检查。

        :param interval: 最小轮次间隔秒数；每轮迭代结束后至少等待此时间再开始下一轮；``0`` 表示不 sleep。
        :param timeout: 超时秒数；见上方语义。
        :param cancel: 返回 ``True`` 时中止并返回 ``False``。
        :returns: 是否成功命中出口。
        :raises PipelineRunningError: 同一实例重入顶层运行时抛出。
        :raises ValueError: ``timeout`` 或 ``interval`` 为负数时抛出。
        """
        if self._running:
            raise PipelineRunningError(
                f"pipeline (entry={self._entry.instance_id}) is already running"
            )
        self._running = True
        try:
            schedule = _make_schedule(interval=interval, timeout=timeout, cancel=cancel)
            return self._run(schedule)
        finally:
            self._running = False

    def try_run(
        self,
        *,
        interval: float = 0.1,
        timeout: float | None = 0,
        cancel: CancelCallback | None = None,
    ) -> bool:
        """尝试运行本 Pipeline，默认只扫描一轮（``timeout=0``）。

        供节点内嵌同步调用子流程使用，调度路径与 ``run()`` 相同。

        :param interval: 最小轮次间隔秒数；每轮迭代结束后至少等待此时间再开始下一轮。
        :param timeout: 超时秒数；默认 ``0`` 表示不阻塞。
        :param cancel: 返回 ``True`` 时中止并返回 ``False``。
        :returns: 是否成功命中出口。
        """
        return self.run(interval=interval, timeout=timeout, cancel=cancel)

    def _run(self, schedule: _RunSchedule) -> bool:
        """执行图的主循环。

        :param schedule: 调度配置。
        :returns: 是否成功完成。
        """
        current = self._entry
        logger.debug("node: %s(id=%s)", current.label, current.instance_id)
        if not current.call():
            logger.debug("node: %s(id=%s) -> exit", current.label, current.instance_id)
            return False
        last_cycle = time.monotonic()
        while True:
            # 结束条件判定
            if current is self._exit:
                logger.debug("node: %s(id=%s) -> exit", current.label, current.instance_id)
                return True
            if self._exit is None and not current._next:
                logger.debug("node: %s(id=%s) -> exit", current.label, current.instance_id)
                return True

            # 截图数据更新
            from kotonebot import device
            device.screenshot()

            # 选择下一个候选
            selected: Node | None = None
            for candidate in current._next:
                if candidate.call():
                    selected = candidate
                    break
            if selected is not None:
                logger.debug("node: %s(id=%s) -> %s(id=%s)",
                    current.label, current.instance_id,
                    selected.label, selected.instance_id)
                current = selected
            else:
                if not current._next:
                    logger.debug("node: %s(id=%s) -> exit", current.label, current.instance_id)
                    return True
                if schedule.single_pass:
                    return False
                if schedule.deadline is not None and time.monotonic() >= schedule.deadline:
                    logger.debug(
                        "Pipeline (entry=%s) polling timeout",
                        self._entry.instance_id,
                    )
                    return False
                if schedule.cancel is not None and schedule.cancel():
                    logger.debug(
                        "Pipeline (entry=%s) cancelled",
                        self._entry.instance_id,
                    )
                    return False

            # 最小轮次间隔
            if schedule.interval > 0:
                elapsed = time.monotonic() - last_cycle
                remaining = schedule.interval - elapsed
                if remaining > 0:
                    time.sleep(remaining)
            last_cycle = time.monotonic()


# ---------------------------------------------------------------------------
# @node 装饰器
# ---------------------------------------------------------------------------

@overload
def node(func: Callable[..., bool]) -> NodeFactory: ...

@overload
def node(
    *,
    id: str | None = None,
    label: str | None = None,
    kind: NodeKind = 'function',
) -> Callable[[Callable[..., bool]], NodeFactory]: ...

def node(
    func: Callable[..., bool] | None = None,
    *,
    id: str | None = None,
    label: str | None = None,
    kind: NodeKind = 'function',
) -> NodeFactory | Callable[[Callable[..., bool]], NodeFactory]:
    """将返回 ``bool`` 的函数或方法定义为节点工厂。

    始终返回 ``NodeFactory``，调用 ``factory()`` 得到 ``Node``。

    :param func: 被装饰的可调用对象。
    :param id: 定义 ID（definition_id）。
    :param label: 面向用户的节点名称。
    :param kind: 节点种类元数据。
    :returns: ``NodeFactory`` 或带参装饰器。
    """

    def decorate(callback: Callable[..., bool]) -> NodeFactory:
        return NodeFactory(callback, id=id, label=label, kind=kind)

    if func is None:
        return decorate
    return decorate(func)


# ---------------------------------------------------------------------------
# 轻量节点构造
# ---------------------------------------------------------------------------

def create_node(
    callback: NodeCallback,
    *,
    definition_id: str,
    label: str | None = None,
    kind: NodeKind = 'function',
) -> Node:
    """创建 Node，自动生成 instance_id。

    跳过签名校验，供 builtins 等没有独立回调定义的使用方构造节点，
    保证与 ``@node`` 工厂路径的 instance_id 格式一致（``definition_id#N``）。

    :param callback: 无参数且返回布尔值的节点函数。
    :param definition_id: 节点定义 ID。
    :param label: 面向用户的节点名称。
    :param kind: 节点种类元数据。
    :returns: 新 Node 实例。
    """
    return Node(
        callback,
        definition_id=definition_id,
        label=label,
        kind=kind,
    )


# ---------------------------------------------------------------------------
# 运行节点
# ---------------------------------------------------------------------------

def run_node(target: Node) -> bool:
    """受控单步执行节点，语义与 Runner 调用节点一致。

    :param target: 要执行的节点。
    :returns: 节点是否命中。
    :raises TypeError: 节点未返回 ``bool`` 时抛出。
    """
    return target.call()


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------

def connect(
    source_head: Node,
    source_tails: list[Node],
    target: object,
) -> ConnectionExpression:
    """将 source_tails 的 ``_next`` 设为 target 展开后的候选节点。

    所有 ``>>`` 连接的唯一入口：标准化目标、查重、冻结校验、写入、返回表达式。
    ``Node.__rshift__`` 的 once-only 检查在调用本函数前完成。

    :param source_head: 连接表达式的入口节点。
    :param source_tails: 需要写入 ``_next`` 的源尾部节点。
    :param target: ``>>`` 右侧操作数。
    :returns: 以 ``source_head`` 为入口、target 尾部为末端的连接表达式。
    :raises PipelineGraphFrozenError: 任一源尾部或候选节点已冻结时抛出。
    :raises ValueError: 候选列表包含重复项时抛出。
    :raises TypeError: 右侧候选类型不正确时抛出。
    """
    candidates, target_tails = _normalize_rshift_target(target)
    _check_duplicates(candidates)
    # 先整体校验冻结状态，避免写入一部分后中途抛错
    _check_frozen(*source_tails, *candidates)
    for tail in source_tails:
        tail._next = list(candidates)
    return ConnectionExpression(head=source_head, tails=target_tails)


def _normalize_rshift_target(target: object) -> tuple[list[Node], list[Node]]:
    """把 ``>>`` 右侧值标准化为（候选节点列表, 尾部节点列表）。

    候选节点：直接写入源节点 ``next`` 的节点。
    尾部节点：后续链式连接要修改 ``next`` 的末端；Fragment 以其出口作为末端，
    保证 ``start >> fragment >> finish`` 等价于把 Fragment 内部节点全部串联。

    通过 ``Connectable`` duck typing 识别 Fragment 等自定义对象，
    无需在 ``pipeline`` 模块中反向导入。

    :param target: 右侧操作数。
    :returns: (候选节点列表, 尾部节点列表)。
    :raises TypeError: 不支持的类型时抛出。
    """
    if isinstance(target, Node):
        return [target], [target]
    if isinstance(target, ConnectionExpression):
        return [target.head], list(target.tails)
    if isinstance(target, (list, tuple)):
        return _normalize_candidates(target)
    if isinstance(target, Connectable):
        return [target._connect_head], list(target._connect_tails)
    raise TypeError(
        f'invalid >> target: expected Node, Fragment, ConnectionExpression, list, or tuple, '
        f'got {type(target).__name__}'
    )


def _normalize_candidates(values: Sequence[object]) -> tuple[list[Node], list[Node]]:
    """校验并标准化候选列表为（候选节点, 尾部节点）。

    列表中的 ConnectionExpression 以 ``head`` 作为候选、以 ``tails`` 作为尾部；
    Connectable（如 ``Fragment``）以 ``_connect_head`` 作为候选、以 ``_connect_tails`` 作为尾部。

    :param values: 候选序列。
    :returns: (候选节点列表, 尾部节点列表)。
    :raises TypeError: 包含非法类型时抛出。
    """
    candidates: list[Node] = []
    tails: list[Node] = []
    for v in values:
        if isinstance(v, Node):
            candidates.append(v)
            tails.append(v)
        elif isinstance(v, ConnectionExpression):
            candidates.append(v.head)
            tails.extend(v.tails)
        elif isinstance(v, Connectable):
            candidates.append(v._connect_head)
            tails.extend(v._connect_tails)
        else:
            raise TypeError(
                f'invalid next candidate: expected Node, Fragment, or ConnectionExpression, '
                f'got {type(v).__name__}'
            )
    return candidates, tails


def _check_duplicates(candidates: list[Node]) -> None:
    """检查候选列表中的重复项。

    :raises ValueError: 存在重复时抛出。
    """
    seen: set[int] = set()
    for c in candidates:
        cid = id(c)
        if cid in seen:
            raise ValueError('duplicate candidates in >>')
        seen.add(cid)


def _check_frozen(*nodes: Node) -> None:
    """校验给定节点均未被冻结。

    :param nodes: 待检查的节点。
    :raises PipelineGraphFrozenError: 任一节点已冻结时抛出。
    """
    for n in nodes:
        if n._frozen:
            raise PipelineGraphFrozenError(
                f"node '{n.instance_id}' belongs to a frozen pipeline")


def _collect_reachable_nodes(entry: Node) -> list[Node]:
    """从 entry 遍历可达的所有 Node。

    :param entry: 入口节点。
    :returns: 可达节点列表（含 entry 自身）。
    """
    stack: list[Node] = [entry]
    seen: set[int] = set()
    nodes: list[Node] = []
    while stack:
        node = stack.pop()
        nid = id(node)
        if nid in seen:
            continue
        seen.add(nid)
        nodes.append(node)
        stack.extend(node._next)
    return nodes


def _validate_pipeline(
    entry: Node,
    exit: Node | None,
    reachable: list[Node],
    strict: bool,
) -> None:
    """校验 Pipeline 图结构。

    :param entry: 入口节点。
    :param exit: 出口节点。
    :param reachable: 从 entry 可达的节点列表。
    :param strict: 严格模式。
    :raises PipelineGraphError: 图结构不合法时抛出。
    """
    if strict and exit is None:
        raise PipelineGraphError('pipeline must configure exit')
    if exit is not None and exit._next:
        raise PipelineGraphError(
            'pipeline exit must be a leaf node with empty next; '
            'use Pipeline.next for external successors'
        )
    if strict and exit is not None:
        reachable_ids = {id(n) for n in reachable}
        if id(exit) not in reachable_ids:
            raise PipelineGraphError(
                f'pipeline exit is not reachable from entry: {exit.instance_id}'
            )
        for n in reachable:
            if not n._next and n is not exit:
                raise PipelineGraphError(
                    f'reachable leaf node is not exit: '
                    f'label={n.label} id={n.instance_id}'
                )


def _make_schedule(
    *,
    interval: float,
    timeout: float | None,
    cancel: CancelCallback | None,
) -> _RunSchedule:
    """根据 Runner 参数构造内部调度配置。

    :param interval: 最小轮次间隔秒数。
    :param timeout: 超时秒数。
    :param cancel: 取消回调。
    :returns: 内部调度配置。
    :raises ValueError: 参数非法时抛出。
    """
    if interval < 0:
        raise ValueError('interval must be >= 0')
    if timeout is not None and timeout < 0:
        raise ValueError('timeout must be None or >= 0')
    if timeout is None:
        return _RunSchedule(interval=interval, deadline=None, single_pass=False, cancel=cancel)
    if timeout == 0:
        return _RunSchedule(interval=interval, deadline=None, single_pass=True, cancel=cancel)
    return _RunSchedule(
        interval=interval,
        deadline=time.monotonic() + timeout,
        single_pass=False,
        cancel=cancel,
    )
