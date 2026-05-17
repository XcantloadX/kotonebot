from kotonebot.util import is_windows, is_macos

from .backend import WindowBackend
from .model import WindowQuery, Window, WindowNotFoundError


class WindowManager:
    """窗口管理器，用于查询和管理系统窗口。"""
    def __init__(self, backend: WindowBackend) -> None:
        """初始化窗口管理器。

        :param backend: 窗口后端实现
        """
        self.backend = backend

    @classmethod
    def default(cls) -> "WindowManager":
        """获取当前平台的默认窗口管理器。

        :return: 窗口管理器实例
        :raise NotImplementedError: 当前平台不支持
        """
        if is_windows():
            from .windows import WindowsWindowBackend
            return cls(WindowsWindowBackend())
        if is_macos():
            from .macos import MacOSWindowBackend
            return cls(MacOSWindowBackend())
        raise NotImplementedError("WindowManager.default is not implemented for this platform.")

    def find_all(self, query: WindowQuery) -> list[Window]:
        """查找所有匹配条件的窗口。

        :param query: 查询条件
        :return: 匹配的窗口列表
        """
        infos = self.backend.find_windows(query)
        return [self.backend.wrap(info) for info in infos]

    def find_one(self, query: WindowQuery) -> Window:
        """查找第一个匹配条件的窗口。

        :param query: 查询条件
        :return: 匹配的窗口
        :raise WindowNotFoundError: 未找到匹配的窗口
        """
        windows = self.find_all(query)
        if not windows:
            raise WindowNotFoundError(query)
        return windows[0]


class WindowSession:
    """窗口会话，维护对特定窗口的引用，支持窗口失效的自动重新查询。"""
    def __init__(self, query: WindowQuery, manager: WindowManager | None = None) -> None:
        """初始化窗口会话。

        :param query: 查询条件
        :param manager: 窗口管理器，如果为 None 则使用默认管理器
        """
        self.query = query
        self._manager = manager
        self._window: Window | None = None

    def get_window(self) -> Window:
        """获取窗口。如果缓存的窗口仍然有效则直接返回，否则重新查询。

        :return: 窗口对象
        :raise WindowNotFoundError: 未找到匹配的窗口
        """
        if self._manager is None:
            self._manager = WindowManager.default()
        if self._window is not None and self._window.is_valid():
            return self._window
        self._window = self._manager.find_one(self.query)
        return self._window

    def invalidate(self) -> None:
        """标记缓存的窗口为失效，下次调用 get_window() 时会重新查询。"""
        self._window = None
