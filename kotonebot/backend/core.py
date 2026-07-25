import logging
from typing import TYPE_CHECKING, Callable
from typing_extensions import deprecated

import cv2
from cv2.typing import MatLike

from kotonebot.util import cv2_imread
from kotonebot.primitives import RectTuple, Rect, Point
if TYPE_CHECKING:
    from kotonebot.primitives.visual import Image
else:
    from kotonebot.primitives.visual import Image as _PrimitivesImage
    Image = deprecated('Use kotonebot.primitives.Image instead.')(_PrimitivesImage)


# TODO: 这里的其他类应该移动到 primitives 模块下面
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

@deprecated('use coerce')
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

