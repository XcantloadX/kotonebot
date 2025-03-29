
from typing import Protocol, Literal

import cv2
import numpy as np
from cv2.typing import MatLike

ImageFormat = Literal['bgr', 'hsv']

class PreprocessorProtocol(Protocol):
    """预处理协议。用于 Image 与 Ocr 中的 `preprocessor` 参数。"""
    def process(self, image: MatLike, *, format: ImageFormat = 'bgr') -> MatLike:
        """
        预处理图像。

        :param image: 输入图像。
        :param format: 输入图像的格式，可选值为 'bgr' 或 'hsv'。
        :return: 预处理后的图像，格式不限。
        """
        ...

class HsvColorFilter(PreprocessorProtocol):
    """HSV 颜色过滤器。用于保留指定颜色。"""
    def __init__(
        self,
        lower: tuple[int, int, int],
        upper: tuple[int, int, int],
        *,
        name: str | None = None,
    ):
        self.lower = np.array(lower)
        self.upper = np.array(upper)
        self.name = name

    def process(self, image: MatLike, *, format: ImageFormat = 'bgr') -> MatLike:
        if format == 'bgr':
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        elif format == 'hsv':
            hsv = image
        else:
            raise ValueError(f'Invalid format: {format}')
        mask = cv2.inRange(hsv, self.lower, self.upper)
        return mask

    def __repr__(self) -> str:
        return f'HsvColorFilter(for color "{self.name}" with range {self.lower} - {self.upper})'

class HsvColorRemover(PreprocessorProtocol):
    """去除指定范围内的 HSV 颜色。"""

    def __init__(
        self,
        lower: tuple[int, int, int],
        upper: tuple[int, int, int],
        *,
        name: str | None = None,
    ):
        self.lower = np.array(lower)
        self.upper = np.array(upper)
        self.name = name

    def process(self, image: MatLike, *, format: ImageFormat = 'bgr') -> MatLike:
        if format == 'bgr':
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        elif format == 'hsv':
            hsv = image
        else:
            raise ValueError(f'Invalid format: {format}')
        mask = cv2.inRange(hsv, self.lower, self.upper)
        mask = cv2.bitwise_not(mask)
        result = cv2.bitwise_and(image, image, mask=mask)
        return result

    def __repr__(self) -> str:
        return f'HsvColorRemover(for color "{self.name}" with range {self.lower} - {self.upper})'

class HsvColorsRemover(PreprocessorProtocol):
    """去除多个指定范围内的 HSV 颜色。"""
    def __init__(
        self,
        colors: list[tuple[tuple[int, int, int], tuple[int, int, int]]],
        *,
        name: str | None = None,
    ):
        self.colors = colors
        self.name = name
        self.__preprocessors = [
            HsvColorRemover(color[0], color[1], name=name) for color in colors
        ]

    def process(self, image: MatLike, *, format: ImageFormat = 'bgr') -> MatLike:
        if format == 'bgr':
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        elif format == 'hsv':
            hsv = image
        else:
            raise ValueError(f'Invalid format: {format}')
        
        for p in self.__preprocessors:
            hsv = p.process(hsv, format='hsv')
        return hsv

    def __repr__(self) -> str:
        return f'HsvColorsRemover(for colors {self.colors})'
