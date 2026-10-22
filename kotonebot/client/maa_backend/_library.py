"""MaaFramework 动态库的按需初始化。"""

import logging
import platform
import threading
from pathlib import Path

from kotonebot.errors import MissingDependencyError

from .errors import MaaLibraryLoadError, MaaLibraryNotFoundError
from ._native_stdout import restore_process_std_handles, start_native_stdout_capture

logger = logging.getLogger(__name__)

_FRAMEWORK_LIBS: dict[str, str] = {
    'windows': 'MaaFramework.dll',
    'darwin': 'libMaaFramework.dylib',
    'linux': 'libMaaFramework.so',
}
"""各平台主库文件名（与 ``maa.library.Library.open`` 一致），仅用于前置校验。"""

_lock = threading.Lock()


def ensure_maa_library() -> Path:
    """确保 MaaFramework 动态库已加载，返回动态库所在目录。

    幂等且线程安全，重复调用直接返回。动态库取自 maafw wheel 自带的 ``bin/``
    目录，随 ``maa`` 包一起安装，调用方无需关心。

    :returns: Maa 动态库所在目录。
    :raises MissingDependencyError: maafw 未安装时抛出。
    :raises MaaLibraryNotFoundError: 动态库缺失时抛出。
    :raises MaaLibraryLoadError: 动态库加载失败时抛出。
    """
    try:
        import maa
    except ImportError as _e:
        raise MissingDependencyError(_e, 'maa') from _e
    bin_dir = Path(maa.__file__).parent / 'bin'
    system = platform.system().lower()
    if system not in _FRAMEWORK_LIBS:
        raise MaaLibraryNotFoundError(bin_dir / f'<unknown-platform:{system}>')
    lib_name = _FRAMEWORK_LIBS[system]
    if not (bin_dir / lib_name).is_file():
        raise MaaLibraryNotFoundError(bin_dir / lib_name)

    from maa.library import Library

    with _lock:
        try:
            start_native_stdout_capture()
            try:
                # Library.open 自身幂等，已 open 时直接返回。
                Library.open(bin_dir)
            finally:
                restore_process_std_handles()
        except OSError as e:
            raise MaaLibraryLoadError(bin_dir, str(e)) from e
    logger.debug('MaaFramework library ready: %s.', bin_dir)
    return bin_dir
