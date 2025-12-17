from typing import Type, Sequence, cast, Any
from typing_extensions import Unpack, override
from kotonebot.core.entities.base import FindKwargs, GameObjectType
from .base import Prefab


class AnyOf(Prefab[Any]):
    """
    复合 Prefab，用于匹配给定的任意一个 Prefab。
    
    作为一个 Class，它可以通过两种方式使用：
    1. 继承定义：
       class MyButton(AnyOf):
           options = [ConfirmButton, CancelButton]
           
    2. 动态泛型（推荐）：
       MyButton = AnyOf[ConfirmButton, CancelButton]
    """
    options: Sequence[Type[Prefab]] = []

    def __class_getitem__(cls, items: Type[Prefab] | tuple[Type[Prefab], ...]):
        """
        允许使用 AnyOf[PrefabA, PrefabB] 的语法动态生成子类。
        """
        if not isinstance(items, tuple):
            items = (items,)
            
        # 动态创建一个新的类，名字由所有子 Prefab 的名字拼接而成
        name = f"AnyOf_{'_'.join(i.__name__ for i in items)}"
        return type(name, (cls,), {'options': items})

    @override
    @classmethod
    def find(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> GameObjectType | None:
        # Cast kwargs to Any to bypass contravariance checks on predicate
        unsafe_kwargs = cast(dict[str, Any], kwargs)
        
        for prefab in cls.options:
            obj = prefab.find(**unsafe_kwargs)
            if obj is not None:
                # 强制转换为 GameObjectType，假设用户定义的 options 均符合泛型约束
                return cast(GameObjectType, obj)
        return None

    @override
    @classmethod
    def find_all(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> list[GameObjectType]:
        unsafe_kwargs = cast(dict[str, Any], kwargs)
        results: list[GameObjectType] = []
        for prefab in cls.options:
            found = prefab.find_all(**unsafe_kwargs)
            # 列表协变问题，需要强制转换
            results.extend(cast(list[GameObjectType], found))
        return results

    @override
    @classmethod
    def exists(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> bool:
        unsafe_kwargs = cast(dict[str, Any], kwargs)
        for prefab in cls.options:
            if prefab.exists(**unsafe_kwargs):
                return True
        return False

    @override
    @classmethod
    def require(cls, **kwargs: Unpack[FindKwargs[GameObjectType]]) -> GameObjectType:
        unsafe_kwargs = cast(dict[str, Any], kwargs)
        for prefab in cls.options:
            obj = prefab.find(**unsafe_kwargs)
            if obj is not None:
                return cast(GameObjectType, obj)
        
        names = ", ".join([p.__name__ for p in cls.options])
        raise RuntimeError(f"AnyOf: Could not find any of the following prefabs: [{names}]")
