from __future__ import annotations

import hashlib
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from kotonebot.devtools.meta import DefinitionRef, parse_meta_v2_file, resolve_prefab_variants

from .diagnostics import make_error
from .models import Diagnostic, IndexedFile, IndexedSymbol, IndexSnapshot
from .parser import parse_meta_file
from .query import symbol_to_lite
from .scanner import scan_meta_files


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
        files: dict[str, IndexedFile] = {}
        symbols: dict[str, IndexedSymbol] = {}
        diagnostics: dict[str, list[Diagnostic]] = {}

        for entry in scan_meta_files(self._resource_root):
            try:
                indexed_file, file_symbols, file_diags = parse_meta_file(
                    abs_meta_path=entry.abs_meta_path,
                    meta_path=entry.meta_path,
                    image_path=entry.image_path,
                    mtime_ns=entry.mtime_ns,
                    prefab_schema=self._prefab_schema,
                )
                files[indexed_file.meta_path] = indexed_file
                if file_diags:
                    diagnostics[indexed_file.meta_path] = file_diags
                for symbol in file_symbols:
                    symbols[symbol.symbol_key] = symbol
            except Exception as exc:
                diagnostics[entry.meta_path] = [
                    make_error(
                        code="INDEX_FILE_PARSE_ERROR",
                        message=str(exc),
                        meta_path=entry.meta_path,
                    )
                ]

        self._append_variant_diagnostics(files=files, diagnostics=diagnostics)

        next_version = self._snapshot.index_version + 1
        self._snapshot = IndexSnapshot(
            index_version=next_version,
            content_hash=self._compute_content_hash(files),
            files=files,
            symbols=symbols,
            diagnostics=diagnostics,
            reverse_refs={},
        )
        self._last_build_ms = int((time.perf_counter() - start) * 1000)
        self._ready = True

    def update_file(self, *, meta_path: str) -> dict[str, Any]:
        self.ensure_ready()
        start = time.perf_counter()
        normalized_meta_path = self._normalize_meta_path(meta_path)

        files = dict(self._snapshot.files)
        symbols = dict(self._snapshot.symbols)
        diagnostics = dict(self._snapshot.diagnostics)

        removed_symbol_keys = [k for k, v in symbols.items() if v.meta_path == normalized_meta_path]
        for key in removed_symbol_keys:
            del symbols[key]

        if normalized_meta_path in files:
            del files[normalized_meta_path]
        if normalized_meta_path in diagnostics:
            del diagnostics[normalized_meta_path]

        upserted_symbols: list[IndexedSymbol] = []
        file_diags: list[Diagnostic] = []

        abs_meta_path = Path(normalized_meta_path)
        if abs_meta_path.exists():
            stat = abs_meta_path.stat()
            try:
                indexed_file, file_symbols, file_diags = parse_meta_file(
                    abs_meta_path=abs_meta_path,
                    meta_path=normalized_meta_path,
                    image_path=abs_meta_path.with_suffix("").as_posix(),
                    mtime_ns=stat.st_mtime_ns,
                    prefab_schema=self._prefab_schema,
                )
                files[normalized_meta_path] = indexed_file
                upserted_symbols = file_symbols
                for symbol in file_symbols:
                    symbols[symbol.symbol_key] = symbol
                if file_diags:
                    diagnostics[normalized_meta_path] = file_diags
            except Exception as exc:
                file_diags = [
                    make_error(
                        code="INDEX_FILE_PARSE_ERROR",
                        message=str(exc),
                        meta_path=normalized_meta_path,
                    )
                ]
                diagnostics[normalized_meta_path] = file_diags

        self._append_variant_diagnostics(files=files, diagnostics=diagnostics)

        next_version = self._snapshot.index_version + 1
        self._snapshot = IndexSnapshot(
            index_version=next_version,
            content_hash=self._compute_content_hash(files),
            files=files,
            symbols=symbols,
            diagnostics=diagnostics,
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

    def _append_variant_diagnostics(
        self,
        *,
        files: dict[str, IndexedFile],
        diagnostics: dict[str, list[Diagnostic]],
    ) -> None:
        refs: list[DefinitionRef] = []
        for meta_path in files.keys():
            try:
                data = parse_meta_v2_file(Path(meta_path))
            except Exception:
                continue
            for definition_id, definition in data.definitions.items():
                refs.append(
                    DefinitionRef(
                        meta_path=meta_path,
                        definition_id=definition_id,
                        definition=definition,
                    )
                )

        try:
            resolve_prefab_variants(refs, resource_variants=self._resource_variants)
        except ValueError as exc:
            first_meta = refs[0].meta_path if refs else self._resource_root.as_posix()
            diagnostics.setdefault(first_meta, []).append(
                make_error(
                    code="INDEX_VARIANT_INVALID",
                    message=str(exc),
                    meta_path=first_meta,
                    field_path="definitions",
                )
            )
