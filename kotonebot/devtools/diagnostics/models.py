from dataclasses import dataclass
from typing import Literal

from .codes import ensure_code_severity


Severity = Literal["error", "warning", "info"]


@dataclass(slots=True)
class Diagnostic:
    code: str
    message: str
    meta_path: str
    severity: Severity = "error"
    definition_id: str | None = None
    field_path: str | None = None

    def __post_init__(self) -> None:
        ensure_code_severity(self.code, self.severity)

