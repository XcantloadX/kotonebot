import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Sequence

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def write_min_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_HEADER)
    return path


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_png_with_meta(root: Path, rel_png_path: str, payload: Any) -> tuple[Path, Path]:
    png_path = root / rel_png_path
    write_min_png(png_path)
    meta_path = Path(f"{png_path.as_posix()}.json")
    write_json(meta_path, payload)
    return png_path, meta_path


def make_resgen_context(root: Path, **overrides: Any) -> dict[str, Any]:
    context = {
        "output_img_dir": root.as_posix(),
        "root_scan_path": root.as_posix(),
    }
    context.update(overrides)
    return context


def write_pyproject(
    path: Path,
    resource_path: str = "resources",
    r_file: str | None = None,
    variant_variants: Sequence[str] | None = None,
    variant_base: str | None = None,
    variant_path_pattern: str | None = None,
) -> Path:
    lines: list[str] = []
    lines.append("[tool.kotonebot.editor]")
    lines.append(f'resource_path = "{resource_path}"')
    if r_file is not None:
        lines.append(f'r_file = "{r_file}"')
    if variant_variants is not None or variant_base is not None or variant_path_pattern is not None:
        lines.append("")
        lines.append("[tool.kotonebot.variant]")
        if variant_variants is not None:
            variant_items = ", ".join(f'"{item}"' for item in variant_variants)
            lines.append(f"variants = [{variant_items}]")
        if variant_base is not None:
            lines.append(f'base = "{variant_base}"')
        if variant_path_pattern is not None:
            lines.append(f'path_pattern = "{variant_path_pattern}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@contextmanager
def in_cwd(path: Path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)
