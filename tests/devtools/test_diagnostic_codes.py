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
    warning_code = next(code for code, code_def in REGISTRY.items() if code_def.severity == "warning")
    with pytest.raises(ValueError):
        Diagnostic(
            code=warning_code,
            severity="error",
            message="x",
            meta_path="a.png.json",
        )
