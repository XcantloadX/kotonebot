"""变体操作路由。"""

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.services.types import (
    CopyPrefabPrecheckResult,
    CopyPrefabResult,
    VariantCloneResult,
    VariantImportPrecheckResult,
    VariantImportResult,
)
from ..dependencies import get_context
from ..models import (
    CloneVariantToImageRequest,
    PrecheckCopySelectedPrefabToVariantRequest, CopySelectedPrefabToVariantRequest,
    ResponseModel,
)
from . import ok_response

router = APIRouter(tags=["variant"])


@router.post("/meta/variant/clone_to_image", response_model=ResponseModel[VariantCloneResult])
async def clone_variant_to_image(body: CloneVariantToImageRequest = Body(...),
                                 ctx: DevtoolsContext = Depends(get_context)) -> JSONResponse:
    result = ctx.workspace.clone_variant_to_image(
        source_meta_path=body.sourceMetaPath,
        target_image_path=body.targetImagePath,
        variant=body.variant,
        force_overwrite=body.forceOverwrite,
    )
    return ok_response(result.model_dump())


@router.post("/meta/variant/import/precheck_path", response_model=ResponseModel[VariantImportPrecheckResult])
async def precheck_variant_import_path(
    sourceMetaPath: str = Form(...),
    baseImagePath: str = Form(...),
    variant: str = Form(...),
    image: UploadFile = File(...),
    ctx: DevtoolsContext = Depends(get_context),
) -> JSONResponse:
    uploaded_image_data = await image.read()
    result = ctx.workspace.precheck_variant_import_path(
        source_meta_path=sourceMetaPath,
        base_image_path=baseImagePath,
        variant=variant,
        uploaded_image_data=uploaded_image_data,
    )
    return ok_response(result.model_dump())


@router.post("/meta/variant/import_image", response_model=ResponseModel[VariantImportResult])
async def import_variant_image(
    baseImagePath: str = Form(...),
    variant: str = Form(...),
    image: UploadFile = File(...),
    deleteExistingTarget: bool = Form(False),
    ctx: DevtoolsContext = Depends(get_context),
) -> JSONResponse:
    image_data = await image.read()
    result = ctx.workspace.import_variant_image(
        base_image_path=baseImagePath,
        variant=variant,
        image_data=image_data,
        delete_existing_target=deleteExistingTarget,
    )
    return ok_response(result.model_dump())


@router.post("/meta/variant/copy_selected_prefab/precheck", response_model=ResponseModel[CopyPrefabPrecheckResult])
async def precheck_copy_selected_prefab_to_variant(
    body: PrecheckCopySelectedPrefabToVariantRequest = Body(...),
    ctx: DevtoolsContext = Depends(get_context),
) -> JSONResponse:
    result = ctx.workspace.precheck_copy_selected_prefab_to_variant(
        source_meta_path=body.sourceMetaPath,
        source_definition_id=body.sourceDefinitionId,
        base_image_path=body.baseImagePath,
        variant=body.variant,
    )
    return ok_response(result.model_dump())


@router.post("/meta/variant/copy_selected_prefab", response_model=ResponseModel[CopyPrefabResult])
async def copy_selected_prefab_to_variant(
    body: CopySelectedPrefabToVariantRequest = Body(...),
    ctx: DevtoolsContext = Depends(get_context),
) -> JSONResponse:
    result = ctx.workspace.copy_selected_prefab_to_variant(
        source_meta_path=body.sourceMetaPath,
        source_definition_id=body.sourceDefinitionId,
        base_image_path=body.baseImagePath,
        variant=body.variant,
        force_overwrite=body.forceOverwrite,
    )
    return ok_response(result.model_dump())
