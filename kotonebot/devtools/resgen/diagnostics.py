from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from rich.console import Console
from rich.text import Text

from ..diagnostics.models import Diagnostic


class DiagnosticSummary(BaseModel):
    error_count: int
    warning_count: int
    info_count: int

    @property
    def total(self) -> int:
        return self.error_count + self.warning_count + self.info_count


_SEVERITY_ORDER: dict[str, int] = {
    "error": 0,
    "warning": 1,
    "info": 2,
}

_SEVERITY_STYLE: dict[str, str] = {
    "error": "bold red",
    "warning": "bold yellow",
    "info": "bold cyan",
}


def summarize_diagnostics(diagnostics: list[Diagnostic]) -> DiagnosticSummary:
    errors = sum(1 for diag in diagnostics if diag.severity == "error")
    warnings = sum(1 for diag in diagnostics if diag.severity == "warning")
    infos = sum(1 for diag in diagnostics if diag.severity == "info")
    return DiagnosticSummary(
        error_count=errors,
        warning_count=warnings,
        info_count=infos,
    )


def print_diagnostics_report(
    diagnostics: list[Diagnostic],
    *,
    cwd: str | None = None,
    console: Console | None = None,
    abort_on_error: bool = True,
) -> DiagnosticSummary:
    summary = summarize_diagnostics(diagnostics)
    if summary.total == 0:
        return summary

    resolved_console = console or Console()
    base = Path(cwd).resolve() if cwd is not None else None
    sorted_diags = sorted(
        diagnostics,
        key=lambda diag: (
            _SEVERITY_ORDER[diag.severity],
            diag.code,
            diag.meta_path,
            diag.definition_id or "",
        ),
    )

    for diag in sorted_diags:
        location = _format_location(diag, base)
        header = Text()
        header.append(diag.severity, style=_SEVERITY_STYLE[diag.severity])
        header.append(f"[{diag.code}]")
        header.append(": ")
        header.append(diag.message)
        resolved_console.print(header)
        resolved_console.print(f"  --> {location}")
        if diag.field_path is not None:
            resolved_console.print(f"   = field: {diag.field_path}")
        resolved_console.print("")

    if summary.error_count > 0 and abort_on_error:
        resolved_console.print(
            Text(
                "error: aborting due to "
                f"{summary.error_count} previous error(s); "
                f"{summary.warning_count} warning(s), "
                f"{summary.info_count} info message(s) emitted",
                style="bold red",
            )
        )
    elif summary.error_count > 0:
        resolved_console.print(
            Text(
                "error: encountered "
                f"{summary.error_count} error(s); "
                f"{summary.warning_count} warning(s), "
                f"{summary.info_count} info message(s) emitted; continuing due to --ignore-error",
                style="bold yellow",
            )
        )
    elif summary.warning_count > 0:
        resolved_console.print(
            Text(
                f"warning: {summary.warning_count} warning(s), "
                f"{summary.info_count} info message(s) emitted",
                style="bold yellow",
            )
        )
    else:
        resolved_console.print(
            Text(
                f"info: {summary.info_count} info message(s) emitted",
                style="bold cyan",
            )
        )
    return summary


def _format_location(diag: Diagnostic, base: Path | None) -> str:
    path = diag.meta_path
    if base is not None:
        try:
            path = Path(path).resolve().relative_to(base).as_posix()
        except ValueError:
            path = Path(path).resolve().as_posix()
    if diag.definition_id is not None:
        return f"{path}::{diag.definition_id}"
    return path
