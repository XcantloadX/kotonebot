import ctypes
import logging
import os

logger = logging.getLogger(__name__)


class NemuIpcIncompatible(RuntimeError):
    """MuMu12 IPC 环境不兼容或 DLL 加载失败"""


class ExternalRendererIpc:
    """对 `external_renderer_ipc.dll` 的轻量封装。

    该类仅处理 DLL 加载与原型声明，并提供带有类型提示的薄包装方法，
    方便在其他模块中调用且保持类型安全。
    """

    def __init__(self, mumu_shell_folder: str):
        if os.name != "nt":
            raise NemuIpcIncompatible("ExternalRendererIpc only supports Windows.")

        self.lib = self.__load_dll(mumu_shell_folder)
        self.raise_on_error: bool = True
        """是否在调用 DLL 函数失败时抛出异常。"""
        self.__declare_prototypes()

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

    def __load_dll(self, mumu_shell_folder: str) -> ctypes.CDLL:
        """尝试多条路径加载 DLL。"""
        candidate_paths = [
            os.path.join(mumu_shell_folder, "sdk", "external_renderer_ipc.dll"),
            os.path.join(
                mumu_shell_folder,
                "nx_device",
                "12.0",
                "sdk",
                "external_renderer_ipc.dll",
            ),
        ]
        for p in candidate_paths:
            if not os.path.exists(p):
                continue
            try:
                return ctypes.CDLL(p)
            except OSError as e:  # pragma: no cover
                logger.warning("Failed to load DLL (%s): %s", p, e)
        raise NemuIpcIncompatible("external_renderer_ipc.dll not found or failed to load.")

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