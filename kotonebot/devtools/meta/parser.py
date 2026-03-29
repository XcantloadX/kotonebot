import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import MetaModel, MetaV3Model


class MetaValidationError(ValueError):
    def __init__(self, message: str, field_path: str | None) -> None:
        super().__init__(message)
        self.field_path = field_path


def _detect_meta_version(data: dict[str, Any]) -> int:
    version = data.get("version")
    if not isinstance(version, int):
        raise MetaValidationError("meta version must be an integer", "version")
    if version != 3:
        raise MetaValidationError(f"unsupported meta version: {version}", "version")
    return version


def parse_meta_text(text: str) -> MetaModel:
    data = json.loads(text)
    _detect_meta_version(data)
    try:
        return MetaV3Model.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors(include_url=False)
        field_path: str | None = None
        if len(errors) > 0:
            first = errors[0]
            loc = first.get("loc")
            if isinstance(loc, tuple) and len(loc) > 0:
                field_path = ".".join(str(item) for item in loc)
        raise MetaValidationError(str(exc), field_path) from exc


def parse_meta_file(meta_path: str | Path) -> MetaModel:
    path = Path(meta_path)
    text = path.read_text(encoding="utf-8")
    return parse_meta_text(text)
