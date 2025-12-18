from typing import Generic, TYPE_CHECKING
from typing_extensions import Unpack, override

from kotonebot.primitives import Rect
from kotonebot.devtools import EditorMetadata

from .base import Prefab, FindKwargs, GameObjectType, ClickKwargs as _ClickKwargs, WaitKwargs as _WaitKwargs


class OcrFindKargs(FindKwargs[GameObjectType], total=False):
    region: Rect | None
    """搜索区域
    
    如果指定，则覆盖 OcrPrefab 中定义的 region 属性。
    """

class ClickKwargs(OcrFindKargs[GameObjectType], _ClickKwargs[GameObjectType], Generic[GameObjectType], total=False): pass
class WaitKwargs(OcrFindKargs[GameObjectType], _WaitKwargs[GameObjectType], Generic[GameObjectType], total=False): pass


class OcrPrefab(Prefab[GameObjectType]):
    """基于 Ocr 的 Prefab"""
    pattern: str
    region: Rect | None = None

    class _Editor(EditorMetadata):
        id = 'base_ocr'
        name = 'OCR'
        description = '基于 OCR + 文字匹配来识别对象'
        export_slice = False

    @override
    @classmethod
    def find(cls, **kwargs: Unpack[OcrFindKargs[GameObjectType]]) -> GameObjectType | None:
        from kotonebot import ocr
        predicate = kwargs.get('predicate')
        region = kwargs.get('region', cls.region)
        result = ocr.find(cls.pattern, rect=region)
        if result is None:
            return None
        obj_class = cls._get_object_class()
        obj = obj_class()
        # 使用原图坐标
        obj.rect = result.original_rect
        obj.prefab = cls
        if predicate is not None and not predicate(obj):
            return None
        return obj

    @override
    @classmethod
    def find_all(cls, **kwargs: Unpack[OcrFindKargs[GameObjectType]]) -> list[GameObjectType]:
        from kotonebot import ocr
        predicate = kwargs.get('predicate')
        region = kwargs.get('region', cls.region)
        # 获取所有 OCR 结果后按文本过滤
        results = ocr.ocr(rect=region)
        obj_class = cls._get_object_class()
        objects: list[GameObjectType] = []
        for r in results:
            if r.text == cls.pattern:
                obj = obj_class()
                obj.rect = r.original_rect
                obj.prefab = cls
                if predicate is None or predicate(obj):
                    objects.append(obj)
        return objects

    @override
    @classmethod
    def require(cls, **kwargs: Unpack[OcrFindKargs[GameObjectType]]) -> GameObjectType:
        from kotonebot import ocr, device
        from kotonebot.backend.ocr import TextNotFoundError
        predicate = kwargs.get('predicate')
        region = kwargs.get('region', cls.region)
        if predicate is None:
            result = ocr.expect(cls.pattern, rect=region)
            obj_class = cls._get_object_class()
            obj = obj_class()
            obj.rect = result.original_rect
            obj.prefab = cls
            return obj
        else:
            # 扫描所有 OCR 结果，匹配文本并套用 predicate
            results = ocr.ocr(rect=cls.region)
            obj_class = cls._get_object_class()
            for r in results:
                if r.text == cls.pattern:
                    obj = obj_class()
                    obj.rect = r.original_rect
                    if predicate(obj):
                        obj.prefab = cls
                        return obj
            raise TextNotFoundError(cls.pattern, device.screenshot())
    
    if TYPE_CHECKING:
        # 这些方法只需要重载声明，实际实现由基类提供不变
        @classmethod
        def exists(cls, **kwargs: Unpack[OcrFindKargs[GameObjectType]]) -> bool: ...
        
        @classmethod
        def click(cls, **kwargs: Unpack[ClickKwargs[GameObjectType]]) -> None: ...

        @classmethod
        def wait(cls, **kwargs: Unpack[WaitKwargs[GameObjectType]]) -> GameObjectType: ...
        
        @classmethod
        def try_click(cls, **kwargs: Unpack[ClickKwargs[GameObjectType]]) -> bool: ...
        
        @classmethod
        def try_wait(cls, **kwargs: Unpack[WaitKwargs[GameObjectType]]) -> GameObjectType | None: ...
