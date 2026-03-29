import re

import pytest

from kotonebot.devtools.diagnostics.codes import REGISTRY
from kotonebot.devtools.diagnostics.models import Diagnostic


def test_diagnostic_codes_format_and_uniqueness():
    pattern = re.compile(r"^KBT-[EWI]-[A-Z]{3,6}-\d{4}$")
    codes = list(REGISTRY.keys())
    assert len(codes) == len(set(codes))
    assert all(pattern.match(code) for code in codes)


def test_diagnostic_registry_has_summary():
    for code, code_def in REGISTRY.items():
        assert code_def.code == code
        assert code_def.summary != ""


def test_diagnostic_severity_must_match_code_registry():
    sample_code, sample_def = next(iter(REGISTRY.items()))
    wrong_severity = "error" if sample_def.severity != "error" else "warning"
    with pytest.raises(ValueError):
        Diagnostic(
            code=sample_code,
            severity=wrong_severity,
            message="x",
            meta_path="a.png.json",
            line=1,
            column=1,
            end_line=1,
            end_column=2,
        )
