from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Pattern, Literal

from kotonebot.errors import KotonebotError
from kotonebot.primitives import Rect

Platform = Literal["windows", "macos", "linux"]


class WindowQueryError(KotonebotError):
    """窗口查询相关的错误基类。"""
    pass


class UnsupportedQueryFieldError(WindowQueryError):
    """平台不支持指定的原生查询类型时抛出。

    :param platform: 平台名称
    :param query_native_type: 不支持的原生查询类型
    """
    def __init__(self, platform: Platform, query_native_type: type | None) -> None:
        native_name = query_native_type.__name__ if query_native_type else "None"
        super().__init__(f"Unsupported native query for platform '{platform}': {native_name}")


class WindowNotFoundError(WindowQueryError):
    """未找到符合查询条件的窗口时抛出。

    :param query: 查询条件
    """
    def __init__(self, query: "WindowQuery") -> None:
        super().__init__(f"Window not found for query: {query}")


@dataclass(frozen=True)
class WindowsNativeQuery:
    """Windows 原生窗口查询条件。"""
    executable: str | None = None
    """进程可执行文件路径。"""
    class_name: str | None = None
    """窗口类名。"""
    hwnd: int | None = None
    """窗口句柄。"""


@dataclass(frozen=True)
class MacOSNativeQuery:
    """macOS 原生窗口查询条件。"""
    bundle_id: str | None = None
    """应用程序 Bundle ID。"""


@dataclass(frozen=True)
class WindowsNativeInfo:
    """Windows 原生窗口信息。"""
    hwnd: int
    """窗口句柄。"""
    class_name: str | None = None
    """窗口类名。"""
    executable: str | None = None
    """进程可执行文件路径。"""
    is_active: bool | None = None
    """窗口是否为当前活跃窗口。"""


@dataclass(frozen=True)
class MacOSNativeInfo:
    """macOS 原生窗口信息。"""
    bundle_id: str | None = None
    """应用程序 Bundle ID。"""
    window_layer: int | None = None
    """窗口图层级别。"""
    owner_name: str | None = None
    """窗口所有者名称（应用程序名称）。"""


@dataclass(frozen=True)
class WindowQuery:
    """窗口查询条件。支持多种匹配模式，可组合使用。"""
    title: str | None = None
    """精确匹配窗口标题。"""
    title_contains: str | None = None
    """窗口标题包含此字符串。"""
    title_regex: Pattern[str] | None = None
    """窗口标题匹配此正则表达式。"""

    app_name: str | None = None
    """应用程序名称精确匹配。"""
    app_name_contains: str | None = None
    """应用程序名称包含此字符串。"""

    process_id: int | None = None
    """进程 ID 精确匹配。"""
    visible_only: bool = True
    """仅匹配可见窗口（默认 True）。"""

    platform: Platform | None = None
    """指定查询的平台。"""
    native: WindowsNativeQuery | MacOSNativeQuery | None = None
    """平台特定的原生查询条件。"""


@dataclass(frozen=True)
class WindowInfo:
    """窗口信息快照。"""
    id: int | str
    """窗口的唯一标识符（平台相关，如 Windows 中为 HWND）。"""
    platform: Platform
    """窗口所在的平台。"""

    title: str | None
    """窗口标题。"""
    app_name: str | None
    """应用程序名称。"""
    process_id: int | None
    """进程 ID。"""
    bounds: Rect | None
    """窗口的边界矩形。"""

    is_visible: bool | None = None
    """窗口是否可见。"""

    native: WindowsNativeInfo | MacOSNativeInfo | None = None
    """平台特定的原生窗口信息。"""


def match_common(info: WindowInfo, query: WindowQuery) -> bool:
    """检查窗口信息是否匹配通用查询条件。

    :param info: 窗口信息
    :param query: 查询条件
    :return: 是否匹配所有条件
    """
    if query.platform and query.platform != info.platform:
        return False
    if query.title is not None and info.title != query.title:
        return False
    if query.title_contains is not None:
        if not info.title or query.title_contains not in info.title:
            return False
    if query.title_regex is not None:
        if not info.title or not query.title_regex.search(info.title):
            return False
    if query.app_name is not None and info.app_name != query.app_name:
        return False
    if query.app_name_contains is not None:
        if not info.app_name or query.app_name_contains not in info.app_name:
            return False
    if query.process_id is not None and info.process_id != query.process_id:
        return False
    if query.visible_only and info.is_visible is False:
        return False
    return True


class Window(ABC):
    """窗口对象的抽象基类。提供平台无关的窗口操作接口。"""
    def __init__(self, info: WindowInfo) -> None:
        self._info = info

    @property
    def info(self) -> WindowInfo:
        """获取窗口信息快照。"""
        return self._info

    @property
    def id(self) -> int | str:
        """获取窗口的唯一标识符。"""
        return self._info.id

    @property
    def platform(self) -> Platform:
        """获取窗口所在的平台。"""
        return self._info.platform

    @abstractmethod
    def activate(self) -> None:
        """激活（前置）此窗口。"""
        raise NotImplementedError

    @abstractmethod
    def get_bounds(self) -> Rect | None:
        """获取窗口的边界矩形。"""
        raise NotImplementedError

    def get_client_bounds(self) -> Rect | None:
        """获取窗口的客户区边界矩形。默认等同于 get_bounds()。"""
        return self.get_bounds()

    def is_valid(self) -> bool:
        """检查窗口是否仍然有效（未被销毁）。"""
        return True

    @staticmethod
    def from_query(query: WindowQuery) -> "Window":
        """通过查询条件查找窗口。

        :param query: 查询条件
        :return: 找到的窗口
        :raise WindowNotFoundError: 未找到匹配的窗口
        """
        from .manager import WindowManager
        return WindowManager.default().find_one(query)

    @staticmethod
    def from_title_contains(title_contains: str) -> "Window":
        """通过标题包含条件查找窗口。

        :param title_contains: 窗口标题应包含的字符串
        :return: 找到的窗口
        :raise WindowNotFoundError: 未找到匹配的窗口
        """
        return Window.from_query(WindowQuery(title_contains=title_contains))

    @staticmethod
    def from_app_name_contains(app_name_contains: str) -> "Window":
        """通过应用程序名称包含条件查找窗口。

        :param app_name_contains: 应用程序名称应包含的字符串
        :return: 找到的窗口
        :raise WindowNotFoundError: 未找到匹配的窗口
        """
        return Window.from_query(WindowQuery(app_name_contains=app_name_contains))

    @staticmethod
    def from_pid(process_id: int) -> "Window":
        """通过进程 ID 查找窗口。

        :param process_id: 进程 ID
        :return: 找到的窗口
        :raise WindowNotFoundError: 未找到匹配的窗口
        """
        return Window.from_query(WindowQuery(process_id=process_id))
