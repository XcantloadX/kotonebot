"""跨平台窗口查询和管理模块。

本包提供了统一的窗口查询和操作接口，支持 Windows、macOS 和 Linux 平台。

核心类及其作用：
===============

**WindowInfo** - 窗口信息快照（只读）
    表示某一时刻的窗口状态，包含窗口标题、应用程序名称、进程 ID、边界等。
    不会自动更新，需要重新查询获取最新信息。

    Example:
        >>> from kotonebot.interop.window import WindowInfo
        >>> info: WindowInfo  # 从查询获得
        >>> print(f"窗口标题: {info.title}, 应用: {info.app_name}, PID: {info.process_id}")

**WindowQuery** - 窗口查询条件（用于查询）
    定义了查询条件，用来从系统中查找窗口。支持多种匹配模式（精确、包含、正则等）。
    是查询的入口点，定义"要找什么"。

    Example:
        >>> from kotonebot.interop.window import WindowQuery
        >>> # 查找标题包含"记事本"的窗口
        >>> query = WindowQuery(title_contains="记事本")
        >>> # 查找特定应用程序的窗口
        >>> query = WindowQuery(app_name_contains="Chrome")
        >>> # 查找特定进程的窗口
        >>> query = WindowQuery(process_id=12345)
        >>> # 组合查询条件
        >>> query = WindowQuery(app_name_contains="VS Code", visible_only=True)

**Window** - 窗口对象（可交互的窗口）
    代表一个实际的窗口，可以对其进行操作（激活、获取边界等）。
    通过 WindowQuery 查询得到，是进行窗口操作的对象。

    Example:
        >>> from kotonebot.interop.window import Window
        >>> window = Window.from_title_contains("记事本")
        >>> window.activate()  # 激活窗口
        >>> bounds = window.get_bounds()  # 获取窗口边界
        >>> print(f"窗口位置: {bounds}")
        >>> # 检查窗口是否仍然存在
        >>> if window.is_valid():
        ...     print("窗口仍然有效")

**WindowManager** - 窗口管理器（查询的执行者）
    执行 WindowQuery 查询，返回匹配的 Window 对象。
    是查询的执行引擎，管理后端实现。

    Example:
        >>> from kotonebot.interop.window import WindowManager, WindowQuery
        >>> manager = WindowManager.default()
        >>> # 查找所有匹配的窗口
        >>> query = WindowQuery(app_name_contains="Chrome")
        >>> windows = manager.find_all(query)  # 返回列表
        >>> # 查找第一个匹配的窗口
        >>> window = manager.find_one(query)  # 返回单个窗口或抛出异常
        >>> # 或使用便捷方法
        >>> window = Window.from_app_name_contains("Chrome")

**WindowBackend** - 窗口后端（平台实现）
    抽象基类，定义窗口查询的接口。
    由 WindowsWindowBackend、MacOSWindowBackend 等平台特定实现。
    通常不直接使用，由 WindowManager 内部管理。

工作流示例：
===========

方案 1: 简单查询（推荐）
    >>> from kotonebot.interop.window import Window
    >>> # 一行代码查找并获取窗口
    >>> window = Window.from_title_contains("Python")
    >>> window.activate()

方案 2: 高级查询
    >>> from kotonebot.interop.window import WindowManager, WindowQuery
    >>> manager = WindowManager.default()
    >>> # 复杂的查询条件
    >>> query = WindowQuery(
    ...     app_name_contains="Chrome",
    ...     title_contains="GitHub",
    ...     visible_only=True,
    ... )
    >>> windows = manager.find_all(query)
    >>> for window in windows:
    ...     print(f"找到窗口: {window.info.title}")

方案 3: 窗口会话（长期监控）
    >>> from kotonebot.interop.window import WindowSession, WindowQuery
    >>> query = WindowQuery(title_contains="记事本")
    >>> session = WindowSession(query)
    >>> # 获取窗口，如果窗口已关闭会自动重新查询
    >>> window = session.get_window()
    >>> window.activate()
    >>> # ... 做一些其他操作 ...
    >>> # 标记窗口失效，下次会重新查询
    >>> session.invalidate()
    >>> window = session.get_window()  # 自动重新查询

类的关系图：
===========

    WindowQuery（查询条件）
         ↓
    WindowManager（查询执行者）
         ↓
    WindowBackend（平台实现）
         ↓
    WindowInfo（查询结果：窗口信息快照）
         ↓
    Window（可交互的窗口对象）

注意事项：
==========

1. WindowInfo 是快照，不会自动更新。需要重新查询获取最新信息。
2. WindowQuery 支持平台特定的原生查询（WindowsNativeQuery 等）。
3. Window.is_valid() 可检查窗口是否仍然存在。
4. WindowSession 可自动处理窗口失效的情况，适合长期持有窗口引用。
"""
from .model import (
    Platform,
    WindowQuery,
    WindowInfo,
    Window,
    WindowsNativeQuery,
    MacOSNativeQuery,
    WindowsNativeInfo,
    MacOSNativeInfo,
    WindowNotFoundError,
    UnsupportedQueryFieldError,
)
from .backend import WindowBackend
from .manager import WindowManager, WindowSession

__all__ = [
    "Platform",
    "WindowQuery",
    "WindowInfo",
    "Window",
    "WindowSession",
    "WindowsNativeQuery",
    "MacOSNativeQuery",
    "WindowsNativeInfo",
    "MacOSNativeInfo",
    "WindowNotFoundError",
    "UnsupportedQueryFieldError",
    "WindowBackend",
    "WindowManager",
]
