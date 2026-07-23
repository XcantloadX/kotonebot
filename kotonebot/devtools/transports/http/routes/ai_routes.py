"""AI 服务路由。"""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from kotonebot.devtools.ai.types import AiConfig
from kotonebot.devtools.services.context import DevtoolsContext
from ..dependencies import get_context
from . import ok_response

router = APIRouter(tags=["ai"])


@router.post("/ai/suggest_path")
async def suggest_document_path(
    image: UploadFile = File(...),
    providerType: str = Form(...),
    endpoint: str = Form(""),
    model: str = Form(""),
    apiKey: str = Form(""),
    ctx: DevtoolsContext = Depends(get_context),
):
    image_data = await image.read()
    ai_config = AiConfig(
        providerType=providerType, endpoint=endpoint, model=model, apiKey=apiKey,
    )
    return ok_response(ctx.ai.suggest_document_path(image_data, ai_config))


@router.post("/ai/infer_definitions")
async def infer_definitions(
    image: UploadFile = File(...),
    definitionsJson: str = Form(...),
    imagePath: str = Form(...),
    providerType: str = Form(...),
    endpoint: str = Form(""),
    model: str = Form(""),
    apiKey: str = Form(""),
    ctx: DevtoolsContext = Depends(get_context),
):
    image_data = await image.read()
    ai_config = AiConfig(
        providerType=providerType, endpoint=endpoint, model=model, apiKey=apiKey,
    )
    return ok_response(ctx.ai.infer_definitions(
        image_bytes=image_data,
        definitions_json=definitionsJson,
        image_path=imagePath,
        ai_config=ai_config,
    ))
