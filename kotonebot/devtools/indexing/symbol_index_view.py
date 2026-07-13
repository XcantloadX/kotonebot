from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from kotonebot.devtools.diagnostics.models import Diagnostic
from kotonebot.devtools.errors import PathSafetyError, ValidationError
from kotonebot.devtools.meta import build_indexing_projection

from .models import IndexedFile, IndexSnapshot
from .query import symbol_to_lite
from .resource_index_store import ResourceIndexStore


class SymbolLiteModel(BaseModel):
    """符号轻量模型。"""

    symbolKey: str
    definitionId: str
    type: str
    name: str
    displayName: str | None
    description: str | None
    prefabId: str | None
    variant: str | None
    metaPath: str
    imagePath: str
    primaryGeometry: dict[str, Any] | None
    searchText: str


class SymbolSnapshotStatsModel(BaseModel):
    """符号快照统计。"""

    fileCount: int
    symbolCount: int
    diagnosticCount: int


class SymbolSnapshotLiteModel(BaseModel):
    """符号索引轻量快照。"""

    indexVersion: int
    contentHash: str
    symbols: list[SymbolLiteModel]
    stats: SymbolSnapshotStatsModel


class SymbolUpdateResultModel(BaseModel):
    """符号索引增量更新结果。"""

    indexVersion: int
    contentHash: str
    updatedMetaPath: str
    removedSymbolKeys: list[str]
    upsertedSymbols: list[SymbolLiteModel]
    diagnostics: list["DiagnosticPayloadModel"]


class DiagnosticPayloadModel(BaseModel):
    code: str
    message: str
    meta_path: str
    severity: str
    definition_id: str | None
    field_path: str | None
    line: int
    column: int
    endLine: int
    endColumn: int

    @classmethod
    def from_diagnostic(cls, diag: Diagnostic) -> "DiagnosticPayloadModel":
        return cls(
            code=diag.code,
            message=diag.message,
            meta_path=diag.meta_path,
            severity=diag.severity,
            definition_id=diag.definition_id,
            field_path=diag.field_path,
            line=diag.line,
            column=diag.column,
            endLine=diag.end_line,
            endColumn=diag.end_column,
        )

    @classmethod
    def from_diagnostics(cls, diagnostics: list[Diagnostic]) -> list["DiagnosticPayloadModel"]:
        return [cls.from_diagnostic(diag) for diag in diagnostics]


class MetaDiagnosticsStatsModel(BaseModel):
    """诊断统计。"""

    total: int
    error: int
    warning: int
    info: int


class MetaDiagnosticsSnapshotModel(BaseModel):
    """诊断快照。"""

    indexVersion: int
    diagnosticsByFile: dict[str, list[DiagnosticPayloadModel]]
    stats: MetaDiagnosticsStatsModel


class SymbolIndexHealthModel(BaseModel):
    """符号索引健康状态。"""

    ready: bool
    indexVersion: int
    lastBuildMs: int
    fileCount: int
    symbolCount: int


class SymbolIndexView:
    """符号索引视图。

    基于 ResourceIndexStore 提供的资源事实快照，构建符号与诊断投影。
    """

    def __init__(
        self,
        *,
        resource_root: Path,
        resource_index_store: ResourceIndexStore | None = None,
        prefab_schema: dict[str, Any] | None = None,
        resource_variants: list[str] | None = None,
        base_variant: str | None = None,
        variant_configured: bool = False,
    ):
        """初始化符号索引视图。"""
        self._resource_root = resource_root.resolve()
        self._resource_index_store = resource_index_store or ResourceIndexStore(resource_root=self._resource_root)
        self._prefab_schema = prefab_schema or {}
        self._resource_variants = resource_variants
        self._base_variant = base_variant
        self._variant_configured = variant_configured
        self._snapshot = IndexSnapshot(index_version=0, content_hash="")
        self._last_build_ms = 0
        self._ready = False

    @property
    def snapshot(self) -> IndexSnapshot:
        """返回当前符号索引快照。"""
        return self._snapshot

    @property
    def last_build_ms(self) -> int:
        """返回最近一次构建耗时（毫秒）。"""
        return self._last_build_ms

    @property
    def ready(self) -> bool:
        """返回视图是否已经完成初始化。"""
        return self._ready

    def ensure_ready(self) -> None:
        """确保视图可用。"""
        if not self._ready:
            self.build_full()

    def build_full(self) -> None:
        """全量重建符号索引投影。"""
        start = time.perf_counter()
        self._resource_index_store.build_full()
        refs = self._resource_index_store.snapshot.meta_refs
        projection = build_indexing_projection(
            meta_refs=refs,
            prefab_schema=self._prefab_schema,
            resource_variants=self._resource_variants,
            base_variant=self._base_variant,
            variant_configured=self._variant_configured,
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

    def update_file(self, *, meta_path: str) -> SymbolUpdateResultModel:
        """按文件路径触发刷新并返回差量结果。"""
        self.ensure_ready()
        start = time.perf_counter()
        normalized_meta_path = self._normalize_meta_path(meta_path)
        previous_snapshot = self._snapshot
        removed_symbol_keys = [k for k, v in previous_snapshot.symbols.items() if v.meta_path == normalized_meta_path]

        self._resource_index_store.build_full()
        refs = self._resource_index_store.snapshot.meta_refs
        projection = build_indexing_projection(
            meta_refs=refs,
            prefab_schema=self._prefab_schema,
            resource_variants=self._resource_variants,
            base_variant=self._base_variant,
            variant_configured=self._variant_configured,
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

        return SymbolUpdateResultModel(
            indexVersion=self._snapshot.index_version,
            contentHash=self._snapshot.content_hash,
            updatedMetaPath=normalized_meta_path,
            removedSymbolKeys=removed_symbol_keys,
            upsertedSymbols=[SymbolLiteModel(**symbol_to_lite(symbol)) for symbol in upserted_symbols],
            diagnostics=DiagnosticPayloadModel.from_diagnostics(file_diags),
        )

    def get_snapshot_lite(self) -> SymbolSnapshotLiteModel:
        """返回轻量符号快照。"""
        self.ensure_ready()
        diagnostics_count = sum(len(items) for items in self._snapshot.diagnostics.values())
        return SymbolSnapshotLiteModel(
            indexVersion=self._snapshot.index_version,
            contentHash=self._snapshot.content_hash,
            symbols=[SymbolLiteModel(**symbol_to_lite(symbol)) for symbol in self._snapshot.symbols.values()],
            stats=SymbolSnapshotStatsModel(
                fileCount=len(self._snapshot.files),
                symbolCount=len(self._snapshot.symbols),
                diagnosticCount=diagnostics_count,
            ),
        )

    def get_diagnostics(self) -> MetaDiagnosticsSnapshotModel:
        """返回诊断快照。"""
        self.ensure_ready()
        total = 0
        error = 0
        warning = 0
        info = 0
        for entries in self._snapshot.diagnostics.values():
            for diag in entries:
                total += 1
                if diag.severity == "error":
                    error += 1
                elif diag.severity == "warning":
                    warning += 1
                elif diag.severity == "info":
                    info += 1
                else:
                    raise ValidationError(f"Unsupported diagnostic severity: {diag.severity}")
        return MetaDiagnosticsSnapshotModel(
            indexVersion=self._snapshot.index_version,
            diagnosticsByFile={
                meta_path: DiagnosticPayloadModel.from_diagnostics(entries)
                for meta_path, entries in self._snapshot.diagnostics.items()
            },
            stats=MetaDiagnosticsStatsModel(total=total, error=error, warning=warning, info=info),
        )

    def get_health(self) -> SymbolIndexHealthModel:
        """返回符号索引健康状态。"""
        self.ensure_ready()
        return SymbolIndexHealthModel(
            ready=self._ready,
            indexVersion=self._snapshot.index_version,
            lastBuildMs=self._last_build_ms,
            fileCount=len(self._snapshot.files),
            symbolCount=len(self._snapshot.symbols),
        )

    def _compute_content_hash(self, files: dict[str, IndexedFile]) -> str:
        """根据投影文件内容计算符号索引哈希。"""
        hasher = hashlib.sha1()
        for meta_path in sorted(files.keys()):
            file = files[meta_path]
            hasher.update(meta_path.encode("utf-8"))
            hasher.update(str(file.mtime_ns).encode("utf-8"))
            hasher.update(str(len(file.definition_ids)).encode("utf-8"))
            hasher.update(",".join(file.definition_ids).encode("utf-8"))
        return hasher.hexdigest()

    def _normalize_meta_path(self, meta_path: str) -> str:
        """规范化 meta 路径并校验合法性。"""
        path = Path(meta_path)
        if not path.is_absolute():
            path = self._resource_root / path
        resolved = path.resolve()
        if not str(resolved).startswith(str(self._resource_root)):
            raise PathSafetyError(f"Meta path is outside resource root: {resolved}")
        if not resolved.as_posix().endswith(".png.json"):
            raise ValidationError("Meta path must end with .png.json")
        return resolved.as_posix()
