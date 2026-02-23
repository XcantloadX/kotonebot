import json
from pathlib import Path

from pydantic import ValidationError

from .models import MetaV2Model


class MetaValidationError(ValueError):
    def __init__(self, message: str, field_path: str | None) -> None:
        super().__init__(message)
        self.field_path = field_path


def parse_meta_text(text: str) -> MetaV2Model:
    data = json.loads(text)
    try:
        return MetaV2Model.model_validate(data)
    except ValidationError as exc:
        errors = exc.errors(include_url=False)
        field_path: str | None = None
        if len(errors) > 0:
            first = errors[0]
            loc = first.get("loc")
            if isinstance(loc, tuple) and len(loc) > 0:
                field_path = ".".join(str(item) for item in loc)
        raise MetaValidationError(str(exc), field_path) from exc


def parse_meta_file(meta_path: str | Path) -> MetaV2Model:
    path = Path(meta_path)
    text = path.read_text(encoding="utf-8")
    return parse_meta_text(text)
