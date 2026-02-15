from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ScanEntry:
    meta_path: str
    image_path: str
    abs_meta_path: Path
    mtime_ns: int
    size: int


def scan_meta_files(resource_root: Path) -> list[ScanEntry]:
    if not resource_root.exists() or not resource_root.is_dir():
        raise ValueError(f"Resource root does not exist or is not a directory: {resource_root}")

    entries: list[ScanEntry] = []
    for abs_meta_path in sorted(resource_root.rglob("*.png.json")):
        stat = abs_meta_path.stat()
        meta_path = abs_meta_path.as_posix()
        image_path = abs_meta_path.with_suffix("").as_posix()
        entries.append(
            ScanEntry(
                meta_path=meta_path,
                image_path=image_path,
                abs_meta_path=abs_meta_path,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
            )
        )
    return entries
