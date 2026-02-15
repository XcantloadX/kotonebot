from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from .models import MetaV2Model

@dataclass(slots=True)
class MetaFileRef:
    meta_path: str
    image_path: str
    abs_meta_path: Path
    mtime_ns: int
    size: int


def scan_meta_v2_files(resource_root: Path) -> list[MetaFileRef]:
    if not resource_root.exists() or not resource_root.is_dir():
        raise ValueError(f"Resource root does not exist or is not a directory: {resource_root}")

    entries: list[MetaFileRef] = []
    for abs_meta_path in sorted(resource_root.rglob("*.png.json")):
        stat = abs_meta_path.stat()
        entries.append(
            MetaFileRef(
                meta_path=abs_meta_path.as_posix(),
                image_path=abs_meta_path.with_suffix("").as_posix(),
                abs_meta_path=abs_meta_path,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
            )
        )
    return entries


def parse_meta_v2_file(abs_meta_path: Path) -> MetaV2Model:
    data = json.loads(abs_meta_path.read_text(encoding="utf-8"))
    try:
        return MetaV2Model.model_validate(data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
