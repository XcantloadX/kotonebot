"""
# 几何基础模块 (geometry)

此模块提供了用于处理几何图形和坐标系统的基础类，包括点、向量、矩形等几何对象的表示和操作。

## 主要功能

- **坐标系统**：提供二维、三维、四维坐标的表示
- **点操作**：支持整数和浮点数坐标点的各种运算
- **矩形操作**：提供矩形的创建、变换、相交检测等功能
- **向量运算**：支持向量的加减乘除、距离计算、单位化等操作
- **类型安全**：使用泛型和类型守卫确保类型安全

## 核心类

- `Vector2D` - 二维向量，支持泛型
- `Vector3D` - 三维向量，适用于颜色和空间坐标
- `Vector4D` - 四维向量，适用于 RGBA 等场景
- `Point` - 整数坐标点，适用于像素定位
- `PointF` - 浮点数坐标点，适用于精确计算
- `Rect` - 矩形类，提供丰富的几何操作

## 使用示例

```python
# 坐标点操作
p1 = Point(100, 200, name="起始点")
p2 = PointF(150.5, 250.8)
distance = p1.distance_to(p2)

# 矩形操作
rect = Rect(10, 20, 100, 50, name="按钮区域")
center = rect.center
enlarged = rect.inflate(5, 5)

# 向量运算
v1 = Vector2D(10, 20)
v2 = Vector2D(5, 8)
result = v1 + v2
```

## 注意事项

- 所有坐标系统遵循屏幕坐标系，原点在左上角
- 矩形操作使用半开区间规则：[x1, x2) x [y1, y2)
- 点和向量的运算会根据输入类型自动选择返回类型
"""

import math
from typing import Generic, TypeVar, TypeGuard, overload, Union

T = TypeVar('T')

class Vector2D(Generic[T]):
    """
    ## Vector2D
    表示一个二维向量。此类支持泛型，可用于表示不同类型的坐标（如整数、浮点数等）。

    ### 例
    ```python
    # 创建二维坐标
    v = Vector2D(10, 20, name="位置")
    print(v.x, v.y)  # 10, 20
    
    # 使用索引访问
    print(v[0], v[1])  # 10, 20
    
    # 坐标计算
    v2 = Vector2D(5, 8)
    print(f"坐标距离: {math.sqrt((v.x - v2.x)**2 + (v.y - v2.y)**2):.2f}")
    
    # 支持命名坐标
    center = Vector2D(640, 360, name="屏幕中心")
    print(center)  # Point<"屏幕中心" at (640, 360)>
    ```
    """
    __slots__ = ('x', 'y', 'name')
    
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

    def __iter__(self):
        yield self.x
        yield self.y

    def as_tuple(self) -> tuple[T, T]:
        """Return coordinates as a tuple of ints: (x, y)."""
        return self.x, self.y

    def __repr__(self) -> str:
        return f'Point<"{self.name}" at ({self.x}, {self.y})>'

    def __str__(self) -> str:
        return f'({self.x}, {self.y})'


class Vector3D(Generic[T]):
    """
    ## Vector3D
    表示一个三维向量。

    ### 例
    ```python
    # 创建三维坐标
    v3 = Vector3D(100, 200, 50, name="3D点")
    print(v3.x, v3.y, v3.z)  # 100, 200, 50
    
    # 使用索引访问
    print(v3[0], v3[1], v3[2])  # 100, 200, 50
    
    # 解构
    x, y, z = v3.xyz  # (100, 200, 50)
    x, y = v3.xy    # (100, 200)
    
    # 颜色值应用
    rgb = Vector3D(255, 128, 64, name="颜色")
    print(f"RGB: {rgb.rgb if hasattr(v3, 'rgb') else '未定义'}")
    ```
    """
    __slots__ = ('x', 'y', 'z', 'name')
    
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

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def as_tuple(self) -> tuple[T, T, T]:
        """Return coordinates as a tuple of ints: (x, y, z)."""
        return self.x, self.y, self.z

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
    """
    ## Vector4D
    此类用于表示四维坐标或向量，通常用于颜色空间（如RGBA）等场景。

    ### 例
    ```python
    # 创建四维坐标
    v4 = Vector4D(100, 200, 150, 255, name="颜色值")
    print(f"RGBA: {v4.x}, {v4.y}, {v4.z}, {v4.w}")  # 100, 200, 150, 255
    
    # 使用索引访问
    print(v4[0], v4[1], v4[2], v4[3])  # 100, 200, 150, 255
    
    # 在颜色空间中使用
    color = Vector4D(255, 0, 0, 128, name="半透明红色")
    print(f"颜色: {color}")
    
    # 四维向量运算
    v4_2 = Vector4D(50, 50, 50, 100)
    # 注意：Vector4D 未定义运算，但可用于数据存储
    ```
    """
    __slots__ = ('x', 'y', 'z', 'w', 'name')
    
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

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
        yield self.w

    def as_tuple(self) -> tuple[T, T, T, T]:
        """Return coordinates as a tuple of ints: (x, y, z, w)."""
        return self.x, self.y, self.z, self.w

RectTuple = tuple[int, int, int, int]
"""矩形。(x, y, w, h)"""
PointTuple = tuple[int, int]
"""点。(x, y)"""
PointFTuple = tuple[float, float]
"""浮点数点。(x, y)"""
Size = Vector2D[int]
"""尺寸。相当于 Vector2D[int]"""
SizeTuple = tuple[int, int]
"""尺寸。(width, height)"""
SizeLike = Union[Size, SizeTuple]
"""尺寸类型，可以是 Size 对象或尺寸元组。"""


Number = TypeVar('Number', int, float)
"""数字类型，可以是整数或浮点数。"""
NumberTuple2D = tuple[Number, Number]
class _BasePoint(Vector2D[Number]):
    __slots__ = (*Vector2D.__slots__,)
    
    @property
    def xy(self) -> NumberTuple2D:
        """
        二元组 (x, y)。

        :return: 包含 x 和 y 坐标的元组。
        """
        return self.x, self.y

    @property
    def length(self) -> float:
        """
        将点视为从原点出发的向量，其长度（模）。

        :return: 向量长度。
        """
        return math.sqrt(self.x**2 + self.y**2)

    def distance_to(self, other: 'AnyPoint | AnyPointTuple') -> float:
        """
        计算到另一个点的距离。
        
        :param other: 另一个点或元组。
        :return: 距离。
        """
        return math.sqrt((self.x - other[0])**2 + (self.y - other[1])**2)

    def __eq__(self, value: object) -> bool:
        """
        比较两个点是否相等。
        
        :param value: 另一个点。
        :return: 如果坐标相等则返回 True，否则返回 False。
        """
        if isinstance(value, _BasePoint):
            return self.x == value.x and self.y == value.y
        return False

    def __lt__(self, other: 'AnyPoint | AnyPointTuple') -> bool:
        """
        小于比较，按 (x, y) 的字典序进行比较。
        支持 `Point` / `PointF` 或长度为2的元组/列表。
        """
        if is_any_point(other):
            ox, oy = other.x, other.y
        elif isinstance(other, tuple) and len(other) == 2:
            ox, oy = other[0], other[1]
        else:
            return NotImplemented
        return (self.x, self.y) < (ox, oy)

    def __le__(self, other: 'AnyPoint | AnyPointTuple') -> bool:
        """小于等于比较，按 (x, y) 的字典序比较。"""
        if is_any_point(other):
            ox, oy = other.x, other.y
        elif isinstance(other, tuple) and len(other) == 2:
            ox, oy = other[0], other[1]
        else:
            return NotImplemented
        return (self.x, self.y) <= (ox, oy)

    def __gt__(self, other: 'AnyPoint | AnyPointTuple') -> bool:
        """大于比较，按 (x, y) 的字典序比较。"""
        if is_any_point(other):
            ox, oy = other.x, other.y
        elif isinstance(other, tuple) and len(other) == 2:
            ox, oy = other[0], other[1]
        else:
            return NotImplemented
        return (self.x, self.y) > (ox, oy)

    def __ge__(self, other: 'AnyPoint | AnyPointTuple') -> bool:
        """大于等于比较，按 (x, y) 的字典序比较。"""
        if is_any_point(other):
            ox, oy = other.x, other.y
        elif isinstance(other, tuple) and len(other) == 2:
            ox, oy = other[0], other[1]
        else:
            return NotImplemented
        return (self.x, self.y) >= (ox, oy)

    def normalized(self) -> 'PointF':
        """
        返回一个新的、方向相同但长度为 1 的 `PointF` 对象（单位向量）。

        :return: 单位向量。
        """
        l = self.length
        if l == 0:
            return PointF(0.0, 0.0, name=self.name)
        return PointF(self.x / l, self.y / l, name=self.name)

    def offset(self, dx: int | float, dy: int | float) -> 'AnyPoint':
        """
        偏移坐标。

        如果 self, dx, dy 均为整数，返回 Point。否则返回 PointF。

        :param dx: x方向偏移量。
        :param dy: y方向偏移量。
        :return: 偏移后的新 Point 或 PointF 对象。
        """
        new_x = self.x + dx
        new_y = self.y + dy
        if isinstance(self, PointF) or isinstance(dx, float) or isinstance(dy, float):
            return PointF(new_x, new_y, name=self.name)
        return Point(int(new_x), int(new_y), name=self.name)

    @overload
    def __add__(self: 'Point', other: 'Point | PointTuple') -> 'Point': ...
    @overload
    def __add__(self, other: 'PointF | PointFTuple') -> 'PointF': ...
    @overload
    def __add__(self: 'PointF', other: 'AnyPoint | AnyPointTuple') -> 'PointF': ...
    def __add__(self, other: 'AnyPoint | AnyPointTuple') -> 'AnyPoint':
        """
        与另一个点或元组相加。

        如果任一操作数为浮点数，则结果提升为 PointF。
        
        :param other: 另一个 Point/PointF 对象或元组。
        :return: 相加后的新 Point 或 PointF 对象。
        """
        new_x = self.x + other[0]
        new_y = self.y + other[1]
        # hasattr check for tuple, which does not have .x attribute
        if isinstance(self, PointF) or isinstance(other, PointF) or \
                (not hasattr(other, 'x') and (isinstance(other[0], float) or isinstance(other[1], float))):
            return PointF(new_x, new_y, name=self.name)
        return Point(int(new_x), int(new_y), name=self.name)

    @overload
    def __sub__(self: 'Point', other: 'Point | PointTuple') -> 'Point': ...
    @overload
    def __sub__(self, other: 'PointF | PointFTuple') -> 'PointF': ...
    @overload
    def __sub__(self: 'PointF', other: 'AnyPoint | AnyPointTuple') -> 'PointF': ...
    def __sub__(self, other: 'AnyPoint | AnyPointTuple') -> 'AnyPoint':
        """
        与另一个点或元组相减。

        如果任一操作数为浮点数，则结果提升为 PointF。
        
        :param other: 另一个 Point/PointF 对象或元组。
        :return: 相减后的新 Point 或 PointF 对象。
        """
        new_x = self.x - other[0]
        new_y = self.y - other[1]
        if isinstance(self, PointF) or isinstance(other, PointF) or \
                (not hasattr(other, 'x') and (isinstance(other[0], float) or isinstance(other[1], float))):
            return PointF(new_x, new_y, name=self.name)
        return Point(int(new_x), int(new_y), name=self.name)

    @overload
    def __mul__(self: 'Point', scalar: int) -> 'Point': ...
    @overload
    def __mul__(self, scalar: float) -> 'PointF': ...
    def __mul__(self, scalar: int | float) -> 'AnyPoint':
        """
        与标量相乘（缩放）。
        
        :param scalar: 用于缩放的标量。
        :return: 缩放后的新 Point 或 PointF 对象。
        """
        new_x = self.x * scalar
        new_y = self.y * scalar
        if isinstance(self, PointF) or isinstance(scalar, float):
            return PointF(new_x, new_y, name=self.name)
        return Point(int(new_x), int(new_y), name=self.name)

    def __truediv__(self, scalar: int | float) -> 'PointF':
        """
        与标量相除（缩放）。总是返回一个 PointF 对象。
        
        :param scalar: 用于缩放的标量。
        :return: 缩放后的新 PointF 对象。
        """
        if scalar == 0:
            raise ValueError("Cannot divide by zero")
        return PointF(self.x / scalar, self.y / scalar, name=self.name)

class PointF(_BasePoint[float]):
    """
    ## PointF
    表示浮点数坐标点。

    ### 例
    ```python
    # 创建浮点数坐标点
    p1 = PointF(10.5, 20.7, name="精确位置")
    p2 = PointF(5.2, 8.9)
    
    # 距离计算
    distance = p1.distance_to(p2)  # 计算到另一点的距离
    print(f"距离: {distance:.2f}")
    
    # 向量运算
    result = p1 + p2  # 坐标相加
    scaled = p1 * 2   # 坐标缩放
    
    # 单位向量
    unit = p1.normalized()  # 转换为单位向量
    
    # 坐标偏移
    moved = p1.offset(5.0, 10.0)  # 偏移坐标
    ```
    """
    __slots__ = (*_BasePoint.__slots__,)


class Point(_BasePoint[int]):
    """
    ## Point
    表示整数坐标点。

    ### 例
    ```python
    # 创建整数坐标点
    pixel = Point(1920, 1080, name="屏幕分辨率")
    button = Point(100, 200, name="按钮位置")
    
    # 像素定位操作
    center = Point(640, 360)
    offset = center.offset(10, -5)  # 向右移动10像素，向下移动5像素
    
    # 点与点的运算
    distance = center.distance_to(button)
    relative_pos = button - center  # 相对位置
    
    # 检查点是否相等
    if center == Point(640, 360):
        print("找到了中心点")
    
    # 与浮点数运算时会自动转换为PointF
    precise = center + (5.5, 3.2)  # 结果为PointF类型
    ```
    """
    __slots__ = (*_BasePoint.__slots__,)

class Rect:
    """
    ## Rect
    表示一个矩形区域，支持多种坐标格式和几何操作。

    ### 例
    ```python
    # 创建矩形
    rect = Rect(10, 20, 100, 50, name="按钮区域")
    rect2 = Rect(xywh=(10, 20, 100, 50))
    
    # 从两点创建矩形
    rect3 = Rect.from_xyxy(10, 20, 110, 70)
    
    # 获取矩形属性
    print(rect.center)     # 中心点
    print(rect.size)       # (100, 50)
    print(rect.top_left)   # 左上角点，其他三个角落同理
    
    # 矩形操作
    moved = rect.move(10, 10)      # 原地移动
    copied = rect.moved(5, 15)     # 移动后的新矩形
    enlarged = rect.inflate(5, 5)  # 原地扩大
    
    # 几何计算
    if rect.contains_point(Point(50, 40)):
        print("点在矩形内")
    
    if rect.intersects_with(other_rect):
        print("两个矩形相交")
    
    union = rect.union_of(other_rect)      # 并集
    intersection = rect.intersection_of(other_rect)  # 交集
    ```
    """
    __slots__ = ('x1', 'y1', 'w', 'h', 'name')
    
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
        
        self.x1 = int(x)
        """矩形左上角的 X 坐标。"""
        self.y1 = int(y)
        """矩形左上角的 Y 坐标。"""
        self.w = int(w)
        """矩形的宽度。"""
        self.h = int(h)
        """矩形的高度。"""
        self.name: str | None = name
        """矩形的名称。"""

    @classmethod
    def from_xyxy(cls, x1: int, y1: int, x2: int, y2: int) -> 'Rect':
        """
        从 (x1, y1, x2, y2) 创建矩形。
        :return: 创建结果。
        """
        return cls(int(x1), int(y1), int(x2 - x1), int(y2 - y1))

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

        :return: 中心点 Point 对象。
        """
        if self.name:
            name = "Center of rect "+ self.name
        else:
            name = None
        return Point(int(self.x1 + self.w / 2), int(self.y1 + self.h / 2), name=name)

    @property
    def center_x(self) -> int:
        """
        中心点的 x 坐标。

        :return: 中心点的 x 坐标。
        """
        return self.x1 + self.w // 2

    @property
    def center_y(self) -> int:
        """
        中心点的 y 坐标。

        :return: 中心点的 y 坐标。
        """
        return self.y1 + self.h // 2

    @property
    def middle_top(self) -> Point:
        """
        矩形顶部边的中点。

        :return: 顶部边的中点。
        """
        return Point(self.center_x, self.y1)

    @property
    def middle_bottom(self) -> Point:
        """
        矩形底部边的中点。

        :return: 底部边的中点。
        """
        return Point(self.center_x, self.y2)

    @property
    def middle_left(self) -> Point:
        """
        矩形左侧边的中点。

        :return: 左侧边的中点。
        """
        return Point(self.x1, self.center_y)

    @property
    def middle_right(self) -> Point:
        """
        矩形右侧边的中点。

        :return: 右侧边的中点。
        """
        return Point(self.x2, self.center_y)

    @property
    def size(self) -> tuple[int, int]:
        """
        一个 `(width, height)` 元组。

        :return: 包含宽度和高度的元组。
        """
        return self.w, self.h

    @size.setter
    def size(self, value: tuple[int, int]):
        """
        设置矩形的尺寸。

        :param value: 包含新宽度和新高度的元组。
        """
        self.w, self.h = value

    def __repr__(self) -> str:
        return f'Rect<"{self.name}" at (x={self.x1}, y={self.y1}, w={self.w}, h={self.h})>'

    def __str__(self) -> str:
        return f'(x={self.x1}, y={self.y1}, w={self.w}, h={self.h})'

    def copy(self) -> 'Rect':
        """
        返回一个与当前对象完全相同的**新** `Rect` 对象。

        :return: 当前 Rect 对象的一个副本。
        """
        return Rect(self.x1, self.y1, self.w, self.h, name=self.name)

    def move(self, dx: int, dy: int) -> 'Rect':
        """
        **原地**移动矩形。

        :param dx: x 方向的移动距离。
        :param dy: y 方向的移动距离。
        :return: 移动后的矩形本身。
        """
        self.x1 += dx
        self.y1 += dy
        return self

    def moved(self, dx: int, dy: int) -> 'Rect':
        """
        返回一个移动后的**新** `Rect` 对象。

        :param dx: x 方向的移动距离。
        :param dy: y 方向的移动距离。
        :return: 移动后的新 Rect 对象。
        """
        return Rect(self.x1 + dx, self.y1 + dy, self.w, self.h, name=self.name)

    def inflate(self, dx: int, dy: int) -> 'Rect':
        """
        **原地**缩放矩形（中心点不变）。

        矩形的宽度增加 `2 * dx`，高度增加 `2 * dy`。
        负值会缩小矩形。

        :param dx: 宽度方向的膨胀量（每边）。
        :param dy: 高度方向的膨胀量（每边）。
        :return: 缩放后的矩形本身。
        """
        self.x1 -= dx
        self.y1 -= dy
        self.w += 2 * dx
        self.h += 2 * dy
        return self

    def inflated(self, dx: int, dy: int) -> 'Rect':
        """
        返回一个缩放后的**新** `Rect` 对象。

        :param dx: 宽度方向的膨胀量（每边）。
        param dy: 高度方向的膨胀量（每边）。
        :return: 缩放后的新 Rect 对象。
        """
        return Rect(self.x1 - dx, self.y1 - dy, self.w + 2 * dx, self.h + 2 * dy, name=self.name)

    def normalize(self) -> 'Rect':
        """
        **原地**修正矩形，确保 `width` 和 `height` 为正数。

        如果宽度或高度为负，则交换坐标以使其为正。

        :return: 修正后的矩形本身。
        """
        if self.w < 0:
            self.x1 += self.w
            self.w = -self.w
        if self.h < 0:
            self.y1 += self.h
            self.h = -self.h
        return self

    def normalized(self) -> 'Rect':
        """
        返回一个修正后的**新** `Rect` 对象，确保 `width` 和 `height` 为正数。

        :return: 修正后的新 Rect 对象。
        """
        x, y, w, h = self.x1, self.y1, self.w, self.h
        if w < 0:
            x += w
            w = -w
        if h < 0:
            y += h
            h = -h
        return Rect(x, y, w, h, name=self.name)

    def contains_point(self, point: 'AnyPoint | PointTuple | PointFTuple') -> bool:
        """
        检查一个点是否在此矩形内部。

        .. note::
            对于边界值，左边界与上边界包含，而右边界与下边界不包含。

            例如 `Rect(0, 0, 10, 10)` 包含 `Point(0, 0)`，但不包含 `Point(10, 10)`。

        :param point: 要检查的点。
        :return: 如果点在矩形内，则返回 `True`。
        """
        return self.x1 <= point[0] < self.x2 and self.y1 <= point[1] < self.y2

    def contains_rect(self, other_rect: 'Rect') -> bool:
        """检查此矩形是否完全包含另一个矩形。

        :param other_rect: 要检查的另一个矩形。
        :return: 是否完全包含。
        """
        # 使用半开区间规则：矩形表示为 [x1, x2) x [y1, y2)
        # 因此 other_rect 完全包含于 self 当且仅当
        # other_rect.x1 >= self.x1, other_rect.y1 >= self.y1,
        # other_rect.x2 <= self.x2, other_rect.y2 <= self.y2
        return (self.x1 <= other_rect.x1 and self.y1 <= other_rect.y1 and
            other_rect.x2 <= self.x2 and other_rect.y2 <= self.y2)


    def intersects_with(self, other_rect: 'Rect') -> bool:
        """
        检查此矩形是否与另一个矩形相交。

        .. note::
            若两个矩形只有边界重叠，不算做相交。

        :param other_rect: 要检查的另一个矩形。
        :return: 如果两个矩形相交，则返回 `True`。
        """
        return not (self.x2 <= other_rect.x1 or self.x1 >= other_rect.x2 or
                    self.y2 <= other_rect.y1 or self.y1 >= other_rect.y2)

    def union_of(self, other_rect: 'Rect') -> 'Rect':
        """
        返回一个能同时包含两个矩形的**新** `Rect` 对象（并集）。

        :param other_rect: 要合并的另一个矩形。
        :return: 包含两个矩形的最小矩形。
        """
        x1 = min(self.x1, other_rect.x1)
        y1 = min(self.y1, other_rect.y1)
        x2 = max(self.x2, other_rect.x2)
        y2 = max(self.y2, other_rect.y2)
        return Rect.from_xyxy(x1, y1, x2, y2)

    def intersection_of(self, other_rect: 'Rect') -> 'Rect | None':
        """
        返回两个矩形相交区域的**新** `Rect` 对象（交集）。

        如果不相交，则返回 `None`。

        :param other_rect: 要计算交集的另一个矩形。
        :return: 相交区域的矩形，或 `None`。
        """
        x1 = max(self.x1, other_rect.x1)
        y1 = max(self.y1, other_rect.y1)
        x2 = min(self.x2, other_rect.x2)
        y2 = min(self.y2, other_rect.y2)
        if x1 >= x2 or y1 >= y2:
            return None
        return Rect.from_xyxy(x1, y1, x2, y2)

    def is_empty(self) -> bool:
        """
        如果矩形的 `width` 或 `height` 小于等于零，则返回 `True`。

        :return: 如果矩形为空，则返回 `True`。
        """
        return self.w <= 0 or self.h <= 0

    @overload
    def __contains__(self, obj: 'Point | PointTuple | PointF | PointFTuple') -> bool: ...
    @overload
    def __contains__(self, obj: 'Rect') -> bool: ...

    def __contains__(self, obj: 'AnyPoint | PointTuple | PointFTuple | Rect') -> bool:
        """
        判断点或矩形是否被此矩形包含。

        - 如果传入的是点或点元组，等价于 `Rect.contains_point`。
        - 如果传入的是 `Rect`，则判断整个矩形是否被包含（完全包含）。

        :param obj: 要检查的点或矩形。
        :return: 如果被包含则返回 `True`。
        """
        # 如果是矩形，则检查矩形包含关系
        if is_rect(obj):
            return self.contains_rect(obj)
        # 如果是任意点类型（Point / PointF）或长度为2的元组，则视为点
        if is_any_point(obj) or (isinstance(obj, tuple) and len(obj) == 2):
            return self.contains_point(obj)
        raise TypeError("Argument must be a Point, PointF, 2-tuple of int or float, or Rect.")

AnyPoint = Union[Point, PointF]
"""任意 Point 对象，包括 Point 与 PointF。"""
AnyPointTuple = Union[PointTuple, PointFTuple]
"""任意 Point 元组，包括 tuple[int, int] 与 tuple[float, float]。"""
PointLike = Union[Point, PointTuple]
PointFLike = Union[PointF, PointFTuple]
AnyPointLike = Union[AnyPoint, AnyPointTuple]
"""任意类似于 Point 的对象，包括 Point、PointF、tuple[int, int]、tuple[float, float]。"""
RectLike = Union[Rect, RectTuple]
"""任意类似于 Rect 的对象，包括 Rect、tuple[int, int, int, int]。"""
def is_point(obj: object) -> TypeGuard[Point]:
    return isinstance(obj, Point)

def is_point_f(obj: object) -> TypeGuard[PointF]:
    return isinstance(obj, PointF)

def is_any_point(obj: object) -> TypeGuard[AnyPoint]:
    return isinstance(obj, (Point, PointF))

def is_rect(obj: object) -> TypeGuard[Rect]:
    return isinstance(obj, Rect)

def unify_point(point: PointLike) -> Point:
    """
    将点或元组统一转换为 `Point` 对象。

    :param point: 要转换的点或元组。
    :return: 转换后的 `Point` 对象。
    :raises TypeError: 如果输入类型不正确则抛出。

    .. note::
        若输入数据为 float，会被强制转换为 int。
    """
    # If already an integer Point, return it directly
    if is_point(point):
        return point

    # If it's a PointF, convert to Point by casting coordinates to int
    if is_point_f(point):
        return Point(int(point.x), int(point.y), name=point.name)

    # If it's a tuple-like (x, y) sequence, attempt to extract
    if isinstance(point, (tuple, list)) and len(point) == 2:
        x, y = point[0], point[1]
        try:
            return Point(int(x), int(y))
        except Exception:
            raise TypeError('Point tuple must contain numeric values')

    raise TypeError('Argument must be a Point, PointF, or 2-tuple of numbers')

def unify_pointf(point: PointLike) -> PointF:
    """
    将点或元组统一转换为 `PointF` 对象。

    :param point: 要转换的点或元组。
    :return: 转换后的 `PointF` 对象。
    :raises TypeError: 如果输入类型不正确则抛出。
    """
    # If already a PointF, return it
    if is_point_f(point):
        return point

    # If it's an integer Point, convert to PointF preserving name
    if is_point(point):
        return PointF(float(point.x), float(point.y), name=point.name)

    # If it's a tuple-like (x, y), convert elements to float
    if isinstance(point, (tuple, list)) and len(point) == 2:
        x, y = point[0], point[1]
        try:
            return PointF(float(x), float(y))
        except Exception:
            raise TypeError('PointF tuple must contain numeric values')

    raise TypeError('Argument must be a Point, PointF, or 2-tuple of numbers')

def unify_any_point(point: AnyPointLike) -> Point | PointF:
    """
    将点或元组统一转换为 `Point` 或 `PointF` 对象。

    如果输入已是 `Point` 或 `PointF` 对象，直接返回。
    如果输入是元组，根据其数值类型决定返回类型：
    - 若所有坐标为整数，返回 `Point`
    - 若有任何坐标为浮点数，返回 `PointF`

    :param point: 要转换的点或元组。
    :return: 转换后的 `Point` 或 `PointF` 对象。
    :raises TypeError: 如果输入类型不正确则抛出。
    """
    # If already a Point or PointF, return it directly
    if is_any_point(point):
        return point

    # If it's a sequence, check types and convert accordingly
    if isinstance(point, (tuple, list)) and len(point) == 2:
        x, y = point[0], point[1]
        try:
            # If both are integers, return Point
            if isinstance(x, int) and isinstance(y, int):
                return Point(x, y)
            # Otherwise, return PointF
            else:
                return PointF(float(x), float(y))
        except Exception:
            raise TypeError('Point tuple must contain numeric values')

    raise TypeError('Argument must be a Point, PointF, or 2-tuple of numbers')

def unify_rect(rect: RectLike) -> Rect:
    """
    将矩形或元组 (x, y, w, h) 统一转换为 `Rect` 对象。

    :param rect: 要转换的矩形或元组。
    :return: 转换后的 `Rect` 对象。
    :raises TypeError: 如果输入类型不正确则抛出。

    .. note::
        若输入数据为 float，会被强制转换为 int。
    """
    # If already a Rect, return it
    if is_rect(rect):
        return rect

    # If it's a tuple-like (x, y, w, h), convert to ints and construct Rect
    if isinstance(rect, (tuple, list)) and len(rect) == 4:
        x, y, w, h = rect[0], rect[1], rect[2], rect[3]
        try:
            return Rect(int(x), int(y), int(w), int(h))
        except Exception:
            raise TypeError('Rect tuple must contain numeric values')

    raise TypeError('Argument must be a Rect or 4-tuple of numbers (x, y, w, h)')
