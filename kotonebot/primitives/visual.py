import logging
import warnings
from functools import cache
from os import PathLike

import cv2
from cv2.typing import MatLike

from .geometry import Size, Rect
from kotonebot.util import cv2_imread, cv2_imwrite

logger = logging.getLogger(__name__)


class Frame:
    """
    运行时图像数据。

    与 `Image` 不同，`Frame` 仅表示内存中的图像数据，
    适用于截图、裁剪结果、调试图等场景。
    """

    def __init__(
        self,
        mat: MatLike,
        *,
        name: str | None = None,
        source: 'Frame | Image | str | None' = None,
        rect: Rect | None = None,
    ):
        self.mat = mat
        """图像像素数据。默认约定为 BGR。"""
        self.name = name
        """图像名称。主要用于日志与调试展示。"""
        self.source = source
        """图像来源。可指向父 `Frame`、资源 `Image` 或路径。"""
        self.rect = rect
        """若图像由父图像裁剪而来，则表示其在父图像中的区域。"""

    @property
    def size(self) -> Size:
        return Size(self.mat.shape[1], self.mat.shape[0])

    @property
    def width(self) -> int:
        return self.mat.shape[1]

    @property
    def height(self) -> int:
        return self.mat.shape[0]

    @property
    def shape(self) -> tuple[int, ...]:
        return self.mat.shape

    def copy(self, *, name: str | None = None) -> 'Frame':
        return Frame(
            self.mat.copy(),
            name=name if name is not None else self.name,
            source=self.source,
            rect=self.rect,
        )

    def crop(self, rect: Rect, *, name: str | None = None) -> 'Frame':
        x, y, w, h = rect.xywh
        cropped = self.mat[y:y+h, x:x+w].copy()
        return Frame(
            cropped,
            name=name if name is not None else self._derived_name('crop'),
            source=self,
            rect=rect,
        )

    def crop_ratio(
        self,
        x1: float = 0,
        y1: float = 0,
        x2: float = 1,
        y2: float = 1,
        *,
        name: str | None = None,
    ) -> 'Frame':
        left = int(self.width * x1)
        top = int(self.height * y1)
        right = int(self.width * x2)
        bottom = int(self.height * y2)
        return self.crop(Rect(left, top, right - left, bottom - top), name=name)

    def resize(
        self,
        width: int,
        height: int,
        *,
        interpolation: int = cv2.INTER_LINEAR,
        name: str | None = None,
    ) -> 'Frame':
        resized = cv2.resize(self.mat, (width, height), interpolation=interpolation)
        return Frame(
            resized,
            name=name if name is not None else self._derived_name('resize'),
            source=self,
            rect=None,
        )

    def scale(
        self,
        *,
        fx: float | None = None,
        fy: float | None = None,
        size: tuple[int, int] | None = None,
        interpolation: int = cv2.INTER_LINEAR,
        name: str | None = None,
    ) -> 'Frame':
        if size is not None and (fx is not None or fy is not None):
            raise ValueError('Cannot specify both `size` and `fx`/`fy`.')
        if size is not None:
            return self.resize(size[0], size[1], interpolation=interpolation, name=name)
        if fx is None and fy is None:
            raise ValueError('Either `size` or `fx`/`fy` must be provided.')
        if fx is None:
            fx = fy
        if fy is None:
            fy = fx
        assert fx is not None and fy is not None
        scaled = cv2.resize(self.mat, None, fx=fx, fy=fy, interpolation=interpolation)
        return Frame(
            scaled,
            name=name if name is not None else self._derived_name('scale'),
            source=self,
            rect=None,
        )

    def save(self, path: str | PathLike[str]) -> str:
        path_str = str(path)
        cv2_imwrite(path_str, self.mat)
        return path_str

    def show(self, *, title: str | None = None, wait_key: int = 0, destroy: bool = True) -> None:
        window_name = title or self.name or 'Frame'
        cv2.imshow(window_name, self.mat)
        cv2.waitKey(wait_key)
        if destroy:
            cv2.destroyWindow(window_name)

    def draw_rect(
        self,
        rect: Rect,
        *,
        color: tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2,
        name: str | None = None,
    ) -> 'Frame':
        result = self.copy(name=name if name is not None else self._derived_name('draw_rect'))
        cv2.rectangle(result.mat, rect.xywh, color, thickness)
        return result

    def draw_point(
        self,
        x: int,
        y: int,
        *,
        radius: int = 6,
        color: tuple[int, int, int] = (0, 0, 255),
        thickness: int = -1,
        name: str | None = None,
    ) -> 'Frame':
        result = self.copy(name=name if name is not None else self._derived_name('draw_point'))
        cv2.circle(result.mat, (x, y), radius, color, thickness)
        return result

    def draw_text(
        self,
        text: str,
        x: int,
        y: int,
        *,
        font_face: int = cv2.FONT_HERSHEY_SIMPLEX,
        font_scale: float = 0.8,
        color: tuple[int, int, int] = (0, 0, 255),
        thickness: int = 2,
        name: str | None = None,
    ) -> 'Frame':
        result = self.copy(name=name if name is not None else self._derived_name('draw_text'))
        cv2.putText(result.mat, text, (x, y), font_face, font_scale, color, thickness)
        return result

    def _derived_name(self, operation: str) -> str | None:
        if self.name is None:
            return None
        return f'{self.name}.{operation}'

    def _source_repr(self) -> str:
        if isinstance(self.source, Frame):
            return self.source.name or 'Frame'
        if isinstance(self.source, Image):
            return self.source.name or self.source.file_path or 'Image'
        return str(self.source)

    def __repr__(self) -> str:
        parts = [f'{self.width}x{self.height}']
        if self.name is not None:
            parts.insert(0, f'"{self.name}"')
        if self.source is not None:
            parts.append(f'source={self._source_repr()}')
        if self.rect is not None:
            parts.append(f'rect={self.rect}')
        return f'<Frame {" ".join(parts)}>'

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

    # Compatibility with older API (deprecated)
    def __compat_warn(self, name: str) -> None:
        warnings.warn(
            f'`Image.{name}` is deprecated — use `kotonebot.primitives.Image` API instead.',
            DeprecationWarning,
            stacklevel=3,
        )

    @property
    def path(self) -> str | None:
        """Deprecated alias for `file_path`."""
        self.__compat_warn('path')
        return self.file_path

    @path.setter
    def path(self, value: str | None) -> None:
        self.__compat_warn('path')
        self.file_path = value

    @property
    def data(self) -> MatLike:
        """Deprecated alias for `pixels`."""
        self.__compat_warn('data')
        return self.pixels

    @property
    def data_with_alpha(self) -> MatLike:
        """Deprecated: return image including alpha channel when available."""
        self.__compat_warn('data_with_alpha')
        # If current pixels already contain alpha, return them
        try:
            if self.__pixels is not None and getattr(self.__pixels, 'shape', None) and len(self.__pixels.shape) >= 3 and self.__pixels.shape[2] == 4:
                return self.__pixels
        except Exception:
            pass
        if not self.file_path:
            raise ValueError('Either pixels or file_path must be provided.')
        arr = cv2_imread(self.file_path, cv2.IMREAD_UNCHANGED)
        return arr

    @cache
    def binary(self) -> 'Image':
        """Deprecated: return a grayscale copy of the image."""
        self.__compat_warn('binary')
        gray = cv2.cvtColor(self.pixels, cv2.COLOR_BGR2GRAY)
        return Image(pixels=gray, name=self.name)

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        if self.file_path is None:
            return f'<{class_name}: memory>'
        else:
            return f'<{class_name}: "{self.name or "untitled"}" at {self.file_path}>'


class ImageSlice(Image):
    def __init__(
        self,
        pixels: MatLike | None = None,
        file_path: str | None = None,
        lazy_load: bool = False,
        name: str | None = None,
        description: str | None = None,
        *,
        slice_rect: Rect | None
    ):
        super().__init__(
            pixels=pixels,
            file_path=file_path,
            lazy_load=lazy_load,
            name=name,
            description=description
        )
        self.slice_rect = slice_rect
        """图像切片的矩形区域。"""


class Template(Image):
    """
    模板图像类。
    """
