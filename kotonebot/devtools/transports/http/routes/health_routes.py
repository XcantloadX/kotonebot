"""健康检查路由。"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import HealthResult
from ..dependencies import get_context
from ..models import ResponseModel
from . import ok_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ResponseModel[HealthResult])
async def health_check(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.health.check().model_dump())
