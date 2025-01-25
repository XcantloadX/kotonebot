import uuid
import logging
import inspect
from logging import Logger
from types import CodeType
from typing import Any, Callable, Concatenate, TypeVar, ParamSpec, Literal, Protocol
from typing_extensions import Self
from dataclasses import dataclass

from .context import ContextColor
from .core import Image, Ocr

logger = logging.getLogger(__name__)
P = ParamSpec('P')
R = TypeVar('R')
ThenAction = Literal['click', 'log']
DoAction = Literal['click']


class DispatcherContext:
    def __init__(self):
        self.finished: bool = False
    
    def finish(self):
        self.finished = True

def dispatcher(func: Callable[Concatenate[DispatcherContext, P], R]) -> Callable[P, R]:
    """
    
    注意：\n
    此装饰器必须在应用 @action/@task 装饰器后再应用，且 `screenshot_mode='manual'` 参数必须设置。
    或者也可以使用 @action/@task 装饰器中的 `dispatcher=True` 参数，
    那么就没有上面两个要求了。
    """
    ctx = DispatcherContext()
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        while not ctx.finished:
            from kotonebot import device
            device.update_screenshot()
            ret = func(ctx, *args, **kwargs)
        return ret
    return wrapper
