"""Maa 后端专用异常定义。"""

from pathlib import Path

from kotonebot.errors import DeviceConnectionError, KotonebotError


class MaaJobFailedError(DeviceConnectionError):
    """Maa 控制器任务执行失败。

    继承自 :class:`~kotonebot.errors.DeviceConnectionError`，
    因此可被设备层的重连重试与错误转译机制统一处理。
    """

    def __init__(self, job_name: str, address: str) -> None:
        """初始化异常。

        :param job_name: 执行失败的 Maa 任务名称，例如 ``"connect"``。
        :param address: 目标设备地址，例如 ``"127.0.0.1:5555"``。
        """
        self.job_name: str = job_name
        """执行失败的 Maa 任务名称。"""
        self.address: str = address
        """目标设备地址。"""
        super().__init__(f'Maa job failed: job="{job_name}" address="{address}".')


class MaaDeviceNotFoundError(DeviceConnectionError):
    """目标地址不在 Maa 已知设备中。

    继承自 :class:`~kotonebot.errors.DeviceConnectionError`，
    因此可被设备层的重连重试与错误转译机制统一处理。
    """

    def __init__(self, address: str) -> None:
        """初始化异常。

        :param address: 未命中的目标设备地址，例如 ``"127.0.0.1:5555"``。
        """
        self.address: str = address
        """未命中的目标设备地址。"""
        super().__init__(
            f'Address "{address}" not found in Maa known devices. '
            'Make sure the emulator is running and discoverable by Maa Toolkit.'
        )


class MaaLibraryNotFoundError(KotonebotError):
    """maafw 安装中缺失 MaaFramework 动态库。"""

    def __init__(self, expected_path: Path) -> None:
        """初始化异常。

        :param expected_path: 期望的动态库完整路径。
        """
        self.expected_path: Path = expected_path
        """期望的动态库完整路径。"""
        super().__init__(
            f'MaaFramework native library not found (expected at "{expected_path}"). '
            'Reinstall the "maafw" package and retry.'
        )


class MaaLibraryLoadError(KotonebotError):
    """MaaFramework 动态库存在但加载失败（常见原因为缺失 VC++ 运行库）。"""

    def __init__(self, bin_dir: Path, detail: str) -> None:
        """初始化异常。

        :param bin_dir: Maa 动态库所在目录。
        :param detail: 底层加载错误详情。
        """
        self.bin_dir: Path = bin_dir
        """Maa 动态库所在目录。"""
        self.detail: str = detail
        """底层加载错误详情。"""
        super().__init__(
            f'Failed to load MaaFramework native libraries from "{bin_dir}" ({detail}). '
            'Make sure the Visual C++ runtime is installed and retry.'
        )
