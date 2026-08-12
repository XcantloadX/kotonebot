"""元数据索引路由。"""

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from kotonebot.devtools.indexing.symbol_index_view import (
    MetaDiagnosticsSnapshotModel,
    SymbolIndexHealthModel,
    SymbolSnapshotLiteModel,
    SymbolUpdateResultModel,
)
from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import PrefabsSchema
from ..dependencies import get_context
from ..models import ResponseModel, UpdateIndexRequest
from . import ok_response

router = APIRouter(tags=["meta"])


@router.get("/prefabs/schema", response_model=ResponseModel[PrefabsSchema])
async def get_prefabs_schema(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.workspace.get_prefabs_schema().model_dump())


@router.get("/meta/index", response_model=ResponseModel[SymbolSnapshotLiteModel])
async def get_meta_index(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.workspace.get_meta_index())


@router.post("/meta/index/update", response_model=ResponseModel[SymbolUpdateResultModel])
async def update_meta_index(body: UpdateIndexRequest = Body(...),
                            ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.workspace.update_meta_index(body.metaPath))


@router.get("/meta/diagnostics", response_model=ResponseModel[MetaDiagnosticsSnapshotModel])
async def get_meta_diagnostics(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.workspace.get_meta_diagnostics())


@router.get("/meta/index/health", response_model=ResponseModel[SymbolIndexHealthModel])
async def get_meta_index_health(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.workspace.get_meta_index_health())
