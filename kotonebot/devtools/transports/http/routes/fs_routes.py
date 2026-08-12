"""文件系统路由。"""

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import CopyResult, FolderTreeNode, RenameResult, UploadResult
from ..dependencies import get_context
from ..models import (
    WriteTextRequest, RenamePathRequest, CopyFileRequest,
    ResponseModel, ListDirResponse, ReadTextResponse,
)
from . import ok_response

router = APIRouter(tags=["filesystem"])


@router.get("/fs/list_dir", response_model=ResponseModel[ListDirResponse])
async def list_dir(path: str = Query(...), ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    entries = ctx.files.list_dir(path)
    data = []
    for entry in entries:
        item = entry.model_dump()
        if entry.is_image:
            item["thumbnailUrl"] = f"/api/image/thumbnail?path={entry.path}&size=128"
        data.append(item)
    return ok_response({"items": data})


@router.get("/fs/read_text", response_model=ResponseModel[ReadTextResponse])
async def read_text(path: str = Query(...), ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    content = ctx.files.read_text(path)
    return ok_response({"content": content})


@router.put("/fs/write_text", response_model=ResponseModel[None])
async def write_text(path: str = Query(...), body: WriteTextRequest = Body(...),
                     ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    ctx.files.write_text(path, body.content)
    return ok_response()


@router.post("/fs/rename", response_model=ResponseModel[RenameResult])
async def rename_path(body: RenamePathRequest = Body(...),
                      ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    result = ctx.files.rename_path(body.sourcePath, body.targetPath)
    return ok_response(result.model_dump())


@router.post("/fs/copy_file", response_model=ResponseModel[CopyResult])
async def copy_file(body: CopyFileRequest = Body(...),
                    ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    result = ctx.files.copy_file(body.sourcePath, body.targetPath)
    return ok_response(result.model_dump())


@router.post("/fs/upload_file", response_model=ResponseModel[UploadResult])
async def upload_file(targetPath: str = Form(...), file: UploadFile = File(...),
                      ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    file_data = await file.read()
    result = ctx.files.upload_file(target_path=targetPath, file_data=file_data)
    return ok_response(result.model_dump())


@router.post("/fs/reveal_in_explorer", response_model=ResponseModel[None])
async def reveal_in_explorer(path: str = Query(...),
                             ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    ctx.files.reveal_in_explorer(path)
    return ok_response()


@router.get("/fs/folder_tree", response_model=ResponseModel[list[FolderTreeNode]])
async def get_folder_tree(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    tree = ctx.files.get_folder_tree()
    return ok_response([node.model_dump() for node in tree])
