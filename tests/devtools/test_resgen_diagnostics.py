from io import StringIO
from pathlib import Path

from rich.console import Console

from kotonebot.devtools.diagnostics.codes import (
    META_VARIANT_INHERIT_DISABLED,
    META_VARIANT_INHERIT_MISSING_VARIANTS,
)
from kotonebot.devtools.diagnostics.models import Diagnostic
from kotonebot.devtools.resgen.diagnostics import print_diagnostics_report


def test_print_diagnostics_report_compiler_style_output(tmp_path: Path):
    meta_path = (tmp_path / "resources" / "ui" / "button.png.json").resolve()
    diagnostics = [
        Diagnostic(
            code=META_VARIANT_INHERIT_DISABLED.code,
            severity="warning",
            message="base prefab has implicit variant_inherit=False while project variant is configured: ui.button",
            meta_path=meta_path.as_posix(),
            definition_id="base",
            field_path="definitions.base.variant_inherit",
        ),
        Diagnostic(
            code=META_VARIANT_INHERIT_MISSING_VARIANTS.code,
            severity="error",
            message="variant_inherit=False requires all configured variants to exist: ui.button; missing=en",
            meta_path=meta_path.as_posix(),
            definition_id="base",
            field_path="definitions.base.variant_inherit",
        ),
    ]

    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=240)
    summary = print_diagnostics_report(
        diagnostics,
        cwd=tmp_path.as_posix(),
        console=console,
    )
    output = stream.getvalue()

    assert summary.error_count == 1
    assert summary.warning_count == 1
    assert "warning[KBT-W-META-0201]:" in output
    assert "error[KBT-E-META-0102]:" in output
    assert "  --> resources/ui/button.png.json::base" in output
    assert "   = field: definitions.base.variant_inherit" in output
    assert "error: aborting due to 1 previous error(s); 1 warning(s), 0 info message(s) emitted" in output


def test_print_diagnostics_report_empty_output():
    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None)
    summary = print_diagnostics_report([], console=console)
    output = stream.getvalue()

    assert summary.total == 0
    assert output == ""


def test_print_diagnostics_report_continue_output_when_not_abort(tmp_path: Path):
    meta_path = (tmp_path / "resources" / "ui" / "button.png.json").resolve()
    diagnostics = [
        Diagnostic(
            code=META_VARIANT_INHERIT_MISSING_VARIANTS.code,
            severity="error",
            message="variant_inherit=False requires all configured variants to exist: ui.button; missing=en",
            meta_path=meta_path.as_posix(),
            definition_id="base",
            field_path="definitions.base.variant_inherit",
        ),
    ]

    stream = StringIO()
    console = Console(file=stream, force_terminal=False, color_system=None, width=240)
    summary = print_diagnostics_report(
        diagnostics,
        cwd=tmp_path.as_posix(),
        console=console,
        abort_on_error=False,
    )
    output = stream.getvalue()

    assert summary.error_count == 1
    assert "error: encountered 1 error(s);" in output
    assert "continuing due to --ignore-error" in output
    assert "error: aborting due to 1 previous error(s);" not in output
