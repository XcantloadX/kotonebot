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


class ListDirItem(BaseModel):
    """目录条目（HTTP 响应）。

    ``thumbnailUrl`` 仅在条目为图片时由路由填充，否则为 None。
    """

    name: str
    isDirectory: bool
    path: str
    isImage: bool
    thumbnailUrl: str | None = None


class ListDirResponse(BaseModel):
    """列出目录响应。"""

    items: list[ListDirItem]


class ReadTextResponse(BaseModel):
    """读取文本响应。"""

    content: str


class ListImagesResponse(BaseModel):
    """工作区图片列表响应。"""

    imagePaths: list[str]


class CaptureScreenshotResponse(BaseModel):
    """设备截图响应。

    成功时填充 ``imagePath`` 与 ``imageUrl``，失败时仅填充 ``success=False`` 与 ``error``。
    """

    success: bool
    imagePath: str | None = None
    imageUrl: str | None = None
    error: str | None = None


class SuggestPathResponse(BaseModel):
    """AI 路径建议响应。

    直接透传 AI 服务返回的目录与文件名建议。
    """

    suggestedDir: str
    suggestedFilename: str
    reason: str
