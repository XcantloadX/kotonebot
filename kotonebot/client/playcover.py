"""PlayCover 原生程序管理。

PlayCover（https://playcover.io ）可在 Apple Silicon Mac 上原生运行 iOS/iPadOS 应用。
每个被 PlayCover 管理的 iOS 应用以独立的 macOS 进程运行，拥有标准的 macOS 窗口，
因此可通过 Quartz API 截图、CGEvent 模拟触控输入。

本模块提供：

- :class:`PlaycoverApp` — 单个 iOS 应用实例，实现 :class:`~kotonebot.client.native_app.NativeApp`
  接口，支持启动、退出、状态检查及创建 :class:`~kotonebot.client.device.Device`。

- :class:`Playcover` — PlayCover 平台管理器，实现
  :class:`~kotonebot.client.native_app.NativeAppManager` 接口，
  负责枚举和查找已安装的 iOS 应用。

典型用法::

    from kotonebot.client.playcover import Playcover

    # 列出所有已安装的 iOS 应用
    for app in Playcover.apps():
        print(app.bundle_id, app.name)

    # 通过 bundle ID 查找并启动
    app = Playcover.find('jp.co.bandainamcoent.BNEI0421')
    if app:
        app.launch()
        app.wait_available(timeout=60)
        device = app.create_device()
"""

import os
import plistlib
import subprocess
from typing import Any


from kotonebot import logging
from kotonebot.client.device import Device, MacOSDevice
from kotonebot.client.native_app import NativeApp, NativeAppManager
from kotonebot.interop.window import MacOSNativeQuery, WindowQuery, WindowSession
from kotonebot.interop.window.macos import MacOSWindow
from kotonebot.util import Countdown, Interval

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PlayCover 应用库路径
# ---------------------------------------------------------------------------

# PlayCover 将已安装的 .app bundle 以 <BundleID>.app 的形式
# 直接存放于此目录的第一层。
# 示例：.../Applications/jp.co.bandainamcoent.BNEI0421.app
_APP_LIBRARY = os.path.expanduser(
    '~/Library/Containers/io.playcover.PlayCover/Applications'
)

# PlayCover.app 的常见安装位置（按优先级排列）
_PLAYCOVER_APP_PATHS = [
    '/Applications/PlayCover.app',
    os.path.expanduser('~/Applications/PlayCover.app'),
]


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _read_bundle_info(app_bundle: str) -> 'tuple[str, str] | None':
    """从 .app bundle 的 Info.plist 中读取 bundle ID 与显示名称。

    :param app_bundle: .app bundle 的完整路径。
    :return: ``(bundle_id, display_name)`` 元组；读取失败时返回 ``None``。
    """
    plist_path = os.path.join(app_bundle, 'Info.plist')
    if not os.path.isfile(plist_path):
        return None
    try:
        with open(plist_path, 'rb') as f:
            plist: dict[str, Any] = plistlib.load(f)
        bundle_id: str = plist.get('CFBundleIdentifier', '')
        if not bundle_id:
            return None
        display_name: str = (
            plist.get('CFBundleDisplayName')
            or plist.get('CFBundleName')
            or os.path.splitext(os.path.basename(app_bundle))[0]
        )
        return bundle_id, display_name
    except Exception as e:
        logger.debug('Failed to read Info.plist at %s: %s', app_bundle, e)
        return None


def _scan_app_library() -> 'list[tuple[str, str, str]]':
    """扫描 PlayCover 应用库，返回所有已安装应用的信息。

    :return: ``[(bundle_id, display_name, app_path), ...]`` 列表。
    """
    results: list[tuple[str, str, str]] = []
    if not os.path.isdir(_APP_LIBRARY):
        return results
    try:
        for entry in os.scandir(_APP_LIBRARY):
            if not (entry.is_dir() and entry.name.endswith('.app')):
                continue
            info = _read_bundle_info(entry.path)
            if info is None:
                logger.debug('Skipping bundle without valid Info.plist: %s', entry.path)
                continue
            bundle_id, display_name = info
            results.append((bundle_id, display_name, entry.path))
    except (PermissionError, FileNotFoundError) as e:
        logger.warning('Cannot scan PlayCover app library at %s: %s', _APP_LIBRARY, e)
    return results


# ---------------------------------------------------------------------------
# PlaycoverApp
# ---------------------------------------------------------------------------

class PlaycoverApp(NativeApp):
    """PlayCover 管理的单个 iOS 应用实例。

    :param bundle_id:    iOS 应用的 bundle ID（例如 ``jp.co.bandainamcoent.BNEI0421``），
                         同时作为 :attr:`~NativeApp.app_id`。
    :param name:         应用的显示名称。
    :param app_path:     .app bundle 在本机的完整路径。
    :param window_query: 用于定位应用窗口的查询条件。若不传入，则自动根据
                         ``bundle_id`` 生成。
    """

    def __init__(
        self,
        bundle_id: str,
        name: str,
        app_path: str,
        window_query: WindowQuery | None = None,
    ) -> None:
        super().__init__(app_id=bundle_id, name=name)
        self.app_path = app_path
        """应用 .app bundle 在本机的完整路径。"""

        # 默认以 bundle ID 精确匹配窗口，避免与同名的其他程序产生歧义
        self._window_query: WindowQuery = window_query or WindowQuery(
            native=MacOSNativeQuery(bundle_id=bundle_id),
            visible_only=True,
        )

    @property
    def bundle_id(self) -> str:
        """iOS bundle ID，与 :attr:`~NativeApp.app_id` 相同。"""
        return self.app_id

    # ------------------------------------------------------------------
    # NativeApp 实现
    # ------------------------------------------------------------------

    def installed(self) -> bool:
        """检查 .app bundle 是否存在于 PlayCover 应用库中。"""
        return os.path.isdir(self.app_path)

    def running(self) -> bool:
        """检查应用进程是否正在运行且窗口可见。

        需同时满足：通过 ``NSRunningApplication`` API 检测到进程，
        以及能通过 :attr:`_window_query` 找到对应窗口。
        """
        from AppKit import NSRunningApplication  # type: ignore[import]
        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
            self.bundle_id
        )
        if len(apps) == 0:
            return False
        from kotonebot.interop.window import WindowManager, WindowNotFoundError
        try:
            return WindowManager.default().find_one(self._window_query) is not None
        except (WindowNotFoundError, Exception):
            return False

    def launch(self) -> None:
        """启动应用。若应用已在运行，则静默忽略。"""
        if self.running():
            logger.warning('PlayCover app %s is already running.', self.bundle_id)
            return
        logger.info('Launching PlayCover app "%s" (%s)...', self.name, self.bundle_id)
        # 优先通过 .app bundle 路径启动，以确保启动的是 PlayCover 管理的版本
        if os.path.isdir(self.app_path):
            subprocess.Popen(['open', self.app_path])
        else:
            subprocess.Popen(['open', '-b', self.bundle_id])

    def terminate(self) -> None:
        """退出应用。若应用未在运行，则静默忽略。"""
        if not self.running():
            logger.warning('PlayCover app %s is not running.', self.bundle_id)
            return
        logger.info('Terminating PlayCover app "%s" (%s)...', self.name, self.bundle_id)
        from AppKit import NSRunningApplication  # type: ignore[import]
        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(
            self.bundle_id
        )
        for app in apps:
            app.terminate()

    def wait_available(self, timeout: float = 60) -> None:
        """等待应用窗口出现后再返回。

        :param timeout: 超时秒数，默认 60 秒。
        :raises TimeoutError: 超过 ``timeout`` 秒后窗口仍未出现时抛出。
        """
        from kotonebot.interop.window import WindowManager, WindowNotFoundError

        logger.info(
            'Waiting for PlayCover app "%s" (%s) window (timeout=%.0fs)...',
            self.name, self.bundle_id, timeout,
        )
        cd = Countdown(timeout)
        it = Interval(1)
        manager = WindowManager.default()

        while not cd.expired():
            try:
                if manager.find_one(self._window_query) is not None:
                    logger.info('PlayCover app "%s" (%s) window is ready.', self.name, self.bundle_id)
                    return
            except (WindowNotFoundError, Exception):
                pass
            it.wait()

        raise TimeoutError(
            f'PlayCover app "{self.name}" ({self.bundle_id}) window '
            f'did not appear within {timeout}s.'
        )

    def create_device(self) -> Device:
        """创建并返回连接到此应用的 :class:`~kotonebot.client.device.Device`。

        使用 :mod:`~kotonebot.client.implements.macos` 实现截图（Quartz）
        和触控输入（CGEvent）。

        :return: 配置好截图与触控实现的 :class:`MacOSDevice` 实例。
        :raises RuntimeError: 若无法初始化 macOS 实现时抛出。
        """
        from kotonebot.client.implements.macos import QuartzImpl

        device = MacOSDevice()
        impl = QuartzImpl(device=device, window_query=self._window_query)
        device.setup(screenshot=impl, touch=impl)
        return device

    def __repr__(self) -> str:
        return (
            f'PlaycoverApp('
            f'bundle_id="{self.bundle_id}", '
            f'name="{self.name}", '
            f'app_path="{self.app_path}")'
        )


# ---------------------------------------------------------------------------
# Playcover（平台管理器）
# ---------------------------------------------------------------------------

class Playcover(NativeAppManager):
    """PlayCover 平台管理器。

    提供枚举、查找 PlayCover 已安装 iOS 应用的静态方法。
    不需要实例化，所有方法均为静态方法。

    示例::

        # 检查 PlayCover 是否安装
        if not Playcover.platform_installed():
            raise RuntimeError('PlayCover is not installed.')

        # 列出所有已安装的应用
        for app in Playcover.apps():
            print(f'{app.bundle_id}: {app.name}')

        # 通过 bundle ID 查找
        app = Playcover.find('jp.co.bandainamcoent.BNEI0421')
    """

    @staticmethod
    def platform_installed() -> bool:
        """检查 PlayCover.app 是否已安装在本机。

        依次检查 ``/Applications/PlayCover.app`` 和
        ``~/Applications/PlayCover.app``。

        :return: PlayCover 已安装返回 ``True``，否则返回 ``False``。
        """
        return any(os.path.isdir(p) for p in _PLAYCOVER_APP_PATHS)

    @staticmethod
    def apps() -> list[PlaycoverApp]:
        """枚举 PlayCover 应用库中所有已安装的 iOS 应用。

        扫描 ``~/Library/Containers/io.playcover.PlayCover/Applications/``
        目录，读取每个 .app bundle 的 ``Info.plist`` 以获取 bundle ID 和名称。

        :return: 已安装应用的列表；若应用库不存在或为空则返回空列表。
        """
        result: list[PlaycoverApp] = []
        for bundle_id, display_name, app_path in _scan_app_library():
            app = PlaycoverApp(
                bundle_id=bundle_id,
                name=display_name,
                app_path=app_path,
            )
            logger.debug('Found PlayCover app: %s', repr(app))
            result.append(app)
        return result

    @staticmethod
    def find(app_id: str) -> PlaycoverApp | None:
        """通过 bundle ID 查找已安装的应用。

        :param app_id: iOS 应用的 bundle ID
                       （例如 ``jp.co.bandainamcoent.BNEI0421``）。
        :return: 找到则返回对应的 :class:`PlaycoverApp`，否则返回 ``None``。
        """
        for app in Playcover.apps():
            if app.bundle_id == app_id:
                return app
        return None


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    )
    print('platform_installed:', Playcover.platform_installed())
    apps = Playcover.apps()
    print(f'Installed apps ({len(apps)}):')
    for a in apps:
        print(' ', a)
