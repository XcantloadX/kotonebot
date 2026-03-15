from typing import Literal

from pydantic import BaseModel, model_validator

from .codes import ensure_code_severity


Severity = Literal["error", "warning", "info"]


class Diagnostic(BaseModel):
    code: str
    message: str
    meta_path: str
    severity: Severity = "error"
    definition_id: str | None = None
    field_path: str | None = None
    line: int
    column: int
    end_line: int
    end_column: int

    @model_validator(mode="after")
    def validate_severity(self) -> "Diagnostic":
        ensure_code_severity(self.code, self.severity)
        return self

