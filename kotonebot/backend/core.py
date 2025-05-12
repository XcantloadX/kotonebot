import logging
from functools import cache
from typing import Callable

import cv2
from cv2.typing import MatLike

from kotonebot.util import cv2_imread
from kotonebot.primitives import RectTuple, Rect, Point
from kotonebot.errors import ResourceFileMissingError

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
            self.__data = cv2_imread(self.path)
            if self.__data is None:
                raise ResourceFileMissingError(self.path, 'sprite')
            logger.debug(f'Read image "{self.name}" from {self.path}')
        return self.__data
    
    @property
    def data_with_alpha(self) -> MatLike:
        if self.__data_with_alpha is None:
            if self.path is None:
                raise ValueError('Either path or data must be provided.')
            self.__data_with_alpha = cv2_imread(self.path, cv2.IMREAD_UNCHANGED)
            if self.__data_with_alpha is None:
                raise ResourceFileMissingError(self.path, 'sprite with alpha')
            logger.debug(f'Read image "{self.name}" from {self.path}')
        return self.__data_with_alpha
    
    def __repr__(self) -> str:
        if self.path is None:
            return f'<Image: memory>'
        else:
            return f'<Image: "{self.name}" at {self.path}>'


class HintBox(Rect):
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
        super().__init__(x1, y1, x2 - x1, y2 - y1, name=name)
        self.description = description
        self.source_resolution = source_resolution

    @property
    def width(self) -> int:
        return self.x2 - self.x1
    
    @property
    def height(self) -> int:
        return self.y2 - self.y1
    
    @property
    def rect(self) -> RectTuple:
        return self.x1, self.y1, self.width, self.height

class HintPoint(Point):
    def __init__(self, x: int, y: int, *, name: str | None = None, description: str | None = None):
        super().__init__(x, y, name=name)
        self.description = description

    def __repr__(self) -> str:
        return f'HintPoint<"{self.name}" at ({self.x}, {self.y})>'

def unify_image(image: MatLike | str | Image, transparent: bool = False) -> MatLike:
    if isinstance(image, str):
        if not transparent:
            image = cv2_imread(image)
        else:
            image = cv2_imread(image, cv2.IMREAD_UNCHANGED)
    elif isinstance(image, Image):
        if transparent:
            image = image.data_with_alpha
        else:
            image = image.data
    return image

logger = logging.getLogger(__name__)


if __name__ == '__main__':
    hint_box = HintBox(100, 100, 200, 200, source_resolution=(1920, 1080))
    print(hint_box.rect)
    print(hint_box.width)
    print(hint_box.height)

