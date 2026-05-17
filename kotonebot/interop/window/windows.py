import os
from typing import TYPE_CHECKING
from pathlib import Path

from kotonebot.primitives import Rect
from kotonebot.util import require_windows

from .backend import WindowBackend
from .model import (
    WindowInfo,
    WindowQuery,
    Window,
    WindowsNativeQuery,
    WindowsNativeInfo,
    Platform,
    match_common,
)
from kotonebot.interop.win.window import Win32Window

if TYPE_CHECKING:
    import win32gui
    import win32con
    import win32api
    import win32process
else:
    win32gui = None
    win32con = None
    win32api = None
    win32process = None


def _load_deps() -> None:
    global win32gui, win32con, win32api, win32process
    if win32gui is not None and win32con is not None and win32api is not None and win32process is not None:
        return
    require_windows("WindowsWindowBackend")
    import win32gui as _win32gui
    import win32con as _win32con
    import win32api as _win32api
    import win32process as _win32process
    win32gui = _win32gui
    win32con = _win32con
    win32api = _win32api
    win32process = _win32process


def _get_process_executable(pid: int) -> str | None:
    """获取进程的可执行文件路径。

    :param pid: 进程 ID
    :return: 可执行文件路径，如果获取失败则返回 None
    """
    _load_deps()
    if pid <= 0:
        return None
    try:
        # 打开进程句柄，获取进程信息和虚拟内存读取权限
        process_handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False,
            pid,
        )
    except Exception:
        return None
    try:
        return win32process.GetModuleFileNameEx(process_handle, 0)
    except Exception:
        return None
    finally:
        try:
            win32api.CloseHandle(process_handle)
        except Exception:
            pass


class WindowsWindow(Window):
    """Windows 平台上的窗口对象。"""
    def __init__(self, info: WindowInfo) -> None:
        super().__init__(info)
        self._win32 = Win32Window(int(info.id))

    @property
    def hwnd(self) -> int:
        """获取窗口句柄。"""
        return self._win32.hwnd

    @property
    def win32_window(self) -> Win32Window:
        """获取底层 Win32Window 对象。"""
        return self._win32

    def activate(self) -> None:
        """激活此窗口（恢复最小化状态并前置）。"""
        _load_deps()
        if self._win32.is_minimized():
            self._win32.restore()
        self._win32.bring_foreground()

    def get_bounds(self) -> Rect | None:
        return self._win32.get_rect()

    def get_client_bounds(self) -> Rect | None:
        """获取窗口的客户区边界矩形（不包括边框和标题栏）。"""
        _load_deps()
        # 获取客户区相对于窗口的坐标
        client_left, client_top, client_right, client_bottom = win32gui.GetClientRect(self.hwnd)
        # 转换为屏幕坐标
        client_left, client_top = win32gui.ClientToScreen(self.hwnd, (client_left, client_top))
        client_right, client_bottom = win32gui.ClientToScreen(self.hwnd, (client_right, client_bottom))
        return Rect(
            client_left,
            client_top,
            client_right - client_left,
            client_bottom - client_top,
        )

    def is_valid(self) -> bool:
        """检查窗口是否仍然存在。"""
        _load_deps()
        return win32gui.IsWindow(self.hwnd) != 0

    def is_minimized(self) -> bool:
        """检查窗口是否处于最小化状态。"""
        return self._win32.is_minimized()

    def restore(self) -> None:
        """从最小化状态恢复窗口。"""
        self._win32.restore()


class WindowsWindowBackend(WindowBackend):
    """Windows 平台的窗口后端实现。"""
    native_query_type = WindowsNativeQuery

    @property
    def platform(self) -> Platform:
        return "windows"

    def _enum_windows(self, *, need_executable: bool) -> list[WindowInfo]:
        """枚举系统上的所有窗口。

        :param need_executable: 是否需要获取可执行文件路径（会降低性能）
        :return: 窗口信息列表
        """
        _load_deps()
        results: list[WindowInfo] = []

        def _enum_handler(hwnd: int, _):
            title = win32gui.GetWindowText(hwnd) or None
            class_name = win32gui.GetClassName(hwnd) if hwnd else None
            thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
            bounds = None
            try:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                bounds = Rect(left, top, right - left, bottom - top, name=f"Bounds of '{title}'")
            except Exception:
                bounds = None
            is_visible = win32gui.IsWindowVisible(hwnd) != 0
            is_active = win32gui.GetForegroundWindow() == hwnd

            executable = _get_process_executable(pid) if need_executable else None
            app_name = Path(executable).stem if executable else None

            info = WindowInfo(
                id=hwnd,
                platform="windows",
                title=title,
                app_name=app_name,
                process_id=pid,
                bounds=bounds,
                is_visible=is_visible,
                native=WindowsNativeInfo(
                    is_active=is_active,
                    hwnd=hwnd,
                    class_name=class_name,
                    executable=executable,
                ),
            )
            results.append(info)
            return True

        win32gui.EnumWindows(_enum_handler, None)
        return results

    def list_windows(self) -> list[WindowInfo]:
        return self._enum_windows(need_executable=True)

    def find_windows(self, query: WindowQuery) -> list[WindowInfo]:
        """查找符合条件的窗口，根据查询条件优化性能。"""
        self.validate_query(query)
        native = query.native if isinstance(query.native, WindowsNativeQuery) else None
        # 只在需要时才获取可执行文件路径，以改善性能
        need_executable = (
            query.app_name is not None
            or query.app_name_contains is not None
            or (native is not None and native.executable is not None)
        )
        return [
            info
            for info in self._enum_windows(need_executable=need_executable)
            if match_common(info, query) and self.match_native(info, query)
        ]

    def match_native(self, info: WindowInfo, query: WindowQuery) -> bool:
        """检查窗口是否匹配 Windows 特定的原生查询条件。"""
        native = query.native
        if native is None:
            return True
        if not isinstance(native, WindowsNativeQuery):
            return False
        if not isinstance(info.native, WindowsNativeInfo):
            return False
        if native.hwnd is not None and info.native.hwnd != native.hwnd:
            return False
        if native.class_name is not None and info.native.class_name != native.class_name:
            return False
        if native.executable is not None:
            target = native.executable.lower()
            current = (info.native.executable or "").lower()
            # 支持完整路径和仅文件名的匹配
            if current != target and os.path.basename(current) != os.path.basename(target):
                return False
        return True

    def wrap(self, info: WindowInfo) -> Window:
        """将窗口信息包装为 WindowsWindow 对象。"""
        return WindowsWindow(info)
