from __future__ import annotations

import re
import string
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.path_utils import get_safe_path
from .resource_index_store import ResourceIndexStore


class DocumentEntry(BaseModel):
    """文档索引条目。"""

    image_path: str
    meta_path: str
    strategy: str
    role: str
    variant: str | None
    file_dir: str
    file_name: str
    file_ext: str
    scoped_base: bool
    has_variant_name: bool
    template: str | None
    group_key: str


class DocumentIndexSnapshot(BaseModel):
    """文档索引快照。"""

    documents_by_image: dict[str, DocumentEntry] = Field(default_factory=dict)
    groups: dict[str, list[DocumentEntry]] = Field(default_factory=dict)


class RenameDocumentItemModel(BaseModel):
    """文档重命名单项。"""

    variant: str
    sourceImagePath: str
    targetImagePath: str
    sourceMetaPath: str
    targetMetaPath: str


class RenameFileItemModel(BaseModel):
    """文件重命名单项。"""

    kind: Literal["image", "meta"]
    variant: str
    sourcePath: str
    targetPath: str


class RenameDocumentPrecheckResultModel(BaseModel):
    """文档重命名预检结果。"""

    documents: list[RenameDocumentItemModel]
    fileRenames: list[RenameFileItemModel]
    conflicts: list[str]
    hasConflicts: bool


class RenameDocumentExecuteResultModel(BaseModel):
    """文档重命名执行结果。"""

    documents: list[RenameDocumentItemModel]
    fileRenames: list[RenameFileItemModel]
    renamedFileCount: int
    renamedDocumentCount: int


class DocumentIndexView:
    """文档索引视图。

    该视图负责文档级关系（base/variant/group）与重命名预检计划，不负责执行副作用。
    """

    def __init__(
        self,
        *,
        project: Project,
        resource_root: Path,
        image_suffixes: set[str],
        resource_index_store: ResourceIndexStore | None = None,
    ):
        """初始化文档索引视图。"""
        self.project = project
        self.resource_root = resource_root.resolve()
        self.resource_index_store = resource_index_store or ResourceIndexStore(resource_root=self.resource_root)
        self.image_suffixes = image_suffixes
        self._snapshot = DocumentIndexSnapshot(documents_by_image={}, groups={})
        self._ready = False
        self._variant_path_placeholders = {
            "variant_name",
            "file_name",
            "file_name_ext",
            "file_ext",
            "file_dir",
        }

    def ensure_ready(self) -> None:
        """确保文档索引已经构建。"""
        if not self._ready:
            self.build_full()

    def build_full(self) -> None:
        """基于资源快照全量构建文档索引。"""
        self.resource_index_store.build_full()
        refs = self.resource_index_store.snapshot.meta_refs
        documents_by_image: dict[str, DocumentEntry] = {}
        groups: dict[str, list[DocumentEntry]] = {}
        for ref in refs:
            image_path = Path(ref.image_path)
            meta_path = Path(ref.meta_path)
            entry = self._build_document_entry(image_path=image_path, meta_path=meta_path)
            documents_by_image[entry.image_path] = entry
            groups.setdefault(entry.group_key, []).append(entry)
        self._snapshot = DocumentIndexSnapshot(documents_by_image=documents_by_image, groups=groups)
        self._ready = True



    def _get_variant_config(self) -> tuple[list[str], str, str] | None:
        """读取并校验 variant 配置。"""
        if self.project.conf.variant is None:
            return None
        variants = self.project.conf.variant.variants
        base_variant = self.project.conf.variant.base
        path_pattern = self.project.conf.variant.path_pattern
        if variants is None:
            raise ValueError("variant.variants must be configured in pyproject.toml")
        if base_variant is None:
            raise ValueError("variant.base must be configured in pyproject.toml")
        if path_pattern is None:
            raise ValueError("variant.path_pattern must be configured in pyproject.toml")
        return (variants, base_variant, path_pattern)

    def _build_pattern_regex(self, template: str) -> tuple[re.Pattern[str], set[str]]:
        """为 pattern 模式构建路径解析正则。"""
        formatter = string.Formatter()
        parts: list[str] = ["^"]
        seen_fields: set[str] = set()
        for literal_text, field_name, _, _ in formatter.parse(template):
            parts.append(re.escape(literal_text))
            if field_name is None:
                continue
            if field_name == "":
                raise ValueError("variant.path_pattern contains empty placeholder")
            if field_name not in self._variant_path_placeholders:
                raise ValueError(f"variant.path_pattern contains unsupported placeholder: {field_name}")
            if field_name in seen_fields:
                raise ValueError(f"variant.path_pattern contains duplicated placeholder: {field_name}")
            seen_fields.add(field_name)
            if field_name == "file_dir":
                parts.append("(?P<file_dir>.*?)")
            elif field_name == "variant_name":
                parts.append("(?P<variant_name>[^/]+)")
            elif field_name == "file_name":
                parts.append("(?P<file_name>[^/]+)")
            elif field_name == "file_name_ext":
                parts.append("(?P<file_name_ext>[^/]+)")
            elif field_name == "file_ext":
                parts.append("(?P<file_ext>[^/]+)")
        parts.append("$")
        return (re.compile("".join(parts)), seen_fields)

    def _build_document_entry(self, *, image_path: Path, meta_path: Path) -> DocumentEntry:
        """将单个 image/meta 路径解析为文档条目。"""
        if image_path.suffix.lower() not in self.image_suffixes:
            raise ValueError(f"Image path is not supported: {image_path}")
        variant_config = self._get_variant_config()
        if variant_config is None:
            return DocumentEntry(
                image_path=image_path.as_posix(),
                meta_path=meta_path.as_posix(),
                strategy="none",
                role="base",
                variant=None,
                file_dir=image_path.parent.as_posix(),
                file_name=image_path.stem,
                file_ext=image_path.suffix[1:],
                scoped_base=False,
                has_variant_name=False,
                template=None,
                group_key=f"none|{image_path.as_posix()}",
            )
        variants, base_variant, path_pattern = variant_config
        rel = image_path.resolve().relative_to(self.resource_root)
        rel_posix = rel.as_posix()
        parent_posix = rel.parent.as_posix()
        file_dir_default = "" if parent_posix == "." else parent_posix
        file_name_default = image_path.stem
        file_ext_default = image_path.suffix[1:]
        if file_ext_default == "":
            raise ValueError(f"Image path has no extension: {image_path}")

        if path_pattern == "nest":
            parent_parts = list(rel.parent.parts) if parent_posix != "." else []
            if len(parent_parts) > 0 and parent_parts[0] in variants:
                variant_name = parent_parts[0]
                file_dir = Path(*parent_parts[1:]).as_posix() if len(parent_parts) > 1 else ""
                return DocumentEntry(
                    image_path=image_path.as_posix(),
                    meta_path=meta_path.as_posix(),
                    strategy="nest",
                    role="variant",
                    variant=variant_name,
                    file_dir=file_dir,
                    file_name=file_name_default,
                    file_ext=file_ext_default,
                    scoped_base=False,
                    has_variant_name=True,
                    template=None,
                    group_key=f"nest|{file_dir}|{file_name_default}|{file_ext_default}",
                )
            if len(parent_parts) > 0 and parent_parts[0] == base_variant:
                file_dir = Path(*parent_parts[1:]).as_posix() if len(parent_parts) > 1 else ""
                return DocumentEntry(
                    image_path=image_path.as_posix(),
                    meta_path=meta_path.as_posix(),
                    strategy="nest",
                    role="base",
                    variant=None,
                    file_dir=file_dir,
                    file_name=file_name_default,
                    file_ext=file_ext_default,
                    scoped_base=True,
                    has_variant_name=True,
                    template=None,
                    group_key=f"nest|{file_dir}|{file_name_default}|{file_ext_default}",
                )
            return DocumentEntry(
                image_path=image_path.as_posix(),
                meta_path=meta_path.as_posix(),
                strategy="nest",
                role="base",
                variant=None,
                file_dir=file_dir_default,
                file_name=file_name_default,
                file_ext=file_ext_default,
                scoped_base=False,
                has_variant_name=True,
                template=None,
                group_key=f"nest|{file_dir_default}|{file_name_default}|{file_ext_default}",
            )

        if path_pattern == "flat":
            role = "base"
            variant_name: str | None = None
            file_name = file_name_default
            for variant in variants:
                suffix = f"_{variant}"
                if file_name_default.endswith(suffix):
                    file_name = file_name_default[: -len(suffix)]
                    if file_name == "":
                        raise ValueError(f"Invalid flat variant file name: {image_path}")
                    role = "variant"
                    variant_name = variant
                    break
            return DocumentEntry(
                image_path=image_path.as_posix(),
                meta_path=meta_path.as_posix(),
                strategy="flat",
                role=role,
                variant=variant_name,
                file_dir=file_dir_default,
                file_name=file_name,
                file_ext=file_ext_default,
                scoped_base=False,
                has_variant_name=True,
                template=None,
                group_key=f"flat|{file_dir_default}|{file_name}|{file_ext_default}",
            )

        if not path_pattern.startswith("pattern:"):
            raise ValueError("variant.path_pattern must be 'nest', 'flat', or 'pattern: <template>'")
        template = path_pattern[len("pattern:"):].strip()
        if template == "":
            raise ValueError("variant.path_pattern 'pattern:' template cannot be empty")
        regex, fields = self._build_pattern_regex(template)
        match = regex.match(rel_posix)
        if match is None:
            raise ValueError(f"Image path does not match variant.path_pattern template: {image_path}")
        values = match.groupdict()
        file_dir = values.get("file_dir") or ""
        file_name = values.get("file_name")
        file_ext = values.get("file_ext")
        file_name_ext = values.get("file_name_ext")
        if file_name_ext is not None:
            if "." not in file_name_ext:
                raise ValueError(f"file_name_ext must contain extension: {image_path}")
            name_from_ext, ext_from_ext = file_name_ext.rsplit(".", 1)
            if name_from_ext == "" or ext_from_ext == "":
                raise ValueError(f"file_name_ext is invalid: {image_path}")
            if file_name is None:
                file_name = name_from_ext
            elif file_name != name_from_ext:
                raise ValueError(f"file_name and file_name_ext mismatch: {image_path}")
            if file_ext is None:
                file_ext = ext_from_ext
            elif file_ext != ext_from_ext:
                raise ValueError(f"file_ext and file_name_ext mismatch: {image_path}")
        if file_name is None or file_name == "":
            raise ValueError(f"Cannot resolve file_name from path: {image_path}")
        if file_ext is None or file_ext == "":
            raise ValueError(f"Cannot resolve file_ext from path: {image_path}")
        role = "base"
        variant_name = None
        has_variant_name = "variant_name" in fields
        if has_variant_name:
            parsed_variant = values.get("variant_name")
            if parsed_variant is None or parsed_variant == "":
                raise ValueError(f"Cannot resolve variant_name from path: {image_path}")
            if parsed_variant == base_variant:
                role = "base"
            elif parsed_variant in variants:
                role = "variant"
                variant_name = parsed_variant
            else:
                raise ValueError(f"variant_name '{parsed_variant}' is not declared in variant config")
        return DocumentEntry(
            image_path=image_path.as_posix(),
            meta_path=meta_path.as_posix(),
            strategy="pattern",
            role=role,
            variant=variant_name,
            file_dir=file_dir,
            file_name=file_name,
            file_ext=file_ext,
            scoped_base=False,
            has_variant_name=has_variant_name,
            template=template,
            group_key=f"pattern|{template}|{file_dir}|{file_name}|{file_ext}",
        )

    def _render_target_image_path(self, *, member: DocumentEntry, target_descriptor: DocumentEntry, source_descriptor: DocumentEntry) -> Path:
        """将组内成员映射到目标重命名后的图片路径。"""
        variant_config = self._get_variant_config()
        if variant_config is None:
            return get_safe_path(target_descriptor.image_path, self.project)
        _, base_variant, _ = variant_config
        if member.strategy == "nest":
            file_name_ext = f"{target_descriptor.file_name}.{target_descriptor.file_ext}"
            if member.role == "variant":
                if member.variant is None:
                    raise ValueError("variant member requires variant name")
                rel = f"{member.variant}/{target_descriptor.file_dir}/{file_name_ext}" if target_descriptor.file_dir else f"{member.variant}/{file_name_ext}"
                return get_safe_path(rel, self.project)
            if source_descriptor.role == "base":
                scoped_base = target_descriptor.scoped_base
            else:
                scoped_base = member.scoped_base
            if scoped_base:
                rel = f"{base_variant}/{target_descriptor.file_dir}/{file_name_ext}" if target_descriptor.file_dir else f"{base_variant}/{file_name_ext}"
            else:
                rel = f"{target_descriptor.file_dir}/{file_name_ext}" if target_descriptor.file_dir else file_name_ext
            return get_safe_path(rel, self.project)
        if member.strategy == "flat":
            if member.role == "variant":
                if member.variant is None:
                    raise ValueError("variant member requires variant name")
                file_name_ext = f"{target_descriptor.file_name}_{member.variant}.{target_descriptor.file_ext}"
            else:
                file_name_ext = f"{target_descriptor.file_name}.{target_descriptor.file_ext}"
            rel = f"{target_descriptor.file_dir}/{file_name_ext}" if target_descriptor.file_dir else file_name_ext
            return get_safe_path(rel, self.project)
        if member.strategy == "pattern":
            if member.template is None:
                raise ValueError("pattern member requires template")
            if source_descriptor.strategy != "pattern":
                raise ValueError("source descriptor strategy mismatch")
            render_variant: str
            if member.role == "variant":
                if member.variant is None:
                    raise ValueError("variant member requires variant name")
                render_variant = member.variant
            else:
                render_variant = base_variant
            rendered = member.template.format(
                variant_name=render_variant,
                file_name=target_descriptor.file_name,
                file_name_ext=f"{target_descriptor.file_name}.{target_descriptor.file_ext}",
                file_ext=target_descriptor.file_ext,
                file_dir=target_descriptor.file_dir,
            ).strip()
            if rendered == "":
                raise ValueError("variant.path_pattern resolved to empty path")
            return get_safe_path(rendered, self.project)
        if member.strategy == "none":
            return get_safe_path(target_descriptor.image_path, self.project)
        raise ValueError(f"Unsupported strategy: {member.strategy}")

    def precheck_rename_document(self, *, source_image_path: str, target_image_path: str) -> RenameDocumentPrecheckResultModel:
        """执行文档重命名预检并返回计划与冲突。"""
        self.build_full()
        source_image = get_safe_path(source_image_path, self.project)
        target_image = get_safe_path(target_image_path, self.project)
        if source_image.suffix.lower() not in self.image_suffixes:
            raise ValueError(f"Source path is not an image: {source_image}")
        if target_image.suffix.lower() not in self.image_suffixes:
            raise ValueError(f"Target path is not an image: {target_image}")
        if source_image == target_image:
            raise ValueError("Target path must be different from source path")

        source_entry = self._snapshot.documents_by_image.get(source_image.as_posix())
        if source_entry is None:
            raise ValueError(f"Source document is not indexed: {source_image.as_posix()}")
        target_entry = self._build_document_entry(
            image_path=target_image,
            meta_path=Path(str(target_image) + ".json"),
        )
        if source_entry.strategy != target_entry.strategy:
            raise ValueError("Target path pattern type must match source document pattern type")
        if source_entry.role != target_entry.role:
            raise ValueError("Target path must keep the same variant role as source path")
        if source_entry.role == "variant" and source_entry.variant != target_entry.variant:
            raise ValueError("Target path must keep the same variant name as source path")
        if source_entry.strategy == "pattern" and source_entry.template != target_entry.template:
            raise ValueError("Target path pattern template must match source document pattern template")

        documents: list[RenameDocumentItemModel] = []
        file_renames: list[RenameFileItemModel] = []
        conflicts: list[str] = []
        group_members = self._snapshot.groups.get(source_entry.group_key)
        if group_members is None:
            raise ValueError(f"Source document group not found: {source_entry.group_key}")
        for member in group_members:
            source_member_image = Path(member.image_path)
            source_member_meta = Path(member.meta_path)
            source_image_exists = source_member_image.exists()
            source_meta_exists = source_member_meta.exists()
            if source_image_exists != source_meta_exists:
                conflicts.append(f"Inconsistent document files: {source_member_image.as_posix()} / {source_member_meta.as_posix()}")
                continue
            if not source_image_exists:
                continue
            target_member_image = self._render_target_image_path(
                member=member,
                target_descriptor=target_entry,
                source_descriptor=source_entry,
            )
            target_member_meta = Path(str(target_member_image) + ".json")
            variant = member.variant if member.variant is not None else "base"
            documents.append(
                RenameDocumentItemModel(
                    variant=variant,
                    sourceImagePath=source_member_image.as_posix(),
                    targetImagePath=target_member_image.as_posix(),
                    sourceMetaPath=source_member_meta.as_posix(),
                    targetMetaPath=target_member_meta.as_posix(),
                )
            )
            file_renames.append(
                RenameFileItemModel(
                    kind="image",
                    variant=variant,
                    sourcePath=source_member_image.as_posix(),
                    targetPath=target_member_image.as_posix(),
                )
            )
            file_renames.append(
                RenameFileItemModel(
                    kind="meta",
                    variant=variant,
                    sourcePath=source_member_meta.as_posix(),
                    targetPath=target_member_meta.as_posix(),
                )
            )

        if len(documents) == 0:
            conflicts.append("No existing related documents found to rename")

        source_file_set = {item.sourcePath for item in file_renames}
        target_file_set: set[str] = set()
        for item in file_renames:
            source_path = Path(item.sourcePath)
            target_path = Path(item.targetPath)
            if not source_path.exists():
                conflicts.append(f"Source file not found: {source_path.as_posix()}")
            if not target_path.parent.exists():
                conflicts.append(f"Target parent directory not found: {target_path.parent.as_posix()}")
            target_key = target_path.as_posix()
            if target_key in target_file_set:
                conflicts.append(f"Duplicate target path in rename plan: {target_key}")
            target_file_set.add(target_key)
            if target_key not in source_file_set and target_path.exists():
                conflicts.append(f"Target path already exists: {target_key}")

        return RenameDocumentPrecheckResultModel(
            documents=documents,
            fileRenames=file_renames,
            conflicts=conflicts,
            hasConflicts=len(conflicts) > 0,
        )
