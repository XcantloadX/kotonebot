import logging
from functools import cache
from typing import Callable, overload, TYPE_CHECKING

import cv2
from cv2.typing import MatLike

from kotonebot.errors import ResourceFileMissingError
if TYPE_CHECKING:
    from kotonebot.util import Rect

class Ocr:
    def __init__(
        self,
        text: str | Callable[[str], bool],
        *,
        language: str = 'jp',
    ):
        self.text = text
        self.language = language


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
        self.__data: MatLike | None = data
        self.__data_with_alpha: MatLike | None = None

    @cache
    def binary(self) -> 'Image':
        return Image(data=cv2.cvtColor(self.data, cv2.COLOR_BGR2GRAY))

    @property
    def data(self) -> MatLike:
        if self.__data is None:
            if self.path is None:
                raise ValueError('Either path or data must be provided.')
            self.__data = cv2.imread(self.path)
            if self.__data is None:
                raise ResourceFileMissingError(self.path, 'sprite')
            logger.debug(f'Read image "{self.name}" from {self.path}')
        return self.__data
    
    @property
    def data_with_alpha(self) -> MatLike:
        if self.__data_with_alpha is None:
            if self.path is None:
                raise ValueError('Either path or data must be provided.')
            self.__data_with_alpha = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)
            if self.__data_with_alpha is None:
                raise ResourceFileMissingError(self.path, 'sprite with alpha')
            logger.debug(f'Read image "{self.name}" from {self.path}')
        return self.__data_with_alpha
    
    def __repr__(self) -> str:
        if self.path is None:
            return f'<Image: memory>'
        else:
            return f'<Image: "{self.name}" at {self.path}>'


class HintBox(tuple[int, int, int, int]):
    def __new__(
        cls,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        source_resolution: tuple[int, int],
    ):
        w = x2 - x1
        h = y2 - y1
        return super().__new__(cls, [x1, y1, w, h])
    
    def __init__(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        *,
        name: str | None = None,
        description: str | None = None,
        source_resolution: tuple[int, int],
    ):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.name = name
        self.description = description
        self.source_resolution = source_resolution

    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def rect(self) -> 'Rect':
        return self.x1, self.y1, self.width, self.height

class HintPoint(tuple[int, int]):
    def __new__(cls, x: int, y: int):
        return super().__new__(cls, (x, y))
    
    def __init__(self, x: int, y: int, *, name: str | None = None, description: str | None = None):
        self.x = x
        self.y = y
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        return f'HintPoint<"{self.name}" at ({self.x}, {self.y})>'

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    hint_box = HintBox(100, 100, 200, 200, source_resolution=(1920, 1080))
    print(hint_box.rect)
    print(hint_box.width)
    print(hint_box.height)

