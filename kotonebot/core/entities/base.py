import time
from abc import ABC
from typing import Callable, Type, cast, get_args
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
    def find(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> GameObjectType | None: ...
    @classmethod
    def find_all(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> list[GameObjectType]: ...
    @classmethod
    def require(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> GameObjectType: ...
    @classmethod
    def exists(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> bool: ...

    @classmethod
    def click(cls, **kwargs: Unpack[ClickKwargs]) -> None:
        return cls.require().click()
    
    @classmethod
    def try_click(cls, **kwargs: Unpack[ClickKwargs]) -> bool:
        obj = cls.find()
        if obj is not None:
            obj.click()
            return True
        return False
    
    @classmethod
    def wait(cls, *, timeout: float | None = None, interval: float | None = None, throw: bool = True):
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
        return cls.wait(timeout=timeout, interval=interval, throw=False)

class GameObject:
    """## GameObject
    GameObject（游戏对象），游戏物体/UI 的基类，所有通过一系列方式从屏幕画面上寻找到的结果都应以 GameObject 的形式展示。
    
    GameObject 本身仅包含基础属性。如果你需要自定义 GameObject 的属性或行为，可以继承 GameObject 并使用你自己的类。
    """
    rect: Rect
    display_name: str | None = None

    def click(self) -> None:
        from kotonebot import device
        device.click(self.rect.center)

    def double_click(self) -> None:
        from kotonebot import device
        device.double_click(*self.rect.center)

class TemplateMatchPrefab(Prefab[GameObjectType]):
    """基于模版匹配的 Prefab"""
    template: Image
    region: Rect | None = None
    threshold: float = 0.7
    colored: bool = False

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
                    return obj
            # 没有任何匹配满足 predicate，抛出未找到异常
            raise TemplateNoMatchError(device.screenshot(), cls.template.pixels)
    
    @override
    @classmethod
    def exists(cls, **kwargs: Unpack[PrefabKwargs[GameObjectType]]) -> bool:
        return cls.find(**kwargs) is not None
        

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
                        return obj
            raise TextNotFoundError(cls.pattern, device.screenshot())

    @override
    @classmethod
    def exists(cls, **kwargs: Unpack[PrefabKwargs]) -> bool:
        return cls.find(**kwargs) is not None