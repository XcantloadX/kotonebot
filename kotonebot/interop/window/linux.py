from __future__ import annotations

from .backend import WindowBackend
from .model import WindowInfo, WindowQuery, Window, Platform


class LinuxWindowBackend(WindowBackend):
    """Linux 平台的窗口后端实现（当前未实现）。"""
    @property
    def platform(self) -> Platform:
        return "linux"

    def list_windows(self) -> list[WindowInfo]:
        """列出系统上的所有窗口。

        :raise NotImplementedError: Linux 窗口后端尚未实现
        """
        raise NotImplementedError("Linux window backend is not implemented yet.")

    def wrap(self, info: WindowInfo) -> Window:
        """将窗口信息包装为 Window 对象。

        :raise NotImplementedError: Linux 窗口后端尚未实现
        """
        raise NotImplementedError("Linux window backend is not implemented yet.")
