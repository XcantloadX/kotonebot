"""图像服务路由。"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context

router = APIRouter(tags=["image"])


@router.get("/image")
async def get_image(path: str = Query(...), ctx: DevtoolsContext = Depends(get_context)):
    safe_path = ctx.images.resolve_image_path(path)
    return FileResponse(safe_path)


@router.get("/image/thumbnail")
async def get_image_thumbnail(
    path: str = Query(...),
    size: int = Query(128, ge=1, le=2048),
    x1: int | None = Query(None),
    y1: int | None = Query(None),
    x2: int | None = Query(None),
    y2: int | None = Query(None),
    ctx: DevtoolsContext = Depends(get_context),
):
    cache_path = ctx.images.get_thumbnail(path, size, x1=x1, y1=y1, x2=x2, y2=y2)
    return FileResponse(cache_path)


@router.get("/image/hover_preview")
async def get_image_hover_preview(
    path: str = Query(...),
    size: int | None = Query(None, ge=1, le=4096),
    x1: float | None = Query(None),
    y1: float | None = Query(None),
    x2: float | None = Query(None),
    y2: float | None = Query(None),
    ctx: DevtoolsContext = Depends(get_context),
):
    cache_path = ctx.images.get_hover_preview(
        path=path, size=size, x1=x1, y1=y1, x2=x2, y2=y2,
    )
    return FileResponse(cache_path)
