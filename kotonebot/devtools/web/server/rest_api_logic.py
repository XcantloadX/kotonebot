import json
import logging
import os
import platform
import shutil
import string
import subprocess
import uuid
import tempfile
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from kotonebot.devtools.image_preview import build_image_preview
from kotonebot.devtools.server_commands.workspace_service import WorkspaceService
from kotonebot.devtools.indexing.symbol_index_view import SymbolIndexView
from kotonebot.devtools.indexing.document_index_view import (
    DocumentIndexView,
    RenameDocumentExecuteResultModel,
    RenameDocumentPrecheckResultModel,
)
from kotonebot.devtools.indexing.resource_index_store import ResourceIndexStore
from kotonebot.devtools.meta import DefinitionV3Model, merge_prefab_definition, parse_meta_file
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.project.scanner import scan_prefabs
from kotonebot.devtools.path_utils import get_safe_path


class RestApiLogic:
    def __init__(self, project: Project):
        self.workspace = WorkspaceService(project)
        self.project = project
        self._prefabs_cache: Optional[dict[str, Any]] = None
        self.project_root = self.workspace.project_root
        self.pyproject_root = project.pyproject_root
        self.resource_index_store = self.workspace.resource_index_store
        self.symbol_index_view = self.workspace.symbol_index_view
        self.document_index_view = self.workspace.document_index_view
        self.thumbnail_cache_root = project.pyproject_root / ".kotonebot" / "cache" / "thumbnails"
        self.image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
        self.variant_path_placeholders = {
            "variant_name",
            "file_name",
            "file_name_ext",
            "file_ext",
            "file_dir",
        }

    def _get_prefabs_cache(self) -> dict[str, Any]:
        if self._prefabs_cache is not None:
            return self._prefabs_cache
        if not self.project.conf or not self.project.conf.editor or not self.project.conf.editor.prefabs_module:
            self._prefabs_cache = {"version": 1, "prefabs": {}}
            return self._prefabs_cache
        self._prefabs_cache = scan_prefabs(self.project.conf.editor.prefabs_module)
        if not isinstance(self._prefabs_cache, dict):
            raise ValueError("Invalid prefab schema response")
        self._prefabs_cache.setdefault("prefabs", {})
        return self._prefabs_cache

    def _is_image_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.image_suffixes

    def _get_thumbnail_path(self, source: Path, size: int) -> Path:
        if size <= 0:
            raise ValueError("size must be positive")
        try:
            rel = source.resolve().relative_to(self.project_root)
        except Exception as e:
            raise ValueError(str(e))
        size_dir = self.thumbnail_cache_root / str(size)
        target_dir = size_dir / rel.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / rel.name

    def _ensure_thumbnail(self, source: Path, size: int) -> Path:
        cache_path = self._get_thumbnail_path(source, size)
        regenerate = True
        if cache_path.exists():
            src_stat = source.stat()
            cache_stat = cache_path.stat()
            if cache_stat.st_mtime >= src_stat.st_mtime and cache_stat.st_size > 0:
                regenerate = False
        if regenerate:
            img = cv2.imread(str(source))
            if img is None:
                raise ValueError(f"Could not read image: {source}")
            height, width = img.shape[:2]
            longest = max(width, height)
            if longest <= 0:
                raise ValueError("invalid image size")
            scale = size / float(longest)
            new_width = max(1, int(round(width * scale)))
            new_height = max(1, int(round(height * scale)))
            resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(cache_path), resized)
        return cache_path

    

    def _assert_variant_declared(self, variant: str) -> str:
        variant_name = variant.strip()
        if variant_name == "":
            raise ValueError("variant cannot be empty")
        declared_variants = self.project.conf.variant.variants if self.project.conf.variant and self.project.conf.variant.variants is not None else []
        if variant_name not in declared_variants:
            raise ValueError(f"variant '{variant_name}' is not declared in variant.variants")
        return variant_name

    def _resolve_variant_import_target_path(self, *, base_image_path: Path, variant_name: str) -> Path:
        if self.project.conf.variant is None:
            raise ValueError("Missing [tool.kotonebot.variant] in pyproject.toml")
        variant_path_pattern = self.project.conf.variant.path_pattern
        if variant_path_pattern is None:
            raise ValueError("Missing [tool.kotonebot.variant.path_pattern] in pyproject.toml")
        rel_base_image_path = base_image_path.resolve().relative_to(self.project_root)
        declared_variants = self.project.conf.variant.variants if self.project.conf.variant.variants is not None else []
        base_variant = self.project.conf.variant.base
        base_parent_parts = list(rel_base_image_path.parent.parts)
        if base_variant is not None and len(base_parent_parts) > 0:
            head = base_parent_parts[0]
            if head == base_variant:
                base_parent_parts = base_parent_parts[1:]
            elif head in declared_variants:
                raise ValueError(f"base image path must use variant.base prefix '{base_variant}' when variant prefix exists")
        file_ext = base_image_path.suffix[1:]
        if file_ext == "":
            raise ValueError(f"base image path has no extension: {base_image_path}")
        file_dir = Path(*base_parent_parts).as_posix() if len(base_parent_parts) > 0 else ""

        rendered: str
        if variant_path_pattern == "nest":
            rendered = f"{variant_name}/{file_dir}/{base_image_path.name}" if file_dir else f"{variant_name}/{base_image_path.name}"
        elif variant_path_pattern == "flat":
            file_name_with_variant = f"{base_image_path.stem}_{variant_name}.{file_ext}"
            rendered = f"{file_dir}/{file_name_with_variant}" if file_dir else file_name_with_variant
        elif variant_path_pattern.startswith("pattern:"):
            template = variant_path_pattern[len("pattern:"):].strip()
            if template == "":
                raise ValueError("variant.path_pattern 'pattern:' template cannot be empty")
            formatter = string.Formatter()
            for _, field_name, _, _ in formatter.parse(template):
                if field_name is None:
                    continue
                if field_name == "":
                    raise ValueError("variant.path_pattern contains empty placeholder")
                if field_name not in self.variant_path_placeholders:
                    raise ValueError(f"variant.path_pattern contains unsupported placeholder: {field_name}")
            rendered = template.format(
                variant_name=variant_name,
                file_name=base_image_path.stem,
                file_name_ext=base_image_path.name,
                file_ext=file_ext,
                file_dir=file_dir,
            ).strip()
        else:
            raise ValueError("variant.path_pattern must be 'nest', 'flat', or 'pattern: <template>'")

        if rendered == "":
            raise ValueError("variant.path_pattern resolved to empty path")
        target_image_path = get_safe_path(rendered, self.project)
        if target_image_path.suffix.lower() not in self.image_suffixes:
            raise ValueError(f"target image extension is not supported: {target_image_path.suffix}")
        return target_image_path

    def _build_prefab_variant_definition(
        self,
        *,
        definition: DefinitionV3Model,
        base_by_name: dict[str, DefinitionV3Model],
        target_variant: str,
    ) -> dict[str, Any]:
        if definition.name is None:
            raise ValueError("prefab definition requires name")
        name = definition.name
        base = base_by_name.get(name)
        if base is None:
            raise ValueError(f"prefab '{name}' has no base definition")

        base_props = base.props or {}
        full = definition if definition.variant is None else merge_prefab_definition(base, definition)

        full_props = full.props or {}
        override_props: dict[str, Any] = {}
        for key, value in full_props.items():
            if key not in base_props or base_props[key] != value:
                override_props[key] = value

        output: dict[str, Any] = {
            "type": "prefab",
            "name": name,
            "variant": target_variant,
            "props": override_props,
        }
        if full.display_name != base.display_name:
            output["displayName"] = full.display_name
        if full.description != base.description:
            output["description"] = full.description
        if full.prefab_id != base.prefab_id:
            output["prefab_id"] = full.prefab_id
        return output

    def _read_image(self, path: Path) -> Any:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not read image: {path}")
        return image

    def _decode_uploaded_image(self, image_data: bytes) -> Any:
        if len(image_data) == 0:
            raise ValueError("Import image is empty")
        decoded = cv2.imdecode(np.frombuffer(image_data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            raise ValueError("Import image decode failed")
        return decoded

    def _validate_template_prop(self, template_prop: Any, *, definition_id: str) -> tuple[int, int, int, int]:
        if not isinstance(template_prop, dict):
            raise ValueError(f"definition '{definition_id}' props.template must be an object")
        if template_prop.get("kind") != "image":
            raise ValueError(f"definition '{definition_id}' props.template.kind must be 'image'")
        x1 = template_prop.get("x1")
        y1 = template_prop.get("y1")
        x2 = template_prop.get("x2")
        y2 = template_prop.get("y2")
        if not isinstance(x1, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.x1 must be number")
        if not isinstance(y1, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.y1 must be number")
        if not isinstance(x2, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.x2 must be number")
        if not isinstance(y2, (int, float)):
            raise ValueError(f"definition '{definition_id}' props.template.y2 must be number")
        ix1 = int(x1)
        iy1 = int(y1)
        ix2 = int(x2)
        iy2 = int(y2)
        if ix2 <= ix1 or iy2 <= iy1:
            raise ValueError(f"definition '{definition_id}' props.template has invalid rect")
        return ix1, iy1, ix2, iy2

    def _extract_region(self, image: Any, rect: tuple[int, int, int, int], *, definition_id: str, image_label: str) -> Any:
        height, width = image.shape[:2]
        x1, y1, x2, y2 = rect
        if x1 < 0 or y1 < 0 or x2 > width or y2 > height:
            raise ValueError(
                f"definition '{definition_id}' props.template rect is out of bounds for {image_label}: "
                f"rect=({x1},{y1},{x2},{y2}), image=({width},{height})"
            )
        return image[y1:y2, x1:x2]

    def _template_similarity_score(
        self,
        *,
        definition_id: str,
        template_prop: Any,
        source_image: Any,
        target_image: Any,
    ) -> float:
        rect = self._validate_template_prop(template_prop, definition_id=definition_id)
        source_region = self._extract_region(source_image, rect, definition_id=definition_id, image_label="source image")
        target_region = self._extract_region(target_image, rect, definition_id=definition_id, image_label="target image")
        if source_region.shape != target_region.shape:
            raise ValueError(f"definition '{definition_id}' source and target template region shape mismatch")
        match = cv2.matchTemplate(target_region, source_region, cv2.TM_CCOEFF_NORMED)
        score = float(match[0][0])
        return score

    def _plan_variant_clone_definitions(
        self,
        *,
        source_meta_path: Path,
        target_variant: str,
        source_image_path: Path,
        target_image_path: Path | None,
        target_image_override: Any | None = None,
    ) -> dict[str, Any]:
        source_meta = parse_meta_file(source_meta_path)
        source_image: Any | None = None
        target_image = target_image_override
        base_by_name: dict[str, DefinitionV3Model] = {}
        for definition in source_meta.definitions.values():
            if definition.type != "prefab":
                continue
            if definition.name is None:
                raise ValueError("prefab definition requires name")
            if definition.variant is None:
                if definition.name in base_by_name:
                    raise ValueError(f"duplicate prefab base definition: {definition.name}")
                base_by_name[definition.name] = definition

        target_definitions: dict[str, Any] = {}
        copied_definitions: list[dict[str, str]] = []
        skipped_definitions: list[dict[str, str]] = []

        for definition_id, definition in source_meta.definitions.items():
            definition_name = definition.name
            if definition_name is None:
                raise ValueError(f"definition '{definition_id}' requires name")
            if definition.type != "prefab":
                skipped_definitions.append(
                    {
                        "definitionId": definition_id,
                        "name": definition_name,
                        "reason": "not prefab",
                    }
                )
                continue
            base_definition = base_by_name.get(definition_name)
            if base_definition is None:
                raise ValueError(f"prefab '{definition_name}' has no base definition")
            full_definition = definition if definition.variant is None else merge_prefab_definition(base_definition, definition)
            full_props = full_definition.props or {}
            template_prop = full_props.get("template")
            if isinstance(template_prop, dict) and template_prop.get("kind") == "image":
                if target_image is None and target_image_path is not None and target_image_path.exists():
                    target_image = self._read_image(target_image_path)
                if target_image is not None:
                    if source_image is None:
                        source_image = self._read_image(source_image_path)
                    similarity_score = self._template_similarity_score(
                        definition_id=definition_id,
                        template_prop=template_prop,
                        source_image=source_image,
                        target_image=target_image,
                    )
                    if similarity_score >= 0.95:
                        skipped_definitions.append(
                            {
                                "definitionId": definition_id,
                                "name": definition_name,
                                "reason": f"same content (score={similarity_score:.4f} >= 0.95)",
                            }
                        )
                        continue
            definition_dump = self._build_prefab_variant_definition(
                definition=definition,
                base_by_name=base_by_name,
                target_variant=target_variant,
            )
            target_definitions[definition_id] = definition_dump
            copied_definitions.append(
                {
                    "definitionId": definition_id,
                    "name": definition_name,
                }
            )

        return {
            "targetDefinitions": target_definitions,
            "copiedDefinitions": copied_definitions,
            "skippedDefinitions": skipped_definitions,
        }

    ############## API Logic Methods ##############

    def get_project_root_data(self) -> dict[str, Any]:
        return self.workspace.get_project_root_data()

    def list_dir(self, path: str) -> dict[str, Any]:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise ValueError("Path not found")
        if not safe_path.is_dir():
            raise ValueError("Not a directory")

        items = []
        entries = sorted(list(safe_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in entries:
            is_image = self._is_image_file(item) if item.is_file() else False
            thumbnail_url: Optional[str]
            if is_image:
                thumbnail_url = f"/api/image/thumbnail?path={item}&size=128"
            else:
                thumbnail_url = None
            items.append(
                {
                    "name": item.name,
                    "isDirectory": item.is_dir(),
                    "path": str(item),
                    "isImage": is_image,
                    "thumbnailUrl": thumbnail_url,
                }
            )

        return {"items": items}

    def read_text(self, path: str) -> dict[str, Any]:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise ValueError("File not found")
        if not safe_path.is_file():
            raise ValueError("Not a file")
        content = safe_path.read_text(encoding="utf-8")
        return {"content": content}

    def write_text(self, path: str, content: str) -> dict[str, Any]:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.parent.exists():
            raise ValueError("Parent directory does not exist")
        temp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, safe_path)
        return {"status": "ok"}

    def rename_path(self, source_path: str, target_path: str) -> dict[str, Any]:
        """重命名单个文件路径。"""
        safe_source = get_safe_path(source_path, self.project)
        safe_target = get_safe_path(target_path, self.project)
        if not safe_source.exists():
            raise ValueError(f"Source path not found: {safe_source}")
        if not safe_source.is_file():
            raise ValueError(f"Source path is not a file: {safe_source}")
        if safe_target.exists():
            raise ValueError(f"Target path already exists: {safe_target}")
        if not safe_target.parent.exists():
            raise ValueError(f"Target parent directory does not exist: {safe_target.parent}")
        os.replace(safe_source, safe_target)
        return {"sourcePath": safe_source.as_posix(), "targetPath": safe_target.as_posix()}

    def copy_file(self, source_path: str, target_path: str) -> dict[str, Any]:
        """将服务端已有图片文件拷贝并覆盖目标路径（原子操作）。"""
        safe_source = get_safe_path(source_path, self.project)
        safe_target = get_safe_path(target_path, self.project)
        if not safe_source.exists():
            raise ValueError(f"Source file not found: {safe_source}")
        if not safe_source.is_file():
            raise ValueError(f"Source path is not a file: {safe_source}")
        if not self._is_image_file(safe_source):
            raise ValueError(f"Source file is not an image: {safe_source}")
        if not safe_target.parent.exists():
            raise ValueError(f"Target parent directory does not exist: {safe_target.parent}")
        if not self._is_image_file(safe_target):
            raise ValueError(f"Target path is not an image file: {safe_target}")
        temp_path = safe_target.with_name(f"{safe_target.name}.copy_tmp_{uuid.uuid4().hex}")
        try:
            shutil.copy2(safe_source, temp_path)
            os.replace(temp_path, safe_target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        return {"status": "ok", "targetPath": safe_target.as_posix()}

    def upload_file(self, target_path: str, file_data: bytes) -> dict[str, Any]:
        """将上传的二进制数据原子写入目标路径（覆盖已有文件）。"""
        safe_target = get_safe_path(target_path, self.project)
        if not safe_target.parent.exists():
            raise ValueError(f"Target parent directory does not exist: {safe_target.parent}")
        if not self._is_image_file(safe_target):
            raise ValueError(f"Target path is not an image file: {safe_target}")
        if len(file_data) == 0:
            raise ValueError("Uploaded file data is empty")
        temp_path = safe_target.with_name(f"{safe_target.name}.upload_tmp_{uuid.uuid4().hex}")
        try:
            temp_path.write_bytes(file_data)
            os.replace(temp_path, safe_target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        return {"status": "ok", "targetPath": safe_target.as_posix()}

    def precheck_rename_document(self, *, source_image_path: str, target_image_path: str) -> RenameDocumentPrecheckResultModel:
        return self.workspace.precheck_rename_document(
            source_image_path=source_image_path,
            target_image_path=target_image_path,
        )

    def _execute_file_rename_batch(self, renames: list[tuple[Path, Path]]) -> None:
        """执行批量重命名并在异常时回滚。"""
        staged: list[tuple[Path, Path, Path]] = []
        completed: list[tuple[Path, Path, Path]] = []
        for source, target in renames:
            temp = source.with_name(f"{source.name}.rename_tmp_{uuid.uuid4().hex}")
            if temp.exists():
                raise ValueError(f"Temporary file path already exists: {temp.as_posix()}")
            os.replace(source, temp)
            staged.append((source, temp, target))
        try:
            for source, temp, target in staged:
                os.replace(temp, target)
                completed.append((source, temp, target))
        except Exception:
            for source, _, target in reversed(completed):
                if target.exists():
                    os.replace(target, source)
            for source, temp, _ in reversed(staged):
                if temp.exists():
                    os.replace(temp, source)
            raise

    def execute_rename_document(self, *, source_image_path: str, target_image_path: str) -> RenameDocumentExecuteResultModel:
        return self.workspace.execute_rename_document(
            source_image_path=source_image_path,
            target_image_path=target_image_path,
        )

    def get_image_path(self, path: str) -> Path:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise ValueError("Not an image file")
        return safe_path

    def get_image_thumbnail_path(self, path: str, size: int) -> Path:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise ValueError("Not an image file")
        return self._ensure_thumbnail(safe_path, size)

    def get_image_hover_preview_path(
        self,
        *,
        path: str,
        size: int | None,
        x1: float | None,
        y1: float | None,
        x2: float | None,
        y2: float | None,
    ) -> Path:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise ValueError("Not an image file")
        if x1 is None and y1 is None and x2 is None and y2 is None:
            rect = None
        elif x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            rect = (x1, y1, x2, y2)
        else:
            raise ValueError("x1,y1,x2,y2 must be all provided or all omitted")
        return build_image_preview(
            source_path=safe_path,
            cache_root=self.project.pyproject_root / ".kotonebot" / "cache" / "hover_previews",
            size=size,
            rect=rect,
        )

    def get_prefabs_schema(self) -> dict[str, Any]:
        return self.workspace.get_prefabs_schema()

    def get_meta_index(self) -> Any:
        return self.workspace.get_meta_index()

    def list_workspace_images(self) -> dict[str, Any]:
        """返回 workspace 内所有 PNG 文件路径（含无 JSON 的新文件）。"""
        self.resource_index_store.ensure_ready()
        indexed = {ref.image_path for ref in self.resource_index_store.snapshot.meta_refs}
        all_pngs = {p.as_posix() for p in self.project_root.rglob("*.png")}
        return {"imagePaths": sorted(indexed | all_pngs)}
    
    def get_project_symbol_tree(self) -> list[dict[str, Any]]:
        self.symbol_index_view.ensure_ready()
        symbols = list(self.symbol_index_view.snapshot.symbols.values())
        root: dict[str, Any] = {"kind": "group", "label": "__root__", "children": []}
        group_map: dict[str, dict[str, Any]] = {"": root}
        
        for symbol in symbols:
            if symbol.name.strip() == "":
                continue
            parts = symbol.name.split(".")
            if len(parts) == 0 or any(part.strip() == "" for part in parts):
                continue
            
            current_path = ""
            current_group = root
            for segment in parts[:-1]:
                current_path = segment if current_path == "" else f"{current_path}.{segment}"
                next_group = group_map.get(current_path)
                if next_group is None:
                    next_group = {"kind": "group", "label": segment, "children": []}
                    group_map[current_path] = next_group
                    current_group["children"].append(next_group)
                current_group = next_group
            
            leaf_label = parts[-1]
            full_name = ".".join(parts)
            symbol_node = None
            for node in current_group["children"]:
                if node["kind"] == "symbol" and node["fullName"] == full_name:
                    symbol_node = node
                    break
            
            if symbol_node is None:
                symbol_node = {
                    "kind": "symbol",
                    "label": leaf_label,
                    "fullName": full_name,
                    "displayName": symbol.display_name,
                    "children": [],
                }
                current_group["children"].append(symbol_node)
            elif symbol_node["displayName"] is None and symbol.display_name is not None:
                symbol_node["displayName"] = symbol.display_name
            
            variant_label = "base" if symbol.variant is None else symbol.variant
            variant_node = None
            for node in symbol_node["children"]:
                if node["label"] == variant_label:
                    variant_node = node
                    break
            if variant_node is None:
                variant_node = {"kind": "variant", "label": variant_label, "children": []}
                symbol_node["children"].append(variant_node)
            
            already_exists = any(
                item["metaPath"] == symbol.meta_path and item["definitionId"] == symbol.definition_id
                for item in variant_node["children"]
            )
            if not already_exists:
                variant_node["children"].append(
                    {
                        "kind": "file",
                        "label": Path(symbol.meta_path).name,
                        "metaPath": symbol.meta_path,
                        "imagePath": symbol.image_path,
                        "definitionId": symbol.definition_id,
                        "variant": symbol.variant,
                    }
                )
        
        def sort_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
            groups: list[dict[str, Any]] = []
            symbol_nodes: list[dict[str, Any]] = []
            for node in nodes:
                kind = node["kind"]
                if kind == "group":
                    node["children"] = sort_nodes(node["children"])
                    groups.append(node)
                    continue
                if kind == "symbol":
                    node["children"].sort(key=lambda item: item["label"])
                    for variant in node["children"]:
                        variant["children"].sort(key=lambda item: item["metaPath"])
                    symbol_nodes.append(node)
                    continue
                raise ValueError(f"Unexpected root node kind: {kind}")
            
            groups.sort(key=lambda item: item["label"])
            symbol_nodes.sort(key=lambda item: item["fullName"])
            return [*groups, *symbol_nodes]
        
        return sort_nodes(root["children"])

    def update_meta_index(self, meta_path: str) -> Any:
        return self.workspace.update_meta_index(meta_path)

    def get_meta_diagnostics(self) -> Any:
        return self.workspace.get_meta_diagnostics()

    def get_meta_index_health(self) -> Any:
        return self.workspace.get_meta_index_health()

    def clone_variant_to_image(
        self,
        *,
        source_meta_path: str,
        target_image_path: str,
        variant: str,
        force_overwrite: bool,
    ) -> dict[str, Any]:
        return self.workspace.clone_variant_to_image(
            source_meta_path=source_meta_path,
            target_image_path=target_image_path,
            variant=variant,
            force_overwrite=force_overwrite,
        )

    def precheck_variant_import_path(
        self,
        *,
        source_meta_path: str,
        base_image_path: str,
        variant: str,
        uploaded_image_data: bytes,
    ) -> dict[str, Any]:
        return self.workspace.precheck_variant_import_path(
            source_meta_path=source_meta_path,
            base_image_path=base_image_path,
            variant=variant,
            uploaded_image_data=uploaded_image_data,
        )

    def import_variant_image(
        self,
        *,
        base_image_path: str,
        variant: str,
        image_data: bytes,
        delete_existing_target: bool,
    ) -> dict[str, Any]:
        return self.workspace.import_variant_image(
            base_image_path=base_image_path,
            variant=variant,
            image_data=image_data,
            delete_existing_target=delete_existing_target,
        )

    def precheck_copy_selected_prefab_to_variant(
        self,
        *,
        source_meta_path: str,
        source_definition_id: str,
        base_image_path: str,
        variant: str,
    ) -> dict[str, Any]:
        return self.workspace.precheck_copy_selected_prefab_to_variant(
            source_meta_path=source_meta_path,
            source_definition_id=source_definition_id,
            base_image_path=base_image_path,
            variant=variant,
        )

    def copy_selected_prefab_to_variant(
        self,
        *,
        source_meta_path: str,
        source_definition_id: str,
        base_image_path: str,
        variant: str,
        force_overwrite: bool,
    ) -> dict[str, Any]:
        return self.workspace.copy_selected_prefab_to_variant(
            source_meta_path=source_meta_path,
            source_definition_id=source_definition_id,
            base_image_path=base_image_path,
            variant=variant,
            force_overwrite=force_overwrite,
        )

    def reveal_in_explorer(self, path: str) -> None:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        sys_platform = platform.system()
        if sys_platform == "Windows":
            subprocess.Popen(["explorer", "/select,", str(safe_path)])
        elif sys_platform == "Darwin":
            subprocess.Popen(["open", "-R", str(safe_path)])
        else:
            subprocess.Popen(["xdg-open", str(safe_path.parent)])

    def get_health(self) -> dict[str, str]:
        return {"status": "ok", "service": "kotonebot-devtools"}

    def list_adb_devices(self) -> dict[str, Any]:
        try:
            from adbutils import adb
        except ImportError:
            return {"devices": [], "error": "adbutils not installed. Please install it with: pip install adbutils"}
        
        devices = []
        for d in adb.device_list():
            serial = d.serial
            state = d.get_state()
            name = f"{serial} ({state})"
            devices.append({
                "serial": serial,
                "state": state,
                "name": name,
            })
        return {"devices": devices}

    def capture_device_screenshot(self, *, serial: str, display_id: int | None = None) -> dict[str, Any]:
        try:
            from adbutils import adb, AdbDevice
            from adbutils.errors import AdbError
        except ImportError:
            return {"error": "adbutils not installed. Please install it with: pip install adbutils", "success": False}
        
        try:
            device: AdbDevice | None = None
            for d in adb.device_list():
                if d.serial == serial:
                    device = d
                    break
            
            if device is None:
                return {"error": f"Device '{serial}' not found", "success": False}
            
            state = device.get_state()
            if state != "device":
                return {"error": f"Device '{serial}' is not available (state: {state})", "success": False}
            
            image = device.screenshot(display_id=display_id, error_ok=False)
            bgr_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            temp_dir = self.project.pyproject_root / ".kotonebot" / "cache" / "device_captures"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            import time
            timestamp = int(time.time() * 1000)
            filename = f"capture_{serial.replace(':', '_')}_{timestamp}.png"
            temp_path = temp_dir / filename
            
            cv2.imwrite(str(temp_path), bgr_image)
            
            return {
                "success": True,
                "imagePath": str(temp_path),
                "imageUrl": f"/api/image?path={temp_path}",
            }
        except AdbError as e:
            return {"error": f"ADB error: {str(e)}", "success": False}
        except Exception as e:
            logging.exception("Error capturing device screenshot")
            return {"error": str(e), "success": False}
