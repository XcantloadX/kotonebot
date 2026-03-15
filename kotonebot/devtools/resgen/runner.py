import os
import shutil
from typing import Callable

from pydantic import BaseModel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .codegen import StandardGenerator
from .diagnostics import print_diagnostics_report
from .parsers import (
    BasicSpriteParser,
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
    files: list[str] = []
    for root, _, filenames in os.walk(path):
        for file_name in filenames:
            files.append(os.path.join(root, file_name))
    return files


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
    if clean_output_img_dir and os.path.exists(output_img_dir):
        shutil.rmtree(output_img_dir)
    os.makedirs(output_img_dir, exist_ok=True)

    runtime_context = load_resgen_runtime_context(
        conf_path=conf_path,
        include_base_variant=include_base_variant,
        output_img_dir=output_img_dir,
    )
    diagnostics = runtime_context.diagnostics
    if show_diagnostics:
        print_diagnostics_report(
            diagnostics,
            cwd=os.getcwd(),
            abort_on_error=not ignore_error,
        )
    error_count = sum(1 for diag in diagnostics if diag.severity == "error")
    if error_count > 0 and not ignore_error:
        raise ValueError(f"resgen aborted due to {error_count} error(s)")

    context = runtime_context.parser_context
    root_scan_path = context["root_scan_path"]

    registry = ParserRegistry()
    registry.register(KotoneV1Parser())
    registry.register(BasicSpriteParser())

    all_files = _scan_files(root_scan_path)
    all_resources = []
    parsed_file_count = 0

    def parse_all_files() -> None:
        nonlocal parsed_file_count
        for file_path in all_files:
            if file_path.endswith(".png") and os.path.exists(file_path + ".json"):
                continue
            parsed_resources = registry.parse_file(file_path, context)
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
                rel_file_path = os.path.relpath(file_path, root_scan_path)
                progress.update(task_id, current_file=rel_file_path)
                if file_path.endswith(".png") and os.path.exists(file_path + ".json"):
                    progress.advance(task_id)
                    continue
                parsed_resources = registry.parse_file(file_path, context)
                if parsed_resources:
                    parsed_file_count += 1
                    all_resources.extend(parsed_resources)
                progress.advance(task_id)
            progress.update(task_id, current_file="done")

    tree = build_class_tree(all_resources)
    generator = generator_factory(runtime_context.default_variant)
    code = generator.generate(tree)

    output_dir = os.path.dirname(output_code_file)
    if output_dir != "" and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(output_code_file, "w", encoding="utf-8") as handle:
        handle.write(code)

    init_file = os.path.join(output_img_dir, "__init__.py")
    with open(init_file, "w", encoding="utf-8") as handle:
        handle.write("")

    variant_names = context.get("resource_variants")
    if variant_names is not None and not isinstance(variant_names, list):
        raise ValueError("resource_variants must be list[str]")

    return ResgenGenerateResult(
        root_scan_path=root_scan_path,
        variant_names=variant_names,
        parsed_file_count=parsed_file_count,
        resource_count=len(all_resources),
        output_code_file=output_code_file,
    )
