"""项目相关路由。"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import ProjectRootData, SymbolTreeGroupNode, SymbolTreeSymbolNode
from ..dependencies import get_context
from ..models import ResponseModel, ListImagesResponse
from . import ok_response

router = APIRouter(tags=["project"])


@router.get("/project/root", response_model=ResponseModel[ProjectRootData])
async def get_project_root(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.workspace.get_project_root_data().model_dump())


@router.get("/project/list_images", response_model=ResponseModel[ListImagesResponse])
async def list_workspace_images(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response({"imagePaths": ctx.workspace.list_workspace_images()})


@router.get("/project/symbol_tree", response_model=ResponseModel[list[SymbolTreeGroupNode | SymbolTreeSymbolNode]])
async def get_project_symbol_tree(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    tree = ctx.workspace.get_symbol_tree()
    return ok_response([node.model_dump(mode="json") for node in tree])
