from typing import Generic, TypeVar, TypeGuard, overload

T = TypeVar('T')

class Vector2D(Generic[T]):
    """2D 坐标类"""
    def __init__(self, x: T, y: T, *, name: str | None = None):
        self.x = x
        self.y = y
        self.name: str | None = name
        """坐标的名称。"""

    def __getitem__(self, item: int):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        else:
            raise IndexError

    def __repr__(self) -> str:
        return f'Point<"{self.name}" at ({self.x}, {self.y})>'

    def __str__(self) -> str:
        return f'({self.x}, {self.y})'


class Vector3D(Generic[T]):
    """三元组类。"""
    def __init__(self, x: T, y: T, z: T, *, name: str | None = None):
        self.x = x
        self.y = y
        self.z = z
        self.name: str | None = name
        """坐标的名称。"""

    def __getitem__(self, item: int):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        elif item == 2:
            return self.z
        else:
            raise IndexError

    @property
    def xyz(self) -> tuple[T, T, T]:
        """
        三元组 (x, y, z)。OpenCV 格式的坐标。
        """
        return self.x, self.y, self.z

    @property
    def xy(self) -> tuple[T, T]:
        """
        二元组 (x, y)。OpenCV 格式的坐标。
        """
        return self.x, self.y

class Vector4D(Generic[T]):
    """四元组类。"""
    def __init__(self, x: T, y: T, z: T, w: T, *, name: str | None = None):
        self.x = x
        self.y = y
        self.z = z
        self.w = w
        self.name: str | None = name
        """坐标的名称。"""

    def __getitem__(self, item: int):
        if item == 0:
            return self.x
        elif item == 1:
            return self.y
        elif item == 2:
            return self.z
        elif item == 3:
            return self.w
        else:
            raise IndexError

Size = Vector2D[int]
"""尺寸。相当于 Vector2D[int]"""
RectTuple = tuple[int, int, int, int]
"""矩形。(x, y, w, h)"""
PointTuple = tuple[int, int]
"""点。(x, y)"""

class Point(Vector2D[int]):
    """点。"""
    
    @property
    def xy(self) -> PointTuple:
        """
        二元组 (x, y)。OpenCV 格式的坐标。
        """
        return self.x, self.y
    
    def offset(self, dx: int, dy: int) -> 'Point':
        """
        偏移坐标。
        
        :param dx: 偏移量。
        :param dy: 偏移量。
        :return: 偏移后的坐标。
        """
        return Point(self.x + dx, self.y + dy, name=self.name)
    
    def __add__(self, other: 'Point | PointTuple') -> 'Point':
        """
        相加。
        
        :param other: 另一个 Point 对象或二元组 (x: int, y: int)。
        :return: 相加后的点。
        """
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y, name=self.name)
        else:
            return Point(self.x + other[0], self.y + other[1], name=self.name)
        
    def __sub__(self, other: 'Point | PointTuple') -> 'Point':
        """
        相减。
        
        :param other: 另一个 Point 对象或二元组 (x: int, y: int)。
        :return: 相减后的点。
        """
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y, name=self.name)
        else:
            return Point(self.x - other[0], self.y - other[1], name=self.name)

class Rect:
    """
    矩形类。
    """
    def __init__(
        self,
        x: int | None = None,
        y: int | None = None,
        w: int | None = None,
        h: int | None = None,
        *,
        xywh: RectTuple | None = None,
        name: str | None = None,
    ):
        """
        从给定的坐标信息创建矩形。
        
        参数 `x`, `y`, `w`, `h` 和 `xywh` 必须至少指定一组。
        
        :param x: 矩形左上角的 X 坐标。
        :param y: 矩形左上角的 Y 坐标。
        :param w: 矩形的宽度。
        :param h: 矩形的高度。
        :param xywh: 四元组 (x, y, w, h)。
        :param name: 矩形的名称。
        :raises ValueError: 提供的坐标参数不完整时抛出。
        """
        if xywh is not None:
            x, y, w, h = xywh
        elif (
            x is not None and
            y is not None and
            w is not None and
            h is not None
        ):
            pass
        else:
            raise ValueError('Either xywh or x, y, w, h must be provided.')
        
        self.x1 = x
        """矩形左上角的 X 坐标。"""
        self.y1 = y
        """矩形左上角的 Y 坐标。"""
        self.w = w
        """矩形的宽度。"""
        self.h = h
        """矩形的高度。"""
        self.name: str | None = name
        """矩形的名称。"""

    @classmethod
    def from_xyxy(cls, x1: int, y1: int, x2: int, y2: int) -> 'Rect':
        """
        从 (x1, y1, x2, y2) 创建矩形。
        :return: 创建结果。
        """
        return cls(x1, y1, x2 - x1, y2 - y1)

    @property
    def x2(self) -> int:
        """矩形右下角的 X 坐标。"""
        return self.x1 + self.w

    @x2.setter
    def x2(self, value: int):
        self.w = value - self.x1

    @property
    def y2(self) -> int:
        """矩形右下角的 Y 坐标。"""
        return self.y1 + self.h

    @y2.setter
    def y2(self, value: int):
        self.h = value - self.y1

    @property
    def xywh(self) -> RectTuple:
        """
        四元组 (x1, y1, w, h)。OpenCV 格式的坐标。
        """
        return self.x1, self.y1, self.w, self.h

    @property
    def xyxy(self) -> RectTuple:
        """
        四元组 (x1, y1, x2, y2)。
        """
        return self.x1, self.y1, self.x2, self.y2

    @property
    def top_left(self) -> Point:
        """
        矩形的左上角点。
        """
        if self.name:
            name = "Left-top of rect "+ self.name
        else:
            name = None
        return Point(self.x1, self.y1, name=name)
    
    @property
    def bottom_right(self) -> Point:
        """
        矩形的右下角点。
        """
        if self.name:
            name = "Right-bottom of rect "+ self.name
        else:
            name = None
        return Point(self.x2, self.y2, name=name)
    
    @property
    def left_bottom(self) -> Point:
        """
        矩形的左下角点。
        """
        if self.name:
            name = "Left-bottom of rect "+ self.name
        else:
            name = None
        return Point(self.x1, self.y2, name=name)
    
    @property
    def right_top(self) -> Point:
        """
        矩形的右上角点。
        """
        if self.name:
            name = "Right-top of rect "+ self.name
        else:
            name = None
        return Point(self.x2, self.y1, name=name)
    
    @property
    def center(self) -> Point:
        """
        矩形的中心点。
        """
        if self.name:
            name = "Center of rect "+ self.name
        else:
            name = None
        return Point(self.x1 + self.w // 2, self.y1 + self.h // 2, name=name)

    def __repr__(self) -> str:
        return f'Rect<"{self.name}" at (x={self.x1}, y={self.y1}, w={self.w}, h={self.h})>'

    def __str__(self) -> str:
        return f'(x={self.x1}, y={self.y1}, w={self.w}, h={self.h})'


def is_point(obj: object) -> TypeGuard[Point]:
    return isinstance(obj, Point)

def is_rect(obj: object) -> TypeGuard[Rect]:
    return isinstance(obj, Rect)
