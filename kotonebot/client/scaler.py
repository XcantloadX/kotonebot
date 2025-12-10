from abc import ABC
from typing import Any, overload
from typing_extensions import override

from cv2.typing import MatLike

from kotonebot.primitives.geometry import (
    PointLike, RectLike, Size, SizeLike, AnyPointLike, unify_any_point
)
from kotonebot.primitives.geometry import (
    is_point, is_point_f, is_rect, unify_rect,
    Point, PointF, Rect
)

class AbstractScaler(ABC):
    """用于定义当实际设备分辨率与预期分辨率不一致时缩放行为的接口。

    该接口定义了包括缩放图像、坐标转换、比例转换在内的方法。
    """
    def __init__(self) -> None:
        # Accept either a `Size` instance or a plain (width, height) tuple.
        self.physical_resolution: SizeLike | None = None
        """物理分辨率 (width, height)。"""
        self.logic_resolution: SizeLike | None = None
        """逻辑分辨率 (width, height)。"""

    def transform_screenshot(self, screenshot: MatLike) -> MatLike:
        """处理设备画面截图数据。

        :param screenshot: 原始截图数据。
        :return: 处理后的截图数据。
        """
        ...
    
    @overload
    def logic_to_physical(self, v: AnyPointLike) -> AnyPointLike: ...
    @overload
    def logic_to_physical(self, v: RectLike) -> RectLike: ...
    def logic_to_physical(self, v: AnyPointLike | RectLike) -> AnyPointLike | RectLike | Any:
        """将逻辑坐标转换为物理坐标。

        :param v: 逻辑坐标点或矩形。
        :return: 转换后的物理坐标点或矩形。

        Examples
        --------
        >>> scaler.logic_to_physical(Point(10, 20))
        <<< Point(..., ...)
        >>> scaler.logic_to_physical(PointF(10.6, 20.5))
        <<< Point(..., ...)
        >>> scaler.logic_to_physical((10, 20))
        <<< Point(..., ...)
        >>> scaler.logic_to_physical(Rect(10, 20, 30, 40))
        <<< Rect(..., ..., ..., ...)
        >>> scaler.logic_to_physical((10, 20, 30, 40))
        <<< Rect(..., ..., ..., ...)
        """ 
        ...

    @overload
    def physical_to_logic(self, v: PointLike) -> PointLike: ...
    @overload
    def physical_to_logic(self, v: RectLike) -> RectLike: ...
    def physical_to_logic(self, v: AnyPointLike | RectLike) -> AnyPointLike | RectLike | Any:
        """将物理坐标转换为逻辑坐标。

        :param v: 物理坐标点或矩形。
        :return: 转换后的逻辑坐标点或矩形。

        Examples
        --------
        见 :meth:`logic_to_physical`。
        """
        ...

    @overload
    def fractional_to_physical(self, v: PointLike) -> PointLike: ...
    @overload
    def fractional_to_physical(self, v: RectLike) -> RectLike: ...
    def fractional_to_physical(self, v: AnyPointLike | RectLike) -> AnyPointLike | RectLike | Any:
        """将比例坐标转换为物理坐标。

        :param v: 比例坐标点或矩形。
        :return: 转换后的物理坐标点或矩形。

        Examples
        --------
        见 :meth:`logic_to_physical`。
        """
        ...

    @overload
    def physical_to_fractional(self, v: PointLike) -> PointLike: ...
    @overload
    def physical_to_fractional(self, v: RectLike) -> RectLike: ...
    def physical_to_fractional(self, v: AnyPointLike | RectLike) -> AnyPointLike | RectLike | Any:
        """将物理坐标转换为比例坐标。

        :param v: 物理坐标点或矩形。
        :return: 转换后的比例坐标点或矩形。

        Examples
        --------
        见 :meth:`logic_to_physical`。
        """
        ...


class ProportionalScaler(AbstractScaler):
    """等比例缩放。
    
    支持在物理分辨率和逻辑分辨率之间进行等比例缩放转换。
    仅支持等比例缩放，若无法等比例缩放，则会抛出异常。
    """
    
    def __init__(
        self,
        match_rotation: bool = True,
        aspect_ratio_tolerance: float = 0.1
    ):
        """初始化等比例缩放器。"""
        super().__init__()

        self.match_rotation = match_rotation
        """分辨率缩放是否自动匹配旋转。
        当目标与真实分辨率的宽高比不一致时，是否允许通过旋转（交换宽高）后再进行匹配。

        True 表示忽略方向差异，只要宽高比一致就视为可缩放；False 表示必须匹配旋转。
        """
        self.aspect_ratio_tolerance = aspect_ratio_tolerance
        """宽高比容差阈值。
        
        判断两分辨率宽高比差异是否接受的阈值。
        该值越小，对比例一致性的要求越严格。默认为 0.1（即 10% 容差）。
        """
    
    @property
    def scale_ratio(self) -> float:
        """获取物理分辨率相对于逻辑分辨率的缩放比例。
        
        由于是等比例缩放，长宽的缩放比例应当一致（在容差范围内）。
        """
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")
        if self.logic_resolution is None:
            return 1.0
            
        phy_w, phy_h = self.physical_resolution
        log_w, log_h = self.logic_resolution
        
        if self.match_rotation:
            return max(phy_w, phy_h) / max(log_w, log_h)
        
        return phy_w / log_w
        
    def _aspect_ratio_compatible(
        self, src_size: SizeLike, tgt_size: SizeLike
    ) -> bool:
        """判断两个尺寸在宽高比意义上是否兼容。
        
        若 ``self.match_rotation`` 为 True，忽略方向（长边/短边）进行比较。
        判断标准由 ``self.aspect_ratio_tolerance`` 决定（默认 0.1）。
        """
        src_w, src_h = src_size
        tgt_w, tgt_h = tgt_size
        
        # 尺寸必须为正
        if src_w <= 0 or src_h <= 0:
            raise ValueError(f"Source size dimensions must be positive for scaling: {src_size}")
        if tgt_w <= 0 or tgt_h <= 0:
            raise ValueError(f"Target size dimensions must be positive for scaling: {tgt_size}")
        
        tolerant = self.aspect_ratio_tolerance
        
        # 直接比较宽高比
        if abs((tgt_w / src_w) - (tgt_h / src_h)) <= tolerant:
            return True
        
        # 尝试忽略方向差异
        if self.match_rotation:
            ratio_src = max(src_w, src_h) / min(src_w, src_h)
            ratio_tgt = max(tgt_w, tgt_h) / min(tgt_w, tgt_h)
            return abs(ratio_src - ratio_tgt) <= tolerant
        
        return False
    
    def _assert_scalable(
        self, source: SizeLike, target: SizeLike
    ) -> SizeLike:
        """校验分辨率是否可缩放，并返回调整后的目标分辨率。
        
        当 match_rotation 为 True 且源分辨率与目标分辨率的旋转方向不一致时，
        自动交换目标分辨率的宽高，使其与源分辨率的方向保持一致。
        
        :param source: 源分辨率 (width, height)
        :param target: 目标分辨率 (width, height)
        :return: 调整后的目标分辨率 (width, height)
        :raises UnscalableResolutionError: 若宽高比不兼容
        """
        from ..errors import UnscalableResolutionError
        
        # 智能调整目标分辨率方向
        adjusted_tgt_size = target
        if self.match_rotation:
            src_w, src_h = source
            tgt_w, tgt_h = target
            
            # 判断源分辨率和目标分辨率的方向
            src_is_landscape = src_w > src_h
            tgt_is_landscape = tgt_w > tgt_h
            
            # 如果方向不一致，交换目标分辨率的宽高
            if src_is_landscape != tgt_is_landscape:
                adjusted_tgt_size = Size(tgt_h, tgt_w)
        
        # 校验调整后的分辨率是否兼容
        if not self._aspect_ratio_compatible(source, adjusted_tgt_size):
            raise UnscalableResolutionError(tuple(target), tuple(source))
        
        return adjusted_tgt_size
    
    def transform_screenshot(self, screenshot: MatLike) -> MatLike:
        """处理设备画面截图数据，将物理分辨率缩放到逻辑分辨率。
        
        :param screenshot: 原始截图数据。
        :return: 处理后的截图数据。
        """
        import cv2
        
        if self.logic_resolution is None:
            return screenshot
        
        target_w, target_h = self.logic_resolution
        h, w = screenshot.shape[:2]
        
        # 校验分辨率是否可缩放并获取调整后的目标分辨率
        adjusted_target = self._assert_scalable(Size(w, h), Size(target_w, target_h))
        
        return cv2.resize(screenshot, tuple(adjusted_target))
    
    def logic_to_physical(self, v: AnyPointLike | RectLike) -> Any:
        """将逻辑坐标转换为物理坐标。
        
        :param v: 逻辑坐标点或矩形。
        :return: 转换后的物理坐标点或矩形。
        """
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")
        if self.logic_resolution is None:
            return v

        # 校验分辨率是否可缩放
        self._assert_scalable(self.logic_resolution, self.physical_resolution)

        ratio = self.scale_ratio

        # 处理点类型
        if is_point(v) or is_point_f(v) or (isinstance(v, tuple) and len(v) == 2):
            point = unify_any_point(v)
            
            new_x = point.x * ratio
            new_y = point.y * ratio
            
            if isinstance(point, PointF):
                return PointF(new_x, new_y, name=point.name)
            else:
                return Point(int(new_x), int(new_y), name=point.name)
        
        # 处理矩形类型
        if is_rect(v) or (isinstance(v, tuple) and len(v) == 4):
            rect = unify_rect(v)
            
            new_x = int(rect.x1 * ratio)
            new_y = int(rect.y1 * ratio)
            new_w = int(rect.w * ratio)
            new_h = int(rect.h * ratio)
            
            return Rect(new_x, new_y, new_w, new_h, name=rect.name)
        
        return v
    
    def physical_to_logic(self, v: AnyPointLike | RectLike) -> Any:
        """将物理坐标转换为逻辑坐标。
        
        :param v: 物理坐标点或矩形。
        :return: 转换后的逻辑坐标点或矩形。
        """
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")
        if self.logic_resolution is None:
            return v

        # 校验分辨率是否可缩放
        self._assert_scalable(self.logic_resolution, self.physical_resolution)

        # 类型断言：如果 logic_resolution 不为 None，则 _adjusted_logic_resolution 也不为 None
        assert self.logic_resolution is not None

        ratio = self.scale_ratio
        
        # 处理点类型
        if is_point(v) or is_point_f(v) or (isinstance(v, tuple) and len(v) == 2):
            point = unify_any_point(v)
            
            new_x = point.x / ratio
            new_y = point.y / ratio
            
            if isinstance(point, PointF):
                return PointF(new_x, new_y, name=point.name)
            else:
                return Point(int(new_x), int(new_y), name=point.name)
        
        # 处理矩形类型
        if is_rect(v) or (isinstance(v, tuple) and len(v) == 4):
            rect = unify_rect(v)
            
            new_x = int(rect.x1 / ratio)
            new_y = int(rect.y1 / ratio)
            new_w = int(rect.w / ratio)
            new_h = int(rect.h / ratio)
            
            return Rect(new_x, new_y, new_w, new_h, name=rect.name)
        
        return v
    
    def fractional_to_physical(self, v: AnyPointLike | RectLike) -> Any:
        """将比例坐标转换为物理坐标。
        
        :param v: 比例坐标点或矩形（0-1范围）。
        :return: 转换后的物理坐标点或矩形。
        """
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")

        # 处理点类型
        if is_point(v) or is_point_f(v) or (isinstance(v, tuple) and len(v) == 2):
            point = unify_any_point(v)
            
            physical_w, physical_h = self.physical_resolution
            
            new_x = point.x * physical_w
            new_y = point.y * physical_h
            
            if isinstance(point, PointF):
                return PointF(new_x, new_y, name=point.name)
            else:
                return Point(int(new_x), int(new_y), name=point.name)
        
        # 处理矩形类型
        if is_rect(v) or (isinstance(v, tuple) and len(v) == 4):
            rect = unify_rect(v)
            
            physical_w, physical_h = self.physical_resolution
            
            new_x = int(rect.x1 * physical_w)
            new_y = int(rect.y1 * physical_h)
            new_w = int(rect.w * physical_w)
            new_h = int(rect.h * physical_h)
            
            return Rect(new_x, new_y, new_w, new_h, name=rect.name)
        
        return v
    
    def physical_to_fractional(self, v: AnyPointLike | RectLike) -> Any:
        """将物理坐标转换为比例坐标。
        
        :param v: 物理坐标点或矩形。
        :return: 转换后的比例坐标点或矩形（0-1范围）。
        """
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")
        
        # 处理点类型
        if is_point(v) or is_point_f(v) or (isinstance(v, tuple) and len(v) == 2):
            point = unify_any_point(v)
            
            physical_w, physical_h = self.physical_resolution
            
            new_x = point.x / physical_w
            new_y = point.y / physical_h
            
            # 比例坐标总是返回 PointF
            return PointF(new_x, new_y, name=point.name)
        
        # 处理矩形类型
        if is_rect(v) or (isinstance(v, tuple) and len(v) == 4):
            rect = unify_rect(v)
            
            physical_w, physical_h = self.physical_resolution
            
            new_x = rect.x1 / physical_w
            new_y = rect.y1 / physical_h
            new_w = rect.w / physical_w
            new_h = rect.h / physical_h
            
            # 比例坐标的矩形需要转换为整数，但这里保持浮点精度
            # 实际使用时可能需要根据具体需求调整
            return Rect(int(new_x * 10000), int(new_y * 10000), int(new_w * 10000), int(new_h * 10000), name=rect.name)
        
        return v
    

class LandscapeGameScaler(ProportionalScaler):
    """横屏游戏等比例缩放。
    
    对于横屏的游戏，通常若两个分辨率的长边一致，那么画面中元素大小也一致。
    因此此缩放器会根据长边进行等比例缩放判断。
    """
    def __init__(
        self,
        aspect_ratio_tolerance: float = 0.1
    ):
        """初始化横屏等比例缩放器。"""
        super().__init__(
            match_rotation=True, 
            aspect_ratio_tolerance=aspect_ratio_tolerance
        )

    @property
    def scale_ratio(self) -> float:
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")
        if self.logic_resolution is None:
            return 1.0
        
        # 横屏游戏根据长边（max）计算缩放比例
        # Unpack explicitly to support both tuple and Vector2D/Size
        phy_w, phy_h = self.physical_resolution
        log_w, log_h = self.logic_resolution
        
        return max(phy_w, phy_h) / max(log_w, log_h)

    @override
    def _assert_scalable(self, source: SizeLike, target: SizeLike) -> Size:
        return Size(int(source[0] / self.scale_ratio), int(source[1] / self.scale_ratio))


class PortraitGameScaler(ProportionalScaler):
    """竖屏游戏等比例缩放。
    
    对于竖屏的游戏，通常以短边（宽度）为基准进行缩放。
    """
    def __init__(
        self,
        aspect_ratio_tolerance: float = 0.1
    ):
        """初始化竖屏等比例缩放器。"""
        super().__init__(
            match_rotation=True,
            aspect_ratio_tolerance=aspect_ratio_tolerance
        )

    @property
    def scale_ratio(self) -> float:
        if self.physical_resolution is None:
            raise RuntimeError("Physical resolution is not set.")
        if self.logic_resolution is None:
            return 1.0
            
        # 竖屏游戏根据短边（min）计算缩放比例
        phy_w, phy_h = self.physical_resolution
        log_w, log_h = self.logic_resolution
        return min(phy_w, phy_h) / min(log_w, log_h)
    
    @override
    def _assert_scalable(self, source: SizeLike, target: SizeLike) -> Size:
        return Size(int(source[0] / self.scale_ratio), int(source[1] / self.scale_ratio))