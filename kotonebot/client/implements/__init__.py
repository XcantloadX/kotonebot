from kotonebot.util import is_windows, require_windows

# 基础实现
from . import adb  # noqa: F401
from . import adb_raw  # noqa: F401
from . import uiautomator2  # noqa: F401

# Windows 实现（默认仅在 Windows 上导入）
if is_windows():
    try:
        from . import nemu_ipc  # noqa: F401
        from . import windows  # noqa: F401
        from . import remote_windows  # noqa: F401
    except ImportError:
        require_windows('"windows" and "remote_windows" implementations')