import socket
import threading

import av

from .frame_store import FrameSnapshot, FrameSubscriber, LatestFrameStore


class ScrcpyVideoStream:
    """scrcpy 视频流解码与帧分发器。"""

    def __init__(self, codec_name: str, timeout: float, frame_store: LatestFrameStore | None = None) -> None:
        self.codec_name = codec_name
        self.timeout = timeout
        self.frame_store = frame_store or LatestFrameStore()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, sock: socket.socket) -> None:
        """启动视频流解码线程。"""
        if self._thread is not None and self._thread.is_alive():
            raise RuntimeError('ScrcpyVideoStream is already running')
        self.frame_store.clear()
        self._ready.clear()
        self._stop.clear()
        self._thread = threading.Thread(target=self._decode_loop, args=(sock,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止视频流解码线程。"""
        self._stop.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._thread = None

    def wait_until_ready(self, timeout: float | None = None) -> None:
        """等待首帧解码完成。"""
        wait_timeout = self.timeout if timeout is None else timeout
        if not self._ready.wait(wait_timeout):
            raise TimeoutError('Scrcpy first frame timeout')
        error = self.frame_store.get_error()
        if error is not None:
            raise RuntimeError('Scrcpy decoder failed') from error
        if self.frame_store.get_latest_frame(copy=False) is None:
            raise RuntimeError('Scrcpy decoder ended without producing frames')

    def get_latest_frame(self, *, copy: bool = True) -> FrameSnapshot | None:
        """获取最新帧快照。"""
        return self.frame_store.get_latest_frame(copy=copy)

    def get_video_size(self) -> tuple[int, int] | None:
        """获取当前视频尺寸。"""
        return self.frame_store.get_video_size()

    def subscribe(self, callback: FrameSubscriber) -> int:
        """订阅帧更新。"""
        return self.frame_store.subscribe(callback)

    def unsubscribe(self, token: int) -> None:
        """取消帧更新订阅。"""
        self.frame_store.unsubscribe(token)

    def _decode_loop(self, sock: socket.socket) -> None:
        codec = av.CodecContext.create(self.codec_name, 'r')
        codec.thread_count = 1
        try:
            with sock:
                while not self._stop.is_set():
                    try:
                        chunk = sock.recv(64 * 1024)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    for packet in codec.parse(chunk):
                        for frame in codec.decode(packet):
                            image = frame.to_ndarray(format='bgr24')
                            self.frame_store.update(image)
                            self._ready.set()
                for frame in codec.decode():
                    image = frame.to_ndarray(format='bgr24')
                    self.frame_store.update(image)
                    self._ready.set()
        except Exception as exc:  # noqa: BLE001
            self.frame_store.set_error(exc)
            self._ready.set()
        finally:
            self._stop.set()
