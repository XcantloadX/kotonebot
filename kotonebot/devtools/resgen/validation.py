from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel

class MetaValidationError(ValueError):
    """Raised when a meta JSON file does not conform to expected schema."""


MetaFormat = Literal["single", "multi"]


class MetaSchemaInfo(BaseModel):
    """Lightweight description of detected meta schema.

    This is intentionally minimal for now but can be extended later
    (e.g. to carry source path, name list, etc.).
    """

    format: MetaFormat
    is_single_flag: bool | None


def _ensure_bool_or_none(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise MetaValidationError(f"Field '{field_name}' must be boolean if present.")


def detect_and_validate_meta_schema(data: Dict[str, Any]) -> MetaSchemaInfo:
    """Detect whether meta JSON is in single or multi format and validate structure.

    Rules:
        - Multi format:
            * Top-level `version` MUST be 3.
      * MUST contain `definitions` (object).
      * MUST NOT contain `annotations`.
    - Single format (V1):
      * Top-level `isSimple` MUST be true.
      * MUST contain `definition` (object).
      * MUST NOT contain `definitions` or `annotations`.
    """

    if not isinstance(data, dict):
        raise MetaValidationError("Meta JSON root must be an object.")

    # --- Multi format branch (versioned schema, no annotations) ---
    version = data.get("version")
    if version is not None:
        if version != 3:
            raise MetaValidationError(f"Unsupported meta version: {version!r}")

        has_definitions = "definitions" in data
        has_annotations = "annotations" in data

        if not has_definitions:
            raise MetaValidationError("Multi meta must contain field 'definitions'.")
        if has_annotations:
            raise MetaValidationError("Multi meta must not contain field 'annotations'.")

        definitions = data["definitions"]
        if not isinstance(definitions, dict):
            raise MetaValidationError("Field 'definitions' must be an object (mapping).")

        return MetaSchemaInfo(format="multi", is_single_flag=None)

    raw_flag = data.get("isSimple")
    is_single_flag = _ensure_bool_or_none(raw_flag, "isSimple")

    has_definition = "definition" in data
    has_definitions = "definitions" in data
    has_annotations = "annotations" in data

    # --- Single format branch (V1) ---
    if is_single_flag is True:
        if not has_definition:
            raise MetaValidationError("Single meta must contain field 'definition'.")
        if has_definitions or has_annotations:
            raise MetaValidationError(
                "Single meta must not contain 'definitions' or 'annotations'."
            )
        definition = data["definition"]
        if not isinstance(definition, dict):
            raise MetaValidationError("Field 'definition' must be an object.")
        return MetaSchemaInfo(format="single", is_single_flag=True)

    raise MetaValidationError(
        "Unrecognized meta format: must have 'isSimple: true' (single) or 'version: 3' (multi)."
    )
