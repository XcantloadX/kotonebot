"""HTTP 请求/响应模型。"""

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

from kotonebot.devtools.conversion.types import ConfirmedMatch


T = TypeVar("T")


class ResponseModel(BaseModel, Generic[T]):
    success: bool
    message: Optional[str] = None
    data: Optional[T] = None


class WriteTextRequest(BaseModel):
    content: str


class RenamePathRequest(BaseModel):
    """单文件重命名请求。"""

    sourcePath: str
    targetPath: str


class CopyFileRequest(BaseModel):
    """文件拷贝覆盖请求。"""

    sourcePath: str
    targetPath: str


class PrecheckRenameDocumentRequest(BaseModel):
    """文档重命名预检请求。"""

    sourceImagePath: str
    targetImagePath: str


class ExecuteRenameDocumentRequest(BaseModel):
    """文档重命名执行请求。"""

    sourceImagePath: str
    targetImagePath: str


class UpdateIndexRequest(BaseModel):
    metaPath: str


class CloneVariantToImageRequest(BaseModel):
    sourceMetaPath: str
    targetImagePath: str
    variant: str
    forceOverwrite: bool = False


class PrecheckCopySelectedPrefabToVariantRequest(BaseModel):
    sourceMetaPath: str
    sourceDefinitionId: str
    baseImagePath: str
    variant: str


class CopySelectedPrefabToVariantRequest(BaseModel):
    sourceMetaPath: str
    sourceDefinitionId: str
    baseImagePath: str
    variant: str
    forceOverwrite: bool = False


class ExecuteConversionRequest(BaseModel):
    matches: list[ConfirmedMatch]
