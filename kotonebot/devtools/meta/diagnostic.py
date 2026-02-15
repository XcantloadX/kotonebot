from dataclasses import dataclass
from typing import Literal


Severity = Literal["error", "warning", "info"]


@dataclass(slots=True)
class Diagnostic:
    """诊断信息。
    
    用于记录解析 meta 文档时发生的错误、警告或提示等。
    """
    code: str
    message: str
    meta_path: str
    severity: Severity = "error"
    definition_id: str | None = None
    field_path: str | None = None
