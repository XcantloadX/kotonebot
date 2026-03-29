from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel

class MetaValidationError(ValueError):
    """Raised when a meta JSON file does not conform to expected schema."""


MetaFormat = Literal["simple", "complex", "v3"]


class MetaSchemaInfo(BaseModel):
    """Lightweight description of detected meta schema.

    This is intentionally minimal for now but can be extended later
    (e.g. to carry source path, name list, etc.).
    """

    format: MetaFormat
    is_simple_flag: bool | None


def _ensure_bool_or_none(value: Any, field_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise MetaValidationError(f"Field '{field_name}' must be boolean if present.")


def detect_and_validate_meta_schema(data: Dict[str, Any]) -> MetaSchemaInfo:
    """Detect whether meta JSON is in simple/complex/v3 format and validate structure.

    Rules:
        - Meta v3 format:
            * Top-level `version` MUST be 3.
      * MUST contain `definitions` (object).
      * MUST NOT contain `annotations`.
    - Simple format (V1):
      * Top-level `isSimple` MUST be true.
      * MUST contain `definition` (object).
      * MUST NOT contain `definitions` or `annotations`.
    - Complex format (V1):
      * `isSimple` is absent or false (these two are strictly equivalent).
      * MUST contain `definitions` and `annotations`.
      * MUST NOT contain `definition`.
    """

    if not isinstance(data, dict):
        raise MetaValidationError("Meta JSON root must be an object.")

    # --- Meta v3 branch (versioned schema, no annotations) ---
    version = data.get("version")
    if version is not None:
        if version != 3:
            raise MetaValidationError(f"Unsupported meta version: {version!r}")

        has_definitions = "definitions" in data
        has_annotations = "annotations" in data

        if not has_definitions:
            raise MetaValidationError("Meta v3 must contain field 'definitions'.")
        if has_annotations:
            raise MetaValidationError("Meta v3 must not contain field 'annotations'.")

        definitions = data["definitions"]
        if not isinstance(definitions, dict):
            raise MetaValidationError("Field 'definitions' must be an object (mapping).")

        return MetaSchemaInfo(format="v3", is_simple_flag=None)

    raw_flag = data.get("isSimple")
    is_simple_flag = _ensure_bool_or_none(raw_flag, "isSimple")

    has_definition = "definition" in data
    has_definitions = "definitions" in data
    has_annotations = "annotations" in data

    # --- Simple format branch (V1) ---
    if is_simple_flag is True:
        if not has_definition:
            raise MetaValidationError("Simple meta must contain field 'definition'.")
        if has_definitions or has_annotations:
            raise MetaValidationError(
                "Simple meta must not contain 'definitions' or 'annotations'."
            )
        definition = data["definition"]
        if not isinstance(definition, dict):
            raise MetaValidationError("Field 'definition' must be an object.")
        return MetaSchemaInfo(format="simple", is_simple_flag=True)

    # --- Complex format branch (V1, isSimple is false or missing) ---
    if has_definition:
        # For complex meta, we never allow the single `definition` field.
        raise MetaValidationError(
            "Complex meta must not contain top-level field 'definition'."
        )

    if not (has_definitions and has_annotations):
        raise MetaValidationError(
            "Complex meta must contain both 'definitions' and 'annotations'."
        )

    # Basic structural checks; detailed content validation can be added later.
    definitions = data["definitions"]
    annotations = data["annotations"]
    if not isinstance(definitions, dict):
        raise MetaValidationError("Field 'definitions' must be an object (mapping).")
    if not isinstance(annotations, list):
        raise MetaValidationError("Field 'annotations' must be an array.")

    return MetaSchemaInfo(format="complex", is_simple_flag=False)
