import time
from abc import ABC
from typing import Any, Callable, Type, cast, get_args
from typing_extensions import Generic, TypeVar, Unpack, TypedDict

from kotonebot.primitives import Rect

GameObjectType = TypeVar('GameObjectType', bound='GameObject', default='GameObject')

class FindKwargs(TypedDict, Generic[GameObjectType], total=False):
    predicate: 'Callable[[GameObjectType], bool] | None'


class ClickKwargs(FindKwargs[GameObjectType], Generic[GameObjectType], total=False):
    pass

class WaitKwargs(FindKwargs[GameObjectType], Generic[GameObjectType], total=False):
    timeout: float | None
    interval: float | None


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
    def find(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> GameObjectType | None:
        """在屏幕画面中寻找当前 Prefab，并返回对应的第一个 GameObject 实例。

        :return: 寻找结果。如果没有找到，返回 None。
        """
        raise NotImplementedError
    
    @classmethod
    def find_all(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> list[GameObjectType]:
        """在屏幕画面中寻找当前 Prefab，并返回对应的所有 GameObject 实例。

        :return: 寻找结果列表。如果没有找到，返回空列表。
        """
        raise NotImplementedError
    
    @classmethod
    def require(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> GameObjectType:
        """在屏幕画面中寻找当前 Prefab，并返回对应的第一个 GameObject 实例。
        
        此方法与 find 类似，但如果没有找到任何结果，则会抛出异常。

        :raises: 如果没有找到，抛出异常。
        :return: 寻找结果。
        """
        raise NotImplementedError
    
    @classmethod
    def exists(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> bool:
        """判断当前 Prefab 是否存在于屏幕画面中。
        
        此方法为 find 的简化版，仅返回是否存在。
        相当于 ``Prefab.find(...) is not None``。
        
        :return: 如果存在，返回 True；否则返回 False。
        """
        return cls.find(**kwargs) is not None

    @classmethod
    def click(cls, **kwargs: Unpack[ClickKwargs[GameObjectType]]) -> None:
        """在屏幕画面中寻找当前 Prefab，并点击第一个找到的 GameObject 实例。
        
        该方法会调用 require 方法，因此如果没有找到任何结果，则会抛出异常。
        """
        return cls.require(**kwargs).click()
    
    @classmethod
    def try_click(cls, **kwargs: Unpack[ClickKwargs[GameObjectType]]) -> bool:
        """尝试点击当前 Prefab 的第一个找到的 GameObject 实例。
        
        :return: 如果找到了对象并成功点击，返回 True；否则返回 False。
        """
        obj = cls.find(**kwargs)
        if obj is not None:
            obj.click()
            return True
        return False
    
    @classmethod
    def wait(
        cls,
        **kwargs: Unpack[WaitKwargs[GameObjectType]],
    ) -> GameObjectType:
        """等待当前 Prefab 出现。
        
        若指定时间内未找到，则抛出超时异常（wait 不再返回 None）。
        """
        # 从 kwargs 中分离出用于等待控制的参数，剩下的传递给 `find`
        timeout = kwargs.pop("timeout", None)
        interval = kwargs.pop("interval", None)
        start_time = time.time()
        while True:
            obj = cls.find(**kwargs)
            if obj is not None:
                return obj
            from kotonebot import sleep
            sleep(interval or 1.0)
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    raise TimeoutError(f"Timeout when waiting for {cls.__name__}（{timeout} s）")

    @classmethod
    def try_wait(
        cls,
        **kwargs: Unpack[WaitKwargs[GameObjectType]],
    ) -> GameObjectType | None:
        """尝试等待当前 Prefab 出现。

        若指定时间内未找到，则返回 None。
        """
        try:
            return cls.wait(**kwargs)
        except TimeoutError:
            return None

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

