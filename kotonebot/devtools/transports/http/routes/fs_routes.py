"""文件系统路由。"""

from fastapi import APIRouter, Body, Depends, File, Form, Query, UploadFile

from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context
from ..models import (
    WriteTextRequest, RenamePathRequest, CopyFileRequest,
)
from . import ok_response

router = APIRouter(tags=["filesystem"])


@router.get("/fs/list_dir")
async def list_dir(path: str = Query(...), ctx: DevtoolsContext = Depends(get_context)):
    entries = ctx.files.list_dir(path)
    data = []
    for entry in entries:
        item = entry.model_dump()
        if entry.is_image:
            item["thumbnailUrl"] = f"/api/image/thumbnail?path={entry.path}&size=128"
        data.append(item)
    return ok_response({"items": data})


@router.get("/fs/read_text")
async def read_text(path: str = Query(...), ctx: DevtoolsContext = Depends(get_context)):
    content = ctx.files.read_text(path)
    return ok_response({"content": content})


@router.put("/fs/write_text")
async def write_text(path: str = Query(...), body: WriteTextRequest = Body(...),
                     ctx: DevtoolsContext = Depends(get_context)):
    ctx.files.write_text(path, body.content)
    return ok_response()


@router.post("/fs/rename")
async def rename_path(body: RenamePathRequest = Body(...),
                      ctx: DevtoolsContext = Depends(get_context)):
    result = ctx.files.rename_path(body.sourcePath, body.targetPath)
    return ok_response(result.model_dump())


@router.post("/fs/copy_file")
async def copy_file(body: CopyFileRequest = Body(...),
                    ctx: DevtoolsContext = Depends(get_context)):
    result = ctx.files.copy_file(body.sourcePath, body.targetPath)
    return ok_response(result.model_dump())


@router.post("/fs/upload_file")
async def upload_file(targetPath: str = Form(...), file: UploadFile = File(...),
                      ctx: DevtoolsContext = Depends(get_context)):
    file_data = await file.read()
    result = ctx.files.upload_file(target_path=targetPath, file_data=file_data)
    return ok_response(result.model_dump())


@router.post("/fs/reveal_in_explorer")
async def reveal_in_explorer(path: str = Query(...),
                             ctx: DevtoolsContext = Depends(get_context)):
    ctx.files.reveal_in_explorer(path)
    return ok_response()


@router.get("/fs/folder_tree")
async def get_folder_tree(ctx: DevtoolsContext = Depends(get_context)):
    tree = ctx.files.get_folder_tree()
    return ok_response([node.model_dump() for node in tree])
