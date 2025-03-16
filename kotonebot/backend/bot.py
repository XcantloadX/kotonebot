import logging
import pkgutil
import importlib
from typing_extensions import Self
from dataclasses import dataclass, field
import threading
import traceback
import os
import zipfile
import cv2
from datetime import datetime
import io
from typing import Any, Literal, Callable, Generic, TypeVar, ParamSpec

from kotonebot.backend.context import Task, Action
from kotonebot.backend.context import init_context, vars
from kotonebot.backend.context import task_registry, action_registry, current_callstack, Task, Action
from kotonebot.client.host.protocol import Instance
from kotonebot.ui import user

log_stream = io.StringIO()
stream_handler = logging.StreamHandler(log_stream)
stream_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d] - %(message)s'))
logging.getLogger('kotonebot').addHandler(stream_handler)
logger = logging.getLogger(__name__)

@dataclass
class TaskStatus:
    task: Task
    status: Literal['pending', 'running', 'finished', 'error', 'cancelled']

@dataclass
class RunStatus:
    running: bool = False
    tasks: list[TaskStatus] = field(default_factory=list)
    current_task: Task | None = None
    callstack: list[Task | Action] = field(default_factory=list)

    def interrupt(self):
        vars.interrupted.set()

def _save_error_report(
    exception: Exception,
    *,
    path: str | None = None
) -> str:
    """
    保存错误报告

    :param path: 保存的路径。若为 `None`，则保存到 `./reports/{YY-MM-DD HH-MM-SS}.zip`。
    :return: 保存的路径
    """
    from kotonebot import device
    try:
        if path is None:
            path = f'./reports/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.zip'
        exception_msg = '\n'.join(traceback.format_exception(exception))
        task_callstack = '\n'.join([f'{i+1}. name={task.name} priority={task.priority}' for i, task in enumerate(current_callstack)])
        screenshot = device.screenshot()
        logs = log_stream.getvalue()
        with open('config.json', 'r', encoding='utf-8') as f:
            config_content = f.read()

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with zipfile.ZipFile(path, 'w') as zipf:
            zipf.writestr('exception.txt', exception_msg)
            zipf.writestr('task_callstack.txt', task_callstack)
            zipf.writestr('screenshot.png', cv2.imencode('.png', screenshot)[1].tobytes())
            zipf.writestr('config.json', config_content)
            zipf.writestr('logs.txt', logs)
        return path
    except Exception as e:
        logger.exception(f'Failed to save error report:')
        return ''

# Modified from https://stackoverflow.com/questions/70982565/how-do-i-make-an-event-listener-with-decorators-in-python
Params = ParamSpec('Params')
Return = TypeVar('Return')
class Event(Generic[Params, Return]):
    def __init__(self):
        self.__listeners = []
    
    @property
    def on(self):
        def wrapper(func: Callable[Params, Return]):
            self.add_listener(func)
            return func
        return wrapper
    
    def add_listener(self, func: Callable[Params, Return]) -> None:
        if func in self.__listeners:
            return
        self.__listeners.append(func)
    
    def remove_listener(self, func: Callable[Params, Return]) -> None:
        if func not in self.__listeners:
            return
        self.__listeners.remove(func)
    
    def __iadd__(self, func: Callable[Params, Return]) -> Self:
        self.add_listener(func)
        return self

    def __isub__(self, func: Callable[Params, Return]) -> Self:
        self.remove_listener(func)
        return self

    def trigger(self, *args: Params.args, **kwargs: Params.kwargs) -> None:
        for func in self.__listeners:
            func(*args, **kwargs)

class KotoneBotEvents:
    def __init__(self):
        self.task_status_changed = Event[
            [Task, Literal['pending', 'running', 'finished', 'error', 'cancelled']], None
        ]()
        self.task_error = Event[
            [Task, Exception], None
        ]()
        self.finished = Event[[], None]()


class KotoneBot:
    def __init__(
        self,
        module: str,
        config_type: type = dict[str, Any],
        *,
        debug: bool = False,
        resume_on_error: bool = False,
        auto_save_error_report: bool = True,
    ):
        """
        初始化 KotoneBot。

        :param module: 主模块名。此模块及其所有子模块都会被载入。
        :param config_type: 配置类型。
        :param debug: 调试模式。
        :param resume_on_error: 在错误时是否恢复。
        :param auto_save_error_report: 是否自动保存错误报告。
        """
        self.module = module
        self.config_type = config_type
        # HACK: 硬编码
        self.current_config: int | str = 0
        self.debug = debug
        self.resume_on_error = resume_on_error
        self.auto_save_error_report = auto_save_error_report
        self.events = KotoneBotEvents()
        self.backend_instance: Instance | None = None

    def initialize(self):
        """
        初始化并载入所有任务和动作。
        """
        logger.info('Initializing tasks and actions...')
        logger.debug(f'Loading module: {self.module}')
        # 加载主模块
        importlib.import_module(self.module)

        # 加载所有子模块
        pkg = importlib.import_module(self.module)
        for loader, name, is_pkg in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):
            logger.debug(f'Loading sub-module: {name}')
            try:
                importlib.import_module(name)
            except Exception as e:
                logger.error(f'Failed to load sub-module: {name}')
                logger.exception(f'Error: ')
        
        logger.info('Tasks and actions initialized.')
        logger.info(f'{len(task_registry)} task(s) and {len(action_registry)} action(s) loaded.')

    def check_backend(self):
        from kotonebot.client.host import create_custom
        from kotonebot.config.manager import load_config
        # HACK: 硬编码
        config = load_config('config.json', type=self.config_type)
        config = config.user_configs[0]
        logger.info('Checking backend...')
        if config.backend.type == 'custom' and config.backend.check_emulator:
            exe = config.backend.emulator_path
            if exe is None:
                user.error('「检查并启动模拟器」已开启但未配置「模拟器 exe 文件路径」。')
                raise ValueError('Emulator executable path is not set.')
            if not os.path.exists(exe):
                user.error('「模拟器 exe 文件路径」对应的文件不存在！请检查路径是否正确。')
                raise FileNotFoundError(f'Emulator executable not found: {exe}')
            self.backend_instance = create_custom(
                adb_ip=config.backend.adb_ip,
                adb_port=config.backend.adb_port,
                adb_emulator_name=config.backend.adb_emulator_name,
                exe_path=exe
            )
            if not self.backend_instance.running():
                logger.info('Starting custom backend...')
                self.backend_instance.start()
                logger.info('Waiting for custom backend to be available...')
                self.backend_instance.wait_available()
            else:
                logger.info('Custom backend "%s" already running.', self.backend_instance)

    def run(self, tasks: list[Task], *, by_priority: bool = True):
        """
        按优先级顺序运行所有任务。
        """
        self.check_backend()
        init_context(config_type=self.config_type)

        if by_priority:
            tasks = sorted(tasks, key=lambda x: x.priority, reverse=True)
        for task in tasks:
            self.events.task_status_changed.trigger(task, 'pending')

        for task in tasks:
            logger.info(f'Task started: {task.name}')
            self.events.task_status_changed.trigger(task, 'running')

            if self.debug:
                task.func()
            else:
                try:
                    task.func()
                    self.events.task_status_changed.trigger(task, 'finished')
                # 用户中止
                except KeyboardInterrupt as e:
                    logger.exception('Keyboard interrupt detected.')
                    for task1 in tasks[tasks.index(task):]:
                        self.events.task_status_changed.trigger(task1, 'cancelled')
                    vars.interrupted.clear()
                    break
                # 其他错误
                except Exception as e:
                    logger.error(f'Task failed: {task.name}')
                    logger.exception(f'Error: ')
                    report_path = None
                    if self.auto_save_error_report:
                        report_path = _save_error_report(e)
                    self.events.task_status_changed.trigger(task, 'error')
                    if not self.resume_on_error:
                        for task1 in tasks[tasks.index(task)+1:]:
                            self.events.task_status_changed.trigger(task1, 'cancelled')
                        break
            logger.info(f'Task finished: {task.name}')
        logger.info('All tasks finished.')
        self.events.finished.trigger()

    def run_all(self) -> None:
        return self.run(list(task_registry.values()), by_priority=True)

    def start_all(self) -> RunStatus:
        run_status = RunStatus(running=True)
        def _on_finished():
            run_status.running = False
            run_status.current_task = None
            run_status.callstack = []
            self.events.finished -= _on_finished
            self.events.task_status_changed -= _on_task_status_changed
        
        def _on_task_status_changed(task: Task, status: Literal['pending', 'running', 'finished', 'error', 'cancelled']):
            def _find(task: Task) -> TaskStatus:
                for task_status in run_status.tasks:
                    if task_status.task == task:
                        return task_status
                raise ValueError(f'Task {task.name} not found in run_status.tasks')
            if status == 'pending':
                run_status.tasks.append(TaskStatus(task=task, status='pending'))
            else:
                _find(task).status = status

        self.events.task_status_changed += _on_task_status_changed
        self.events.finished += _on_finished
        thread = threading.Thread(target=self.run_all)
        thread.start()
        return run_status
        