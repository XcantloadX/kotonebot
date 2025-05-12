import logging

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

class Template(Image):
    """
    模板图像类。
    """
