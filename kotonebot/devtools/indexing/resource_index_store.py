from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, Field

from kotonebot.devtools.meta.scanner import DocRef, scan_docs


class ResourceSnapshot(BaseModel):
    """资源扫描快照。

    该快照仅包含文件层面的事实数据，不包含符号语义与业务操作。
    """

    index_version: int
    content_hash: str
    doc_refs: list[DocRef] = Field(default_factory=list)


class ResourceIndexStore:
    """资源事实索引。

    负责统一扫描资源根目录下的文档，生成可复用的文件事实快照，
    供 SymbolIndex / DocumentIndex 等上层投影视图复用。
    """

    def __init__(self, *, resource_root: Path):
        """初始化资源事实索引。"""
        self._resource_root = resource_root.resolve()
        self._snapshot = ResourceSnapshot(index_version=0, content_hash="")
        self._ready = False

    @property
    def snapshot(self) -> ResourceSnapshot:
        """返回当前资源快照。"""
        return self._snapshot

    @property
    def ready(self) -> bool:
        """返回索引是否已经完成初始化。"""
        return self._ready

    def ensure_ready(self) -> None:
        """确保索引已构建。"""
        if not self._ready:
            self.build_full()

    def build_full(self) -> None:
        """全量扫描资源并刷新快照。"""
        refs = scan_docs(self._resource_root)
        self._snapshot = ResourceSnapshot(
            index_version=self._snapshot.index_version + 1,
            content_hash=self._compute_content_hash(refs),
            doc_refs=refs,
        )
        self._ready = True

    def _compute_content_hash(self, refs: list[DocRef]) -> str:
        """计算资源快照哈希。"""
        hasher = hashlib.sha1()
        for ref in refs:
            hasher.update(ref.image_path.encode("utf-8"))
            hasher.update(str(ref.mtime_ns).encode("utf-8"))
            hasher.update(str(ref.size).encode("utf-8"))
        return hasher.hexdigest()
