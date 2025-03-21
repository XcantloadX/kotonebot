
from typing import Protocol

import cv2
import numpy as np
from cv2.typing import MatLike

class PreprocessorProtocol(Protocol):
    """预处理协议。用于 Image 与 Ocr 中的 `preprocessor` 参数。"""
    def process(self, image: MatLike) -> MatLike:
        """
        预处理图像。

        :param image: 输入图像，格式为 BGR。
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

    def process(self, image: MatLike) -> MatLike:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        return mask

    def __repr__(self) -> str:
        return f'HsvColorFilter(for color "{self.name}" with range {self.lower} - {self.upper})'
