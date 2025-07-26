import logging
from typing import Callable, ParamSpec, TypeVar, overload, Literal
from dataclasses import dataclass


from .context import ContextStackVars, ScreenshotMode
from ...errors import TaskNotFoundError

P = ParamSpec('P')
R = TypeVar('R')
logger = logging.getLogger(__name__)

TaskRunAtType = Literal['pre', 'post', 'manual', 'regular'] | str


@dataclass
class Task:
    name: str
    id: str
    description: str
    func: Callable
    priority: int
    """
    任务优先级，数字越大优先级越高。
    """
    run_at: TaskRunAtType = 'regular'


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
    task_id: str|None = None,
    description: str|None = None,
    *,
    pass_through: bool = False,
    priority: int = 0,
    screenshot_mode: ScreenshotMode = 'auto',
    run_at: TaskRunAtType = 'regular'
):
    """
    `task` 装饰器，用于标记一个函数为任务函数。

    :param name: 任务名称
    :param task_id: 任务 ID。如果为 None，则使用函数名称作为 ID。
    :param description: 任务描述。如果为 None，则使用函数的 docstring 作为描述。
    :param pass_through: 
        默认情况下， @task 装饰器会包裹任务函数，跟踪其执行情况。
        如果不想跟踪，则设置此参数为 False。
    :param priority: 任务优先级，数字越大优先级越高。
    :param run_at: 任务运行时间。
    """
    # 设置 ID
    # 获取 caller 信息
    def _task_decorator(func: Callable[P, R]) -> Callable[P, R]:
        nonlocal description, task_id
        description = description or func.__doc__ or ''
        # TODO: task_id 冲突检测
        task_id = task_id or func.__name__
        task = Task(name, task_id, description, _placeholder, priority, run_at)
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
    """
    ...

# TODO: 需要找个地方统一管理这些属性名
ATTR_ORIGINAL_FUNC = '_kb_inner'
ATTR_ACTION_MARK = '__kb_action_mark'
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
        setattr(_wrapper, ATTR_ORIGINAL_FUNC, func)
        setattr(_wrapper, ATTR_ACTION_MARK, True)
        action.func = _wrapper
        return _wrapper
    else:
        name = args[0]
        description = kwargs.get('description', None)
        pass_through = kwargs.get('pass_through', False)
        priority = kwargs.get('priority', 0)
        screenshot_mode = kwargs.get('screenshot_mode', None)
        def _action_decorator(func: Callable):
            nonlocal pass_through
            action = _register(_placeholder, name, description)
            pass_through = kwargs.get('pass_through', False)
            if pass_through:
                return func
            else:
                def _wrapper(*args: P.args, **kwargs: P.kwargs):
                    current_callstack.append(action)
                    vars = ContextStackVars.push(screenshot_mode=screenshot_mode)
                    ret = func(*args, **kwargs)
                    ContextStackVars.pop()
                    current_callstack.pop()
                    return ret
                setattr(_wrapper, ATTR_ORIGINAL_FUNC, func)
                setattr(_wrapper, ATTR_ACTION_MARK, True)
                action.func = _wrapper
                return _wrapper
        return _action_decorator

def tasks_from_id(task_ids: list[str]) -> list[Task]:
    result = []
    for tid in task_ids:
        target = next(task for task in task_registry.values() if task.id == tid)
        if target is None:
            raise TaskNotFoundError(f'Task "{tid}" not found.')
        result.append(target)
    return result