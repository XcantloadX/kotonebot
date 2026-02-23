import logging
from typing import Any, Generic, Optional, TypeVar

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pydantic.generics import GenericModel

from kotonebot.devtools.server_commands.types import parse_server_command_request
from kotonebot.devtools.project.project import Project

from .rest_api_logic import RestApiLogic


T = TypeVar("T")


class ResponseModel(GenericModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None


class WriteTextRequest(BaseModel):
    content: str


class RenamePathRequest(BaseModel):
    """单文件重命名请求。"""

    sourcePath: str
    targetPath: str


class PrecheckRenameDocumentRequest(BaseModel):
    """文档重命名预检请求。"""

    sourceImagePath: str
    targetImagePath: str


class ExecuteRenameDocumentRequest(BaseModel):
    """文档重命名执行请求。"""

    sourceImagePath: str
    targetImagePath: str


class UpdateIndexRequest(BaseModel):
    metaPath: str


class CloneVariantToImageRequest(BaseModel):
    sourceMetaPath: str
    targetImagePath: str
    variant: str
    forceOverwrite: bool = False


class PrecheckCopySelectedPrefabToVariantRequest(BaseModel):
    sourceMetaPath: str
    sourceDefinitionId: str
    baseImagePath: str
    variant: str


class CopySelectedPrefabToVariantRequest(BaseModel):
    sourceMetaPath: str
    sourceDefinitionId: str
    baseImagePath: str
    variant: str
    forceOverwrite: bool = False


def create_rest_router(project: Project) -> APIRouter:
    router = APIRouter(prefix="/api")
    logic = RestApiLogic(project)

    def _ok(data: Any = None, message: Optional[str] = None) -> JSONResponse:
        return JSONResponse(ResponseModel[Any](success=True, message=message, data=data).model_dump())

    def _err(message: str) -> JSONResponse:
        return JSONResponse(ResponseModel[Any](success=False, message=message, data=None).model_dump())

    @router.get("/project/root")
    async def get_project_root():
        try:
            return _ok(logic.get_project_root_data())
        except Exception as e:
            logging.exception("Error while handling /project/root")
            return _err(str(e))

    @router.get("/fs/list_dir")
    async def list_dir(path: str = Query(..., description="Path relative to project root or absolute path")):
        try:
            return _ok(logic.list_dir(path))
        except PermissionError:
            return _err("Permission denied")
        except Exception as e:
            return _err(str(e))

    @router.get("/fs/read_text")
    async def read_text(path: str = Query(...)):
        try:
            return _ok(logic.read_text(path))
        except Exception as e:
            return _err(str(e))

    @router.put("/fs/write_text")
    async def write_text(path: str = Query(...), body: WriteTextRequest = Body(...)):
        try:
            return _ok(logic.write_text(path, body.content))
        except Exception as e:
            return _err(str(e))

    @router.post("/fs/rename")
    async def rename_path(body: RenamePathRequest = Body(...)):
        try:
            return _ok(logic.rename_path(body.sourcePath, body.targetPath))
        except Exception as e:
            return _err(str(e))

    @router.post("/fs/rename_document/precheck")
    async def precheck_rename_document(body: PrecheckRenameDocumentRequest = Body(...)):
        try:
            return _ok(
                logic.precheck_rename_document(
                    source_image_path=body.sourceImagePath,
                    target_image_path=body.targetImagePath,
                )
            )
        except Exception as e:
            return _err(str(e))

    @router.post("/fs/rename_document/execute")
    async def execute_rename_document(body: ExecuteRenameDocumentRequest = Body(...)):
        try:
            return _ok(
                logic.execute_rename_document(
                    source_image_path=body.sourceImagePath,
                    target_image_path=body.targetImagePath,
                )
            )
        except Exception as e:
            return _err(str(e))

    @router.get("/image")
    async def get_image(path: str = Query(...)):
        try:
            safe_path = logic.get_image_path(path)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return FileResponse(safe_path)

    @router.get("/image/thumbnail")
    async def get_image_thumbnail(path: str = Query(...), size: int = Query(128, ge=1, le=2048)):
        try:
            cache_path = logic.get_image_thumbnail_path(path, size)
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return FileResponse(cache_path)

    @router.get("/prefabs/schema")
    async def get_prefabs_schema():
        try:
            return _ok(logic.get_prefabs_schema())
        except Exception as e:
            return _err(str(e))

    @router.get("/meta/index")
    async def get_meta_index():
        try:
            return _ok(logic.get_meta_index())
        except Exception as e:
            logging.exception("Error while handling /meta/index")
            return _err(str(e))

    @router.post("/meta/index/update")
    async def update_meta_index(body: UpdateIndexRequest = Body(...)):
        try:
            return _ok(logic.update_meta_index(body.metaPath))
        except Exception as e:
            logging.exception("Error while handling /meta/index/update")
            return _err(str(e))

    @router.get("/meta/diagnostics")
    async def get_meta_diagnostics():
        try:
            return _ok(logic.get_meta_diagnostics())
        except Exception as e:
            logging.exception("Error while handling /meta/diagnostics")
            return _err(str(e))

    @router.get("/meta/index/health")
    async def get_meta_index_health():
        try:
            return _ok(logic.get_meta_index_health())
        except Exception as e:
            logging.exception("Error while handling /meta/index/health")
            return _err(str(e))

    @router.post("/meta/variant/clone_to_image")
    async def clone_variant_to_image(body: CloneVariantToImageRequest = Body(...)):
        try:
            result = logic.clone_variant_to_image(
                source_meta_path=body.sourceMetaPath,
                target_image_path=body.targetImagePath,
                variant=body.variant,
                force_overwrite=body.forceOverwrite,
            )
            return _ok(result)
        except Exception as e:
            logging.exception("Error while handling /meta/variant/clone_to_image")
            return _err(str(e))

    @router.post("/meta/variant/import/precheck_path")
    async def precheck_variant_import_path(
        sourceMetaPath: str = Form(...),
        baseImagePath: str = Form(...),
        variant: str = Form(...),
        image: UploadFile = File(...),
    ):
        try:
            uploaded_image_data = await image.read()
            result = logic.precheck_variant_import_path(
                source_meta_path=sourceMetaPath,
                base_image_path=baseImagePath,
                variant=variant,
                uploaded_image_data=uploaded_image_data,
            )
            return _ok(result)
        except Exception as e:
            logging.exception("Error while handling /meta/variant/import/precheck_path")
            return _err(str(e))

    @router.post("/meta/variant/import_image")
    async def import_variant_image(
        baseImagePath: str = Form(...),
        variant: str = Form(...),
        image: UploadFile = File(...),
        deleteExistingTarget: bool = Form(False),
    ):
        try:
            image_data = await image.read()
            result = logic.import_variant_image(
                base_image_path=baseImagePath,
                variant=variant,
                image_data=image_data,
                delete_existing_target=deleteExistingTarget,
            )
            return _ok(result)
        except Exception as e:
            logging.exception("Error while handling /meta/variant/import_image")
            return _err(str(e))

    @router.post("/meta/variant/copy_selected_prefab/precheck")
    async def precheck_copy_selected_prefab_to_variant(body: PrecheckCopySelectedPrefabToVariantRequest = Body(...)):
        try:
            result = logic.precheck_copy_selected_prefab_to_variant(
                source_meta_path=body.sourceMetaPath,
                source_definition_id=body.sourceDefinitionId,
                base_image_path=body.baseImagePath,
                variant=body.variant,
            )
            return _ok(result)
        except Exception as e:
            logging.exception("Error while handling /meta/variant/copy_selected_prefab/precheck")
            return _err(str(e))

    @router.post("/meta/variant/copy_selected_prefab")
    async def copy_selected_prefab_to_variant(body: CopySelectedPrefabToVariantRequest = Body(...)):
        try:
            result = logic.copy_selected_prefab_to_variant(
                source_meta_path=body.sourceMetaPath,
                source_definition_id=body.sourceDefinitionId,
                base_image_path=body.baseImagePath,
                variant=body.variant,
                force_overwrite=body.forceOverwrite,
            )
            return _ok(result)
        except Exception as e:
            logging.exception("Error while handling /meta/variant/copy_selected_prefab")
            return _err(str(e))

    @router.get("/health")
    async def health_check():
        return _ok(logic.get_health())

    @router.get("/server/commands")
    async def get_server_commands():
        try:
            return _ok([item.model_dump() for item in logic.workspace.list_server_commands()])
        except Exception as e:
            logging.exception("Error while handling /server/commands")
            return _err(str(e))

    @router.post("/server/execute_command")
    async def execute_server_command(body: dict[str, Any] = Body(...)):
        try:
            request = parse_server_command_request(body)
            return _ok(logic.workspace.execute_server_command(request).model_dump())
        except Exception as e:
            logging.exception("Error while handling /server/execute_command")
            return _err(str(e))

    return router
