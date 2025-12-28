from typing import TYPE_CHECKING, Generic
from typing_extensions import Unpack, override

from kotonebot.devtools.project.schema import BoolProp, FloatProp, ImageProp, RectProp
from kotonebot.primitives import Rect, ImageSlice
from kotonebot.devtools import EditorMetadata

from .base import Prefab, FindKwargs, GameObjectType, ClickKwargs as _ClickKwargs, WaitKwargs as _WaitKwargs


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

class ClickKwargs(TemplateMatchFindKargs[GameObjectType], _ClickKwargs[GameObjectType], Generic[GameObjectType], total=False): pass
class WaitKwargs(TemplateMatchFindKargs[GameObjectType], _WaitKwargs[GameObjectType], Generic[GameObjectType], total=False): pass


class TemplateMatchPrefab(Prefab[GameObjectType]):
    """基于模版匹配的 Prefab"""
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
        # If prefab is fixed and no explicit region provided, use template.slice_rect
        if region is None and cls.fixed:
            slice_rect = cls.template.slice_rect
            if slice_rect is None:
                raise ValueError(f"Prefab {cls.__name__} is marked fixed but template has no slice_rect")
            region = slice_rect
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
        if region is None and cls.fixed:
            slice_rect = cls.template.slice_rect
            if slice_rect is None:
                raise ValueError(f"Prefab {cls.__name__} is marked fixed but template has no slice_rect")
            region = slice_rect
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
        if region is None and cls.fixed:
            slice_rect = cls.template.slice_rect
            if slice_rect is None:
                raise ValueError(f"Prefab {cls.__name__} is marked fixed but template has no slice_rect")
            region = slice_rect
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
        # 这些方法只需要重载声明，实际实现由基类提供不变
        @classmethod
        def exists(cls, **kwargs: Unpack[TemplateMatchFindKargs[GameObjectType]]) -> bool: ...
        
        @classmethod
        def click(cls, **kwargs: Unpack[ClickKwargs[GameObjectType]]) -> None: ...

        @classmethod
        def wait(cls, **kwargs: Unpack[WaitKwargs[GameObjectType]]) -> GameObjectType: ...
        
        @classmethod
        def try_click(cls, **kwargs: Unpack[ClickKwargs[GameObjectType]]) -> bool: ...
        
        @classmethod
        def try_wait(cls, **kwargs: Unpack[WaitKwargs[GameObjectType]]) -> GameObjectType | None: ...