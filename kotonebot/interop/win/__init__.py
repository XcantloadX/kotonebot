# ruff: noqa: E402
from kotonebot.util import require_windows
require_windows('kotonebot.interop.win module')


from . import _mouse as mouse
from .shake_mouse import ShakeMouse
from .window import Win32Window, FindWindowMethod

__all__ = [
    'mouse',
    'ShakeMouse',
    'Win32Window', 'FindWindowMethod'
]