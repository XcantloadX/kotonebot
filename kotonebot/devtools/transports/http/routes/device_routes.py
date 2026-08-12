"""设备操作路由。"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import DeviceListResult, DeviceScreenshotResult
from ..dependencies import get_context
from ..models import CaptureScreenshotResponse, ResponseModel
from . import ok_response

router = APIRouter(tags=["device"])


@router.get("/device/adb/list", response_model=ResponseModel[DeviceListResult])
async def list_adb_devices(ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    return ok_response(ctx.device.list_adb_devices().model_dump())


@router.get("/device/adb/screenshot", response_model=ResponseModel[CaptureScreenshotResponse])
async def capture_adb_screenshot(serial: str = Query(...), displayId: int | None = Query(None),
                                 ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    result = ctx.device.capture_screenshot(serial=serial, display_id=displayId)
    if isinstance(result, DeviceScreenshotResult) and not result.success:
        return ok_response(result.model_dump())
    image_url = f"/api/image?path={result.imagePath}"
    return ok_response({"success": True, "imagePath": result.imagePath, "imageUrl": image_url})
