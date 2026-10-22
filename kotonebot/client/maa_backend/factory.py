"""基于 Maa 控制器的设备工厂函数。"""

import logging
from typing import TYPE_CHECKING

from kotonebot.errors import MissingDependencyError

try:
    from maa.controller import AdbController, Win32Controller
    from maa.define import (
        MaaAdbInputMethodEnum,
        MaaAdbScreencapMethodEnum,
        MaaWin32InputMethodEnum,
        MaaWin32ScreencapMethodEnum,
    )
except ImportError as _e:
    raise MissingDependencyError(_e, 'maa') from _e

from kotonebot.client.device import AndroidDevice, WindowsDevice
from kotonebot.interop.window import WindowQuery

if TYPE_CHECKING:
    from adbutils._device import AdbDevice as AdbUtilsDevice

    from kotonebot.client.host.adb_common import AdbTarget

from .adb import MaaAdbAdapter
from .errors import MaaJobFailedError
from .resolve import resolve_adb, resolve_hwnd
from ._library import ensure_maa_library
from ._selection import capture_maa_logs, report_adb_selection, report_win32_selection
from .sync import MaaSyncController
from .win32 import MaaWin32Adapter

logger = logging.getLogger(__name__)


def create_maa_adb(
    target: 'AdbTarget',
    adb_connection: 'AdbUtilsDevice',
    *,
    screencap_methods: MaaAdbScreencapMethodEnum | int | None = None,
    input_methods: MaaAdbInputMethodEnum | int | None = None,
) -> AndroidDevice:
    """基于 Maa AdbController 创建 Android 设备。

    内部自动完成 MaaFramework 动态库初始化，调用方无需预先 ``Library.open``。

    :param target: ADB 连接目标。
    :param adb_connection: 已建好的 adbutils 连接。
    :param screencap_methods: Maa ADB 截图方式位掩码（可按位或），为 None 时使用
        ``resolve_adb`` 从 Toolkit 发现的最优掩码。
    :param input_methods: Maa ADB 输入方式位掩码（可按位或），为 None 时使用
        ``resolve_adb`` 从 Toolkit 发现的最优掩码。
    :returns: 配置好 Maa 截图与触控实现的设备实例。
    :raises MaaJobFailedError: 控制器构造或连接失败时抛出。
    """
    ensure_maa_library()
    params = resolve_adb(target)
    if screencap_methods is None:
        screencap_methods = params.screencap_methods
    if input_methods is None:
        input_methods = params.input_methods
    logger.debug(
        'Creating Maa AdbController: address=%s adb_path=%s.',
        params.address, params.adb_path,
    )
    try:
        controller = AdbController(
            adb_path=params.adb_path,
            address=params.address,
            screencap_methods=screencap_methods,
            input_methods=input_methods,
            config=params.config.model_dump(),
        )
    except RuntimeError as e:
        raise MaaJobFailedError('create_adb_controller', params.address) from e
    # 关闭 Maa 侧截图缩放，坐标换算只留 scaler.py 一处，避免双重 resize。
    if not controller.set_screenshot_use_raw_size(True):
        raise MaaJobFailedError('set_screenshot_use_raw_size', params.address)
    sync = MaaSyncController(controller, address=params.address)
    with capture_maa_logs() as capture:
        sync.connect()
    report_adb_selection(
        capture.text(), address=params.address, input_methods=int(input_methods)
    )
    adapter = MaaAdbAdapter(sync, adb_connection=adb_connection)
    device = AndroidDevice(adb_connection)
    device.setup(screenshot=adapter, touch=adapter, commands=adapter, multitouch=adapter)
    return device


def create_maa_win32(
    query: WindowQuery,
    *,
    screencap_method: MaaWin32ScreencapMethodEnum | int | None = None,
    mouse_method: MaaWin32InputMethodEnum | int | None = None,
    keyboard_method: MaaWin32InputMethodEnum | int | None = None,
) -> WindowsDevice:
    """基于 Maa Win32Controller 创建 Windows 设备。

    不改动 host 旧代码。内部自动完成 MaaFramework 动态库初始化。

    :param query: 窗口查询条件。
    :param screencap_method: Maa Win32 截图方式，为 None 时使用 Maa 默认
        （后台截图掩码，connect 时测速二选一）。
    :param mouse_method: Maa Win32 鼠标输入方式，为 None 时使用 Maa 默认
        （抢占式前台输入）；纯后台操作可传 SendMessage/PostMessage 对应取值。
    :param keyboard_method: Maa Win32 键盘输入方式，为 None 时使用 Maa 默认。
    :returns: 配置好 Maa 截图与鼠标实现的设备实例。
    :raises MaaJobFailedError: 控制器构造或连接失败时抛出。
    """
    ensure_maa_library()
    hwnd = resolve_hwnd(query)
    logger.debug('Creating Maa Win32Controller: hwnd=%d.', hwnd)
    kwargs: dict[str, int] = {}
    if screencap_method is not None:
        kwargs['screencap_method'] = screencap_method
    if mouse_method is not None:
        kwargs['mouse_method'] = mouse_method
    if keyboard_method is not None:
        kwargs['keyboard_method'] = keyboard_method
    try:
        controller = Win32Controller(hwnd, **kwargs)
    except RuntimeError as e:
        raise MaaJobFailedError('create_win32_controller', f'hwnd={hwnd}') from e
    # 关闭 Maa 侧截图缩放，坐标换算只留 scaler.py 一处，避免双重 resize。
    if not controller.set_screenshot_use_raw_size(True):
        raise MaaJobFailedError('set_screenshot_use_raw_size', f'hwnd={hwnd}')
    sync = MaaSyncController(controller, address=f'hwnd={hwnd}')
    with capture_maa_logs() as capture:
        sync.connect()
    report_win32_selection(
        capture.text(),
        hwnd=hwnd,
        mouse_method=None if mouse_method is None else int(mouse_method),
        keyboard_method=None if keyboard_method is None else int(keyboard_method),
    )
    adapter = MaaWin32Adapter(sync, hwnd)
    device = WindowsDevice()
    device.setup(screenshot=adapter, touch=adapter)
    return device
