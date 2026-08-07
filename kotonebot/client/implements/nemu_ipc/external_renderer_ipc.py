import ctypes
import logging
import os
import threading
import types
from collections import deque
from ctypes import wintypes

logger = logging.getLogger(__name__)

from kotonebot.util import windows_only

class NemuIpcIncompatible(RuntimeError):
    """MuMu12 IPC 环境不兼容或 DLL 加载失败"""


class StdRedirectError(RuntimeError):
    """重定向 stdout/stderr 到匿名管道失败。"""


class _SecurityAttributes(ctypes.Structure):
    """对应 Win32 SECURITY_ATTRIBUTES 结构，用于设置管道句柄的继承属性。"""
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


class _StdIoRedirector:
    """将进程级 stdout/stderr 句柄重定向到匿名管道，用于收集 DLL 的调试日志。

    external_renderer_ipc.dll 在加载时（DLL_PROCESS_ATTACH 的 CRT 初始化）
    会用 GetStdHandle 一次性快照 stdout/stderr 句柄到自身的 ioinfo 表，之后
    所有日志都直接 WriteFile 到该快照句柄，与进程级句柄无关。因此本类在
    DLL 加载前把进程级 STD_OUTPUT_HANDLE / STD_ERROR_HANDLE 换成匿名管道
    写端，使 DLL 快照到管道句柄；加载完成后立即还原进程级句柄，宿主的
    sys.stdout / sys.stderr / 其它 GetStdHandle 调用不受影响，而 DLL 的
    日志则永久进入管道被后台线程收集。
    """

    # GetStdHandle / SetStdHandle 的标准输出 / 错误句柄 ID
    _STD_OUTPUT_HANDLE = -11
    _STD_ERROR_HANDLE = -12
    # 后台线程单次 ReadFile 读取的缓冲区大小（字节）
    _BUFFER_SIZE = 4096
    # 收集日志行的默认上限，超过时丢弃最旧的行，防止长时间运行内存溢出
    _MAX_LOG_LINES = 2000

    def __init__(self, max_log_lines: int = _MAX_LOG_LINES) -> None:
        # 匿名管道句柄：读端由后台线程持有排空，写端被 DLL 永久持有
        self._read_handle: wintypes.HANDLE | None = None
        self._write_handle: wintypes.HANDLE | None = None
        # begin 时快照的原始进程级 stdout/stderr 句柄，用于 end 时还原
        self._original_stdout: wintypes.HANDLE | None = None
        self._original_stderr: wintypes.HANDLE | None = None
        # kernel32 库对象（含已声明的函数原型），仅 Windows 上初始化
        self._kernel32: ctypes.WinDLL | None = None
        # 后台收集线程
        self._thread: threading.Thread | None = None
        # 控制后台线程是否继续读取（仅 close 时置 False）
        self._reader_active: bool = False
        # 保护日志行列表的锁
        self._lock = threading.Lock()
        # 已收集的完整日志行（有界，超出 max_log_lines 时丢弃最旧的行，避免长期运行溢出）
        self._lines: deque[str] = deque(maxlen=max_log_lines)

    def begin(self) -> None:
        """重定向进程级 stdout/stderr 到管道写端，并启动后台收集线程。

        :raises StdRedirectError: 创建管道或设置句柄失败。
        """
        if self._reader_active:
            return
        kernel32 = self._configure_kernel32()
        self._kernel32 = kernel32

        # 设置可继承属性，保证句柄可被 DLL / 子进程继承
        security = _SecurityAttributes()
        security.nLength = ctypes.sizeof(_SecurityAttributes)
        security.bInheritHandle = True
        security.lpSecurityDescriptor = None

        read_handle = wintypes.HANDLE()
        write_handle = wintypes.HANDLE()
        ok = kernel32.CreatePipe(
            ctypes.byref(read_handle),
            ctypes.byref(write_handle),
            ctypes.byref(security),
            0,
        )
        if not ok:
            raise StdRedirectError(f"CreatePipe failed: {ctypes.WinError(ctypes.get_last_error())}")

        # 快照原始进程级 stdout/stderr 句柄，随后替换为管道写端
        original_stdout = kernel32.GetStdHandle(self._STD_OUTPUT_HANDLE)
        original_stderr = kernel32.GetStdHandle(self._STD_ERROR_HANDLE)

        ok = kernel32.SetStdHandle(self._STD_OUTPUT_HANDLE, write_handle)
        if not ok:
            # 失败时回收管道句柄，避免句柄泄漏
            kernel32.CloseHandle(read_handle)
            kernel32.CloseHandle(write_handle)
            raise StdRedirectError(f"SetStdHandle(stdout) failed: {ctypes.WinError(ctypes.get_last_error())}")
        ok = kernel32.SetStdHandle(self._STD_ERROR_HANDLE, write_handle)
        if not ok:
            # 还原 stdout 后回收管道句柄，避免句柄泄漏
            kernel32.SetStdHandle(self._STD_OUTPUT_HANDLE, original_stdout)
            kernel32.CloseHandle(read_handle)
            kernel32.CloseHandle(write_handle)
            raise StdRedirectError(f"SetStdHandle(stderr) failed: {ctypes.WinError(ctypes.get_last_error())}")

        self._read_handle = read_handle
        self._write_handle = write_handle
        self._original_stdout = original_stdout
        self._original_stderr = original_stderr
        self._reader_active = True
        # daemon 线程：进程退出时不阻塞，避免遗留管道导致挂起
        self._thread = threading.Thread(
            target=self._reader_loop,
            name="kotonebot-ExternalRendererIpc-std-redirect",
            daemon=True,
        )
        self._thread.start()
        logger.debug("stdout/stderr redirector started")

    def end(self) -> None:
        """还原 begin 时快照的进程级 stdout/stderr 句柄。

        注意：这里**不会**关闭管道写端句柄（DLL 永久持用它，关闭会导致 DLL
        后续 WriteFile 失败报警），也不会停止后台读取线程（它仍需持续排空
        管道以收集 DLL 运行期日志）。真正的资源回收由 close() / 进程退出时
        （daemon 线程）完成。
        """
        if self._kernel32 is None:
            return
        if self._original_stdout is not None:
            self._kernel32.SetStdHandle(self._STD_OUTPUT_HANDLE, self._original_stdout)
            self._original_stdout = None
        if self._original_stderr is not None:
            self._kernel32.SetStdHandle(self._STD_ERROR_HANDLE, self._original_stderr)
            self._original_stderr = None
        logger.debug("stderr/stdout redirector restored original handle")

    def close(self) -> None:
        """停止后台收集线程并释放本对象持有的句柄引用。

        由于写端句柄由 DLL 永久持有、读端被后台线程阻塞占用，这里仅置位
        停止标志并释放引用；句柄的真实回收交给进程退出时完成。
        """
        self._reader_active = False
        self._thread = None
        self._read_handle = None
        self._write_handle = None
        self._original_stdout = None
        self._original_stderr = None
        self._kernel32 = None

    def __del__(self) -> None:
        self.close()

    def drain_logs(self) -> list[str]:
        """取回并清空已收集的日志行列表。

        :returns: 当前已收集的全部日志行（原样拷贝）。
        """
        with self._lock:
            lines = list(self._lines)
            self._lines.clear()
        return lines

    def __enter__(self) -> "_StdIoRedirector":
        self.begin()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> bool:
        # 只还原进程级 stdout/stderr 句柄，不停止收集（原因见 begin/end 的注释）
        self.end()
        return False

    def _configure_kernel32(self) -> ctypes.WinDLL:
        """获取 kernel32 并声明用到的函数原型，保证 ctypes 类型安全。"""
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        kernel32.CreatePipe.argtypes = [
            ctypes.POINTER(wintypes.HANDLE),
            ctypes.POINTER(wintypes.HANDLE),
            ctypes.POINTER(_SecurityAttributes),
            wintypes.DWORD,
        ]
        kernel32.CreatePipe.restype = wintypes.BOOL

        kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel32.GetStdHandle.restype = wintypes.HANDLE

        kernel32.SetStdHandle.argtypes = [wintypes.DWORD, wintypes.HANDLE]
        kernel32.SetStdHandle.restype = wintypes.BOOL

        kernel32.ReadFile.argtypes = [
            wintypes.HANDLE,
            wintypes.LPVOID,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.LPVOID,
        ]
        kernel32.ReadFile.restype = wintypes.BOOL

        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL

        return kernel32

    def _reader_loop(self) -> None:
        """后台线程主循环：持续 ReadFile 排空管道，并把字节流按行拆分收集。"""
        kernel32 = self._kernel32
        read_handle = self._read_handle
        if kernel32 is None or read_handle is None:
            return

        buf = ctypes.create_string_buffer(self._BUFFER_SIZE)
        nread = wintypes.DWORD(0)
        partial = b""
        while self._reader_active:
            ok = kernel32.ReadFile(
                read_handle, buf, self._BUFFER_SIZE, ctypes.byref(nread), None
            )
            if not ok or nread.value == 0:
                # 读端已关闭或管道结束，停止收集
                break
            partial += buf.raw[: nread.value]
            # 按 \n 拆行，兼容 \r\n 行尾
            while True:
                index = partial.find(b"\n")
                if index == -1:
                    break
                line, partial = partial[:index], partial[index + 1 :]
                if line.endswith(b"\r"):
                    line = line[:-1]
                text = line.decode("utf-8", errors="replace")
                with self._lock:
                    self._lines.append(text)
        # 结束时把残余的未换行缓冲作为一行提交，避免丢数据
        if partial:
            with self._lock:
                self._lines.append(partial.decode("utf-8", errors="replace"))


@windows_only("ExternalRendererIpc")
class ExternalRendererIpc:
    r"""对 `external_renderer_ipc.dll` 的轻量封装。

    该类仅处理 DLL 加载与原型声明，并提供带有类型提示的薄包装方法，
    方便在其他模块中调用且保持类型安全。
    传入参数为 MuMu 根目录（如 F:\Apps\Netease\MuMuPlayer-12.0）。
    若 `capture_output` 为 True，在加载 DLL 前会先把进程级 stdout/stderr 重定向
    到匿名管道，以收集 DLL 写入 stdout/stderr 的调试日志（见 :class:`_StdIoRedirector`）。
    """

    def __init__(self, mumu_root_folder: str, capture_output: bool = True):
        self._output_redirector: _StdIoRedirector | None = None
        if capture_output:
            # 加载 DLL 前开始重定向：DLL 会一次性快照当前 stdout/stderr 句柄到管道
            self._output_redirector = _StdIoRedirector()
            with self._output_redirector:
                self.lib = self.__load_dll(mumu_root_folder)
            # with 退出时已还原进程级 stdout/stderr，但后台线程仍在收集 DLL 日志
        else:
            self.lib = self.__load_dll(mumu_root_folder)
        self.raise_on_error: bool = True
        """是否在调用 DLL 函数失败时抛出异常。"""
        self.__declare_prototypes()

    def get_dll_logs(self) -> list[str]:
        """取回并清空 external_renderer_ipc.dll 已收集的 stdout/stderr 日志。

        DLL 把连接状态消息写入 stdout、错误消息写入 stderr（见
        :class:`_StdIoRedirector` 说明）；二者合并到一个管道，此处一并取回。

        若未启用输出捕获（capture_output=False），返回空列表。

        :returns: DLL 写入 stdout/stderr 的已收集日志行列表。
        """
        if self._output_redirector is None:
            return []
        return self._output_redirector.drain_logs()

    def connect(self, nemu_folder: str, instance_id: int) -> int:
        """
        建立连接。

        API 原型：
        `int nemu_connect(const wchar_t* path, int index)`

        :param nemu_folder: 模拟器安装路径。
        :param instance_id: 模拟器实例 ID。
        :return: 成功返回连接 ID，失败返回 0。
        """
        return self.lib.nemu_connect(nemu_folder, instance_id)

    def disconnect(self, connect_id: int) -> None:
        """
        断开连接。

        API 原型：
        `void nemu_disconnect(int handle)`

        :param connect_id: 连接 ID。
        :return: 无返回值。
        """
        return self.lib.nemu_disconnect(connect_id)

    def get_display_id(self, connect_id: int, pkg: str, app_index: int) -> int:
        """
        获取指定包的 display id。

        API 原型：
        `int nemu_get_display_id(int handle, const char* pkg, int appIndex)`

        :param connect_id: 连接 ID。
        :param pkg: 包名。
        :param app_index: 多开应用索引。
        :return: <0 表示失败，>=0 表示有效 display id。
        """
        return self.lib.nemu_get_display_id(connect_id, pkg.encode('utf-8'), app_index)

    def capture_display(
        self,
        connect_id: int,
        display_id: int,
        buf_len: int,
        width_ptr: ctypes.c_void_p,
        height_ptr: ctypes.c_void_p,
        buffer_ptr: ctypes.c_void_p,
    ) -> int:
        """
        截取指定显示屏内容。

        API 原型：
        `int nemu_capture_display(int handle, unsigned int displayid, int buffer_size, int *width, int *height, unsigned char* pixels)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :param buf_len: 缓冲区长度（字节）。
        :param width_ptr: 用于接收宽度的指针（ctypes.c_void_p/int 指针）。
        :param height_ptr: 用于接收高度的指针（ctypes.c_void_p/int 指针）。
        :param buffer_ptr: 用于接收像素数据的指针（ctypes.c_void_p/unsigned char* 指针）。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_capture_display(
            connect_id,
            display_id,
            buf_len,
            width_ptr,
            height_ptr,
            buffer_ptr,
        )

    def input_text(self, connect_id: int, text: str) -> int:
        """
        输入文本。

        API 原型：
        `int nemu_input_text(int handle, int size, const char* buf)`

        :param connect_id: 连接 ID。
        :param text: 输入文本（utf-8）。
        :return: 0 表示成功，>0 表示失败。
        """
        buf = text.encode('utf-8')
        return self.lib.nemu_input_text(connect_id, len(buf), buf)

    def input_touch_down(self, connect_id: int, display_id: int, x: int, y: int) -> int:
        """
        发送触摸按下事件。

        API 原型：
        `int nemu_input_event_touch_down(int handle, int displayid, int x_point, int y_point)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :param x: 触摸点 X 坐标。
        :param y: 触摸点 Y 坐标。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_input_event_touch_down(connect_id, display_id, x, y)

    def input_touch_up(self, connect_id: int, display_id: int) -> int:
        """
        发送触摸抬起事件。

        API 原型：
        `int nemu_input_event_touch_up(int handle, int displayid)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_input_event_touch_up(connect_id, display_id)

    def input_key_down(self, connect_id: int, display_id: int, key_code: int) -> int:
        """
        发送按键按下事件。

        API 原型：
        `int nemu_input_event_key_down(int handle, int displayid, int key_code)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :param key_code: 按键码。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_input_event_key_down(connect_id, display_id, key_code)

    def input_key_up(self, connect_id: int, display_id: int, key_code: int) -> int:
        """
        发送按键抬起事件。

        API 原型：
        `int nemu_input_event_key_up(int handle, int displayid, int key_code)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :param key_code: 按键码。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_input_event_key_up(connect_id, display_id, key_code)

    def input_finger_touch_down(self, connect_id: int, display_id: int, finger_id: int, x: int, y: int) -> int:
        """
        多指触摸按下。

        API 原型：
        `int nemu_input_event_finger_touch_down(int handle, int displayid, int finger_id, int x_point, int y_point)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :param finger_id: 手指编号（1-10）。
        :param x: 触摸点 X 坐标。
        :param y: 触摸点 Y 坐标。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_input_event_finger_touch_down(connect_id, display_id, finger_id, x, y)

    def input_finger_touch_up(self, connect_id: int, display_id: int, finger_id: int) -> int:
        """
        多指触摸抬起。

        API 原型：
        `int nemu_input_event_finger_touch_up(int handle, int displayid, int slot_id)`

        :param connect_id: 连接 ID。
        :param display_id: 显示屏 ID。
        :param finger_id: 手指编号（1-10）。
        :return: 0 表示成功，>0 表示失败。
        """
        return self.lib.nemu_input_event_finger_touch_up(connect_id, display_id, finger_id)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def __load_dll(self, mumu_root_folder: str) -> ctypes.CDLL:
        """尝试多条路径加载 DLL。传入为 MuMu 根目录。

        优先级：优先 nx_main，其次动态枚举 nx_device 下的各引擎目录，
        最后回退到老版本 MuMu 的固定路径。
        """
        candidate_paths = [
            # 优先：主程序目录（nx_main）
            os.path.join(mumu_root_folder, "nx_main", "sdk", "external_renderer_ipc.dll"),
            # 其次：动态枚举 nx_device 下的所有引擎版本目录
            *self.__enum_engine_dll_paths(mumu_root_folder),
            # 老目录结构兜底
            # < 5.x
            os.path.join(
                mumu_root_folder,
                "shell",
                "nx_device",
                "12.0",
                "sdk",
                "external_renderer_ipc.dll",
            ),
            # <= 4.x
            os.path.join(mumu_root_folder, "shell", "sdk", "external_renderer_ipc.dll"),
        ]
        for p in candidate_paths:
            if not os.path.exists(p):
                continue
            try:
                dll = ctypes.CDLL(p)
                logger.debug("Loaded external_renderer_ipc.dll from %s", p)
                return dll
            except OSError as e:  # pragma: no cover
                logger.warning("Failed to load DLL (%s): %s", p, e)
        raise NemuIpcIncompatible("external_renderer_ipc.dll not found or failed to load.")

    def __enum_engine_dll_paths(self, mumu_root_folder: str) -> list[str]:
        """枚举 nx_device 下各引擎目录中的 external_renderer_ipc.dll 路径。"""
        nx_device_root = os.path.join(mumu_root_folder, "nx_device")
        if not os.path.isdir(nx_device_root):
            return []
        paths = []
        for engine in sorted(os.listdir(nx_device_root)):
            p = os.path.join(
                nx_device_root, engine, "shell", "sdk", "external_renderer_ipc.dll"
            )
            if os.path.exists(p):
                paths.append(p)
        return paths

    def __declare_prototypes(self) -> None:
        """声明 DLL 函数原型，确保 ctypes 类型安全。"""
        # 连接 / 断开
        self.lib.nemu_connect.argtypes = [ctypes.c_wchar_p, ctypes.c_int]
        self.lib.nemu_connect.restype = ctypes.c_int

        self.lib.nemu_disconnect.argtypes = [ctypes.c_int]
        self.lib.nemu_disconnect.restype = None

        # 获取 display id
        self.lib.nemu_get_display_id.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        self.lib.nemu_get_display_id.restype = ctypes.c_int

        # 截图
        self.lib.nemu_capture_display.argtypes = [
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.lib.nemu_capture_display.restype = ctypes.c_int

        # 输入文本
        self.lib.nemu_input_text.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p]
        self.lib.nemu_input_text.restype = ctypes.c_int

        # 触摸
        self.lib.nemu_input_event_touch_down.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.lib.nemu_input_event_touch_down.restype = ctypes.c_int

        self.lib.nemu_input_event_touch_up.argtypes = [ctypes.c_int, ctypes.c_int]
        self.lib.nemu_input_event_touch_up.restype = ctypes.c_int

        # 按键
        self.lib.nemu_input_event_key_down.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.lib.nemu_input_event_key_down.restype = ctypes.c_int

        self.lib.nemu_input_event_key_up.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.lib.nemu_input_event_key_up.restype = ctypes.c_int

        # 多指触摸
        self.lib.nemu_input_event_finger_touch_down.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.lib.nemu_input_event_finger_touch_down.restype = ctypes.c_int

        self.lib.nemu_input_event_finger_touch_up.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.lib.nemu_input_event_finger_touch_up.restype = ctypes.c_int

        logger.debug("DLL function prototypes declared") 
