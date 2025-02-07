import uuid
import logging
import inspect
from logging import Logger
from types import CodeType
from typing import Annotated, Any, Callable, Concatenate, TypeVar, ParamSpec, Literal, Protocol, cast
from typing_extensions import Self
from dataclasses import dataclass

from .context import ContextColor
from .core import Image, Ocr

logger = logging.getLogger(__name__)
P = ParamSpec('P')
R = TypeVar('R')
ThenAction = Literal['click', 'log']
DoAction = Literal['click']
# TODO: 需要找个地方统一管理这些属性名
ATTR_DISPATCHER_MARK = '__kb_dispatcher_mark'
ATTR_ORIGINAL_FUNC = '_kb_inner'


class DispatchFunc: pass

wrapper_to_func: dict[Callable, Callable] = {}

class DispatcherContext:
    def __init__(self):
        self.finished: bool = False
        self._first_run: bool = True
    
    def finish(self):
        """标记已完成 dispatcher 循环。循环将在下次条件检测时退出。"""
        self.finished = True

    def expand(self, func: Annotated[Callable[[], Any], DispatchFunc], ignore_finish: bool = True):
        """
        调用其他 dispatcher 函数。

        使用 `expand` 和直接调用的区别是：
        * 直接调用会执行 while 循环，直到满足结束条件
        * 而使用 `expand` 则只会执行一次。效果类似于将目标函数里的代码直接复制粘贴过来。
        """
        # 获取原始函数
        original_func = func
        while not getattr(original_func, ATTR_DISPATCHER_MARK, False):
            original_func = getattr(original_func, ATTR_ORIGINAL_FUNC)
        original_func = getattr(original_func, ATTR_ORIGINAL_FUNC)

        if not original_func:
            raise ValueError(f'{repr(func)} is not a dispatcher function.')
        elif not callable(original_func):
            raise ValueError(f'{repr(original_func)} is not callable.')
        original_func = cast(Callable[[DispatcherContext], Any], original_func)

        old_finished = self.finished
        ret = original_func(self)
        if ignore_finish:
            self.finished = old_finished
        return ret

    @property
    def beginning(self) -> bool:
        """是否为第一次运行"""
        return self._first_run
    
    @property
    def finishing(self) -> bool:
        """是否即将结束运行"""
        return self.finished

def dispatcher(
        func: Callable[Concatenate[DispatcherContext, P], R],
        *,
        fragment: bool = False
    ) -> Annotated[Callable[P, R], DispatchFunc]:
    """
    注意：\n
    此装饰器必须在应用 @action/@task 装饰器后再应用，且 `screenshot_mode='manual'` 参数必须设置。
    或者也可以使用 @action/@task 装饰器中的 `dispatcher=True` 参数，
    那么就没有上面两个要求了。

    :param fragment:
        片段模式，默认不启用。
        启用后，被装饰函数将会只执行依次，
        而不会一直循环到 ctx.finish() 被调用。
    """
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        ctx = DispatcherContext()
        while not ctx.finished:
            from kotonebot import device
            device.update_screenshot()
            ret = func(ctx, *args, **kwargs)
            ctx._first_run = False
        return ret
    def fragment_wrapper(*args: P.args, **kwargs: P.kwargs):
        ctx = DispatcherContext()
        from kotonebot import device
        device.update_screenshot()
        return func(ctx, *args, **kwargs)
    setattr(wrapper, ATTR_ORIGINAL_FUNC, func)
    setattr(fragment_wrapper, ATTR_ORIGINAL_FUNC, func)
    setattr(wrapper, ATTR_DISPATCHER_MARK, True)
    setattr(fragment_wrapper, ATTR_DISPATCHER_MARK, True)
    wrapper_to_func[wrapper] = func
    if fragment:
        return fragment_wrapper

    else:
        return wrapper

if __name__ == '__main__':
    from .context.task_action import action
    from .context import init_context
    init_context()
    @action('inner', dispatcher=True)
    def inner(ctx: DispatcherContext):
        print('inner')
        ctx.finish()

    @action('test', dispatcher=True)
    def test(ctx: DispatcherContext):
        print('test')
        inner()
        ctx.finish()
    test()
