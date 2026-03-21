# ruff: noqa: E402
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import _mouse as mouse
    from .shake_mouse import ShakeMouse
    from .window import Win32Window, FindWindowMethod

def __getattr__(name: str):
    if name == "mouse":
        from . import _mouse as mouse
        return mouse
    if name == "ShakeMouse":
        from .shake_mouse import ShakeMouse
        return ShakeMouse
    if name in {"Win32Window", "FindWindowMethod"}:
        from .window import Win32Window, FindWindowMethod
        return Win32Window if name == "Win32Window" else FindWindowMethod
    raise AttributeError(name=name)

__all__ = [
    'mouse',
    'ShakeMouse',
    'Win32Window', 'FindWindowMethod'
]
