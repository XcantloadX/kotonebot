import re
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict


class DiagnosticCodeDef(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    severity: Literal["error", "warning", "info"]
    summary: str

# 元数据文件无法解析（JSON 格式错误或 schema 校验失败）。
META_FILE_PARSE_ERROR: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-META-0001",
    severity="error",
    summary="Meta file parse failed.",
)
# 变体定义本身非法（类型、名称、声明值等不符合规则）。
META_VARIANT_INVALID: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-META-0101",
    severity="error",
    summary="Meta variant declaration is invalid.",
)
# 项目已启用 variant，但 base prefab 未显式声明 variant_inherit（隐式等同 False）。
META_VARIANT_INHERIT_DISABLED: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-W-META-0201",
    severity="warning",
    summary="Base prefab has implicit variant_inherit=False while project variant is configured.",
)
# 项目未启用 variant，但 prefab 显式设置了 variant_inherit（该配置当前无效）。
META_VARIANT_INHERIT_UNUSED: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-W-META-0202",
    severity="warning",
    summary="variant_inherit is set but project variant is not configured.",
)
# base prefab 声明 variant_inherit=False 时，缺少项目要求的某些 variant 文档。
META_VARIANT_INHERIT_MISSING_VARIANTS: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-META-0102",
    severity="error",
    summary="variant_inherit=False requires all configured variant documents.",
)
# 索引阶段：definition_id 非法（为空或类型错误）。
INDEX_DEF_ID_INVALID: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-IDX-0001",
    severity="error",
    summary="Definition id is invalid.",
)
# 索引阶段：definition 结构解析失败。
INDEX_DEF_PARSE_ERROR: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-IDX-0002",
    severity="error",
    summary="Definition parse failed during indexing.",
)
# 索引阶段：文件层解析失败（通常来自 meta 读入失败）。
INDEX_FILE_PARSE_ERROR: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-IDX-0003",
    severity="error",
    summary="Meta file parse failed during indexing.",
)
# 索引阶段：variant 规则校验失败（通用入口）。
INDEX_VARIANT_INVALID: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-IDX-0101",
    severity="error",
    summary="Variant validation failed during indexing.",
)
# 索引阶段：项目启用 variant 时，base prefab 未显式声明 variant_inherit。
INDEX_VARIANT_INHERIT_DISABLED: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-W-IDX-0201",
    severity="warning",
    summary="Variant inheritance is disabled during indexing.",
)
# 索引阶段：项目未启用 variant，但出现了 variant_inherit 显式配置。
INDEX_VARIANT_INHERIT_UNUSED: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-W-IDX-0202",
    severity="warning",
    summary="variant_inherit is set but project variant is not configured during indexing.",
)
# 索引阶段：variant_inherit=False 时缺少必需的 variant 文档。
INDEX_VARIANT_INHERIT_MISSING_VARIANTS: Final[DiagnosticCodeDef] = DiagnosticCodeDef(
    code="KBT-E-IDX-0102",
    severity="error",
    summary="variant_inherit=False requires all configured variant documents during indexing.",
)

ALL_CODES: Final[tuple[DiagnosticCodeDef, ...]] = (
    META_FILE_PARSE_ERROR,
    META_VARIANT_INVALID,
    META_VARIANT_INHERIT_DISABLED,
    META_VARIANT_INHERIT_UNUSED,
    META_VARIANT_INHERIT_MISSING_VARIANTS,
    INDEX_DEF_ID_INVALID,
    INDEX_DEF_PARSE_ERROR,
    INDEX_FILE_PARSE_ERROR,
    INDEX_VARIANT_INVALID,
    INDEX_VARIANT_INHERIT_DISABLED,
    INDEX_VARIANT_INHERIT_UNUSED,
    INDEX_VARIANT_INHERIT_MISSING_VARIANTS,
)

REGISTRY: Final[dict[str, DiagnosticCodeDef]] = {item.code: item for item in ALL_CODES}

_CODE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^KBT-[EWI]-[A-Z]{3,6}-\d{4}$")


def ensure_code_registered(code: str) -> None:
    if code not in REGISTRY:
        raise ValueError(f"Unregistered diagnostic code: {code}")
    if _CODE_PATTERN.match(code) is None:
        raise ValueError(f"Invalid diagnostic code format: {code}")


def get_code_def(code: str) -> DiagnosticCodeDef:
    ensure_code_registered(code)
    return REGISTRY[code]


def ensure_code_severity(code: str, severity: str) -> None:
    expected = get_code_def(code).severity
    if severity != expected:
        raise ValueError(
            f"Diagnostic severity mismatch for {code}: expected '{expected}', got '{severity}'"
        )


for _item in ALL_CODES:
    ensure_code_registered(_item.code)
