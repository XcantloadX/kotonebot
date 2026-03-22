from dataclasses import dataclass
from typing import overload
from typing_extensions import override

from kotonebot.devtools.project.schema import StrProp, RectProp
from kotonebot.primitives import Rect
from kotonebot.devtools import EditorMetadata

from .base import (
    BoundPrefab,
    FindQuery,
    GameObjectType,
    Prefab,
)


@dataclass(frozen=True, slots=True)
class OcrQuery(FindQuery[GameObjectType]):
    region: Rect | None = None
    """搜索区域
    
    如果指定，则覆盖 OcrPrefab 中定义的 region 属性。
    """


class OcrPrefab(Prefab[GameObjectType]):
    """基于 Ocr 的 Prefab"""
    Query = OcrQuery

    pattern: str
    region: Rect | None = None

    class _Editor(EditorMetadata):
        name = 'OCR'
        description = '基于 OCR + 文字匹配来识别对象'
        primary_prop = 'region'
        icon = 'search-text'
        shortcut = 'o'
        props = {
            'pattern':  StrProp(label='匹配文本', description='用于匹配的文本内容', default_value=''),
            'region': RectProp(label='搜索区域', description='限定搜索区域以提升识别速度', default_value=None),
        }

    @classmethod
    def _resolve_region(cls, query: OcrQuery[GameObjectType]) -> Rect | None:
        return cls.region if query.region is None else query.region

    @override
    @classmethod
    def _find_impl(cls, query: OcrQuery[GameObjectType]) -> GameObjectType | None:
        from kotonebot import ocr
        region = cls._resolve_region(query)
        result = ocr.find(cls.pattern, rect=region)
        if result is None:
            return None
        obj_class = cls._get_object_class()
        obj = obj_class()
        # 使用原图坐标
        obj.rect = result.original_rect
        obj.prefab = cls
        if query.predicate is not None and not query.predicate(obj):
            return None
        return obj

    @override
    @classmethod
    def _find_all_impl(cls, query: OcrQuery[GameObjectType]) -> list[GameObjectType]:
        from kotonebot import ocr
        region = cls._resolve_region(query)
        # 获取所有 OCR 结果后按文本过滤
        results = ocr.ocr(rect=region)
        obj_class = cls._get_object_class()
        objects: list[GameObjectType] = []
        for r in results:
            if r.text == cls.pattern:
                obj = obj_class()
                obj.rect = r.original_rect
                obj.prefab = cls
                if query.predicate is None or query.predicate(obj):
                    objects.append(obj)
        return objects

    @override
    @classmethod
    def _require_impl(cls, query: OcrQuery[GameObjectType]) -> GameObjectType:
        from kotonebot import ocr, device
        from kotonebot.backend.ocr import TextNotFoundError
        region = cls._resolve_region(query)
        if query.predicate is None:
            result = ocr.expect(cls.pattern, rect=region)
            obj_class = cls._get_object_class()
            obj = obj_class()
            obj.rect = result.original_rect
            obj.prefab = cls
            return obj
        else:
            # 扫描所有 OCR 结果，匹配文本并套用 predicate
            results = ocr.ocr(rect=region)
            obj_class = cls._get_object_class()
            for r in results:
                if r.text == cls.pattern:
                    obj = obj_class()
                    obj.rect = r.original_rect
                    if query.predicate(obj):
                        obj.prefab = cls
                        return obj
            raise TextNotFoundError(cls.pattern, device.screenshot())

    @overload
    @classmethod
    def q(cls, query: OcrQuery[GameObjectType]) -> BoundPrefab[GameObjectType, OcrQuery[GameObjectType]]: ...
    @overload
    @classmethod
    def q(
        cls,
        *,
        region: Rect | None = None,
    ) -> BoundPrefab[GameObjectType, OcrQuery[GameObjectType]]: ...
    @classmethod
    def q(
        cls,
        query: OcrQuery[GameObjectType] | None = None,
        *,
        region: Rect | None = None,
    ) -> BoundPrefab[GameObjectType, OcrQuery[GameObjectType]]:
        actual_query: OcrQuery[GameObjectType]
        if query is not None:
            actual_query = query
        else:
            actual_query = OcrQuery(region=region)

        return BoundPrefab(cls, actual_query)
