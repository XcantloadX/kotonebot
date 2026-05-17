"""原生程序管理的抽象接口。

本模块定义了管理「原生程序」所需的两个抽象基类：

- :class:`NativeApp` — 代表一个具体的可执行应用，提供启动、退出、状态检查、
  创建 Device 等操作。

- :class:`NativeAppManager` — 负责发现和枚举某个平台下已安装的应用。

与 ``client/host/`` 体系的区别
---------------------------------
``host/`` 体系（Host + Instance）是为**模拟器多开**场景设计的：
一个 Instance 代表一个 VM 容器，容器内跑的是通用 Android 环境，
调用方再决定在容器内启动哪个 App。

本模块面向的是**原生程序**场景：没有"容器"这一层，
应用本身就是可直接启动的进程。适用案例包括：

- macOS 上通过 PlayCover 运行的 iOS 应用
- Windows 原生游戏（直接跑 .exe）
- Steam 游戏

典型用法::

    # 发现并启动应用
    app = Playcover.find('jp.co.bandainamcoent.BNEI0421')
    if app and not app.running():
        app.launch()
    app.wait_available(timeout=60)
    device = app.create_device()
"""

from abc import ABC, abstractmethod

from kotonebot import logging
from kotonebot.client.device import Device
from kotonebot.util import Countdown, Interval

logger = logging.getLogger(__name__)


class NativeApp(ABC):
    """原生程序实例的抽象基类。

    代表一个可被程序管理的具体应用。子类需实现生命周期方法
    （:meth:`installed`、:meth:`running`、:meth:`launch`、:meth:`terminate`）
    以及 :meth:`create_device`。

    :param app_id: 应用的唯一标识符，由具体平台定义
                   （例如 PlayCover 使用 bundle ID，Steam 使用 AppID）。
    :param name:   应用的显示名称。
    """

    def __init__(self, app_id: str, name: str) -> None:
        self.app_id = app_id
        """应用的唯一标识符。"""
        self.name = name
        """应用的显示名称。"""

    @abstractmethod
    def installed(self) -> bool:
        """检查此应用是否已安装在本机。

        :return: 已安装返回 ``True``，否则返回 ``False``。
        """
        ...

    @abstractmethod
    def running(self) -> bool:
        """检查此应用当前是否正在运行。

        :return: 正在运行返回 ``True``，否则返回 ``False``。
        """
        ...

    @abstractmethod
    def launch(self) -> None:
        """启动此应用。

        若应用已在运行，则应静默忽略（不抛出异常）。
        """
        ...

    @abstractmethod
    def terminate(self) -> None:
        """退出此应用。

        若应用未在运行，则应静默忽略（不抛出异常）。
        """
        ...

    def wait_available(self, timeout: float = 60) -> None:
        """等待应用进入可交互状态。

        默认实现为轮询 :meth:`running`，每秒检查一次。
        子类可覆盖此方法以实现更精确的等待策略，
        例如等待特定窗口出现，而非仅等待进程存在。

        :param timeout: 超时秒数，默认 60 秒。
        :raises TimeoutError: 超过 ``timeout`` 秒后应用仍未就绪时抛出。
        """
        logger.info(
            'Waiting for app "%s" (%s) to become available (timeout=%.0fs)...',
            self.name, self.app_id, timeout,
        )
        cd = Countdown(timeout)
        it = Interval(1)
        while not cd.expired():
            if self.running():
                logger.info('App "%s" (%s) is now available.', self.name, self.app_id)
                return
            it.wait()
        raise TimeoutError(
            f'App "{self.name}" ({self.app_id}) did not become available '
            f'within {timeout}s.'
        )

    @abstractmethod
    def create_device(self) -> Device:
        """创建并返回已连接到此应用的 :class:`~kotonebot.client.device.Device` 实例。

        调用前应确保应用已在运行（例如先调用 :meth:`launch` 和 :meth:`wait_available`）。

        :return: 配置好截图与触控实现的 Device 对象。
        """
        ...

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(app_id="{self.app_id}", name="{self.name}")'


class NativeAppManager(ABC):
    """原生程序管理器的抽象基类。

    负责发现和枚举某个平台下已安装的应用。
    子类应对应一个具体的运行平台，例如 :class:`~kotonebot.client.playcover.Playcover`。

    ``NativeAppManager`` 与 ``NativeApp`` 的分工：

    - **Manager** — 回答「有哪些可用的应用」（枚举 / 查找）
    - **NativeApp** — 回答「如何操作某个应用」（启动 / 退出 / 连接）
    """

    @staticmethod
    @abstractmethod
    def platform_installed() -> bool:
        """检查运行平台本身是否已安装。

        区别于 :meth:`NativeApp.installed`（检查某个具体应用是否安装），
        此方法检查的是托管这些应用的平台程序是否存在。

        示例：

        - PlayCover → 检查 ``PlayCover.app`` 是否存在
        - Steam → 检查 ``Steam.app`` / ``Steam.exe`` 是否存在

        :return: 平台已安装返回 ``True``，否则返回 ``False``。
        """
        ...

    @staticmethod
    @abstractmethod
    def apps() -> 'list[NativeApp]':
        """枚举此平台下所有已安装的应用。

        :return: 已安装应用的列表；若平台未安装或无应用，则返回空列表。
        """
        ...

    @staticmethod
    @abstractmethod
    def find(app_id: str) -> 'NativeApp | None':
        """通过唯一标识查找应用。

        :param app_id: 应用的唯一标识（bundle ID / AppID / 路径等，
                       由具体子类定义其含义）。
        :return: 找到则返回对应的 :class:`NativeApp` 实例，否则返回 ``None``。
        """
        ...
