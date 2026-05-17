from typing import TYPE_CHECKING

from kotonebot.primitives import Rect
from kotonebot.util import require_macos

from .backend import WindowBackend
from .model import (
    WindowInfo,
    WindowQuery,
    Window,
    MacOSNativeQuery,
    MacOSNativeInfo,
    Platform,
)

if TYPE_CHECKING:
    from Quartz import CGWindowListCopyWindowInfo # type: ignore[import]
    from AppKit import NSRunningApplication # type: ignore[import]
else:
    CGWindowListCopyWindowInfo = None
    NSRunningApplication = None


def _load_deps() -> None:
    global CGWindowListCopyWindowInfo, NSRunningApplication
    if CGWindowListCopyWindowInfo is not None and NSRunningApplication is not None:
        return
    require_macos("MacOSWindowBackend")
    from Quartz import (
        CGWindowListCopyWindowInfo as _CGWindowListCopyWindowInfo, # type: ignore[import]
        kCGWindowListOptionOnScreenOnly, # type: ignore[import]
        kCGWindowListExcludeDesktopElements, # type: ignore[import]
        kCGNullWindowID, # type: ignore[import]
    )
    from AppKit import NSRunningApplication as _NSRunningApplication # type: ignore[import]
    CGWindowListCopyWindowInfo = _CGWindowListCopyWindowInfo
    globals()["kCGWindowListOptionOnScreenOnly"] = kCGWindowListOptionOnScreenOnly
    globals()["kCGWindowListExcludeDesktopElements"] = kCGWindowListExcludeDesktopElements
    globals()["kCGNullWindowID"] = kCGNullWindowID
    NSRunningApplication = _NSRunningApplication


class MacOSWindow(Window):
    """macOS 平台上的窗口对象。"""
    def __init__(self, info: WindowInfo) -> None:
        super().__init__(info)

    def activate(self) -> None:
        """激活此窗口（前置应用程序）。"""
        _load_deps()
        if self._info.process_id is None:
            return
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(self._info.process_id)
        if app is None:
            return
        try:
            from AppKit import NSApplicationActivateIgnoringOtherApps # type: ignore[import]
        except Exception:
            return
        app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)

    def get_bounds(self) -> Rect | None:
        _load_deps()
        if self._info.id is None:
            return None
        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements  # type: ignore[name-defined]
        windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID)  # type: ignore[name-defined]
        if not windows:
            return None
        for w in windows:
            if w.get("kCGWindowNumber") == self._info.id:
                bounds_dict = w.get("kCGWindowBounds") or {}
                if not bounds_dict:
                    return None
                return Rect(
                    int(bounds_dict.get("X", 0)),
                    int(bounds_dict.get("Y", 0)),
                    int(bounds_dict.get("Width", 0)),
                    int(bounds_dict.get("Height", 0)),
                )
        return None

    def is_valid(self) -> bool:
        """检查窗口是否仍然有效。"""
        _load_deps()
        if self._info.id is None:
            return False
        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements # type: ignore[import]
        windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) # type: ignore[import]
        if not windows:
            return False
        return any(w.get("kCGWindowNumber") == self._info.id for w in windows)


class MacOSWindowBackend(WindowBackend):
    """macOS 平台的窗口后端实现。"""
    native_query_type = MacOSNativeQuery

    @property
    def platform(self) -> Platform:
        return "macos"

    def list_windows(self) -> list[WindowInfo]:
        _load_deps()
        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements # type: ignore[import]
        windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) # type: ignore[import]
        results: list[WindowInfo] = []
        if not windows:
            return results
        for info in windows:
            window_id = info.get("kCGWindowNumber")
            title = info.get("kCGWindowName")
            owner_name = info.get("kCGWindowOwnerName")
            pid = info.get("kCGWindowOwnerPID")
            bounds_dict = info.get("kCGWindowBounds") or {}
            bounds = None
            if bounds_dict:
                bounds = Rect(
                    int(bounds_dict.get("X", 0)),
                    int(bounds_dict.get("Y", 0)),
                    int(bounds_dict.get("Width", 0)),
                    int(bounds_dict.get("Height", 0)),
                    name=f"Bounds of '{title}'",
                )
            is_visible = bool(info.get("kCGWindowIsOnscreen", True))

            bundle_id = None
            app_name = owner_name
            if pid:
                # 获取应用程序信息（Bundle ID 和本地化名称）
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                if app is not None:
                    try:
                        bundle_id = app.bundleIdentifier()
                    except Exception:
                        bundle_id = None
                    try:
                        app_name = app.localizedName() or owner_name
                    except Exception:
                        app_name = owner_name

            native = MacOSNativeInfo(
                bundle_id=bundle_id,
                window_layer=info.get("kCGWindowLayer"),
                owner_name=owner_name,
            )

            results.append(
                WindowInfo(
                    id=window_id,
                    platform="macos",
                    title=title,
                    app_name=app_name,
                    process_id=pid,
                    bounds=bounds,
                    is_visible=is_visible,
                    native=native,
                )
            )
        return results

    def match_native(self, info: WindowInfo, query: WindowQuery) -> bool:
        """检查窗口是否匹配 macOS 特定的原生查询条件。"""
        native = query.native
        if native is None:
            return True
        if not isinstance(native, MacOSNativeQuery):
            return False
        if not isinstance(info.native, MacOSNativeInfo):
            return False
        if native.bundle_id is not None and info.native.bundle_id != native.bundle_id:
            return False
        return True

    def wrap(self, info: WindowInfo) -> Window:
        """将窗口信息包装为 MacOSWindow 对象。"""
        return MacOSWindow(info)
