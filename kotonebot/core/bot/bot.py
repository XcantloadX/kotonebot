import logging
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, TypeVar, ParamSpec, Generic, List, Protocol, runtime_checkable

from kotonebot.client import Device
from kotonebot.backend.context import init_context, vars, Task, Action


T = TypeVar("T", covariant=True)

@runtime_checkable
class Throwable(Protocol[T]):
    def __iter__(self) -> "Throwable[T]": ...
    def __next__(self) -> T: ...
    def throw(self, typ, val=None, tb=None) -> T: ...


class TaskStatus(str, Enum):
    PENDING = "pending"   # 等待中
    RUNNING = "running"   # 运行中
    SUCCESS = "success"   # 成功
    FAILED = "failed"     # 失败

class BotStopReason(str, Enum):
    USER_REQUEST = "user_request"  # 用户请求停止
    ERROR = "error"                 # 发生错误
    COMPLETED = "completed"         # 任务完成

@dataclass
class BotContext:
    bot: 'KotoneBot'
    device: Device
    
    # 运行时状态
    is_running: bool = True
    has_error: bool = False
    last_exception: Exception | None = None

    data: dict[str, Any] = field(default_factory=dict)

    def stop(self):
        self.is_running = False

@dataclass
class RunStatus:
    bot: 'KotoneBot'
    thread: threading.Thread
    running: bool = False
    tasks: list[TaskStatus] = field(default_factory=list)
    current_task: Task | None = None
    callstack: list[Task | Action] = field(default_factory=list)

    def interrupt(self):
        vars.flow.request_interrupt()

logger = logging.getLogger(__name__)
NextHandler = Callable[[], None]
TaskMiddleware = Callable[[BotContext, Task, NextHandler], None]
Params = ParamSpec('Params')
Return = TypeVar('Return')

class Event(Generic[Params, Return]):
    def __init__(self):
        self.__listeners = []
    
    def on(self, func: Callable[Params, Return]):
        self.add_listener(func)
        return func
    
    def add_listener(self, func: Callable[Params, Return]) -> None:
        if func not in self.__listeners:
            self.__listeners.append(func)
    
    def remove_listener(self, func: Callable[Params, Return]) -> None:
        if func in self.__listeners:
            self.__listeners.remove(func)
    
    def __iadd__(self, func: Callable[Params, Return]):
        self.add_listener(func)
        return self
        
    def __isub__(self, func: Callable[Params, Return]):
        self.remove_listener(func)
        return self
        
    def trigger(self, *args: Params.args, **kwargs: Params.kwargs) -> None:
        for func in list(self.__listeners):
            func(*args, **kwargs)

class BotEvents:
    def __init__(self):
        self.task_status_changed = Event[[Task, str], None]()
        self.started = Event[[], None]()
        self.stopped = Event[[BotStopReason, Exception | None], None]()

class KotoneBot:
    def __init__(
        self,
        device_factory: Callable[[], Device],
        middlewares: List[TaskMiddleware] | None = None,
    ):
        """
        :param device_factory: 一个函数，接收 config 字典，返回 Device 对象
        :param config: 配置字典
        :param middlewares: 中间件列表（按顺序执行）
        """
        self.device_factory = device_factory
        self.middlewares = middlewares or []
        self.events = BotEvents()
        self._ctx: BotContext | None = None

    def _initialize(self):
        """系统级初始化"""
        
        logger.info("Initializing Device...")
        device = self.device_factory()
        self._ctx = BotContext(bot=self, device=device)
        
        init_context(
            target_device=device
        )

    def run(self, tasks: Iterable[Task] | Throwable[Task]) -> None:
        self._initialize()
        assert self._ctx is not None, 'BotContext not initialized (this should not happen)'
        self._ctx.device.start()
        self.events.started.trigger()
        iterator = iter(tasks)
        pending_exc = None
        try:
            while True:
                try:
                    if pending_exc is not None:
                        if isinstance(iterator, Throwable):
                            task = iterator.throw(pending_exc)
                            pending_exc = None
                        else:
                            raise RuntimeError("Cannot throw exception into non-throwable iterator") from pending_exc
                    else:
                        task = next(iterator)
                except StopIteration:
                    break

                logger.info('=' * 20)
                logger.info(f'Task started: {task.name}')
                self.events.task_status_changed.trigger(task, 'running')

                if not self._ctx.is_running:
                    break

                vars.flow.check()

                def core_execution():
                    task.func()

                # 递归包装中间件
                # 顺序：Middleware[0] -> Middleware[1] -> ... -> Core -> ... -> Middleware[1] -> Middleware[0]
                handler = core_execution
                for md in reversed(self.middlewares):
                    def wrapper(h=handler, m=md):
                        m(self._ctx, task, h)
                    handler = wrapper # type: ignore
                
                # 执行
                try:
                    handler()
                except Exception as e:
                    pending_exc = e

                self.events.task_status_changed.trigger(task, 'finished')
            self.events.stopped.trigger(BotStopReason.COMPLETED, None)
        # 用户中止
        except KeyboardInterrupt:
            logger.exception('Keyboard interrupt detected.')
            vars.flow.clear_interrupt()
            self.events.stopped.trigger(BotStopReason.USER_REQUEST, None)
            return
        # 其他异常
        except Exception as e:
            logger.critical(f"Bot Main Loop Crashed: {e}", exc_info=True)
            self.events.stopped.trigger(BotStopReason.ERROR, e)
        finally:
            self._ctx.device.stop()

    def start(self, tasks: Iterable[Task]) -> RunStatus:
        t = threading.Thread(target=lambda: self.run(tasks))
        t.start()
        s = RunStatus(bot=self, thread=t, running=True)
        def _on_started():
            s.running = True
        def _on_stopped(reason: BotStopReason, exc: Exception | None):
            s.running = False
            self.events.started -= _on_started
            self.events.stopped -= _on_stopped
        self.events.started += _on_started
        self.events.stopped += _on_stopped
        return s
