import logging
import warnings
from functools import cache

import cv2
from cv2.typing import MatLike

from .geometry import Size
from kotonebot.util import cv2_imread

logger = logging.getLogger(__name__)

class Image:
    """
    图像类。
    """
    def __init__(
        self,
        pixels: MatLike | None = None,
        file_path: str | None = None,
        lazy_load: bool = False,
        name: str | None = None,
        description: str | None = None
    ):
        """
        从内存数据或图像文件创建图像类。
        
        :param pixels: 图像数据。格式必须为 BGR。
        :param file_path: 图像文件路径。
        :param lazy_load: 是否延迟加载图像数据。
            若为 False，立即载入，否则仅当访问图像数据时才载入。仅当从文件创建图像类时生效。
        :param name: 图像名称。
        :param description: 图像描述。
        """
        self.name: str | None = name
        """图像名称。"""
        self.description: str | None = description
        """图像描述。"""
        self.file_path: str | None = file_path
        """图像的文件路径。"""
        self.__pixels: MatLike | None = None
        # 立即加载
        if not lazy_load and self.file_path:
            _ = self.pixels
        # 传入像素数据而不是文件
        if pixels is not None:
            self.__pixels = pixels

    @property
    def pixels(self) -> MatLike:
        """图像的像素数据。"""
        if self.__pixels is None:
            if not self.file_path:
                raise ValueError('Either pixels or file_path must be provided.')
            logger.debug('Loading image "%s" from %s...', self.name or '(unnamed)', self.file_path)
            self.__pixels = cv2_imread(self.file_path)
        return self.__pixels

    @property
    def size(self) -> Size:
        return Size(self.pixels.shape[1], self.pixels.shape[0])

    # Compatibility with older API (deprecated)
    def __compat_warn(self, name: str) -> None:
        warnings.warn(
            f'`Image.{name}` is deprecated — use `kotonebot.primitives.Image` API instead.',
            DeprecationWarning,
            stacklevel=3,
        )

    @property
    def path(self) -> str | None:
        """Deprecated alias for `file_path`."""
        self.__compat_warn('path')
        return self.file_path

    @path.setter
    def path(self, value: str | None) -> None:
        self.__compat_warn('path')
        self.file_path = value

    @property
    def data(self) -> MatLike:
        """Deprecated alias for `pixels`."""
        self.__compat_warn('data')
        return self.pixels

    @property
    def data_with_alpha(self) -> MatLike:
        """Deprecated: return image including alpha channel when available."""
        self.__compat_warn('data_with_alpha')
        # If current pixels already contain alpha, return them
        try:
            if self.__pixels is not None and getattr(self.__pixels, 'shape', None) and len(self.__pixels.shape) >= 3 and self.__pixels.shape[2] == 4:
                return self.__pixels
        except Exception:
            pass
        if not self.file_path:
            raise ValueError('Either pixels or file_path must be provided.')
        arr = cv2_imread(self.file_path, cv2.IMREAD_UNCHANGED)
        return arr

    @cache
    def binary(self) -> 'Image':
        """Deprecated: return a grayscale copy of the image."""
        self.__compat_warn('binary')
        gray = cv2.cvtColor(self.pixels, cv2.COLOR_BGR2GRAY)
        return Image(pixels=gray, name=self.name)

    def __repr__(self) -> str:
        # Keep representation similar to the old API (not itself deprecated)
        if self.file_path is None:
            return '<Image: memory>'
        else:
            return f'<Image: "{self.name or "untitled"}" at {self.file_path}>'

class Template(Image):
    """
    模板图像类。
    """
