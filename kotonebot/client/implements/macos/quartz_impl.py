# ruff: noqa: E402
from kotonebot.util import macos_only, require_macos

import time
from typing import TYPE_CHECKING, Literal

import cv2
import numpy as np
from cv2.typing import MatLike

from ...protocol import MouseButton, MouseDriver, SimpleInputDriver, Touchable, Screenshotable, Lifecycle
from kotonebot.interop.window import WindowQuery, WindowSession
from kotonebot.interop.window.macos import MacOSWindow

if TYPE_CHECKING:
    from Quartz import (
        CGWindowListCreateImageFromArray, # type: ignore[import]
        CGImageGetWidth, # type: ignore[import]
        CGImageGetHeight, # type: ignore[import]
        CGImageGetBytesPerRow, # type: ignore[import]
        CGImageGetDataProvider, # type: ignore[import]
        CGDataProviderCopyData, # type: ignore[import]
        CGEventCreateMouseEvent, # type: ignore[import]
        CGEventCreateScrollWheelEvent, # type: ignore[import]
        CGEventPost, # type: ignore[import]
    )
    from ...device import Device
else:
    CGWindowListCreateImageFromArray = None
    CGImageGetWidth = None
    CGImageGetHeight = None
    CGImageGetBytesPerRow = None
    CGImageGetDataProvider = None
    CGDataProviderCopyData = None
    CGEventCreateMouseEvent = None
    CGEventCreateScrollWheelEvent = None
    CGEventPost = None


def _load_deps() -> None:
    global CGWindowListCreateImageFromArray
    global CGImageGetWidth, CGImageGetHeight
    global CGImageGetBytesPerRow, CGImageGetDataProvider
    global CGDataProviderCopyData
    global CGEventCreateMouseEvent, CGEventCreateScrollWheelEvent, CGEventPost
    if CGWindowListCreateImageFromArray is not None:
        return
    require_macos('"QuartzImpl" implementation')
    from Quartz import (
        CGWindowListCreateImageFromArray as _CGWindowListCreateImageFromArray, # type: ignore[import]
        CGImageGetWidth as _CGImageGetWidth, # type: ignore[import]
        CGImageGetHeight as _CGImageGetHeight, # type: ignore[import]
        CGImageGetBytesPerRow as _CGImageGetBytesPerRow, # type: ignore[import]
        CGImageGetDataProvider as _CGImageGetDataProvider, # type: ignore[import]
        CGDataProviderCopyData as _CGDataProviderCopyData, # type: ignore[import]
        CGEventCreateMouseEvent as _CGEventCreateMouseEvent, # type: ignore[import]
        CGEventCreateScrollWheelEvent as _CGEventCreateScrollWheelEvent, # type: ignore[import]
        CGEventPost as _CGEventPost, # type: ignore[import]
    )
    CGWindowListCreateImageFromArray = _CGWindowListCreateImageFromArray
    CGImageGetWidth = _CGImageGetWidth
    CGImageGetHeight = _CGImageGetHeight
    CGImageGetBytesPerRow = _CGImageGetBytesPerRow
    CGImageGetDataProvider = _CGImageGetDataProvider
    CGDataProviderCopyData = _CGDataProviderCopyData
    CGEventCreateMouseEvent = _CGEventCreateMouseEvent
    CGEventCreateScrollWheelEvent = _CGEventCreateScrollWheelEvent
    CGEventPost = _CGEventPost


# ---------------------------------------------------------------------------
# CGEvent 常量映射
# ---------------------------------------------------------------------------

# MouseButton → (按下事件类型, 抬起事件类型, 拖拽事件类型, CGMouseButton 编号)
# CGMouseButton: 0=左键 1=右键 2=中键
_BUTTON_EVENTS: dict[str, tuple[int, int, int, int]] = {}

def _get_button_events() -> dict[str, tuple[int, int, int, int]]:
    """懒加载 CGEvent 鼠标按键常量映射。"""
    if _BUTTON_EVENTS:
        return _BUTTON_EVENTS
    from Quartz import (
        kCGEventLeftMouseDown, kCGEventLeftMouseUp, kCGEventLeftMouseDragged, # type: ignore[import]
        kCGEventRightMouseDown, kCGEventRightMouseUp, kCGEventRightMouseDragged, # type: ignore[import]
        kCGEventOtherMouseDown, kCGEventOtherMouseUp, kCGEventOtherMouseDragged, # type: ignore[import]
        kCGMouseButtonLeft, kCGMouseButtonRight, kCGMouseButtonCenter, # type: ignore[import]
    )
    _BUTTON_EVENTS.update({
        'left':   (kCGEventLeftMouseDown,  kCGEventLeftMouseUp,  kCGEventLeftMouseDragged,  kCGMouseButtonLeft),
        'right':  (kCGEventRightMouseDown, kCGEventRightMouseUp, kCGEventRightMouseDragged, kCGMouseButtonRight),
        'middle': (kCGEventOtherMouseDown, kCGEventOtherMouseUp, kCGEventOtherMouseDragged, kCGMouseButtonCenter),
    })
    return _BUTTON_EVENTS


# ---------------------------------------------------------------------------
# 模块级截图辅助函数
# ---------------------------------------------------------------------------

def _title_bar_height_pts(frame_w_pts: int, frame_h_pts: int) -> float:
    """计算 macOS 标准标题栏高度（逻辑点，points）。

    利用 ``NSWindow.contentRectForFrameRect_styleMask_`` 将整个窗口框架矩形
    换算为内容矩形，差值即为标题栏高度（单位：逻辑点）。

    :param frame_w_pts: 窗口框架宽度（逻辑点，包含标题栏）。
    :param frame_h_pts: 窗口框架高度（逻辑点，包含标题栏）。
    :return: 标题栏高度，单位逻辑点。
    """
    from AppKit import NSWindow, NSWindowStyleMaskTitled  # type: ignore[import]
    from Foundation import NSMakeRect  # type: ignore[import]
    frame_rect = NSMakeRect(0, 0, frame_w_pts, frame_h_pts)
    content_rect = NSWindow.contentRectForFrameRect_styleMask_(
        frame_rect, NSWindowStyleMaskTitled
    )
    return frame_h_pts - content_rect.size.height


def _cgimage_to_numpy(cg_image) -> MatLike:
    """将 CGImage 转换为 OpenCV BGR 格式的 numpy 数组。"""
    _load_deps()
    width = CGImageGetWidth(cg_image)
    height = CGImageGetHeight(cg_image)
    bytes_per_row = CGImageGetBytesPerRow(cg_image)

    provider = CGImageGetDataProvider(cg_image)
    raw_data = CGDataProviderCopyData(provider)

    arr = np.frombuffer(raw_data, dtype=np.uint8)
    # bytes_per_row 可能因内存对齐而大于 width * 4，需要裁剪
    arr = arr.reshape((height, bytes_per_row // 4, 4))
    arr = arr[:, :width, :]  # 裁掉水平 padding

    # macOS CGImage 数据为 BGRA（小端 32 位，预乘 alpha），转为 BGR
    return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)


def _capture_window(window_id: int) -> MatLike:
    """通过 CGWindowNumber 截取指定窗口完整帧（含标题栏）。

    :param window_id: 目标窗口的 CGWindowNumber。
    :raises RuntimeError: 截图失败（例如未授予屏幕录制权限）时抛出。
    """
    _load_deps()
    from Quartz import (
        CGRectNull, # type: ignore[import]
        kCGWindowImageDefault, # type: ignore[import]
        kCGWindowImageBoundsIgnoreFraming, # type: ignore[import]
    )
    image = CGWindowListCreateImageFromArray(
        CGRectNull,
        [window_id],
        kCGWindowImageDefault | kCGWindowImageBoundsIgnoreFraming,
    )
    if image is None:
        raise RuntimeError(
            f'Failed to capture window (id={window_id}). '
            'Screen Recording permission may be required.'
        )
    return _cgimage_to_numpy(image)


# ---------------------------------------------------------------------------
# QuartzImpl
# ---------------------------------------------------------------------------

@macos_only('"QuartzImpl" implementation')
class QuartzImpl(Screenshotable, MouseDriver, SimpleInputDriver, Touchable, Lifecycle):
    """macOS 平台实现，基于 Quartz 截图 + CGEvent 模拟鼠标输入。

    **截图**：使用 ``CGWindowListCreateImageFromArray`` 按窗口 ID 精确捕获，
    不影响其他窗口，也无需窗口处于前台。

    **输入**：通过 ``CGEventPost`` 向系统 HID 事件流注入鼠标事件。
    PlayCover 内置键鼠映射层会将鼠标事件转译为 iOS 触控事件。
    实现了 :class:`~kotonebot.client.protocol.MouseDriver`（原语操作）和
    :class:`~kotonebot.client.protocol.SimpleInputDriver`（高层 click/swipe）。

    **坐标系**：所有公开方法接受的 x/y 均为**窗口客户区相对坐标**
    （左上角为原点）。内部通过 ``MacOSWindow.get_bounds()`` 自动换算为
    屏幕绝对坐标后再投递事件。
    """

    def __init__(self, device: 'Device', window_query: WindowQuery) -> None:
        _load_deps()
        self._window_session = WindowSession(window_query)
        self.device = device
        self._started = False
        # 记录当前鼠标在屏幕上的绝对坐标，供 button_down/up 使用
        self._cursor_pos: tuple[float, float] = (0.0, 0.0)
        # 记录当前按下的按键，供 move() 判断是否处于拖拽状态
        self._pressed_button: MouseButton | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._started:
            raise RuntimeError('QuartzImpl lifecycle is already started.')
        # 检查辅助功能权限；缺少该权限时 CGEventPost 会被系统静默丢弃。
        # 传入 kAXTrustedCheckOptionPrompt=True 可主动弹出系统授权对话框。
        from ApplicationServices import (
            AXIsProcessTrustedWithOptions, # type: ignore[import]
            kAXTrustedCheckOptionPrompt, # type: ignore[import]
        )
        if not AXIsProcessTrustedWithOptions({ kAXTrustedCheckOptionPrompt: True }):
            raise PermissionError(
                'Accessibility permission is required for mouse event injection. '
                'Please grant access in the dialog that just appeared, '
                'or grant access in: System Settings → Privacy & Security → Accessibility, '
                'then restart the application.'
            )
        self._started = True

    def stop(self) -> None:
        self._started = False

    def _require_started(self) -> None:
        if not self._started:
            raise RuntimeError('QuartzImpl lifecycle is not started.')

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _window(self) -> MacOSWindow:
        w = self._window_session.get_window()
        if not isinstance(w, MacOSWindow):
            raise TypeError(f'Expected MacOSWindow, got {type(w).__name__}')
        return w

    def _content_bounds(self):
        """返回窗口内容区域在屏幕上的绝对边界（去除标题栏，单位：逻辑点）。

        :return: ``(x1, y1, w, h)``，其中 ``(x1, y1)`` 为内容区域左上角屏幕坐标（逻辑点）。
        :raises RuntimeError: 无法获取窗口边界时抛出。
        """
        bounds = self._window().get_bounds()
        if bounds is None:
            raise RuntimeError('Cannot obtain window bounds.')
        tb_pts = _title_bar_height_pts(bounds.w, bounds.h)
        return bounds.x1, bounds.y1 + tb_pts, bounds.w, bounds.h - tb_pts

    def _to_screen(self, x: int, y: int) -> tuple[float, float]:
        """将窗口客户区坐标转换为屏幕绝对坐标（内容区域原点为 (0,0)）。"""
        cx1, cy1, _, _ = self._content_bounds()
        return float(cx1 + x), float(cy1 + y)

    def _post(self, event_type: int, x: float, y: float, button_num: int = 0) -> None:
        """向 HID 事件流投递一个鼠标事件。

        :param event_type: CGEvent 鼠标事件类型常量。
        :param x: 屏幕绝对坐标 X。
        :param y: 屏幕绝对坐标 Y。
        :param button_num: CGMouseButton 编号（0=左 1=右 2=中）。
        """
        from Quartz import kCGHIDEventTap, CGPoint  # type: ignore[import]
        event = CGEventCreateMouseEvent(None, event_type, CGPoint(x, y), button_num)
        CGEventPost(kCGHIDEventTap, event)
        self._cursor_pos = (x, y)

    # ------------------------------------------------------------------
    # Screenshotable
    # ------------------------------------------------------------------

    @property
    def screen_size(self) -> tuple[int, int]:
        """返回内容区域尺寸（逻辑点）。

        与 :meth:`screenshot` 返回图像的像素尺寸不同，此处遵循平台惯例返回逻辑点，
        以便坐标传入 :meth:`click` / :meth:`swipe` 时与 CGEvent 坐标系一致。
        """
        self._require_started()
        _, _, w, h = self._content_bounds()
        return int(w), int(h)

    def detect_orientation(self) -> Literal['portrait', 'landscape'] | None:
        self._require_started()
        try:
            _, _, w, h = self._content_bounds()
        except RuntimeError:
            return None
        return 'landscape' if w > h else 'portrait'

    def screenshot(self) -> MatLike:
        self._require_started()
        window = self._window()
        window_id = window.info.id
        if window_id is None:
            raise RuntimeError('Window ID is not available.')
        if not isinstance(window_id, int):
            raise RuntimeError(
                f'Expected integer CGWindowNumber, '
                f'got {type(window_id).__name__}: {window_id!r}'
            )
        bounds = window.get_bounds()
        if bounds is None:
            raise RuntimeError('Cannot obtain window bounds.')

        # 捕获完整窗口帧（含标题栏）
        frame = _capture_window(window_id)

        # 从图像实际像素宽度与窗口逻辑点宽度的比值推算 DPI 倍数（Retina 通常为 2.0）
        # frame.shape[1] 为像素宽，bounds.w 为逻辑点宽
        pixel_scale = frame.shape[1] / bounds.w if bounds.w > 0 else 1.0

        # 标题栏高度（逻辑点）→ 像素
        tb_pts = _title_bar_height_pts(bounds.w, bounds.h)
        crop_top = int(round(tb_pts * pixel_scale))

        return frame[crop_top:, :, :]

    # ------------------------------------------------------------------
    # MouseDriver — 原语操作
    # ------------------------------------------------------------------

    def move(self, x: int, y: int) -> None:
        """将鼠标移动到窗口坐标 (x, y)。

        若当前有按键处于按下状态则投递拖拽事件，否则投递普通移动事件。
        """
        self._require_started()
        sx, sy = self._to_screen(x, y)
        events = _get_button_events()
        if self._pressed_button is not None:
            _, _, drag_type, btn_num = events[self._pressed_button]
            self._post(drag_type, sx, sy, btn_num)
        else:
            from Quartz import kCGEventMouseMoved  # type: ignore[import]
            self._post(kCGEventMouseMoved, sx, sy, 0)

    def button_down(self, button: MouseButton | None = None) -> None:
        """在当前鼠标位置按下指定按键。

        :param button: 鼠标按键，默认为左键 ``'left'``。
        """
        self._require_started()
        btn = button or 'left'
        down_type, _, _, btn_num = _get_button_events()[btn]
        x, y = self._cursor_pos
        self._post(down_type, x, y, btn_num)
        self._pressed_button = btn

    def button_up(self, button: MouseButton | None = None) -> None:
        """在当前鼠标位置抬起指定按键。

        :param button: 鼠标按键，默认为左键 ``'left'``。
        """
        self._require_started()
        btn = button or 'left'
        _, up_type, _, btn_num = _get_button_events()[btn]
        x, y = self._cursor_pos
        self._post(up_type, x, y, btn_num)
        if self._pressed_button == btn:
            self._pressed_button = None

    def scroll(self, dx: int = 0, dy: int = 0) -> None:
        """在当前鼠标位置滚动。

        :param dx: 水平滚动量（像素），正值向右。
        :param dy: 垂直滚动量（像素），正值向下。
        """
        self._require_started()
        from Quartz import (
            kCGHIDEventTap, # type: ignore[import]
            kCGScrollEventUnitPixel, # type: ignore[import]
        )
        # CGEventCreateScrollWheelEvent(source, units, wheelCount, wheel1, wheel2, ...)
        # wheel1=垂直，wheel2=水平；macOS 中垂直正值为向上，需取反
        event = CGEventCreateScrollWheelEvent(
            None, kCGScrollEventUnitPixel, 2, -dy, dx
        )
        CGEventPost(kCGHIDEventTap, event)

    # ------------------------------------------------------------------
    # SimpleInputDriver — 高层操作（基于 MouseDriver 实现）
    # ------------------------------------------------------------------

    def click(self, x: int, y: int) -> None:
        """在窗口坐标 (x, y) 处执行左键单击。

        等效于：激活窗口 → move → button_down → 短暂等待 → button_up。
        """
        self._require_started()
        self._window().activate()
        time.sleep(0.05)
        self.move(x, y)
        self.button_down('left')
        time.sleep(0.05)
        self.button_up('left')

    def swipe(
        self,
        x1: int, y1: int,
        x2: int, y2: int,
        duration: float | None = None,
    ) -> None:
        """从窗口坐标 (x1, y1) 滑动到 (x2, y2)。

        等效于：激活窗口 → move(start) → button_down →
        按 60fps 插值 move → button_up。

        :param duration: 滑动总时长（秒），默认 0.5 秒。
        """
        self._require_started()
        if duration is None:
            duration = 0.5

        self._window().activate()
        self.move(x1, y1)
        self.button_down('left')

        fps = 60
        steps = max(2, int(duration * fps))
        step_interval = duration / steps

        for i in range(1, steps + 1):
            t = i / steps
            xi = int(x1 + (x2 - x1) * t)
            yi = int(y1 + (y2 - y1) * t)
            self.move(xi, yi)
            time.sleep(step_interval)

        self.button_up('left')
