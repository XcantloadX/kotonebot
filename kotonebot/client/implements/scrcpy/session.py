from __future__ import annotations

import secrets
import shlex
import socket
import threading
import time
from collections import deque
from pathlib import Path
from typing import IO, Protocol, cast

from adbutils._device import AdbDevice as AdbUtilsDevice

from kotonebot import logging

from .config import ScrcpyConfig, VirtualDisplayConfig
from .control import ScrcpyControlChannel
from .probe import find_reusable_display
from .video import ScrcpyVideoStream

logger = logging.getLogger(__name__)

REMOTE_SERVER_PATH = '/data/local/tmp/kotonebot-scrcpy-server.jar'
SCRCPY_SOCKET_NAME = 'scrcpy'

class _ShellStreamConnection(Protocol):
    def makefile(self, mode: str, encoding: str | None = None, newline: str | None = None) -> IO[str]: ...


class _ShellStreamLike(Protocol):
    conn: _ShellStreamConnection

    def close(self) -> None: ...


class ScrcpySession:
    """管理 scrcpy server、视频流与控制通道的会话对象。"""

    def __init__(self, adb_connection: AdbUtilsDevice, config: ScrcpyConfig) -> None:
        self.adb = adb_connection
        self.config = config
        serial = config.device_serial or adb_connection.serial
        if serial is None:
            raise ValueError('Device serial is required')
        self.serial: str = serial

        self.video = ScrcpyVideoStream(codec_name=config.video_codec, timeout=config.timeout)
        self.control: ScrcpyControlChannel | None = None

        self._lock = threading.Lock()
        self._start_count = 0
        self._started = False
        self._effective_scid: int | None = None
        self._forward_port: int | None = None
        self._server_stream: _ShellStreamLike | None = None
        self._stdout_lines: deque[str] = deque(maxlen=64)
        self._stdout_thread: threading.Thread | None = None
        self._stdout_file: IO[str] | None = None
        self._server_stream_closed = threading.Event()
        self._attached_display_id: int | None = None
        self._created_new_display = False

    @property
    def start_count(self) -> int:
        """当前会话的启动引用计数。"""
        return self._start_count

    @property
    def scid(self) -> int:
        """当前会话使用的 scid。"""
        if self._effective_scid is None:
            raise RuntimeError('ScrcpySession has not been started yet')
        return self._effective_scid

    @property
    def started(self) -> bool:
        """会话是否已经启动。"""
        return self._started

    def start(self) -> None:
        """启动 scrcpy 会话。"""
        with self._lock:
            self._start_count += 1
            if self._started:
                return

            self._effective_scid = self._resolve_scid()
            params, effective = self._build_server_params()
            self._validate_effective_params(effective)

            try:
                if self.config.cleanup_strategy == 'aggressive':
                    self._kill_all_scrcpy_processes()
                self._push_server()
                self._forward_port = self._setup_forward()

                command = [
                    f'CLASSPATH={REMOTE_SERVER_PATH}',
                    'app_process',
                    '/',
                    'com.genymobile.scrcpy.Server',
                    self._server_version(),
                    *params,
                ]
                self._server_stream_closed.clear()
                self._server_stream = cast(_ShellStreamLike, self.adb.shell(shlex.join(command), stream=True))
                self._stdout_thread = threading.Thread(target=self._stdout_pump, daemon=True)
                self._stdout_thread.start()

                self._wait_for_socket_ready(timeout=min(self.config.timeout, 10.0))

                if self.config.video:
                    video_socket = self._connect_forward_socket()
                    self.video.start(video_socket)

                if self.config.control:
                    control_socket = self._connect_forward_socket()
                    self.control = ScrcpyControlChannel(control_socket, self.video.get_video_size)

                if (
                    self._created_new_display
                    and self._attached_display_id is None
                    and self.control is not None
                    and self.config.virtual_display is not None
                    and self.config.virtual_display.enabled
                    and self.config.virtual_display.launch_package
                ):
                    self.control.start_app(self.config.virtual_display.launch_package)

                if self.config.video:
                    self.video.wait_until_ready(timeout=self.config.timeout)

                self._started = True
            except Exception:
                self._start_count -= 1
                self._stop_locked(force=True)
                raise

    def stop(self) -> None:
        """停止 scrcpy 会话。"""
        with self._lock:
            if self._start_count == 0:
                return
            self._start_count -= 1
            if self._start_count > 0:
                return
            self._stop_locked(force=False)

    def _stop_locked(self, *, force: bool) -> None:
        """在持锁状态下清理会话资源。"""
        if not self._started and not force:
            return

        self.video.stop()

        if self.control is not None:
            try:
                self.control.close()
            except OSError:
                pass
            self.control = None

        if self._stdout_file is not None:
            try:
                self._stdout_file.close()
            except OSError:
                pass
            self._stdout_file = None
        if self._server_stream is not None:
            try:
                self._server_stream.close()
            except OSError:
                pass
            self._server_stream = None
        self._server_stream_closed.set()
        self._stdout_thread = None

        self._remove_forward()
        if self.config.cleanup_strategy == 'aggressive':
            self._kill_all_scrcpy_processes()

        self._started = False
        self._effective_scid = None
        self._attached_display_id = None
        self._created_new_display = False

    def _server_version(self) -> str:
        """获取 server 版本号。"""
        if not self.config.server_version:
            raise ValueError('ScrcpyConfig.server_version is required')
        return self.config.server_version

    def _resolve_scid(self) -> int:
        """生成或返回会话 scid。"""
        if self.config.scid is not None:
            return self.config.scid
        while True:
            candidate = secrets.randbits(31)
            if candidate != 0:
                return candidate

    def _socket_name(self) -> str:
        """构造 scrcpy 使用的 socket 名称。"""
        if self._effective_scid is None:
            raise RuntimeError('ScrcpySession socket name requested before start')
        if self._effective_scid == -1:
            return SCRCPY_SOCKET_NAME
        return f'{SCRCPY_SOCKET_NAME}_{self._effective_scid:08x}'

    def _shell_text(self, command: str | list[str], **kwargs) -> str:
        """执行 adb shell 命令并返回文本输出。"""
        return str(self.adb.shell(command, **kwargs))

    def _build_virtual_display_arg(self, config: VirtualDisplayConfig) -> str:
        """构造 virtual_display 参数值。"""
        if config.width is not None and config.height is not None:
            size_part = f'{config.width}x{config.height}'
        elif config.width is None and config.height is None:
            size_part = ''
        else:
            raise ValueError('virtual_display width and height must be both set or both omitted')

        if config.dpi is not None:
            return f'{size_part}/{config.dpi}'
        return size_part

    def _build_server_params(self) -> tuple[list[str], dict[str, str]]:
        """构造 scrcpy server 启动参数。"""
        if not self.config.server_jar_path:
            raise ValueError('ScrcpyConfig.server_jar_path is required')
        if not Path(self.config.server_jar_path).is_file():
            raise FileNotFoundError(self.config.server_jar_path)

        display_id_override, create_new_display = self._resolve_display_strategy()
        self._attached_display_id = display_id_override
        self._created_new_display = create_new_display

        params = [
            f'log_level={self.config.log_level}',
            f'scid={self._format_scid_param(self._resolve_scid_for_params())}',
            f'video={"true" if self.config.video else "false"}',
            f'audio={"true" if self.config.audio else "false"}',
            f'control={"true" if self.config.control else "false"}',
            f'video_codec={self.config.video_codec}',
            'tunnel_forward=true',
            'cleanup=false',
            'raw_stream=true',
        ]
        effective_display_id = display_id_override if display_id_override is not None else self.config.display_id
        if effective_display_id is not None:
            params.append(f'display_id={effective_display_id}')
        if self.config.max_size is not None:
            params.append(f'max_size={self.config.max_size}')
        if self.config.video_bit_rate is not None:
            params.append(f'video_bit_rate={self.config.video_bit_rate}')
        if create_new_display and self.config.virtual_display is not None and self.config.virtual_display.enabled:
            if effective_display_id is not None:
                raise ValueError('display_id cannot be set together with virtual_display')
            params.append(f'new_display={self._build_virtual_display_arg(self.config.virtual_display)}')
            if self.config.virtual_display.destroy_content is not None:
                params.append(f'vd_destroy_content={str(self.config.virtual_display.destroy_content).lower()}')
            if self.config.virtual_display.system_decorations is not None:
                params.append(f'vd_system_decorations={str(self.config.virtual_display.system_decorations).lower()}')

        params.extend(self.config.extra_args)

        effective: dict[str, str] = {}
        for param in params:
            if '=' in param:
                key, value = param.split('=', 1)
                effective[key] = value
        return params, effective

    def _resolve_display_strategy(self) -> tuple[int | None, bool]:
        """决定是否复用已有虚拟显示。"""
        vd = self.config.virtual_display
        if vd is None or not vd.enabled:
            return None, False
        if not vd.reuse_existing:
            return None, True
        if vd.launch_package is None or vd.width is None or vd.height is None:
            return None, True

        logger.info(
            'Scrcpy display reuse probe start: package=%s size=%sx%s',
            vd.launch_package,
            vd.width,
            vd.height,
        )
        reused = find_reusable_display(
            self.adb,
            target_package=vd.launch_package,
            width=vd.width,
            height=vd.height,
        )
        if reused is None:
            logger.info('No reusable display found, creating new virtual display')
            return None, True
        logger.info(
            'Reusing existing display_id=%s size=%sx%s top_package=%s',
            reused.display_id,
            reused.width,
            reused.height,
            reused.top_package,
        )
        return reused.display_id, False

    def _resolve_scid_for_params(self) -> int:
        """获取用于参数传递的 scid。"""
        if self.config.scid is not None:
            return self.config.scid
        if self._effective_scid is None:
            raise RuntimeError('ScrcpySession scid requested before initialization')
        return self._effective_scid

    def _format_scid_param(self, scid: int) -> str:
        """格式化 scid 参数。"""
        if scid == -1:
            return '-1'
        return f'{scid:08x}'

    def _validate_effective_params(self, effective: dict[str, str]) -> None:
        """校验最终生效的 server 参数。"""
        if effective.get('video', 'true').lower() != 'true':
            raise ValueError('ScrcpySession requires video=true')
        if effective.get('audio', 'false').lower() == 'true':
            raise ValueError('ScrcpySession does not support audio')

    def _push_server(self) -> None:
        """推送 scrcpy server 到设备。"""
        logger.info('Push scrcpy server from %s to %s', self.config.server_jar_path, REMOTE_SERVER_PATH)
        self.adb.sync.push(self.config.server_jar_path, REMOTE_SERVER_PATH)

    def _setup_forward(self) -> int:
        """创建 adb 端口转发。"""
        port = int(self.adb.forward_port(f'localabstract:{self._socket_name()}'))
        logger.info('Forwarded tcp:%s -> localabstract:%s for %s', port, self._socket_name(), self.serial)
        return port

    def _remove_forward(self) -> None:
        """移除 adb 端口转发。"""
        if self._forward_port is None:
            return
        local = f'tcp:{self._forward_port}'
        try:
            forward_remove = getattr(self.adb, 'forward_remove', None)
            if callable(forward_remove):
                forward_remove(local)
            else:
                # Older adbutils versions expose open_transport("killforward:...")
                # but do not provide the forward_remove convenience wrapper yet.
                self.adb.open_transport(f'killforward:{local}').close()
        except Exception:
            logger.debug('Failed to remove forward tcp:%s on %s', self._forward_port, self.serial, exc_info=True)
        self._forward_port = None

    def _stdout_pump(self) -> None:
        """持续收集 scrcpy server 的输出日志。"""
        stream = self._server_stream
        if stream is None:
            return
        fileobj = self._stdout_file
        if fileobj is None:
            fileobj = stream.conn.makefile('r', encoding='utf-8', newline='')
            self._stdout_file = fileobj
        try:
            for line in fileobj:
                text = line.rstrip()
                if text:
                    self._stdout_lines.append(text)
                    logger.debug('[scrcpy-server] %s', text)
        except OSError:
            logger.debug('scrcpy server output stream closed', exc_info=True)
        finally:
            self._server_stream_closed.set()

    def _server_output_message(self) -> str:
        """拼接最近的 server 输出。"""
        if not self._stdout_lines:
            return '<no scrcpy output captured>'
        return '\n'.join(self._stdout_lines)

    def _wait_for_socket_ready(self, timeout: float = 10.0) -> None:
        """等待 scrcpy socket 出现。"""
        deadline = time.monotonic() + timeout
        needle = f'@{self._socket_name()}'
        while time.monotonic() < deadline:
            if self._server_stream_closed.is_set():
                raise RuntimeError(f'scrcpy server exited early:\n{self._server_output_message()}')
            unix_table = self._shell_text(['cat', '/proc/net/unix'])
            if needle in unix_table:
                time.sleep(0.2)
                return
            time.sleep(0.1)
        raise TimeoutError(f'Scrcpy socket {needle} did not appear on {self.serial}')

    def _connect_forward_socket(self) -> socket.socket:
        """连接已建立转发的本地 socket。"""
        if self._forward_port is None:
            raise RuntimeError('Forward port is not initialized')
        sock = socket.create_connection(('127.0.0.1', self._forward_port), timeout=5)
        sock.settimeout(1.0)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
        if hasattr(socket, 'TCP_NODELAY'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return sock

    def _iter_scrcpy_server_pids(self) -> list[int]:
        """枚举设备上残留的 scrcpy server 进程。"""
        try:
            ps_output = self._shell_text(['ps', '-A'])
            if not ps_output.strip():
                ps_output = self._shell_text(['ps'])
        except Exception as exc:
            logger.warning('Failed to enumerate Android processes via adb: %s', exc)
            return []
        pids: list[int] = []
        for line in ps_output.splitlines():
            if 'app_process' not in line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            try:
                pid = int(parts[1])
            except ValueError:
                continue
            try:
                cmdline = self._shell_text(['cat', f'/proc/{pid}/cmdline']).replace('\x00', ' ')
            except Exception:
                continue
            if 'com.genymobile.scrcpy.Server' in cmdline:
                pids.append(pid)
        return pids

    def _kill_all_scrcpy_processes(self) -> None:
        """清理设备上所有 scrcpy server 进程。"""
        for pid in self._iter_scrcpy_server_pids():
            logger.info('Kill residual scrcpy server pid=%s on %s', pid, self.serial)
            try:
                self._shell_text(['kill', str(pid)])
            except Exception:
                logger.debug('Failed to kill scrcpy server pid=%s on %s', pid, self.serial, exc_info=True)
        time.sleep(0.2)
