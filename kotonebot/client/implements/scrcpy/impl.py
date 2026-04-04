import time
from typing import Literal, cast

from adbutils._device import AdbDevice as AdbUtilsDevice
from cv2.typing import MatLike
from typing_extensions import override

from kotonebot.util import windows_only

from ....errors import CapabilityNotSupportedError
from ...protocol import MouseButton
from ...protocol import AndroidCommandable, KeyboardDriver, MouseDriver, MultiTouchable, Screenshotable, TouchDriver, Lifecycle
from .config import ScrcpyConfig
from .session import ScrcpySession


@windows_only('ScrcpyImpl')
class ScrcpyImpl(Lifecycle, TouchDriver, Screenshotable, MultiTouchable, MouseDriver, KeyboardDriver, AndroidCommandable):
    max_contacts = 10

    def __init__(self, adb_connection: AdbUtilsDevice, config: ScrcpyConfig, session: ScrcpySession | None = None):
        self.adb = adb_connection
        self.config = config
        self._session = session or ScrcpySession(adb_connection, config)

    @property
    def session(self) -> ScrcpySession:
        return self._session

    @override
    def start(self) -> None:
        self._session.start()

    @override
    def stop(self) -> None:
        self._session.stop()

    @property
    def screen_size(self) -> tuple[int, int]:
        snapshot = self._session.video.get_latest_frame(copy=False)
        if snapshot is None:
            raise RuntimeError('Scrcpy video size is not available yet')
        return snapshot.width, snapshot.height

    @override
    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        width, height = self.screen_size
        if width > height:
            return 'landscape'
        if height > width:
            return 'portrait'
        return None

    @override
    def screenshot(self) -> MatLike:
        snapshot = self._session.video.get_latest_frame(copy=True)
        if snapshot is None:
            error = self._session.video.frame_store.get_error()
            if error is not None:
                raise RuntimeError('Scrcpy decoder failed') from error
            raise RuntimeError('No scrcpy frame is available')
        return snapshot.frame

    def _control(self):
        if self._session.control is None:
            raise CapabilityNotSupportedError('scrcpy control socket')
        return self._session.control

    @override
    def click(self, x: int, y: int) -> None:
        self.touch_down(x, y)
        time.sleep(0.03)
        self.touch_up(x, y)

    @override
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        duration = duration or 0.3
        steps = max(int(duration / 0.01), 1)
        self.touch_down(x1, y1)
        for i in range(steps):
            nx = int(round(x1 + (x2 - x1) * (i + 1) / steps))
            ny = int(round(y1 + (y2 - y1) * (i + 1) / steps))
            self.touch_move(nx, ny)
            time.sleep(0.01)
        self.touch_up(x2, y2)

    @override
    def multi_touch_down(self, x: int, y: int, pointer_id: int) -> None:
        self._control().send_touch_down(x, y, contact_id=pointer_id)

    @override
    def multi_touch_up(self, x: int, y: int, pointer_id: int) -> None:
        self._control().send_touch_up(x, y, contact_id=pointer_id)

    @override
    def touch_down(self, x: int, y: int, contact_id: int = 0) -> None:
        self._control().send_touch_down(x, y, contact_id=contact_id)

    @override
    def touch_move(self, x: int, y: int, contact_id: int = 0) -> None:
        self._control().send_touch_move(x, y, contact_id=contact_id)

    @override
    def touch_up(self, x: int, y: int, contact_id: int = 0) -> None:
        self._control().send_touch_up(x, y, contact_id=contact_id)

    @override
    def move(self, x: int, y: int) -> None:
        self._control().move(x, y)

    @override
    def button_down(self, button: MouseButton | None = None) -> None:
        self._control().button_down(button)

    @override
    def button_up(self, button: MouseButton | None = None) -> None:
        self._control().button_up(button)

    @override
    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        self._control().scroll(dx=dx, dy=dy)

    @override
    def key_down(self, key: str) -> None:
        self._control().key_down(key)

    @override
    def key_up(self, key: str) -> None:
        self._control().key_up(key)

    @override
    def type_text(self, text: str) -> None:
        self._control().type_text(text)

    @override
    def launch_app(self, package_name: str) -> None:
        cast(str, self.adb.shell(f'monkey -p {package_name} 1'))

    @override
    def current_package(self) -> str | None:
        result_text = cast(str, self.adb.shell('dumpsys activity top | grep ACTIVITY | tail -n 1')).strip()
        if not result_text:
            return None
        _, activity, *_ = result_text.split(' ')
        return activity.split('/')[0]

    @override
    def adb_shell(self, cmd: str) -> str:
        return cast(str, self.adb.shell(cmd))
