import os
import logging
from pathlib import Path
from typing import Any, TypeVar, Generic, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pydantic.generics import GenericModel

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.project.scanner import scan_prefabs


T = TypeVar("T")


class ResponseModel(GenericModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None


class WriteTextRequest(BaseModel):
    content: str

def create_rest_router(project: Project) -> APIRouter:
    router = APIRouter(prefix="/api")
    _prefabs_cache = None

    def _get_safe_path(path_str: str) -> Path:
        """Ensure path is within project root. Raises ValueError on invalid access.
        """
        root = Path(project.conf_path).parent.resolve()

        p = Path(path_str)
        if not p.is_absolute():
            p = root / p

        try:
            p = p.resolve()
            if not str(p).startswith(str(root)):
                raise ValueError(f"Access denied: Path {p} is outside project root {root}")
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")

        return p

    def _ok(data: Any = None, message: Optional[str] = None) -> JSONResponse:
        return JSONResponse(ResponseModel[Any](success=True, message=message, data=data).dict())


    def _err(message: str) -> JSONResponse:
        return JSONResponse(ResponseModel[Any](success=False, message=message, data=None).dict())


    @router.get("/project/root")
    async def get_project_root():
        try:
            root = Path(project.conf_path).parent.resolve()
            data: dict = {"resource_root": str(root)}
            # include editor configuration if available (prefabs_module, resource_path)
            try:
                if project.conf and project.conf.editor:
                    data["editor"] = project.conf.editor.model_dump()
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
                items.append({
                    "name": item.name,
                    "isDirectory": item.is_dir(),
                    "path": str(item)
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
        
        if safe_path.suffix.lower() not in ['.png', '.jpg', '.jpeg', '.bmp', '.webp']:
             raise HTTPException(status_code=400, detail="Not an image file")
             
        return FileResponse(safe_path)

    @router.get("/prefabs/schema")
    async def get_prefabs_schema():
        nonlocal _prefabs_cache
        try:
            if _prefabs_cache is not None:
                return _ok(_prefabs_cache)

            if not project.conf or not project.conf.editor or not project.conf.editor.prefabs_module:
                return _ok({"version": 1, "prefabs": {}})

            schema = scan_prefabs(project.conf.editor.prefabs_module)
            _prefabs_cache = schema
            return _ok(schema)
        except Exception as e:
            return _err(str(e))


    @router.get("/health")
    async def health_check():
        return _ok({"status": "ok", "service": "kotonebot-devtools"})

    return router
