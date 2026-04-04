import threading
import time
from dataclasses import dataclass
from typing import Callable

from cv2.typing import MatLike

from kotonebot import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class FrameSnapshot:
    """最新视频帧的快照。"""

    frame: MatLike
    """当前帧图像。"""
    width: int
    """帧宽度。"""
    height: int
    """帧高度。"""
    seq: int
    """帧序号。"""
    timestamp: float
    """帧更新时间戳。"""


FrameSubscriber = Callable[[FrameSnapshot], None]


class LatestFrameStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._frame: MatLike | None = None
        self._width = 0
        self._height = 0
        self._seq = 0
        self._timestamp = 0.0
        self._error: Exception | None = None
        self._subscribers: dict[int, FrameSubscriber] = {}
        self._next_token = 1

    def clear(self) -> None:
        """清空当前帧和错误状态。"""
        with self._lock:
            self._frame = None
            self._width = 0
            self._height = 0
            self._seq = 0
            self._timestamp = 0.0
            self._error = None

    def set_error(self, error: Exception) -> None:
        """记录解码或采集过程中出现的错误。"""
        with self._lock:
            self._error = error

    def get_error(self) -> Exception | None:
        """获取最近一次错误。"""
        with self._lock:
            return self._error

    def update(self, frame: MatLike) -> FrameSnapshot:
        """更新最新帧并通知订阅者。"""
        subscribers: list[FrameSubscriber]
        with self._lock:
            self._frame = frame
            self._height, self._width = frame.shape[:2]
            self._seq += 1
            self._timestamp = time.time()
            snapshot = FrameSnapshot(
                frame=frame,
                width=self._width,
                height=self._height,
                seq=self._seq,
                timestamp=self._timestamp,
            )
            subscribers = list(self._subscribers.values())

        for callback in subscribers:
            try:
                callback(snapshot)
            except Exception:  # noqa: BLE001
                logger.exception('Scrcpy frame subscriber raised an exception')

        return snapshot

    def get_latest_frame(self, *, copy: bool = True) -> FrameSnapshot | None:
        """获取当前最新帧快照。"""
        with self._lock:
            if self._frame is None:
                return None
            frame = self._frame.copy() if copy else self._frame
            return FrameSnapshot(
                frame=frame,
                width=self._width,
                height=self._height,
                seq=self._seq,
                timestamp=self._timestamp,
            )

    def get_video_size(self) -> tuple[int, int] | None:
        """获取当前视频尺寸。"""
        with self._lock:
            if self._width <= 0 or self._height <= 0:
                return None
            return self._width, self._height

    def subscribe(self, callback: FrameSubscriber) -> int:
        """订阅帧更新通知。"""
        with self._lock:
            token = self._next_token
            self._next_token += 1
            self._subscribers[token] = callback
            return token

    def unsubscribe(self, token: int) -> None:
        """取消帧更新订阅。"""
        with self._lock:
            self._subscribers.pop(token, None)
