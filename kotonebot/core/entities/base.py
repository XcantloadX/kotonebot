import time
from abc import ABC
from typing import Any, Callable, Type, cast, get_args
from typing_extensions import Generic, TypeVar, override, Unpack, TypedDict

from kotonebot.primitives import Rect, Image
from kotonebot.devtools import EditorMetadata

GameObjectType = TypeVar('GameObjectType', bound='GameObject', default='GameObject')

class PrefabKwargs(TypedDict, Generic[GameObjectType], total=False):
    predicate: 'Callable[[GameObjectType], bool] | None'


class ClickKwargs(TypedDict, total=False):
    pass


class Prefab(Generic[GameObjectType], ABC):
    __object_class__: Type[GameObjectType] | None = None
    display_name: str | None = None
    """展示名称
    
    可选，用于在编辑器或日志中显示更友好的名称。
    如果未设置，则使用类名。
    """

    @classmethod
    def _get_object_class(cls) -> Type[GameObjectType]:
        """
        核心魔法：获取用于实例化的类。
        优先使用显式定义的 object_class，
        如果没有，则尝试从泛型定义中推断。
        """
        # 1. 如果用户手动定义了，直接用
        if cls.__object_class__ is not None:
            return cls.__object_class__

        # 2. 尝试从 __orig_bases__ 推断
        # 遍历基类，寻找 Prefab[T] 的定义
        for base in getattr(cls, "__orig_bases__", []):
            origin = getattr(base, "__origin__", None)
            # 检查这个基类是不是 Prefab (或者其子类)
            if origin is not None and issubclass(origin, Prefab):
                args = get_args(base)
                if args and isinstance(args[0], type) and issubclass(args[0], GameObject):
                    # 缓存结果，下次不用再推断
                    cls.__object_class__ = args[0]
                    return cls.__object_class__
        # 3. 如果都失败了，回退到默认的 GameObject
        # (这通常发生在用户没有指定泛型参数时，如 class MyPrefab(TemplateMatchPrefab): ...)
        return cast(Type[GameObjectType], GameObject)

    @classmethod
    def find(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> GameObjectType | None:
        """在屏幕画面中寻找当前 Prefab，并返回对应的第一个 GameObject 实例。

        :return: 寻找结果。如果没有找到，返回 None。
        """
        raise NotImplementedError
    
    @classmethod
    def find_all(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> list[GameObjectType]:
        """在屏幕画面中寻找当前 Prefab，并返回对应的所有 GameObject 实例。

        :return: 寻找结果列表。如果没有找到，返回空列表。
        """
        raise NotImplementedError
    
    @classmethod
    def require(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> GameObjectType:
        """在屏幕画面中寻找当前 Prefab，并返回对应的第一个 GameObject 实例。
        
        此方法与 find 类似，但如果没有找到任何结果，则会抛出异常。

        :raises: 如果没有找到，抛出异常。
        :return: 寻找结果。
        """
        raise NotImplementedError
    
    @classmethod
    def exists(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> bool:
        """判断当前 Prefab 是否存在于屏幕画面中。
        
        此方法为 find 的简化版，仅返回是否存在。
        相当于 ``Prefab.find(...) is not None``。
        
        :return: 如果存在，返回 True；否则返回 False。
        """
        return cls.find(**kwargs) is not None

    @classmethod
    def click(cls, **kwargs: Unpack[ClickKwargs]) -> None:
        """在屏幕画面中寻找当前 Prefab，并点击第一个找到的 GameObject 实例。
        
        该方法会调用 require 方法，因此如果没有找到任何结果，则会抛出异常。
        """
        return cls.require().click()
    
    @classmethod
    def try_click(cls, **kwargs: Unpack[ClickKwargs]) -> bool:
        """尝试点击当前 Prefab 的第一个找到的 GameObject 实例。
        
        :return: 如果找到了对象并成功点击，返回 True；否则返回 False。
        """
        obj = cls.find()
        if obj is not None:
            obj.click()
            return True
        return False
    
    @classmethod
    def wait(cls, *, timeout: float | None = None, interval: float | None = None, throw: bool = True):
        """等待当前 Prefab 出现。
        
        若指定时间内未找到，则根据 throw 参数决定是抛出异常还是返回 None。
        """
        start_time = time.time()
        while True:
            obj = cls.find()
            if obj is not None:
                return obj
            from kotonebot import sleep
            sleep(interval or 1.0)
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    if throw:
                        raise TimeoutError(f"Timeout when waiting for {cls.__name__}（{timeout} s）")
                    
                    
    @classmethod
    def try_wait(cls, *, timeout: float | None = None, interval: float | None = None):
        """尝试等待当前 Prefab 出现。
        
        若指定时间内未找到，则返回 None。
        """
        return cls.wait(timeout=timeout, interval=interval, throw=False)

class GameObject:
    """## GameObject
    GameObject（游戏对象），游戏物体/UI 的基类，所有通过一系列方式从屏幕画面上寻找到的结果都应以 GameObject 的形式展示。
    
    GameObject 本身仅包含基础属性。如果你需要自定义 GameObject 的属性或行为，可以继承 GameObject 并使用你自己的类。
    """
    rect: Rect
    """对象在屏幕上的范围"""
    display_name: str | None = None
    """展示名称
    
    可选，用于在编辑器或日志中显示更友好的名称。
    如果未设置，则使用类名。
    """
    prefab: type[Prefab[Any]]
    """当前对象对应的 Prefab 类"""

    def click(self) -> None:
        """点击当前对象的中心位置。"""
        from kotonebot import device
        device.click(self.rect.center)

    def double_click(self) -> None:
        """双击当前对象的中心位置。"""
        from kotonebot import device
        device.double_click(*self.rect.center)

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
    def find(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> GameObjectType | None:
        from kotonebot import image
        predicate = kwargs.get('predicate')
        result = image.find(
            cls.template.pixels,
            rect=cls.region,
            threshold=cls.threshold,
            colored=cls.colored,
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
    def find_all(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> list[GameObjectType]:
        from kotonebot import image
        predicate = kwargs.get('predicate')
        results = image.find_all(
            cls.template.pixels,
            rect=cls.region,
            threshold=cls.threshold,
            colored=cls.colored,
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
    def require(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> GameObjectType:
        from kotonebot import image, device
        from kotonebot.backend.image import TemplateNoMatchError
        predicate = kwargs.get('predicate')
        if predicate is None:
            # 直接使用 expect，未找到会抛出 TemplateNoMatchError
            result = image.expect(
                cls.template.pixels,
                rect=cls.region,
                threshold=cls.threshold,
                colored=cls.colored,
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
                rect=cls.region,
                threshold=cls.threshold,
                colored=cls.colored,
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
    def find(cls, **kwargs: Unpack[PrefabKwargs]) -> GameObjectType | None:
        from kotonebot import ocr
        predicate = kwargs.get('predicate')
        result = ocr.find(cls.pattern, rect=cls.region)
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
    def find_all(cls, **kwargs: Unpack[PrefabKwargs]) -> list[GameObjectType]:
        from kotonebot import ocr
        predicate = kwargs.get('predicate')
        # 获取所有 OCR 结果后按文本过滤
        results = ocr.ocr(rect=cls.region)
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
    def require(cls, **kwargs: Unpack[PrefabKwargs]) -> GameObjectType:
        from kotonebot import ocr, device
        from kotonebot.backend.ocr import TextNotFoundError
        predicate = kwargs.get('predicate')
        if predicate is None:
            result = ocr.expect(cls.pattern, rect=cls.region)
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
