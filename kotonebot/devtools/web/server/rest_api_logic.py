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

from kotonebot.devtools.errors import InvalidImageError, NotFoundError, ValidationError, VariantNotDeclaredError
from kotonebot.devtools.image_preview import build_image_preview
from kotonebot.devtools.server_commands.workspace_service import WorkspaceService
from kotonebot.devtools.indexing.document_index_view import (
    RenameDocumentExecuteResultModel,
    RenameDocumentPrecheckResultModel,
)
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.path_utils import get_safe_path, to_rel


class RestApiLogic:
    def __init__(self, project: Project):
        self.workspace = WorkspaceService(project)
        self.project = project
        self.project_root = self.workspace.project_root
        self.pyproject_root = project.pyproject_root
        self.thumbnail_cache_root = project.pyproject_root / ".kotonebot" / "cache" / "thumbnails"
        self.image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def _is_image_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.image_suffixes

    def _get_thumbnail_path(self, source: Path, size: int) -> Path:
        if size <= 0:
            raise ValidationError("size must be positive")
        rel = source.resolve().relative_to(self.project_root)
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
                raise InvalidImageError(f"Could not read image: {source}")
            height, width = img.shape[:2]
            longest = max(width, height)
            if longest <= 0:
                raise ValidationError("invalid image size")
            scale = size / float(longest)
            new_width = max(1, int(round(width * scale)))
            new_height = max(1, int(round(height * scale)))
            resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(cache_path), resized)
        return cache_path

    ############## API Logic Methods ##############

    def get_project_root_data(self) -> dict[str, Any]:
        return self.workspace.get_project_root_data()

    def list_dir(self, path: str) -> dict[str, Any]:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise NotFoundError("Path not found")
        if not safe_path.is_dir():
            raise ValidationError("Not a directory")

        root = self.pyproject_root
        items = []
        entries = sorted(list(safe_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in entries:
            is_image = self._is_image_file(item) if item.is_file() else False
            thumbnail_url: Optional[str]
            rel_item = to_rel(item, root)
            if is_image:
                thumbnail_url = f"/api/image/thumbnail?path={rel_item}&size=128"
            else:
                thumbnail_url = None
            items.append(
                {
                    "name": item.name,
                    "isDirectory": item.is_dir(),
                    "path": rel_item,
                    "isImage": is_image,
                    "thumbnailUrl": thumbnail_url,
                }
            )

        return {"items": items}

    def read_text(self, path: str) -> dict[str, Any]:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise NotFoundError("File not found")
        if not safe_path.is_file():
            raise ValidationError("Not a file")
        content = safe_path.read_text(encoding="utf-8")
        return {"content": content}

    def write_text(self, path: str, content: str) -> dict[str, Any]:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.parent.exists():
            raise NotFoundError("Parent directory does not exist")
        temp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, safe_path)
        return {"status": "ok"}

    def rename_path(self, source_path: str, target_path: str) -> dict[str, Any]:
        safe_source = get_safe_path(source_path, self.project)
        safe_target = get_safe_path(target_path, self.project)
        if not safe_source.exists():
            raise NotFoundError(f"Source path not found: {safe_source}")
        if not safe_source.is_file():
            raise ValidationError(f"Source path is not a file: {safe_source}")
        if safe_target.exists():
            raise ValidationError(f"Target path already exists: {safe_target}")
        if not safe_target.parent.exists():
            raise NotFoundError(f"Target parent directory does not exist: {safe_target.parent}")
        os.replace(safe_source, safe_target)
        root = self.pyproject_root
        return {"sourcePath": to_rel(safe_source, root), "targetPath": to_rel(safe_target, root)}

    def copy_file(self, source_path: str, target_path: str) -> dict[str, Any]:
        safe_source = get_safe_path(source_path, self.project)
        safe_target = get_safe_path(target_path, self.project)
        if not safe_source.exists():
            raise NotFoundError(f"Source file not found: {safe_source}")
        if not safe_source.is_file():
            raise ValidationError(f"Source path is not a file: {safe_source}")
        if not self._is_image_file(safe_source):
            raise InvalidImageError(f"Source file is not an image: {safe_source}")
        if not safe_target.parent.exists():
            raise NotFoundError(f"Target parent directory does not exist: {safe_target.parent}")
        if not self._is_image_file(safe_target):
            raise InvalidImageError(f"Target path is not an image file: {safe_target}")
        temp_path = safe_target.with_name(f"{safe_target.name}.copy_tmp_{uuid.uuid4().hex}")
        try:
            shutil.copy2(safe_source, temp_path)
            os.replace(temp_path, safe_target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        root = self.pyproject_root
        return {"status": "ok", "targetPath": to_rel(safe_target, root)}

    def upload_file(self, target_path: str, file_data: bytes) -> dict[str, Any]:
        safe_target = get_safe_path(target_path, self.project)
        if not safe_target.parent.exists():
            raise NotFoundError(f"Target parent directory does not exist: {safe_target.parent}")
        if not self._is_image_file(safe_target):
            raise InvalidImageError(f"Target path is not an image file: {safe_target}")
        if len(file_data) == 0:
            raise ValidationError("Uploaded file data is empty")
        temp_path = safe_target.with_name(f"{safe_target.name}.upload_tmp_{uuid.uuid4().hex}")
        try:
            temp_path.write_bytes(file_data)
            os.replace(temp_path, safe_target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        root = self.pyproject_root
        return {"status": "ok", "targetPath": to_rel(safe_target, root)}

    def precheck_rename_document(self, *, source_image_path: str, target_image_path: str) -> RenameDocumentPrecheckResultModel:
        return self.workspace.precheck_rename_document(
            source_image_path=source_image_path,
            target_image_path=target_image_path,
        )

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
            raise InvalidImageError("Not an image file")
        return safe_path

    def get_image_thumbnail_path(self, path: str, size: int) -> Path:
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise InvalidImageError("Not an image file")
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
            raise InvalidImageError("Not an image file")
        if x1 is None and y1 is None and x2 is None and y2 is None:
            rect = None
        elif x1 is not None and y1 is not None and x2 is not None and y2 is not None:
            rect = (x1, y1, x2, y2)
        else:
            raise ValidationError("x1,y1,x2,y2 must be all provided or all omitted")
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
        self.workspace.resource_index_store.ensure_ready()
        root = self.pyproject_root
        indexed = {Path(ref.image_path) for ref in self.workspace.resource_index_store.snapshot.meta_refs}
        all_pngs = set(self.project_root.rglob("*.png"))
        return {"imagePaths": sorted(to_rel(p, root) for p in (indexed | all_pngs))}
    
    def get_project_symbol_tree(self) -> list[dict[str, Any]]:
        self.workspace.symbol_index_view.ensure_ready()
        symbols = list(self.workspace.symbol_index_view.snapshot.symbols.values())
        root_path = self.pyproject_root
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
                        "metaPath": to_rel(symbol.meta_path, root_path),
                        "imagePath": to_rel(symbol.image_path, root_path),
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

            root = self.pyproject_root
            rel_path = to_rel(temp_path, root)
            return {
                "success": True,
                "imagePath": rel_path,
                "imageUrl": f"/api/image?path={rel_path}",
            }
        except AdbError as e:
            return {"error": f"ADB error: {str(e)}", "success": False}
        except Exception as e:
            logging.exception("Error capturing device screenshot")
            return {"error": str(e), "success": False}
