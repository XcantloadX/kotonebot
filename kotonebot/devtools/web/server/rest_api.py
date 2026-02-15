import os
import json
import logging
import string
from pathlib import Path
from typing import Any, TypeVar, Generic, Optional

import cv2
from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pydantic.generics import GenericModel

from kotonebot.devtools.indexing.index_store import IndexStore
from kotonebot.devtools.meta import DefinitionV2Model, merge_prefab_definition, parse_meta_file
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.project.scanner import scan_prefabs


T = TypeVar("T")


class ResponseModel(GenericModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None


class WriteTextRequest(BaseModel):
    content: str


class UpdateIndexRequest(BaseModel):
    metaPath: str


class CloneVariantToImageRequest(BaseModel):
    sourceMetaPath: str
    targetImagePath: str
    variant: str
    forceOverwrite: bool = False


class PreviewVariantImportPathRequest(BaseModel):
    baseImagePath: str
    variant: str


def create_rest_router(project: Project) -> APIRouter:
    router = APIRouter(prefix="/api")
    _prefabs_cache = None

    if project.conf is None or project.conf.editor is None or project.conf.editor.resource_path is None:
        raise ValueError("Missing [tool.kotonebot.editor.resource_path] in pyproject.toml")
    project_root = Path(project.conf.editor.resource_path).resolve()
    
    def _get_prefabs_cache() -> dict[str, Any]:
        nonlocal _prefabs_cache
        if _prefabs_cache is not None:
            return _prefabs_cache
        if not project.conf or not project.conf.editor or not project.conf.editor.prefabs_module:
            _prefabs_cache = {"version": 1, "prefabs": {}}
            return _prefabs_cache
        _prefabs_cache = scan_prefabs(project.conf.editor.prefabs_module)
        if not isinstance(_prefabs_cache, dict):
            raise ValueError("Invalid prefab schema response")
        _prefabs_cache.setdefault("prefabs", {})
        return _prefabs_cache

    try:
        prefab_schema_for_index = _get_prefabs_cache().get("prefabs", {})
    except Exception:
        logging.exception("Failed to preload prefab schema for index store")
        prefab_schema_for_index = {}

    index_store = IndexStore(
        resource_root=project_root,
        prefab_schema=prefab_schema_for_index,
        resource_variants=project.conf.variant.names if project.conf.variant and project.conf.variant.names is not None else None,
    )

    thumbnail_cache_root = project.pyproject_root / ".kotonebot" / "cache" / "thumbnails"
    image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def _is_image_file(path: Path) -> bool:
        return path.suffix.lower() in image_suffixes

    def _get_thumbnail_path(source: Path, size: int) -> Path:
        if size <= 0:
            raise ValueError("size must be positive")
        try:
            rel = source.resolve().relative_to(project_root)
        except Exception as e:
            raise ValueError(str(e))
        size_dir = thumbnail_cache_root / str(size)
        target_dir = size_dir / rel.parent
        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / rel.name

    def _ensure_thumbnail(source: Path, size: int) -> Path:
        cache_path = _get_thumbnail_path(source, size)
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

    def _get_safe_path(path_str: str) -> Path:
        p = Path(path_str)
        if not p.is_absolute():
            p = project_root / p

        try:
            p = p.resolve()
            if not str(p).startswith(str(project_root)):
                raise ValueError(f"Access denied: Path {p} is outside project root {project_root}")
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

        return p

    def _ok(data: Any = None, message: Optional[str] = None) -> JSONResponse:
        return JSONResponse(ResponseModel[Any](success=True, message=message, data=data).model_dump())


    def _err(message: str) -> JSONResponse:
        return JSONResponse(ResponseModel[Any](success=False, message=message, data=None).model_dump())

    def _to_dump(definition: DefinitionV2Model) -> dict[str, Any]:
        return definition.model_dump(by_alias=True, exclude_none=True)

    variant_path_placeholders = {
        "variant_name",
        "file_name",
        "file_name_ext",
        "file_ext",
        "file_dir",
    }

    def _assert_variant_declared(variant: str) -> str:
        variant_name = variant.strip()
        if variant_name == "":
            raise ValueError("variant cannot be empty")
        declared_variants = project.conf.variant.names if project.conf.variant and project.conf.variant.names is not None else []
        if variant_name not in declared_variants:
            raise ValueError(f"variant '{variant_name}' is not declared in variant.names")
        return variant_name

    def _resolve_variant_import_target_path(*, base_image_path: Path, variant_name: str) -> Path:
        if project.conf.variant is None:
            raise ValueError("Missing [tool.kotonebot.variant] in pyproject.toml")
        variant_path_pattern = project.conf.variant.path_pattern
        if variant_path_pattern is None:
            raise ValueError("Missing [tool.kotonebot.variant.path_pattern] in pyproject.toml")
        rel_base_image_path = base_image_path.resolve().relative_to(project_root)
        declared_variants = project.conf.variant.names if project.conf.variant.names is not None else []
        base_variant = project.conf.variant.base
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
                if field_name not in variant_path_placeholders:
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
        target_image_path = _get_safe_path(rendered)
        if target_image_path.suffix.lower() not in image_suffixes:
            raise ValueError(f"target image extension is not supported: {target_image_path.suffix}")
        return target_image_path

    def _build_prefab_variant_definition(
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


    @router.get("/project/root")
    async def get_project_root():
        try:
            data: dict = {"resource_root": str(project_root)}
            # include editor configuration if available (prefabs_module, resource_path)
            try:
                if project.conf and project.conf.editor:
                    data["editor"] = project.conf.editor.model_dump()
                if project.conf and project.conf.variant:
                    data["variant"] = project.conf.variant.model_dump()
            except Exception:
                logging.exception("Failed to include editor config in /project/root response")

            return _ok(data)
        except Exception as e:
            logging.exception("Error while handling /project/root")
            return _err(str(e))

    @router.get("/fs/list_dir")
    async def list_dir(path: str = Query(..., description="Path relative to project root or absolute path")):
        try:
            safe_path = _get_safe_path(path)
            if not safe_path.exists():
                return _err("Path not found")
            if not safe_path.is_dir():
                return _err("Not a directory")

            items = []
            entries = sorted(list(safe_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in entries:
                is_image = _is_image_file(item) if item.is_file() else False
                thumbnail_url: Optional[str]
                if is_image:
                    thumbnail_url = f"/api/image/thumbnail?path={item}&size=128"
                else:
                    thumbnail_url = None
                items.append({
                    "name": item.name,
                    "isDirectory": item.is_dir(),
                    "path": str(item),
                    "isImage": is_image,
                    "thumbnailUrl": thumbnail_url,
                })

            return _ok({"items": items})
        except PermissionError:
            return _err("Permission denied")
        except Exception as e:
            return _err(str(e))

    @router.get("/fs/read_text")
    async def read_text(path: str = Query(...)):
        try:
            safe_path = _get_safe_path(path)
            if not safe_path.exists():
                return _err("File not found")
            if not safe_path.is_file():
                return _err("Not a file")

            content = safe_path.read_text(encoding="utf-8")
            return _ok({"content": content})
        except Exception as e:
            return _err(str(e))

    @router.put("/fs/write_text")
    async def write_text(path: str = Query(...), body: WriteTextRequest = Body(...)):
        try:
            safe_path = _get_safe_path(path)
            if not safe_path.parent.exists():
                return _err("Parent directory does not exist")

            temp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
            temp_path.write_text(body.content, encoding="utf-8")
            os.replace(temp_path, safe_path)
            return _ok({"status": "ok"})
        except Exception as e:
            return _err(str(e))

    @router.get("/image")
    async def get_image(path: str = Query(...)):
        safe_path = _get_safe_path(path)
        if not safe_path.exists():
             raise HTTPException(status_code=404, detail="Image not found")
        
        if not _is_image_file(safe_path):
             raise HTTPException(status_code=400, detail="Not an image file")
             
        return FileResponse(safe_path)

    @router.get("/image/thumbnail")
    async def get_image_thumbnail(path: str = Query(...), size: int = Query(128, ge=1, le=2048)):
        safe_path = _get_safe_path(path)
        if not safe_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")
        if not _is_image_file(safe_path):
            raise HTTPException(status_code=400, detail="Not an image file")
        try:
            cache_path = _ensure_thumbnail(safe_path, size)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return FileResponse(cache_path)

    @router.get("/prefabs/schema")
    async def get_prefabs_schema():
        try:
            return _ok(_get_prefabs_cache())
        except Exception as e:
            return _err(str(e))

    @router.get("/meta/index")
    async def get_meta_index():
        try:
            return _ok(index_store.get_snapshot_lite())
        except Exception as e:
            logging.exception("Error while handling /meta/index")
            return _err(str(e))

    @router.post("/meta/index/update")
    async def update_meta_index(body: UpdateIndexRequest = Body(...)):
        try:
            return _ok(index_store.update_file(meta_path=body.metaPath))
        except Exception as e:
            logging.exception("Error while handling /meta/index/update")
            return _err(str(e))

    @router.get("/meta/diagnostics")
    async def get_meta_diagnostics():
        try:
            return _ok(index_store.get_diagnostics())
        except Exception as e:
            logging.exception("Error while handling /meta/diagnostics")
            return _err(str(e))

    @router.get("/meta/index/health")
    async def get_meta_index_health():
        try:
            return _ok(index_store.get_health())
        except Exception as e:
            logging.exception("Error while handling /meta/index/health")
            return _err(str(e))

    @router.post("/meta/variant/clone_to_image")
    async def clone_variant_to_image(body: CloneVariantToImageRequest = Body(...)):
        try:
            variant_name = _assert_variant_declared(body.variant)

            source_meta_path = _get_safe_path(body.sourceMetaPath)
            target_image_path = _get_safe_path(body.targetImagePath)
            if not source_meta_path.exists():
                return _err(f"Source meta not found: {source_meta_path}")
            if not target_image_path.exists():
                return _err(f"Target image not found: {target_image_path}")
            if not _is_image_file(target_image_path):
                return _err(f"Target path is not an image: {target_image_path}")

            target_meta_path = Path(str(target_image_path) + ".json")
            if target_meta_path.exists() and not body.forceOverwrite:
                return _err(f"Target meta already exists: {target_meta_path}")

            source_meta = parse_meta_file(source_meta_path)
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
            for definition_id, definition in source_meta.definitions.items():
                if definition.type != "prefab":
                    continue
                target_definitions[definition_id] = _build_prefab_variant_definition(
                    definition=definition,
                    base_by_name=base_by_name,
                    target_variant=variant_name,
                )

            payload = {"version": 2, "definitions": target_definitions}
            target_meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return _ok(
                {
                    "targetMetaPath": target_meta_path.as_posix(),
                    "definitionCount": len(target_definitions),
                }
            )
        except Exception as e:
            logging.exception("Error while handling /meta/variant/clone_to_image")
            return _err(str(e))

    @router.post("/meta/variant/import/preview_path")
    async def preview_variant_import_path(body: PreviewVariantImportPathRequest = Body(...)):
        try:
            variant_name = _assert_variant_declared(body.variant)
            base_image_path = _get_safe_path(body.baseImagePath)
            if not base_image_path.exists():
                return _err(f"Base image not found: {base_image_path}")
            if not _is_image_file(base_image_path):
                return _err(f"Base path is not an image: {base_image_path}")
            target_image_path = _resolve_variant_import_target_path(
                base_image_path=base_image_path,
                variant_name=variant_name,
            )
            return _ok({"targetImagePath": target_image_path.as_posix()})
        except Exception as e:
            logging.exception("Error while handling /meta/variant/import/preview_path")
            return _err(str(e))

    @router.post("/meta/variant/import_image")
    async def import_variant_image(
        baseImagePath: str = Form(...),
        variant: str = Form(...),
        image: UploadFile = File(...),
        deleteExistingTarget: bool = Form(False),
    ):
        try:
            variant_name = _assert_variant_declared(variant)
            base_image_path = _get_safe_path(baseImagePath)
            if not base_image_path.exists():
                return _err(f"Base image not found: {base_image_path}")
            if not _is_image_file(base_image_path):
                return _err(f"Base path is not an image: {base_image_path}")
            target_image_path = _resolve_variant_import_target_path(
                base_image_path=base_image_path,
                variant_name=variant_name,
            )
            if target_image_path.exists():
                if not deleteExistingTarget:
                    return _err(f"Target image already exists: {target_image_path}")
                target_image_path.unlink()
                target_meta_path = Path(str(target_image_path) + ".json")
                if target_meta_path.exists():
                    target_meta_path.unlink()
            image_data = await image.read()
            if len(image_data) == 0:
                return _err("Import image is empty")
            target_image_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = target_image_path.with_suffix(target_image_path.suffix + ".tmp")
            temp_path.write_bytes(image_data)
            os.replace(temp_path, target_image_path)
            return _ok(
                {
                    "targetImagePath": target_image_path.as_posix(),
                    "size": len(image_data),
                }
            )
        except Exception as e:
            logging.exception("Error while handling /meta/variant/import_image")
            return _err(str(e))

    @router.get("/health")
    async def health_check():
        return _ok({"status": "ok", "service": "kotonebot-devtools"})

    return router
