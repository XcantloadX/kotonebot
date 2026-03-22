from dataclasses import dataclass
from typing import overload
from typing_extensions import override

from kotonebot.devtools.project.schema import BoolProp, FloatProp, ImageProp, RectProp
from kotonebot.primitives import Rect, ImageSlice
from kotonebot.devtools import EditorMetadata

from .base import (
    BoundPrefab,
    FindQuery,
    GameObjectType,
    Prefab,
)

@dataclass(frozen=True, slots=True)
class TemplateMatchQuery(FindQuery[GameObjectType]):
    threshold: float | None = None
    """匹配阈值
    
    如果指定，则覆盖 TemplateMatchPrefab 中定义的 threshold 属性。
    """
    colored: bool | None = None
    """是否匹配颜色
    
    如果指定，则覆盖 TemplateMatchPrefab 中定义的 colored 属性。
    """
    region: Rect | None = None
    """搜索区域
    
    如果指定，则覆盖 TemplateMatchPrefab 中定义的 region 属性。
    """

class TemplateMatchPrefab(Prefab[GameObjectType]):
    """基于模版匹配的 Prefab"""
    Query = TemplateMatchQuery

    template: ImageSlice
    """[必填] 用于匹配的模版图像"""
    fixed: bool = False
    """[可选] 是否固定位置。

    当 `fixed` 为 True 时，匹配将限定在 `template.slice_rect`（若存在）定义的区域内。
    若 `template` 无 `slice_rect`，会在运行时抛出 ValueError，以提示生成代码或资源定义不完整。
    """
    region: Rect | None = None
    """[可选] 限定搜索区域
    
    默认为 None（全屏搜索）。
    """
    threshold: float = 0.8
    """[可选] 匹配阈值
    
    范围 0.0 - 1.0，默认为 0.8。
    """
    colored: bool = False
    """[可选] 是否匹配颜色
    
    默认为 False（不匹配颜色）。
    """

    class _Editor(EditorMetadata):
        name = '模版'
        description = '基于模版匹配来寻找对象'
        primary_prop = 'template'
        icon = 'media'
        shortcut = 't'
        props = {
            'template':  ImageProp(label='模版图像', description='用于匹配的模版图像', default_value=None),
            'fixed': BoolProp(label='固定位置', description='对象位置是否固定不变，若固定可提升匹配速度', default_value=False),
            'region': RectProp(label='搜索区域', description='限定搜索区域以提升匹配速度', default_value=None),
            'threshold': FloatProp(label='匹配阈值', description='模版匹配的相似度阈值，范围 0.0 - 1.0', min=0.0, max=1.0, default_value=0.8),
            'colored': BoolProp(label='匹配颜色', description='是否在匹配时考虑颜色信息', default_value=False),
        }


    @classmethod
    def _resolve_match_options(cls, query: TemplateMatchQuery[GameObjectType]) -> tuple[float, bool, Rect | None]:
        threshold = cls.threshold if query.threshold is None else query.threshold
        colored = cls.colored if query.colored is None else query.colored
        region = cls.region if query.region is None else query.region
        # If prefab is fixed and no explicit region provided, use template.slice_rect
        if region is None and cls.fixed:
            slice_rect = cls.template.slice_rect
            if slice_rect is None:
                raise ValueError(f"Prefab {cls.__name__} is marked fixed but template has no slice_rect")
            region = slice_rect
        return threshold, colored, region

    @override
    @classmethod
    def _find_impl(cls, query: TemplateMatchQuery[GameObjectType]) -> GameObjectType | None:
        from kotonebot import image
        threshold, colored, region = cls._resolve_match_options(query)
        result = image.find(
            cls.template.pixels,
            rect=region,
            threshold=threshold,
            colored=colored,
        )
        if result is None:
            return None
        obj_class = cls._get_object_class()
        obj = obj_class()
        obj.rect = result.rect
        obj.prefab = cls
        if query.predicate is not None and not query.predicate(obj):
            return None
        return obj

    @override
    @classmethod
    def _find_all_impl(cls, query: TemplateMatchQuery[GameObjectType]) -> list[GameObjectType]:
        from kotonebot import image
        threshold, colored, region = cls._resolve_match_options(query)
        results = image.find_all(
            cls.template.pixels,
            rect=region,
            threshold=threshold,
            colored=colored,
        )
        obj_class = cls._get_object_class()
        objects: list[GameObjectType] = []
        for r in results:
            obj = obj_class()
            obj.rect = r.rect
            obj.prefab = cls
            if query.predicate is None or query.predicate(obj):
                objects.append(obj)
        return objects

    @override
    @classmethod
    def _require_impl(cls, query: TemplateMatchQuery[GameObjectType]) -> GameObjectType:
        from kotonebot import image, device
        from kotonebot.backend.image import TemplateNoMatchError
        threshold, colored, region = cls._resolve_match_options(query)
        if query.predicate is None:
            # 直接使用 expect，未找到会抛出 TemplateNoMatchError
            result = image.expect(
                cls.template.pixels,
                rect=region,
                threshold=threshold,
                colored=colored,
            )
            obj_class = cls._get_object_class()
            obj = obj_class()
            obj.rect = result.rect
            obj.prefab = cls
            return obj
        else:
            # 需要满足 predicate，则遍历所有匹配项
            results = image.find_all(
                cls.template.pixels,
                rect=region,
                threshold=threshold,
                colored=colored,
            )
            obj_class = cls._get_object_class()
            for r in results:
                obj = obj_class()
                obj.rect = r.rect
                if query.predicate(obj):
                    obj.prefab = cls
                    return obj
            # 没有任何匹配满足 predicate，抛出未找到异常
            raise TemplateNoMatchError(device.screenshot(), cls.template.pixels)

    @overload
    @classmethod
    def q(cls, query: TemplateMatchQuery[GameObjectType]) -> BoundPrefab[GameObjectType, TemplateMatchQuery[GameObjectType]]: ...
    @overload
    @classmethod
    def q(cls,
        *,
        threshold: float | None = None,
        colored: bool | None = None,
        region: Rect | None = None,
    ) -> BoundPrefab[GameObjectType, TemplateMatchQuery[GameObjectType]]: ...
    @classmethod
    def q(
        cls,
        query: TemplateMatchQuery[GameObjectType] | None = None,
        *,
        threshold: float | None = None,
        colored: bool | None = None,
        region: Rect | None = None,
    ) -> BoundPrefab[GameObjectType, TemplateMatchQuery[GameObjectType]]:
        actual_query: TemplateMatchQuery[GameObjectType]
        if query is not None:
            actual_query = query
        else:
            actual_query = TemplateMatchQuery(
                threshold=threshold,
                colored=colored,
                region=region,
            )

        return BoundPrefab(cls, actual_query)