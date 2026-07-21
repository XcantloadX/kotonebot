"""Single → Multi 转换的数据类型定义。"""

from enum import Enum

from pydantic import BaseModel


class ConversionMatch(BaseModel):
    """单个匹配结果：single 文档模板在目标图片中的命中记录。"""

    singleMetaPath: str | None
    """Single 文档的 JSON 元数据文件相对路径，_None_ 表示裸 PNG。"""
    singleImagePath: str
    """Single 文档对应的图片文件相对路径。"""
    matchedImagePath: str
    """匹配命中的目标图片相对路径。"""
    matchScore: float
    """模板匹配得分（归一化相关系数）。"""
    matchX: int
    """匹配区域左上角 X 坐标。"""
    matchY: int
    """匹配区域左上角 Y 坐标。"""
    matchW: int
    """匹配区域宽度。"""
    matchH: int
    """匹配区域高度。"""
    definitionType: str
    """定义类型（template / prefab）。"""
    definitionName: str
    """生成的定义名称（大驼峰）。"""
    definitionDisplayName: str
    """定义的显示名称（文件名）。"""


class ConfirmedMatch(BaseModel):
    """用户确认后的单条转换项。"""

    singleMetaPath: str | None
    """Single 文档的 JSON 元数据文件相对路径，_None_ 表示裸 PNG。"""
    singleImagePath: str
    """Single 文档对应的图片文件相对路径。"""
    matchedImagePath: str
    """匹配命中的目标图片相对路径。"""
    matchX: int
    """匹配区域左上角 X 坐标。"""
    matchY: int
    """匹配区域左上角 Y 坐标。"""
    matchW: int
    """匹配区域宽度。"""
    matchH: int
    """匹配区域高度。"""
    definitionType: str
    """定义类型（template / prefab）。"""
    definitionName: str
    """生成的定义名称（大驼峰）。"""
    definitionDisplayName: str
    """定义的显示名称（文件名）。"""
    targetMetaPath: str | None = None
    """目标 Multi 文档的元数据文件路径，不指定时由后端推算。"""


class ConversionScanResponse(BaseModel):
    """扫描结果响应。"""

    matches: list[ConversionMatch]
    """匹配结果列表。"""


class ConversionExecuteResponse(BaseModel):
    """转换执行结果。"""

    modifiedMetaPaths: list[str]
    """被修改的 Multi 元数据文件路径列表。"""
    deletedSingleMetaPaths: list[str]
    """被删除的 Single 元数据文件路径列表。"""
    deletedSingleImagePaths: list[str]
    """被删除的 Single 图片文件路径列表。"""


class ScanTaskState(str, Enum):
    """扫描任务状态枚举。"""

    PENDING = "pending"
    """任务已创建，等待执行。"""
    CLASSIFYING = "classifying"
    """正在分类 meta 文件。"""
    SCANNING = "scanning"
    """正在执行模板匹配。"""
    COMPLETED = "completed"
    """任务完成。"""
    CANCELLED = "cancelled"
    """任务已取消。"""
    ERROR = "error"
    """任务出错。"""


class ScanProgress(BaseModel):
    """扫描任务进度。"""

    taskId: str
    """任务唯一标识。"""
    state: ScanTaskState
    """当前状态。"""
    total: int = 0
    """待扫描总数。"""
    current: int = 0
    """已完成数量。"""
    currentFile: str = ""
    """当前正在处理的文件名。"""
    matches: list[ConversionMatch] | None = None
    """匹配结果，仅在 COMPLETED 状态时存在。"""
    error: str | None = None
    """错误信息，仅在 ERROR 状态时存在。"""


class ScanRequest(BaseModel):
    """启动扫描请求。"""

    mode: str
    """扫描模式: ``all`` / ``files`` / ``device``。"""
    imagePaths: list[str] | None = None
    """文件模式下的图片路径列表。"""
    screenshotPath: str | None = None
    """设备模式下的截图路径。"""


class ScanStartResponse(BaseModel):
    """启动扫描响应。"""

    taskId: str
    """任务 ID。"""
