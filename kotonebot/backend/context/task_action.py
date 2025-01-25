import logging
from typing import Callable, ParamSpec, TypeVar, overload, Concatenate, Literal
from dataclasses import dataclass

import cv2
from cv2.typing import MatLike

from .context import ContextStackVars, ScreenshotMode
from ..dispatch import dispatcher as dispatcher_decorator, DispatcherContext

P = ParamSpec('P')
R = TypeVar('R')
logger = logging.getLogger(__name__)

@dataclass
class Task:
    name: str
    description: str
    func: Callable
    priority: int
    """
    任务优先级，数字越大优先级越高。
    """

@dataclass
class Action:
    name: str
    description: str
    func: Callable
    priority: int
    """
    动作优先级，数字越大优先级越高。
    """


task_registry: dict[str, Task] = {}
action_registry: dict[str, Action] = {}
current_callstack: list[Task|Action] = []

def _placeholder():
    raise NotImplementedError('Placeholder function')

def task(
    name: str,
    description: str|None = None,
    *,
    pass_through: bool = False,
    priority: int = 0,
    screenshot_mode: ScreenshotMode = 'auto',
):
    """
    `task` 装饰器，用于标记一个函数为任务函数。

    :param name: 任务名称
    :param description: 任务描述。如果为 None，则使用函数的 docstring 作为描述。
    :param pass_through: 
        默认情况下， @task 装饰器会包裹任务函数，跟踪其执行情况。
        如果不想跟踪，则设置此参数为 False。
    :param priority: 任务优先级，数字越大优先级越高。
    """
    def _task_decorator(func: Callable[P, R]) -> Callable[P, R]:
        nonlocal description
        description = description or func.__doc__ or ''
        task = Task(name, description, _placeholder, priority)
        task_registry[name] = task
        logger.debug(f'Task "{name}" registered.')
        if pass_through:
            return func
        else:
            def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                current_callstack.append(task)
                vars = ContextStackVars.push(screenshot_mode=screenshot_mode)
                ret = func(*args, **kwargs)
                ContextStackVars.pop()
                current_callstack.pop()
                return ret
            task.func = _wrapper
            return _wrapper
    return _task_decorator

@overload
def action(func: Callable[P, R]) -> Callable[P, R]: ...

@overload
def action(
    name: str,
    *,
    description: str|None = None,
    pass_through: bool = False,
    priority: int = 0,
    screenshot_mode: ScreenshotMode | None = None,
    dispatcher: Literal[False] = False,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """
    `action` 装饰器，用于标记一个函数为动作函数。

    :param name: 动作名称。如果为 None，则使用函数的名称作为名称。
    :param description: 动作描述。如果为 None，则使用函数的 docstring 作为描述。
    :param pass_through: 
        默认情况下， @action 装饰器会包裹动作函数，跟踪其执行情况。
        如果不想跟踪，则设置此参数为 False。
    :param priority: 动作优先级，数字越大优先级越高。
    :param screenshot_mode: 截图模式。
    :param dispatcher: 
        是否为分发器模式。默认为假。
        如果使用分发器，则函数的第一个参数必须为 `ctx: DispatcherContext`。
    """
    ...

@overload
def action(
    name: str,
    *,
    description: str|None = None,
    pass_through: bool = False,
    priority: int = 0,
    screenshot_mode: ScreenshotMode | None = None,
    dispatcher: Literal[True] = True,
) -> Callable[[Callable[Concatenate[DispatcherContext, P], R]], Callable[P, R]]:
    """
    `action` 装饰器，用于标记一个函数为动作函数。

    此重载启用了分发器模式。被装饰函数的第一个参数必须为 `ctx: DispatcherContext`。

    :param name: 动作名称。如果为 None，则使用函数的名称作为名称。
    :param description: 动作描述。如果为 None，则使用函数的 docstring 作为描述。
    :param pass_through: 
        默认情况下， @action 装饰器会包裹动作函数，跟踪其执行情况。
        如果不想跟踪，则设置此参数为 False。
    :param priority: 动作优先级，数字越大优先级越高。
    :param screenshot_mode: 截图模式，必须为 `'manual' / None`。
    :param dispatcher: 
        是否为分发器模式。默认为假。
        如果使用分发器，则函数的第一个参数必须为 `ctx: DispatcherContext`。
    """
    ...

def action(*args, **kwargs):
    def _register(func: Callable, name: str, description: str|None = None, priority: int = 0) -> Action:
        description = description or func.__doc__ or ''
        action = Action(name, description, func, priority)
        action_registry[name] = action
        logger.debug(f'Action "{name}" registered.')
        return action


    if len(args) == 1 and isinstance(args[0], Callable):
        func = args[0]
        action = _register(_placeholder, func.__name__, func.__doc__)
        def _wrapper(*args: P.args, **kwargs: P.kwargs):
            current_callstack.append(action)
            vars = ContextStackVars.push()
            ret = func(*args, **kwargs)
            ContextStackVars.pop()
            current_callstack.pop()
            return ret
        action.func = _wrapper
        return _wrapper
    else:
        name = args[0]
        description = kwargs.get('description', None)
        pass_through = kwargs.get('pass_through', False)
        priority = kwargs.get('priority', 0)
        screenshot_mode = kwargs.get('screenshot_mode', None)
        dispatcher = kwargs.get('dispatcher', False)
        if dispatcher:
            if not (screenshot_mode is None or screenshot_mode == 'manual'):
                raise ValueError('`screenshot_mode` must be None or "manual" when `dispatcher=True`.')
            screenshot_mode = 'manual'
        def _action_decorator(func: Callable):
            nonlocal pass_through
            action = _register(_placeholder, name, description)
            pass_through = kwargs.get('pass_through', False)
            if pass_through:
                return func
            else:
                if dispatcher:
                    func = dispatcher_decorator(func) # type: ignore
                def _wrapper(*args: P.args, **kwargs: P.kwargs):
                    current_callstack.append(action)
                    vars = ContextStackVars.push(screenshot_mode=screenshot_mode)
                    ret = func(*args, **kwargs)
                    ContextStackVars.pop()
                    current_callstack.pop()
                    return ret
                action.func = _wrapper
                return _wrapper
        return _action_decorator

