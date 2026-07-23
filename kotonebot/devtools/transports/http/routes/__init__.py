"""路由共享工具函数。"""

from fastapi.responses import JSONResponse
from ..models import ResponseModel


def ok_response(data=None, message=None) -> JSONResponse:
    return JSONResponse(ResponseModel(success=True, message=message, data=data).model_dump())


def err_response(message: str) -> JSONResponse:
    return JSONResponse(ResponseModel(success=False, message=message, data=None).model_dump())
