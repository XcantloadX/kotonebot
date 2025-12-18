from typing import TYPE_CHECKING
from typing_extensions import Unpack, override

from kotonebot.primitives import Rect, Image
from kotonebot.devtools import EditorMetadata

from .base import Prefab, FindKwargs, GameObjectType


class TemplateMatchFindKargs(FindKwargs[GameObjectType], total=False):
    threshold: float | None
    """匹配阈值
    
    如果指定，则覆盖 TemplateMatchPrefab 中定义的 threshold 属性。
    """
    colored: bool | None
    """是否匹配颜色
    
    如果指定，则覆盖 TemplateMatchPrefab 中定义的 colored 属性。
    """
    region: Rect | None
    """搜索区域
    
    如果指定，则覆盖 TemplateMatchPrefab 中定义的 region 属性。
    """


class TemplateMatchPrefab(Prefab[GameObjectType]):
    """基于模版匹配的 Prefab"""
    template: Image
    """[必填] 用于匹配的模版图像"""
    region: Rect | None = None
    """[可选] 限定搜索区域
    
    默认为 None（全屏搜索）。
    """
    threshold: float = 0.7
    """[可选] 匹配阈值
    
    范围 0.0 - 1.0，默认为 0.7。
    """
    colored: bool = False
    """[可选] 是否匹配颜色
    
    默认为 False（不匹配颜色）。
    """

    class _Editor(EditorMetadata):
        id = 'base_template_match'
        name = '模版'
        description = '基于模版匹配来寻找对象'
        export_slice = True

    @override
    @classmethod
    def find(cls, **kwargs: Unpack[TemplateMatchFindKargs[GameObjectType]]) -> GameObjectType | None:
        from kotonebot import image
        predicate = kwargs.get('predicate')
        threshold_override = kwargs.get('threshold')
        threshold = cls.threshold if threshold_override is None else threshold_override
        colored_override = kwargs.get('colored')
        colored = cls.colored if colored_override is None else colored_override
        region = kwargs.get('region', cls.region)
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
        if predicate is not None and not predicate(obj):
            return None
        return obj

    @override
    @classmethod
    def find_all(cls, **kwargs: Unpack[TemplateMatchFindKargs[GameObjectType]]) -> list[GameObjectType]:
        from kotonebot import image
        predicate = kwargs.get('predicate')
        threshold_override = kwargs.get('threshold')
        threshold = cls.threshold if threshold_override is None else threshold_override
        colored_override = kwargs.get('colored')
        colored = cls.colored if colored_override is None else colored_override
        region = kwargs.get('region', cls.region)
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
            if predicate is None or predicate(obj):
                objects.append(obj)
        return objects

    @override
    @classmethod
    def require(cls, **kwargs: Unpack[TemplateMatchFindKargs[GameObjectType]]) -> GameObjectType:
        from kotonebot import image, device
        from kotonebot.backend.image import TemplateNoMatchError
        predicate = kwargs.get('predicate')
        threshold_override = kwargs.get('threshold')
        threshold = cls.threshold if threshold_override is None else threshold_override
        colored_override = kwargs.get('colored')
        colored = cls.colored if colored_override is None else colored_override
        region = kwargs.get('region', cls.region)
        if predicate is None:
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
                if predicate(obj):
                    obj.prefab = cls
                    return obj
            # 没有任何匹配满足 predicate，抛出未找到异常
            raise TemplateNoMatchError(device.screenshot(), cls.template.pixels)

    if TYPE_CHECKING:
        # 这个方法只需要重载声明，实际实现由基类提供不变
        @classmethod
        def exists(cls, **kwargs: Unpack[TemplateMatchFindKargs[GameObjectType]]) -> bool: ...
