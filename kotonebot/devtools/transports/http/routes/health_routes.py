"""健康检查路由。"""

from fastapi import APIRouter, Depends

from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context
from . import ok_response

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.health.check().model_dump())
