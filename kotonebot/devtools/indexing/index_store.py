from __future__ import annotations

import hashlib
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from kotonebot.devtools.meta import build_indexing_projection, scan_meta_files

from .models import IndexedFile, IndexSnapshot
from .query import symbol_to_lite


class IndexStore:
    def __init__(
        self,
        *,
        resource_root: Path,
        prefab_schema: dict[str, Any] | None = None,
        resource_variants: list[str] | None = None,
    ):
        self._resource_root = resource_root.resolve()
        self._prefab_schema = prefab_schema or {}
        self._resource_variants = resource_variants
        self._snapshot = IndexSnapshot(index_version=0, content_hash="")
        self._last_build_ms = 0
        self._ready = False

    @property
    def snapshot(self) -> IndexSnapshot:
        return self._snapshot

    @property
    def last_build_ms(self) -> int:
        return self._last_build_ms

    @property
    def ready(self) -> bool:
        return self._ready

    def ensure_ready(self) -> None:
        if not self._ready:
            self.build_full()

    def build_full(self) -> None:
        start = time.perf_counter()
        refs = scan_meta_files(self._resource_root)
        projection = build_indexing_projection(
            meta_refs=refs,
            prefab_schema=self._prefab_schema,
            resource_variants=self._resource_variants,
        )

        next_version = self._snapshot.index_version + 1
        self._snapshot = IndexSnapshot(
            index_version=next_version,
            content_hash=self._compute_content_hash(projection.files),
            files=projection.files,
            symbols=projection.symbols,
            diagnostics=projection.diagnostics,
            reverse_refs={},
        )
        self._last_build_ms = int((time.perf_counter() - start) * 1000)
        self._ready = True

    def update_file(self, *, meta_path: str) -> dict[str, Any]:
        self.ensure_ready()
        start = time.perf_counter()
        normalized_meta_path = self._normalize_meta_path(meta_path)
        previous_snapshot = self._snapshot
        removed_symbol_keys = [k for k, v in previous_snapshot.symbols.items() if v.meta_path == normalized_meta_path]

        refs = scan_meta_files(self._resource_root)
        projection = build_indexing_projection(
            meta_refs=refs,
            prefab_schema=self._prefab_schema,
            resource_variants=self._resource_variants,
        )
        upserted_symbols = [s for s in projection.symbols.values() if s.meta_path == normalized_meta_path]
        file_diags = projection.diagnostics.get(normalized_meta_path, [])

        next_version = self._snapshot.index_version + 1
        self._snapshot = IndexSnapshot(
            index_version=next_version,
            content_hash=self._compute_content_hash(projection.files),
            files=projection.files,
            symbols=projection.symbols,
            diagnostics=projection.diagnostics,
            reverse_refs={},
        )
        self._last_build_ms = int((time.perf_counter() - start) * 1000)
        self._ready = True

        return {
            "indexVersion": self._snapshot.index_version,
            "contentHash": self._snapshot.content_hash,
            "updatedMetaPath": normalized_meta_path,
            "removedSymbolKeys": removed_symbol_keys,
            "upsertedSymbols": [symbol_to_lite(symbol) for symbol in upserted_symbols],
            "diagnostics": [asdict(diag) for diag in file_diags],
        }

    def get_snapshot_lite(self) -> dict[str, Any]:
        self.ensure_ready()
        diagnostics_count = sum(len(items) for items in self._snapshot.diagnostics.values())
        return {
            "indexVersion": self._snapshot.index_version,
            "contentHash": self._snapshot.content_hash,
            "symbols": [symbol_to_lite(symbol) for symbol in self._snapshot.symbols.values()],
            "stats": {
                "fileCount": len(self._snapshot.files),
                "symbolCount": len(self._snapshot.symbols),
                "diagnosticCount": diagnostics_count,
            },
        }

    def get_diagnostics(self) -> dict[str, Any]:
        self.ensure_ready()
        return {
            "indexVersion": self._snapshot.index_version,
            "diagnosticsByFile": {
                meta_path: [asdict(diag) for diag in entries]
                for meta_path, entries in self._snapshot.diagnostics.items()
            },
        }

    def get_health(self) -> dict[str, Any]:
        self.ensure_ready()
        return {
            "ready": self._ready,
            "indexVersion": self._snapshot.index_version,
            "lastBuildMs": self._last_build_ms,
            "fileCount": len(self._snapshot.files),
            "symbolCount": len(self._snapshot.symbols),
        }

    def _compute_content_hash(self, files: dict[str, IndexedFile]) -> str:
        hasher = hashlib.sha1()
        for meta_path in sorted(files.keys()):
            file = files[meta_path]
            hasher.update(meta_path.encode("utf-8"))
            hasher.update(str(file.mtime_ns).encode("utf-8"))
            hasher.update(str(len(file.definition_ids)).encode("utf-8"))
            hasher.update(",".join(file.definition_ids).encode("utf-8"))
        return hasher.hexdigest()

    def _normalize_meta_path(self, meta_path: str) -> str:
        path = Path(meta_path)
        if not path.is_absolute():
            path = self._resource_root / path
        resolved = path.resolve()
        if not str(resolved).startswith(str(self._resource_root)):
            raise ValueError(f"Meta path is outside resource root: {resolved}")
        if not resolved.as_posix().endswith(".png.json"):
            raise ValueError("Meta path must end with .png.json")
        return resolved.as_posix()
