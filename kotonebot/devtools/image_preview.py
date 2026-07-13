from __future__ import annotations

import hashlib
import os
from pathlib import Path

import cv2
from kotonebot.devtools.errors import InvalidImageError, ValidationError


Rect = tuple[int, int, int, int]


def _normalize_rect(rect: tuple[float, float, float, float]) -> Rect:
    x1 = int(rect[0])
    y1 = int(rect[1])
    x2 = int(rect[2])
    y2 = int(rect[3])
    if x2 <= x1 or y2 <= y1:
        raise ValidationError("invalid rect")
    return (x1, y1, x2, y2)


def _cache_key(*, source_path: Path, mtime_ns: int, size: int, rect: Rect | None) -> str:
    hasher = hashlib.sha1()
    hasher.update(source_path.as_posix().encode("utf-8"))
    hasher.update(str(mtime_ns).encode("utf-8"))
    hasher.update(str(size).encode("utf-8"))
    if rect is None:
        hasher.update(b"full")
    else:
        hasher.update(f"{rect[0]},{rect[1]},{rect[2]},{rect[3]}".encode("utf-8"))
    return hasher.hexdigest()


def build_image_preview(
    *,
    source_path: Path,
    cache_root: Path,
    size: int | None,
    rect: tuple[float, float, float, float] | None,
) -> Path:
    if size is not None and size <= 0:
        raise ValidationError("size must be positive")
    if not source_path.exists():
        raise FileNotFoundError(f"Image not found: {source_path}")
    if not source_path.is_file():
        raise InvalidImageError(f"Not a file: {source_path}")

    normalized_rect = _normalize_rect(rect) if rect is not None else None
    stat = source_path.stat()
    key_size = -1 if size is None else size
    key = _cache_key(source_path=source_path.resolve(), mtime_ns=stat.st_mtime_ns, size=key_size, rect=normalized_rect)
    cache_root.mkdir(parents=True, exist_ok=True)
    target_path = cache_root / f"{key}.png"
    if target_path.exists() and target_path.stat().st_size > 0:
        return target_path

    image = cv2.imread(str(source_path))
    if image is None:
        raise InvalidImageError(f"Could not read image: {source_path}")

    if normalized_rect is not None:
        height, width = image.shape[:2]
        x1, y1, x2, y2 = normalized_rect
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            raise ValidationError("rect is out of bounds")
        image = image[y1:y2, x1:x2]

    if size is None:
        resized = image
    else:
        cropped_height, cropped_width = image.shape[:2]
        longest = max(cropped_width, cropped_height)
        if longest <= 0:
            raise ValidationError("invalid image size")
        scale = size / float(longest)
        resized_width = max(1, int(round(cropped_width * scale)))
        resized_height = max(1, int(round(cropped_height * scale)))
        resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)

    temp_path = target_path.with_suffix(".tmp.png")
    ok = cv2.imwrite(str(temp_path), resized)
    if not ok:
        raise InvalidImageError(f"failed to write preview: {temp_path}")
    os.replace(temp_path, target_path)
    return target_path
