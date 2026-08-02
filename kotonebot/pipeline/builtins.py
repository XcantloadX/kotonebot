"""Pipeline 自带节点库（builtins）。

提供预封装节点工厂与命中后动作配置（``actions=``）。
调度语义与手写 ``@node`` 相同：匹配成功则执行 actions 并返回 ``True``，
否则返回 ``False``。动作不是控制流，控制流仍只有 ``next`` / ``>>``。
"""

import inspect
from typing import Any, Callable, Generic, Sequence, TypeVar, cast, overload

from kotonebot.backend.context import ocr as _backend_ocr, image as _backend_image
from kotonebot.backend.image import TemplateMatchResult
from kotonebot.backend.ocr import OcrResult
from kotonebot.client.protocol import ClickableObjectProtocol
from kotonebot.core.entities.base import GameObject, Prefab, BoundPrefab
from kotonebot.primitives import ImageLike, Rect

from .pipeline import Node, create_node


T = TypeVar('T')
CT = TypeVar('CT', bound=ClickableObjectProtocol)
G = TypeVar('G', bound=GameObject)

class AfterMatch(Generic[T]):
    """匹配结果包装，供 action 消费。

    :param matches: 所有命中的结果列表。
    """

    matches: list[T]

    def __init__(self, matches: list[T]) -> None:
        """初始化包装。

        :param matches: 命中的结果列表。
        """
        self.matches = matches

    @property
    def first(self) -> T | None:
        """返回第一个命中结果，若无则返回 ``None``。"""
        return self.matches[0] if self.matches else None

    @property
    def hit(self) -> bool:
        """是否有至少一个命中结果。"""
        return len(self.matches) > 0

def _normalize_actions(
    actions: Callable[..., Any] | Sequence[Callable[..., Any]] | None,
) -> list[Callable[..., Any]]:
    """将单个或一组 action 规范为列表。"""
    if actions is None:
        return []
    # 单回调：函数/可调用对象；列表/元组：多 action
    if isinstance(actions, Sequence) and not isinstance(actions, (str, bytes)):
        return list(actions)
    return [actions]


def ocr(
    matches: str | list[str],
    actions: Callable[[AfterMatch[OcrResult]], Any] | Sequence[Callable[[AfterMatch[OcrResult]], Any]] | None = None,
    *,
    roi: Rect | None = None,
    id: str | None = None,
    label: str | None = None,
) -> Node:
    """创建 OCR 文本节点。

    使用 `kotonebot.backend.context` 中的 OCR 引擎进行识别。
    动作通过 ``actions=`` 参数配置，构造后不可变更。

    :param matches: 目标文本，或文本列表。
    :param actions: 命中后动作列表。
    :param roi: 可选识别区域。
    :param id: 定义 ID（definition_id）；未传入时自动生成，instance_id 统一为 ``definition_id#N``。
    :param label: 面向用户的节点名称。
    :returns: ``Node``（``kind="ocr"``）。
    """
    if isinstance(matches, list):
        default_id = "ocr:" + "|".join(matches)
    else:
        default_id = f"ocr:{matches}"

    normalized_actions = _normalize_actions(actions)

    def callback() -> bool:
        if isinstance(matches, list):
            results = _backend_ocr.find_all(matches, rect=roi)
            matched = [r for r in results if r is not None]
            if not matched:
                return False
            result = AfterMatch(matched)
        else:
            result_obj = _backend_ocr.find(matches, rect=roi)
            if result_obj is None:
                return False
            result = AfterMatch([result_obj])
        for action in normalized_actions:
            action(result)
        return True

    return create_node(callback, definition_id=id or default_id, label=label, kind="ocr")


def template_match(
    template: ImageLike | Sequence[ImageLike],
    actions: Callable[[AfterMatch[TemplateMatchResult]], Any] | Sequence[Callable[[AfterMatch[TemplateMatchResult]], Any]] | None = None,
    *,
    roi: Rect | None = None,
    id: str | None = None,
    label: str | None = None,
) -> Node:
    """创建模板匹配节点。

    使用 `kotonebot.backend.context` 中的图像识别引擎进行匹配。
    动作通过 ``actions=`` 参数配置，构造后不可变更。

    :param template: 模板图像或模板序列。
    :param actions: 命中后动作列表。
    :param roi: 可选识别区域。
    :param id: 定义 ID（definition_id）；未传入时自动生成，instance_id 统一为 ``definition_id#N``。
    :param label: 面向用户的节点名称。
    :returns: ``Node``（``kind="template"``）。
    """
    if isinstance(template, (list, tuple)):
        default_id = "template:multi"
    else:
        default_id = "template:single"

    normalized_actions = _normalize_actions(actions)

    def callback() -> bool:
        if isinstance(template, (list, tuple)):
            result = _backend_image.find_multi(templates=list(template), rect=roi)
            if result is None:
                return False
            result_wrapper = AfterMatch([cast(TemplateMatchResult, result)])
        else:
            _template = cast(ImageLike, template)
            elem = _backend_image.find(template=_template, rect=roi)
            if elem is None:
                return False
            result_wrapper = AfterMatch([elem])
        for action in normalized_actions:
            action(result_wrapper)
        return True

    return create_node(callback, definition_id=id or default_id, label=label, kind="template")


@overload
def prefab(
    prefab_cls: type[Prefab[G]],
    actions: Callable[[AfterMatch[G]], Any] | Sequence[Callable[[AfterMatch[G]], Any]] | None = None,
    *,
    id: str | None = None,
    label: str | None = None,
) -> Node: ...


@overload
def prefab(
    prefab_cls: BoundPrefab[G, Any],
    actions: Callable[[AfterMatch[G]], Any] | Sequence[Callable[[AfterMatch[G]], Any]] | None = None,
    *,
    id: str | None = None,
    label: str | None = None,
) -> Node: ...


@overload
def prefab(
    prefab_cls: Sequence[type[Prefab[Any]] | BoundPrefab[Any, Any]],
    actions: Callable[[AfterMatch[GameObject]], Any] | Sequence[Callable[[AfterMatch[GameObject]], Any]] | None = None,
    *,
    id: str | None = None,
    label: str | None = None,
) -> Node: ...


def prefab(
    prefab_cls: type[Prefab[G]] | BoundPrefab[G, Any] | Sequence[type[Prefab[Any]] | BoundPrefab[Any, Any]],
    actions: Callable[[AfterMatch[Any]], Any] | Sequence[Callable[[AfterMatch[Any]], Any]] | None = None,
    *,
    id: str | None = None,
    label: str | None = None,
) -> Node:
    """创建 Prefab 节点。

    使用 Prefab 类的查找逻辑进行识别。
    动作通过 ``actions=`` 参数配置，构造后不可变更。

    :param prefab_cls: Prefab 类、BoundPrefab 实例，或它们的列表（按序尝试，返回首个命中）。
    :param actions: 命中后动作列表。
    :param id: 定义 ID（definition_id）；未传入时自动生成，instance_id 统一为 ``definition_id#N``。
    :param label: 面向用户的节点名称。
    :returns: ``Node``（``kind="prefab"``）。
    """
    normalized_actions = _normalize_actions(actions)

    def callback() -> bool:
        if isinstance(prefab_cls, BoundPrefab):
            obj = prefab_cls.find()
            if obj is not None:
                result = AfterMatch([obj])
            else:
                return False
        elif isinstance(prefab_cls, Sequence) and not isinstance(prefab_cls, type):
            matched = None
            for cls in prefab_cls:
                obj = cls.find()
                if obj is not None:
                    matched = obj
                    break
            if matched is None:
                return False
            result = AfterMatch([matched])
        else:
            cls = cast(type[Prefab[G]], prefab_cls)
            obj = cls.find()
            if obj is not None:
                result = AfterMatch([obj])
            else:
                return False
        for action in normalized_actions:
            action(result)
        return True

    if isinstance(prefab_cls, BoundPrefab):
        default_id = f"prefab:{prefab_cls.prefab_cls.__name__}"
    elif isinstance(prefab_cls, Sequence) and not isinstance(prefab_cls, type):
        names: list[str] = []
        for c in prefab_cls:
            if isinstance(c, BoundPrefab):
                names.append(c.prefab_cls.__name__)
            else:
                names.append(cast(type, c).__name__)
        default_id = "prefab:" + "|".join(names)
    else:
        default_id = f"prefab:{cast(type, prefab_cls).__name__}"

    return create_node(callback, definition_id=id or default_id, label=label, kind="prefab")


def dummy(
    actions: Callable[[AfterMatch[None]], Any] | Sequence[Callable[[AfterMatch[None]], Any]] | None = None,
    *,
    id: str | None = None,
    label: str | None = None,
) -> Node:
    """创建恒命中的占位节点（无识别）。

    动作通过 ``actions=`` 参数配置，构造后不可变更。

    :param actions: 命中后动作列表。
    :param id: 定义 ID（definition_id）；默认 ``dummy``，instance_id 统一为 ``definition_id#N``。
    :param label: 面向用户的节点名称。
    :returns: 普通 ``Node``，``call()`` 恒为 ``True``。
    """
    normalized_actions = _normalize_actions(actions)

    def _cb() -> bool:
        result = AfterMatch([])
        for action in normalized_actions:
            action(result)
        return True

    return create_node(_cb, definition_id=id or "dummy", label=label, kind="function")


def click_first(ctx: AfterMatch[CT]) -> None:
    """点击第一个匹配结果的中心位置。

    作为 action 传入 ``actions=``。
    匹配结果类型需具有 ``.rect`` 属性（如
    ``OcrResult``、``TemplateMatchResult``、``GameObject``）。

    :param ctx: 匹配结果包装。
    """
    first = ctx.first
    if first is not None:
        from kotonebot import device
        device.click(first)

def sleep(seconds: float) -> Callable[[AfterMatch[Any]], None]:
    """睡眠指定秒数。

    作为 action 传入 ``actions=``。
    匹配结果类型不限制。

    :param ctx: 匹配结果包装。
    :param seconds: 睡眠秒数。
    """
    def _action(ctx: AfterMatch[Any]) -> None:
        from kotonebot import sleep as _sleep
        _sleep(seconds)

    return _action


def resolve_labels() -> None:
    """自动为调用者局部作用域中的 Node 变量设置 label 为其变量名。

    遍历调用者的局部变量，找出所有 ``Node`` 实例，
    将它们各自的变量名设为 ``label``。若同一个节点被多个变量引用，
    仅使用最先出现（即首个赋值）的变量名。
    """
    frame = inspect.currentframe()
    if frame is None:
        return
    outer = frame.f_back
    if outer is None:
        return
    try:
        local_vars = outer.f_locals
        node_to_name: dict[int, str] = {}
        for name, value in local_vars.items():
            if isinstance(value, Node):
                if id(value) not in node_to_name:
                    node_to_name[id(value)] = name
        for name, value in local_vars.items():
            if isinstance(value, Node):
                value.label = node_to_name[id(value)]
    finally:
        del frame, outer