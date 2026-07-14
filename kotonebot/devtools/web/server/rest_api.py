import logging
from typing import Any, Generic, Optional, TypeVar

from fastapi import APIRouter, Body, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from kotonebot.devtools.ai.types import AiConfig
from kotonebot.devtools.errors import DevtoolsError
from kotonebot.devtools.server_commands.types import parse_server_command_request
from kotonebot.devtools.project.project import Project

from .rest_api_logic import RestApiLogic


T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None


class WriteTextRequest(BaseModel):
    content: str


class RenamePathRequest(BaseModel):
    """单文件重命名请求。"""

    sourcePath: str
    targetPath: str


class CopyFileRequest(BaseModel):
    """文件拷贝覆盖请求（用于替换当前文档图片的服务端路径来源）。"""

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
        return _ok(logic.get_project_root_data())

    @router.get("/project/list_images")
    async def list_workspace_images():
        return _ok(logic.list_workspace_images())

    @router.get("/project/symbol_tree")
    async def get_project_symbol_tree():
        return _ok(logic.get_project_symbol_tree())

    @router.get("/fs/list_dir")
    async def list_dir(path: str = Query(..., description="Path relative to project root or absolute path")):
        return _ok(logic.list_dir(path))

    @router.get("/fs/read_text")
    async def read_text(path: str = Query(...)):
        return _ok(logic.read_text(path))

    @router.put("/fs/write_text")
    async def write_text(path: str = Query(...), body: WriteTextRequest = Body(...)):
        return _ok(logic.write_text(path, body.content))

    @router.post("/fs/rename")
    async def rename_path(body: RenamePathRequest = Body(...)):
        return _ok(logic.rename_path(body.sourcePath, body.targetPath))

    @router.post("/fs/copy_file")
    async def copy_file(body: CopyFileRequest = Body(...)):
        return _ok(logic.copy_file(body.sourcePath, body.targetPath))

    @router.post("/fs/upload_file")
    async def upload_file(
        targetPath: str = Form(...),
        file: UploadFile = File(...),
    ):
        file_data = await file.read()
        return _ok(logic.upload_file(target_path=targetPath, file_data=file_data))

    @router.post("/fs/rename_document/precheck")
    async def precheck_rename_document(body: PrecheckRenameDocumentRequest = Body(...)):
        return _ok(
            logic.precheck_rename_document(
                source_image_path=body.sourceImagePath,
                target_image_path=body.targetImagePath,
            )
        )

    @router.post("/fs/rename_document/execute")
    async def execute_rename_document(body: ExecuteRenameDocumentRequest = Body(...)):
        return _ok(
            logic.execute_rename_document(
                source_image_path=body.sourceImagePath,
                target_image_path=body.targetImagePath,
            )
        )

    @router.get("/image")
    async def get_image(path: str = Query(...)):
        safe_path = logic.get_image_path(path)
        return FileResponse(safe_path)

    @router.get("/image/thumbnail")
    async def get_image_thumbnail(path: str = Query(...), size: int = Query(128, ge=1, le=2048)):
        cache_path = logic.get_image_thumbnail_path(path, size)
        return FileResponse(cache_path)

    @router.get("/image/hover_preview")
    async def get_image_hover_preview(
        path: str = Query(...),
        size: int | None = Query(None, ge=1, le=4096),
        x1: float | None = Query(None),
        y1: float | None = Query(None),
        x2: float | None = Query(None),
        y2: float | None = Query(None),
    ):
        cache_path = logic.get_image_hover_preview_path(
            path=path,
            size=size,
            x1=x1,
            y1=y1,
            x2=x2,
            y2=y2,
        )
        return FileResponse(cache_path)

    @router.get("/prefabs/schema")
    async def get_prefabs_schema():
        return _ok(logic.get_prefabs_schema())

    @router.get("/meta/index")
    async def get_meta_index():
        return _ok(logic.get_meta_index())

    @router.post("/meta/index/update")
    async def update_meta_index(body: UpdateIndexRequest = Body(...)):
        return _ok(logic.update_meta_index(body.metaPath))

    @router.get("/meta/diagnostics")
    async def get_meta_diagnostics():
        return _ok(logic.get_meta_diagnostics())

    @router.get("/meta/index/health")
    async def get_meta_index_health():
        return _ok(logic.get_meta_index_health())

    @router.post("/meta/variant/clone_to_image")
    async def clone_variant_to_image(body: CloneVariantToImageRequest = Body(...)):
        result = logic.clone_variant_to_image(
            source_meta_path=body.sourceMetaPath,
            target_image_path=body.targetImagePath,
            variant=body.variant,
            force_overwrite=body.forceOverwrite,
        )
        return _ok(result)

    @router.post("/meta/variant/import/precheck_path")
    async def precheck_variant_import_path(
        sourceMetaPath: str = Form(...),
        baseImagePath: str = Form(...),
        variant: str = Form(...),
        image: UploadFile = File(...),
    ):
        uploaded_image_data = await image.read()
        result = logic.precheck_variant_import_path(
            source_meta_path=sourceMetaPath,
            base_image_path=baseImagePath,
            variant=variant,
            uploaded_image_data=uploaded_image_data,
        )
        return _ok(result)

    @router.post("/meta/variant/import_image")
    async def import_variant_image(
        baseImagePath: str = Form(...),
        variant: str = Form(...),
        image: UploadFile = File(...),
        deleteExistingTarget: bool = Form(False),
    ):
        image_data = await image.read()
        result = logic.import_variant_image(
            base_image_path=baseImagePath,
            variant=variant,
            image_data=image_data,
            delete_existing_target=deleteExistingTarget,
        )
        return _ok(result)

    @router.post("/meta/variant/copy_selected_prefab/precheck")
    async def precheck_copy_selected_prefab_to_variant(body: PrecheckCopySelectedPrefabToVariantRequest = Body(...)):
        result = logic.precheck_copy_selected_prefab_to_variant(
            source_meta_path=body.sourceMetaPath,
            source_definition_id=body.sourceDefinitionId,
            base_image_path=body.baseImagePath,
            variant=body.variant,
        )
        return _ok(result)

    @router.post("/meta/variant/copy_selected_prefab")
    async def copy_selected_prefab_to_variant(body: CopySelectedPrefabToVariantRequest = Body(...)):
        result = logic.copy_selected_prefab_to_variant(
            source_meta_path=body.sourceMetaPath,
            source_definition_id=body.sourceDefinitionId,
            base_image_path=body.baseImagePath,
            variant=body.variant,
            force_overwrite=body.forceOverwrite,
        )
        return _ok(result)

    @router.post("/fs/reveal_in_explorer")
    async def reveal_in_explorer(path: str = Query(...)):
        logic.reveal_in_explorer(path)
        return _ok()

    @router.get("/fs/folder_tree")
    async def get_folder_tree():
        return _ok(logic.get_folder_tree())

    @router.post("/ai/suggest_path")
    async def suggest_document_path(
        image: UploadFile = File(...),
        providerType: str = Form(...),
        endpoint: str = Form(""),
        model: str = Form(""),
        apiKey: str = Form(""),
    ):
        image_data = await image.read()
        ai_config = AiConfig(
            providerType=providerType,
            endpoint=endpoint,
            model=model,
            apiKey=apiKey,
        )
        return _ok(logic.suggest_document_path(image_data, ai_config))

    @router.post("/ai/infer_definitions")
    async def infer_definitions(
        image: UploadFile = File(...),
        definitionsJson: str = Form(...),
        imagePath: str = Form(...),
        providerType: str = Form(...),
        endpoint: str = Form(""),
        model: str = Form(""),
        apiKey: str = Form(""),
    ):
        image_data = await image.read()
        ai_config = AiConfig(
            providerType=providerType,
            endpoint=endpoint,
            model=model,
            apiKey=apiKey,
        )
        return _ok(logic.infer_definitions(
            image_bytes=image_data,
            definitions_json=definitionsJson,
            image_path=imagePath,
            ai_config=ai_config,
        ))

    @router.post("/document/create")
    async def create_document(
        targetPath: str = Form(...),
        image: UploadFile = File(...),
    ):
        image_data = await image.read()
        return _ok(logic.create_document(image_data, targetPath))

    @router.get("/health")
    async def health_check():
        return _ok(logic.get_health())

    @router.get("/device/adb/list")
    async def list_adb_devices():
        return _ok(logic.list_adb_devices())

    @router.get("/device/adb/screenshot")
    async def capture_adb_screenshot(serial: str = Query(...), displayId: int | None = Query(None)):
        return _ok(logic.capture_device_screenshot(serial=serial, display_id=displayId))

    @router.get("/server/commands")
    async def get_server_commands():
        return _ok([item.model_dump() for item in logic.workspace.list_server_commands()])

    @router.post("/server/execute_command")
    async def execute_server_command(body: dict[str, Any] = Body(...)):
        request = parse_server_command_request(body)
        return _ok(logic.workspace.execute_server_command(request).model_dump())

    return router
