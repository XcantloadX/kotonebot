import shutil
from pathlib import Path
from typing import Callable
import traceback

from pydantic import BaseModel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from kotonebot.devtools.errors import CommandError, ValidationError

from .codegen import StandardGenerator
from .diagnostics import print_diagnostics_report
from .parsers import (
    KotoneV1Parser,
    ParserRegistry,
    load_resgen_runtime_context,
)
from .utils import build_class_tree


class ResgenGenerateResult(BaseModel):
    root_scan_path: str
    variant_names: list[str] | None
    parsed_file_count: int
    resource_count: int
    output_code_file: str


def _scan_files(path: str) -> list[str]:
    return [str(p) for p in Path(path).rglob("*") if p.is_file()]


def generate_resources(
    *,
    output_code_file: str,
    generator_factory: Callable[[str], StandardGenerator],
    conf_path: str = "./pyproject.toml",
    output_img_dir: str = "tmp",
    include_base_variant: bool = True,
    clean_output_img_dir: bool = True,
    show_progress: bool = True,
    show_diagnostics: bool = True,
    ignore_error: bool = False,
) -> ResgenGenerateResult:
    output_img_dir_path = Path(output_img_dir)
    if clean_output_img_dir and output_img_dir_path.exists():
        shutil.rmtree(output_img_dir_path)
    output_img_dir_path.mkdir(parents=True, exist_ok=True)

    runtime_context = load_resgen_runtime_context(
        conf_path=conf_path,
        include_base_variant=include_base_variant,
        output_img_dir=output_img_dir,
    )
    diagnostics = runtime_context.diagnostics
    if show_diagnostics:
        print_diagnostics_report(
            diagnostics,
            cwd=str(Path.cwd()),
            abort_on_error=not ignore_error,
        )
    error_count = sum(1 for diag in diagnostics if diag.severity == "error")
    if error_count > 0 and not ignore_error:
        raise CommandError(f"resgen aborted due to {error_count} error(s)")

    context = runtime_context.parser_context
    context['ignore_error'] = ignore_error
    root_scan_path = context["root_scan_path"]

    registry = ParserRegistry()
    registry.register(KotoneV1Parser())

    all_files = _scan_files(root_scan_path)
    all_resources = []
    parsed_file_count = 0

    def parse_all_files() -> None:
        nonlocal parsed_file_count
        for file_path in all_files:
            try:
                parsed_resources = registry.parse_file(file_path, context)
            except Exception:
                if not ignore_error:
                    raise
                else:
                    trace = traceback.format_exc()
                    print('WARN: Failed to parse file "{}":\n{}'.format(file_path, trace))
                    continue
            if not parsed_resources:
                continue
            parsed_file_count += 1
            all_resources.extend(parsed_resources)

    if not show_progress:
        parse_all_files()
    else:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TextColumn("{task.fields[current_file]}"),
            transient=False,
        )
        with progress:
            task_id = progress.add_task("Parsing resources", total=len(all_files), current_file="")
            for file_path in all_files:
                p = Path(file_path)
                rel_file_path = p.relative_to(root_scan_path).as_posix()
                progress.update(task_id, current_file=rel_file_path)
                try:
                    parsed_resources = registry.parse_file(file_path, context)
                except Exception:
                    if not ignore_error:
                        raise
                    else:
                        trace = traceback.format_exc()
                        print('WARN: Failed to parse file "{}":\n{}'.format(file_path, trace))
                        progress.advance(task_id)
                        continue
                if parsed_resources:
                    parsed_file_count += 1
                    all_resources.extend(parsed_resources)
                progress.advance(task_id)
            progress.update(task_id, current_file="done")

    tree = build_class_tree(all_resources)
    generator = generator_factory(runtime_context.default_variant)
    code = generator.generate(tree)

    output_code_path = Path(output_code_file)
    output_dir = output_code_path.parent
    if str(output_dir) != "" and not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    output_code_path.write_text(code, encoding="utf-8")

    init_file = output_img_dir_path / "__init__.py"
    init_file.write_text("", encoding="utf-8")

    variant_names = context.get("resource_variants")
    if variant_names is not None and not isinstance(variant_names, list):
        raise ValidationError("resource_variants must be list[str]")

    return ResgenGenerateResult(
        root_scan_path=root_scan_path,
        variant_names=variant_names,
        parsed_file_count=parsed_file_count,
        resource_count=len(all_resources),
        output_code_file=output_code_file,
    )
