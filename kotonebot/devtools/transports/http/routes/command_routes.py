"""服务器命令路由。"""

from typing import Any

from fastapi import APIRouter, Body, Depends
from fastapi.responses import JSONResponse

from kotonebot.devtools.commands.types import (
    ServerCommandResponse,
    ServerCommandSpec,
    parse_server_command_request,
)
from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context
from ..models import ResponseModel
from . import ok_response

router = APIRouter(tags=["commands"])


@router.get("/server/commands", response_model=ResponseModel[list[ServerCommandSpec]])
async def get_server_commands(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response([item.model_dump() for item in ctx.workspace.list_server_commands()])


@router.post("/server/execute_command", response_model=ResponseModel[ServerCommandResponse])
async def execute_server_command(body: dict[str, Any] = Body(...),
                                 ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    request = parse_server_command_request(body)
    dispatcher = ctx.command_dispatcher
    return ok_response(dispatcher.execute(request).model_dump())
