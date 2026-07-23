"""元数据索引路由。"""

from fastapi import APIRouter, Body, Depends

from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context
from ..models import UpdateIndexRequest
from . import ok_response

router = APIRouter(tags=["meta"])


@router.get("/prefabs/schema")
async def get_prefabs_schema(ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.workspace.get_prefabs_schema().model_dump())


@router.get("/meta/index")
async def get_meta_index(ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.workspace.get_meta_index())


@router.post("/meta/index/update")
async def update_meta_index(body: UpdateIndexRequest = Body(...),
                            ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.workspace.update_meta_index(body.metaPath))


@router.get("/meta/diagnostics")
async def get_meta_diagnostics(ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.workspace.get_meta_diagnostics())


@router.get("/meta/index/health")
async def get_meta_index_health(ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.workspace.get_meta_index_health())
