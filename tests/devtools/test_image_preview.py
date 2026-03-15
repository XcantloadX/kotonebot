from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np

from kotonebot.devtools.image_preview import build_image_preview


def _write_png(path: Path, *, width: int, height: int) -> None:
    image = np.zeros((height, width, 3), dtype=np.uint8)
    ok = cv2.imwrite(str(path), image)
    if not ok:
        raise ValueError("failed to create test png")


def test_build_image_preview_resize_full_image():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.png"
        cache = root / "cache"
        _write_png(source, width=100, height=50)
        preview = build_image_preview(source_path=source, cache_root=cache, size=40, rect=None)
        assert preview.exists()
        result = cv2.imread(str(preview))
        assert result is not None
        assert result.shape[1] == 40
        assert result.shape[0] == 20


def test_build_image_preview_crop_rect():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.png"
        cache = root / "cache"
        _write_png(source, width=100, height=80)
        preview = build_image_preview(
            source_path=source,
            cache_root=cache,
            size=40,
            rect=(10.0, 10.0, 30.0, 20.0),
        )
        assert preview.exists()
        result = cv2.imread(str(preview))
        assert result is not None
        assert result.shape[1] == 40
        assert result.shape[0] == 20


def test_build_image_preview_without_size_keeps_original_dimensions():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source.png"
        cache = root / "cache"
        _write_png(source, width=100, height=80)
        preview = build_image_preview(
            source_path=source,
            cache_root=cache,
            size=None,
            rect=(10.0, 10.0, 30.0, 20.0),
        )
        assert preview.exists()
        result = cv2.imread(str(preview))
        assert result is not None
        assert result.shape[1] == 20
        assert result.shape[0] == 10
