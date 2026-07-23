"""共享数据类型定义。"""

from typing import Any, Literal, Optional

from pydantic import BaseModel


class SymbolTreeFileNode(BaseModel):
    kind: Literal["file"]
    label: str
    meta_path: str
    image_path: str
    definition_id: str
    variant: str | None = None


class SymbolTreeVariantNode(BaseModel):
    kind: Literal["variant"]
    label: str
    children: list[SymbolTreeFileNode]


class SymbolTreeSymbolNode(BaseModel):
    kind: Literal["symbol"]
    label: str
    full_name: str
    display_name: str | None = None
    children: list[SymbolTreeVariantNode]


class SymbolTreeGroupNode(BaseModel):
    kind: Literal["group"]
    label: str
    children: list["SymbolTreeGroupNode | SymbolTreeSymbolNode"]


class DirEntry(BaseModel):
    """目录条目。"""

    name: str
    is_directory: bool
    path: str
    is_image: bool


class FolderTreeNode(BaseModel):
    """目录树节点。"""

    name: str
    children: list["FolderTreeNode"]


class RenameResult(BaseModel):
    """重命名结果。"""

    source_path: str
    target_path: str


class CopyResult(BaseModel):
    """拷贝结果。"""

    status: str
    target_path: str


class UploadResult(BaseModel):
    """上传结果。"""

    status: str
    target_path: str


class SuggestPathResult(BaseModel):
    """AI 路径建议结果。"""
    path: str
    confidence: float = 0.0
    reason: str = ""


class ScreenshotResult(BaseModel):
    """设备截图结果。"""

    image_path: str


class HealthResult(BaseModel):
    """健康检查结果。"""

    status: str
    service: str


class ProjectRootData(BaseModel):
    """项目根数据。"""
    resource_root: str
    editor: Optional[dict] = None
    variant: Optional[dict] = None


class PrefabsSchema(BaseModel):
    """Prefab 模式版本。"""
    version: int
    prefabs: dict[str, Any]


class VariantCloneResult(BaseModel):
    """变体克隆结果。"""
    targetMetaPath: str
    definitionCount: int


class VariantImportPrecheckResult(BaseModel):
    """变体导入预检结果。"""
    targetImagePath: str
    targetImageExists: bool
    targetMetaPath: str
    targetMetaExists: bool
    copiedDefinitions: list[dict[str, str]]
    skippedDefinitions: list[dict[str, str]]


class VariantImportResult(BaseModel):
    """变体导入结果。"""
    targetImagePath: str
    size: int


class CopyPrefabPrecheckResult(BaseModel):
    """复制 Prefab 预检结果。"""
    targetImagePath: str
    targetImageExists: bool
    targetMetaPath: str
    targetMetaExists: bool
    targetDefinitionExists: bool
    sourceDefinitionId: str
    sourceDefinitionName: str
    targetDefinition: dict[str, Any]
    targetDefinitionOverwritten: Optional[bool] = None


class CopyPrefabResult(BaseModel):
    """复制 Prefab 结果。"""
    targetImagePath: str
    targetMetaPath: str
    definitionId: str
    definitionName: str
    targetDefinitionOverwritten: bool


class CreateDocumentResult(BaseModel):
    """创建文档结果。"""
    imagePath: str
    metaPath: str


class DeviceInfo(BaseModel):
    """ADB 设备信息。"""
    serial: str
    state: str
    name: str


class DeviceListResult(BaseModel):
    """ADB 设备列表结果。"""
    devices: list[DeviceInfo]
    error: Optional[str] = None


class DeviceScreenshotResult(BaseModel):
    """设备截图结果。"""
    success: bool
    imagePath: Optional[str] = None
    error: Optional[str] = None


class InferDefinitionsResult(BaseModel):
    """AI 定义推断结果。"""
    definitions: dict[str, Any]
