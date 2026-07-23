"""格式转换路由。"""

from fastapi import APIRouter, Body, Depends, HTTPException

from kotonebot.devtools.conversion.types import ScanRequest, ScanStartResponse
from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context
from ..models import ExecuteConversionRequest
from . import ok_response

router = APIRouter(tags=["conversion"])


@router.post("/conversion/execute")
async def conversion_execute(body: ExecuteConversionRequest = Body(...),
                             ctx: DevtoolsContext = Depends(get_context)):
    return ok_response(ctx.conversion.execute(body.matches))


@router.post("/conversion/scan")
async def conversion_scan(body: ScanRequest = Body(...),
                          ctx: DevtoolsContext = Depends(get_context)):
    mode = body.mode
    if mode == "all":
        task_id = ctx.conversion.start_scan_all()
    elif mode == "files":
        task_id = ctx.conversion.start_scan_files(body.imagePaths or [])
    elif mode == "device":
        task_id = ctx.conversion.start_scan_device(body.screenshotPath or "")
    elif mode == "current":
        task_id = ctx.conversion.start_scan_current(body.singleImagePath or "")
    else:
        raise ValueError(f"Unknown scan mode: {mode}")
    return ok_response(ScanStartResponse(taskId=task_id))


@router.get("/conversion/scan_progress/{task_id}")
async def conversion_scan_progress(task_id: str,
                                   ctx: DevtoolsContext = Depends(get_context)):
    progress = ctx.conversion.get_scan_progress(task_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return ok_response(progress)


@router.delete("/conversion/scan/{task_id}")
async def conversion_cancel_scan(task_id: str,
                                 ctx: DevtoolsContext = Depends(get_context)):
    cancelled = ctx.conversion.cancel_scan(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found")
    return ok_response()
