import logging

from typing import Callable, ParamSpec, TypeVar, overload

import cv2
from cv2.typing import MatLike

class Ocr:
    def __init__(
        self,
        text: str | Callable[[str], bool],
        *,
        language: str = 'jp',
    ):
        self.text = text
        self.language = language


# TODO: 支持透明背景
class Image:
    def __init__(
        self,
        *,
        path: str | None = None,
        name: str | None = 'untitled',
        data: MatLike | None = None,
    ):
        self.path = path
        self.name = name
        self.__data = data
        self.__data_with_alpha: MatLike | None = None

    @property
    def data(self) -> MatLike:
        if self.__data is None:
            if self.path is None:
                raise ValueError('Either path or data must be provided.')
            self.__data = cv2.imread(self.path)
        return self.__data
    
    @property
    def data_with_alpha(self) -> MatLike:
        if self.__data_with_alpha is None:
            if self.path is None:
                raise ValueError('Either path or data must be provided.')
            self.__data_with_alpha = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)
        return self.__data_with_alpha
    
    def __repr__(self) -> str:
        if self.path is None:
            return f'<Image: memory>'
        else:
            return f'<Image: "{self.name}" at {self.path}>'

logger = logging.getLogger(__name__)


@overload
def image(data: str) -> Image:
    """从文件路径创建 Image 对象。"""
    ...
@overload
def image(data: MatLike) -> Image:
    """从 OpenCV 的 MatLike 对象创建 Image 对象。"""
    ...

def image(data: str | MatLike) -> Image:
    if isinstance(data, str):
        return Image(path=data)
    else:
        return Image(data=data)
 
def ocr(text: str | Callable[[str], bool], language: str = 'jp') -> Ocr:
    return Ocr(text, language=language)
