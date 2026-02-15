from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from kotonebot.devtools.meta import scan_meta_v2_files


@dataclass(slots=True)
class ScanEntry:
    meta_path: str
    image_path: str
    abs_meta_path: Path
    mtime_ns: int
    size: int


def scan_meta_files(resource_root: Path) -> list[ScanEntry]:
    entries: list[ScanEntry] = []
    for ref in scan_meta_v2_files(resource_root):
        entries.append(
            ScanEntry(
                meta_path=ref.meta_path,
                image_path=ref.image_path,
                abs_meta_path=ref.abs_meta_path,
                mtime_ns=ref.mtime_ns,
                size=ref.size,
            )
        )
    return entries
