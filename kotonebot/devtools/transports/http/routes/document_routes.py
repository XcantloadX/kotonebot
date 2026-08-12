"""文档操作路由（重命名、创建）。"""

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from kotonebot.devtools.indexing.document_index_view import (
    RenameDocumentExecuteResultModel,
    RenameDocumentPrecheckResultModel,
)
from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import CreateDocumentResult
from ..dependencies import get_context
from ..models import (
    PrecheckRenameDocumentRequest, ExecuteRenameDocumentRequest,
    ResponseModel,
)
from . import ok_response

router = APIRouter(tags=["document"])


@router.post("/fs/rename_document/precheck", response_model=ResponseModel[RenameDocumentPrecheckResultModel])
async def precheck_rename_document(body: PrecheckRenameDocumentRequest = Body(...),
                                   ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(
        ctx.workspace.precheck_rename_document(
            source_image_path=body.sourceImagePath,
            target_image_path=body.targetImagePath,
        )
    )


@router.post("/fs/rename_document/execute", response_model=ResponseModel[RenameDocumentExecuteResultModel])
async def execute_rename_document(body: ExecuteRenameDocumentRequest = Body(...),
                                  ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(
        ctx.workspace.execute_rename_document(
            source_image_path=body.sourceImagePath,
            target_image_path=body.targetImagePath,
        )
    )


@router.post("/document/create", response_model=ResponseModel[CreateDocumentResult])
async def create_document(targetPath: str = Form(...), image: UploadFile = File(...),
                          ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    image_data = await image.read()
    return ok_response(ctx.workspace.create_document(image_data, targetPath).model_dump())
