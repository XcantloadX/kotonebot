"""后台扫描任务管理器。

封装扫描任务的创建、进度更新、取消和自动清理，与 ConversionService 的业务逻辑解耦。
"""

import threading
import time
import uuid
from dataclasses import dataclass

from kotonebot.devtools.conversion.types import (
    ConversionMatch,
    ScanProgress,
    ScanTaskState,
)

_REAPER_INTERVAL = 60.0
"""清理线程间隔（秒）。"""
_TASK_TTL = 300.0
"""任务保留时间（秒），超过此时间的终态任务将被清理。"""


@dataclass
class _TaskEntry:
    """内部任务条目，分离 API 模型与内部状态。"""

    progress: ScanProgress
    """对外暴露的进度模型。"""
    cancel_event: threading.Event
    """取消事件，供后台线程检查。"""
    completed_at: float | None = None
    """任务进入终态的时间戳，用于清理判断。"""


class ScanTaskManager:
    """后台扫描任务管理器。"""

    def __init__(self):
        self._tasks: dict[str, _TaskEntry] = {}
        self._lock: threading.Lock = threading.Lock()
        self._reaper_started = False
        self._reaper_lock: threading.Lock = threading.Lock()

    def create_task(self) -> str:
        """创建新任务，返回 task_id。"""
        task_id = str(uuid.uuid4())
        with self._lock:
            self._tasks[task_id] = _TaskEntry(
                progress=ScanProgress(taskId=task_id, state=ScanTaskState.PENDING),
                cancel_event=threading.Event(),
            )
        self._ensure_reaper()
        return task_id

    def update_progress(
        self,
        task_id: str,
        state: ScanTaskState | None = None,
        total: int | None = None,
        current: int | None = None,
        current_file: str | None = None,
        matches: list[ConversionMatch] | None = None,
        error: str | None = None,
    ):
        """线程安全地更新任务进度。"""
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is None:
                return
            p = entry.progress
            if state is not None:
                p.state = state
                if state in (
                    ScanTaskState.COMPLETED,
                    ScanTaskState.ERROR,
                    ScanTaskState.CANCELLED,
                ):
                    entry.completed_at = time.time()
            if total is not None:
                p.total = total
            if current is not None:
                p.current = current
            if current_file is not None:
                p.currentFile = current_file
            if matches is not None:
                p.matches = matches
            if error is not None:
                p.error = error

    def get_progress(self, task_id: str) -> ScanProgress | None:
        """获取任务进度的深拷贝。"""
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is None:
                return None
            return entry.progress.model_copy(deep=True)

    def get_cancel_event(self, task_id: str) -> threading.Event | None:
        """获取任务的取消事件。"""
        with self._lock:
            entry = self._tasks.get(task_id)
            return entry.cancel_event if entry else None

    def cancel_task(self, task_id: str) -> bool:
        """取消指定任务。返回是否成功取消。"""
        with self._lock:
            entry = self._tasks.get(task_id)
            if entry is None:
                return False
            if entry.progress.state in (
                ScanTaskState.COMPLETED,
                ScanTaskState.ERROR,
                ScanTaskState.CANCELLED,
            ):
                return False
            entry.cancel_event.set()
            entry.progress.state = ScanTaskState.CANCELLED
            entry.completed_at = time.time()
            return True

    def _ensure_reaper(self):
        """确保后台清理线程已启动（仅启动一次）。"""
        with self._reaper_lock:
            if self._reaper_started:
                return
            self._reaper_started = True

        def _reaper_loop():
            while True:
                time.sleep(_REAPER_INTERVAL)
                now = time.time()
                with self._lock:
                    stale = [
                        tid
                        for tid, entry in self._tasks.items()
                        if entry.progress.state
                        in (
                            ScanTaskState.COMPLETED,
                            ScanTaskState.ERROR,
                            ScanTaskState.CANCELLED,
                        )
                        and entry.completed_at is not None
                        and (entry.completed_at + _TASK_TTL) < now
                    ]
                    for tid in stale:
                        del self._tasks[tid]

        thread = threading.Thread(
            target=_reaper_loop, name="scan-task-reaper", daemon=True
        )
        thread.start()
