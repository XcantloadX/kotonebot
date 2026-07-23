"""图像服务。

从 RestApiLogic 提取，封装原图路径解析、缩略图生成、悬停预览。
"""

from pathlib import Path

import cv2

from kotonebot.devtools.errors import InvalidImageError, ValidationError
from kotonebot.devtools.image_preview import build_image_preview
from kotonebot.devtools.path_utils import CACHE_HOVER_PREVIEWS, CACHE_THUMBNAILS, get_safe_path
from kotonebot.devtools.project.project import Project


class ImageService:
    """图像服务：原图路径解析、缩略图、悬停预览。"""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.pyproject_root = project.pyproject_root
        self.project_root = Path(project.conf.editor.resource_path).resolve()
        self.thumbnail_cache_root = project.pyproject_root / CACHE_THUMBNAILS
        self.image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def _is_image_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.image_suffixes

    def resolve_image_path(self, path: str) -> Path:
        """验证并返回图像绝对路径。"""
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise InvalidImageError("Not an image file")
        return safe_path

    def _get_thumbnail_path(self, source: Path, size: int) -> Path:
        if size <= 0:
            raise ValidationError("size must be positive")
        rel = source.resolve().relative_to(self.project_root)
        size_dir = self.thumbnail_cache_root / str(size)
        target_dir = size_dir / rel.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / rel.name

    def _ensure_thumbnail(self, source: Path, size: int) -> Path:
        cache_path = self._get_thumbnail_path(source, size)
        regenerate = True
        if cache_path.exists():
            src_stat = source.stat()
            cache_stat = cache_path.stat()
            if cache_stat.st_mtime >= src_stat.st_mtime and cache_stat.st_size > 0:
                regenerate = False
        if regenerate:
            img = cv2.imread(str(source))
            if img is None:
                raise InvalidImageError(f"Could not read image: {source}")
            height, width = img.shape[:2]
            longest = max(width, height)
            if longest <= 0:
                raise ValidationError("invalid image size")
            scale = size / float(longest)
            new_width = max(1, int(round(width * scale)))
            new_height = max(1, int(round(height * scale)))
            resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(cache_path), resized)
        return cache_path

    def _ensure_thumbnail_crop(
        self, source: Path, size: int, x1: int, y1: int, x2: int, y2: int
    ) -> Path:
        cache_key = f"{x1}_{y1}_{x2}_{y2}_{size}"
        cache_dir = self.thumbnail_cache_root / "crop"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{source.name}.{cache_key}.png"
        if cache_path.exists():
            return cache_path
        img = cv2.imread(str(source))
        if img is None:
            raise InvalidImageError(f"Could not read image: {source}")
        cropped = img[y1:y2, x1:x2]
        h, w = cropped.shape[:2]
        if h <= 0 or w <= 0:
            raise ValidationError("invalid crop region")
        longest = max(w, h)
        scale = size / float(longest)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        resized = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(cache_path), resized)
        return cache_path

    def get_thumbnail(self, path: str, size: int = 128,
                      x1: int | None = None, y1: int | None = None,
                      x2: int | None = None, y2: int | None = None) -> Path:
        """获取缩略图缓存路径，不存在则生成。"""
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise InvalidImageError("Not an image file")
        has_rect = x1 is not None and y1 is not None and x2 is not None and y2 is not None
        if has_rect:
            return self._ensure_thumbnail_crop(safe_path, size, x1, y1, x2, y2)
        return self._ensure_thumbnail(safe_path, size)

    def get_hover_preview(self, path: str, size: int | None = None,
                          x1: float | None = None, y1: float | None = None,
                          x2: float | None = None, y2: float | None = None) -> Path:
        """获取悬停预览图缓存路径。"""
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise InvalidImageError("Not an image file")
        if x1 is None and y1 is None and x2 is None and y2 is None:
            rect = None
        elif x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            rect = (x1, y1, x2, y2)
        else:
            raise ValidationError("x1,y1,x2,y2 must be all provided or all omitted")
        return build_image_preview(
            source_path=safe_path,
            cache_root=self.project.pyproject_root / CACHE_HOVER_PREVIEWS,
            size=size,
            rect=rect,
        )
