import json
import logging
import os
import string
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from kotonebot.devtools.indexing.index_store import IndexStore
from kotonebot.devtools.meta import DefinitionV2Model, merge_prefab_definition, parse_meta_file
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.project.scanner import scan_prefabs


class RestApiLogic:
    def __init__(self, project: Project):
        self.project = project
        self._prefabs_cache: Optional[dict[str, Any]] = None

        if project.conf is None or project.conf.editor is None or project.conf.editor.resource_path is None:
            raise ValueError("Missing [tool.kotonebot.editor.resource_path] in pyproject.toml")
        self.project_root = Path(project.conf.editor.resource_path).resolve()

        try:
            prefab_schema_for_index = self._get_prefabs_cache().get("prefabs", {})
        except Exception:
            logging.exception("Failed to preload prefab schema for index store")
            prefab_schema_for_index = {}

        self.index_store = IndexStore(
            resource_root=self.project_root,
            prefab_schema=prefab_schema_for_index,
            resource_variants=project.conf.variant.names if project.conf.variant and project.conf.variant.names is not None else None,
            variant_configured=project.conf.variant is not None,
        )
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

    def _get_safe_path(self, path_str: str) -> Path:
        p = Path(path_str)
        if not p.is_absolute():
            p = self.project_root / p

        try:
            p = p.resolve()
            p.relative_to(self.project_root)
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

        return p

    def _assert_variant_declared(self, variant: str) -> str:
        variant_name = variant.strip()
        if variant_name == "":
            raise ValueError("variant cannot be empty")
        declared_variants = self.project.conf.variant.names if self.project.conf.variant and self.project.conf.variant.names is not None else []
        if variant_name not in declared_variants:
            raise ValueError(f"variant '{variant_name}' is not declared in variant.names")
        return variant_name

    def _resolve_variant_import_target_path(self, *, base_image_path: Path, variant_name: str) -> Path:
        if self.project.conf.variant is None:
            raise ValueError("Missing [tool.kotonebot.variant] in pyproject.toml")
        variant_path_pattern = self.project.conf.variant.path_pattern
        if variant_path_pattern is None:
            raise ValueError("Missing [tool.kotonebot.variant.path_pattern] in pyproject.toml")
        rel_base_image_path = base_image_path.resolve().relative_to(self.project_root)
        declared_variants = self.project.conf.variant.names if self.project.conf.variant.names is not None else []
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
        target_image_path = self._get_safe_path(rendered)
        if target_image_path.suffix.lower() not in self.image_suffixes:
            raise ValueError(f"target image extension is not supported: {target_image_path.suffix}")
        return target_image_path

    def _build_prefab_variant_definition(
        self,
        *,
        definition: DefinitionV2Model,
        base_by_name: dict[str, DefinitionV2Model],
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
        source_image = self._read_image(source_image_path)
        target_image = target_image_override
        if target_image is None and target_image_path is not None and target_image_path.exists():
            target_image = self._read_image(target_image_path)
        base_by_name: dict[str, DefinitionV2Model] = {}
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
            if target_image is not None and isinstance(template_prop, dict) and template_prop.get("kind") == "image":
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
        data: dict[str, Any] = {"resource_root": str(self.project_root)}
        try:
            if self.project.conf and self.project.conf.editor:
                data["editor"] = self.project.conf.editor.model_dump()
            if self.project.conf and self.project.conf.variant:
                data["variant"] = self.project.conf.variant.model_dump()
        except Exception:
            logging.exception("Failed to include editor config in /project/root response")
        return data

    def list_dir(self, path: str) -> dict[str, Any]:
        safe_path = self._get_safe_path(path)
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
        safe_path = self._get_safe_path(path)
        if not safe_path.exists():
            raise ValueError("File not found")
        if not safe_path.is_file():
            raise ValueError("Not a file")
        content = safe_path.read_text(encoding="utf-8")
        return {"content": content}

    def write_text(self, path: str, content: str) -> dict[str, Any]:
        safe_path = self._get_safe_path(path)
        if not safe_path.parent.exists():
            raise ValueError("Parent directory does not exist")
        temp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, safe_path)
        return {"status": "ok"}

    def get_image_path(self, path: str) -> Path:
        safe_path = self._get_safe_path(path)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise ValueError("Not an image file")
        return safe_path

    def get_image_thumbnail_path(self, path: str, size: int) -> Path:
        safe_path = self._get_safe_path(path)
        if not safe_path.exists():
            raise FileNotFoundError("Image not found")
        if not self._is_image_file(safe_path):
            raise ValueError("Not an image file")
        return self._ensure_thumbnail(safe_path, size)

    def get_prefabs_schema(self) -> dict[str, Any]:
        return self._get_prefabs_cache()

    def get_meta_index(self) -> Any:
        return self.index_store.get_snapshot_lite()

    def update_meta_index(self, meta_path: str) -> Any:
        return self.index_store.update_file(meta_path=meta_path)

    def get_meta_diagnostics(self) -> Any:
        return self.index_store.get_diagnostics()

    def get_meta_index_health(self) -> Any:
        return self.index_store.get_health()

    def clone_variant_to_image(
        self,
        *,
        source_meta_path: str,
        target_image_path: str,
        variant: str,
        force_overwrite: bool,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)

        source_meta = self._get_safe_path(source_meta_path)
        target_image = self._get_safe_path(target_image_path)
        if not source_meta.exists():
            raise ValueError(f"Source meta not found: {source_meta}")
        if not target_image.exists():
            raise ValueError(f"Target image not found: {target_image}")
        if not self._is_image_file(target_image):
            raise ValueError(f"Target path is not an image: {target_image}")

        target_meta_path = Path(str(target_image) + ".json")
        if target_meta_path.exists() and not force_overwrite:
            raise ValueError(f"Target meta already exists: {target_meta_path}")
        plan = self._plan_variant_clone_definitions(
            source_meta_path=source_meta,
            target_variant=variant_name,
            source_image_path=Path(str(source_meta.with_suffix(""))),
            target_image_path=target_image,
        )
        target_definitions = plan["targetDefinitions"]

        payload = {"version": 2, "definitions": target_definitions}
        target_meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "targetMetaPath": target_meta_path.as_posix(),
            "definitionCount": len(target_definitions),
        }

    def precheck_variant_import_path(
        self,
        *,
        source_meta_path: str,
        base_image_path: str,
        variant: str,
        uploaded_image_data: bytes,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)
        source_meta = self._get_safe_path(source_meta_path)
        base_image = self._get_safe_path(base_image_path)
        if not source_meta.exists():
            raise ValueError(f"Source meta not found: {source_meta}")
        if not base_image.exists():
            raise ValueError(f"Base image not found: {base_image}")
        if not self._is_image_file(base_image):
            raise ValueError(f"Base path is not an image: {base_image}")
        uploaded_target_image = self._decode_uploaded_image(uploaded_image_data)
        target_image_path = self._resolve_variant_import_target_path(
            base_image_path=base_image,
            variant_name=variant_name,
        )
        plan = self._plan_variant_clone_definitions(
            source_meta_path=source_meta,
            target_variant=variant_name,
            source_image_path=Path(str(source_meta.with_suffix(""))),
            target_image_path=target_image_path,
            target_image_override=uploaded_target_image,
        )
        target_meta_path = Path(str(target_image_path) + ".json")
        return {
            "targetImagePath": target_image_path.as_posix(),
            "targetImageExists": target_image_path.exists(),
            "targetMetaPath": target_meta_path.as_posix(),
            "targetMetaExists": target_meta_path.exists(),
            "copiedDefinitions": plan["copiedDefinitions"],
            "skippedDefinitions": plan["skippedDefinitions"],
        }

    def import_variant_image(
        self,
        *,
        base_image_path: str,
        variant: str,
        image_data: bytes,
        delete_existing_target: bool,
    ) -> dict[str, Any]:
        variant_name = self._assert_variant_declared(variant)
        base_image = self._get_safe_path(base_image_path)
        if not base_image.exists():
            raise ValueError(f"Base image not found: {base_image}")
        if not self._is_image_file(base_image):
            raise ValueError(f"Base path is not an image: {base_image}")
        target_image_path = self._resolve_variant_import_target_path(
            base_image_path=base_image,
            variant_name=variant_name,
        )
        if target_image_path.exists():
            if not delete_existing_target:
                raise ValueError(f"Target image already exists: {target_image_path}")
            target_image_path.unlink()
            target_meta_path = Path(str(target_image_path) + ".json")
            if target_meta_path.exists():
                target_meta_path.unlink()
        if len(image_data) == 0:
            raise ValueError("Import image is empty")
        target_image_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_image_path.with_suffix(target_image_path.suffix + ".tmp")
        temp_path.write_bytes(image_data)
        os.replace(temp_path, target_image_path)
        return {
            "targetImagePath": target_image_path.as_posix(),
            "size": len(image_data),
        }

    def get_health(self) -> dict[str, str]:
        return {"status": "ok", "service": "kotonebot-devtools"}
