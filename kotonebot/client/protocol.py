from typing_extensions import deprecated
from typing import Protocol, TYPE_CHECKING, runtime_checkable, Literal

from cv2.typing import MatLike

from kotonebot.primitives import Rect
if TYPE_CHECKING:
    from .device import Device

@runtime_checkable
class ClickableObjectProtocol(Protocol):
    """
    可点击对象的协议
    """
    @property
    def rect(self) -> Rect:
        ...

@runtime_checkable
class Commandable(Protocol):
    def __init__(self, device: 'Device'): ...
    def launch_app(self, package_name: str) -> None: ...
    def current_package(self) -> str | None: ...

@runtime_checkable
class AndroidCommandable(Protocol):
    """定义 Android 平台的特定命令"""
    def launch_app(self, package_name: str) -> None: ...
    def current_package(self) -> str | None: ...
    def adb_shell(self, cmd: str) -> str: ...
    def install_apk(self, path: str) -> None: ...

@runtime_checkable
class WindowsCommandable(Protocol):
    """定义 Windows 平台的特定命令"""
    def get_foreground_window(self) -> tuple[int, str]: ...
    def exec_command(self, command: str) -> tuple[int, str, str]: ...

@runtime_checkable
class Screenshotable(Protocol):
    def __init__(self, device: 'Device'): ...
    @property
    def screen_size(self) -> tuple[int, int]:
        """
        屏幕尺寸。格式为 `(width, height)`。
        
        **注意**： 此属性返回的分辨率会随设备方向变化。
        如果 `self.orientation` 为 `landscape`，则返回的分辨率是横屏下的分辨率，
        否则返回竖屏下的分辨率。

        `self.orientation` 属性默认为竖屏。如果需要自动检测，
        调用 `self.detect_orientation()` 方法。
        如果已知方向，也可以直接设置 `self.orientation` 属性。
        """
        ...
    
    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None: ...
    def screenshot(self) -> MatLike: ...

@deprecated('Use TouchDriver or MouseDriver instead')
@runtime_checkable
class Touchable(Protocol):
    def __init__(self, device: 'Device'): ...
    def click(self, x: int, y: int) -> None: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None) -> None: ...

@runtime_checkable
class Lifecycle(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...

@deprecated('Inerit from TouchDriver or MouseDriver instead')
@runtime_checkable
class MultiTouchable(Touchable, Protocol):
    def multi_touch_down(self, x: int, y: int, pointer_id: int) -> None:
        """以指定的 pointer_id 按下坐标 (x, y)。
        
        可以在同一 pointer_id 上传入不同的坐标调用多次以模拟拖动。

        :param x: 横坐标
        :param y: 纵坐标
        :param pointer_id: 指针 ID
        """

    def multi_touch_up(self, x: int, y: int, pointer_id: int) -> None:
        """抬起指定 pointer_id 的触摸点。
    
        :param x: 横坐标
        :param y: 纵坐标
        :param pointer_id: 指针 ID
        """

@runtime_checkable
class Driver(Protocol): pass

MouseButton = Literal['left', 'right', 'middle']
@runtime_checkable
class MouseDriver(Driver, Protocol):
    def move(self, x: int, y: int) -> None: ...
    def button_down(self, button: MouseButton | None = None) -> None: ...
    def button_up(self, button: MouseButton | None = None) -> None: ...
    def scroll(self, dx: int = 0, dy: int = 0) -> None: ...


@runtime_checkable
class TouchDriver(Driver, Protocol):
    max_contacts: int

    def touch_down(self, x: int, y: int, contact_id: int = 0) -> None: ...
    def touch_move(self, x: int, y: int, contact_id: int = 0) -> None: ...
    def touch_up(self, x: int, y: int, contact_id: int = 0) -> None: ...

@runtime_checkable
class KeyboardDriver(Driver, Protocol):
    def key_down(self, key: str) -> None: ...
    def key_up(self, key: str) -> None: ...
    def type_text(self, text: str) -> None: ...

@runtime_checkable
class SimpleInputDriver(Driver, Protocol):
    def click(self, x: int, y: int) -> None: ...
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float|None = None) -> None: ...