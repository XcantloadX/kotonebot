from __future__ import annotations

from .models import Diagnostic


def make_error(
    *,
    code: str,
    message: str,
    meta_path: str,
    definition_id: str | None = None,
    field_path: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity="error",
        message=message,
        meta_path=meta_path,
        definition_id=definition_id,
        field_path=field_path,
    )
