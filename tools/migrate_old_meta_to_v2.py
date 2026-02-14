import argparse
import json
import struct
from pathlib import Path
from typing import Any


class MigrationError(ValueError):
    pass


def _require_dict(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MigrationError(f"Field '{field}' must be an object.")
    return value


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise MigrationError(f"Field '{field}' must be an array.")
    return value


def _require_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MigrationError(f"Field '{field}' must be a non-empty string.")
    return value


def _require_number(value: Any, field: str) -> int | float:
    if not isinstance(value, (int, float)):
        raise MigrationError(f"Field '{field}' must be a number.")
    return value


def _parse_old_format(data: dict[str, Any]) -> str:
    version = data.get("version")
    if version is not None:
        raise MigrationError("Input already has 'version'; expected old v1 meta.")
    if data.get("isSimple") is True:
        if "definition" not in data:
            raise MigrationError("Simple v1 meta missing top-level 'definition'.")
        return "simple"
    if "definitions" in data and "annotations" in data:
        return "complex"
    raise MigrationError("Unknown input format; expected v1 simple or v1 complex.")


def _read_png_size(png_path: Path) -> tuple[int, int]:
    with png_path.open("rb") as f:
        sig = f.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise MigrationError(f"Not a PNG file: {png_path}")
        chunk_len_bytes = f.read(4)
        chunk_type = f.read(4)
        if len(chunk_len_bytes) != 4 or chunk_type != b"IHDR":
            raise MigrationError(f"Invalid PNG header: {png_path}")
        chunk_len = struct.unpack(">I", chunk_len_bytes)[0]
        if chunk_len != 13:
            raise MigrationError(f"Unexpected IHDR length in PNG: {png_path}")
        ihdr = f.read(13)
        if len(ihdr) != 13:
            raise MigrationError(f"Corrupted IHDR in PNG: {png_path}")
        width, height = struct.unpack(">II", ihdr[:8])
    return width, height


def _build_image_rect(rect_data: dict[str, Any]) -> dict[str, int | float | str]:
    x1 = _require_number(rect_data.get("x1"), "annotation.data.x1")
    y1 = _require_number(rect_data.get("y1"), "annotation.data.y1")
    x2 = _require_number(rect_data.get("x2"), "annotation.data.x2")
    y2 = _require_number(rect_data.get("y2"), "annotation.data.y2")
    return {"kind": "image", "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _build_rect(rect_data: dict[str, Any]) -> dict[str, int | float | str]:
    x1 = _require_number(rect_data.get("x1"), "annotation.data.x1")
    y1 = _require_number(rect_data.get("y1"), "annotation.data.y1")
    x2 = _require_number(rect_data.get("x2"), "annotation.data.x2")
    y2 = _require_number(rect_data.get("y2"), "annotation.data.y2")
    return {"kind": "rect", "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def _build_point(point_data: dict[str, Any]) -> dict[str, int | float | str]:
    x = _require_number(point_data.get("x"), "annotation.data.x")
    y = _require_number(point_data.get("y"), "annotation.data.y")
    return {"kind": "point", "x": x, "y": y}


def _convert_complex(old_data: dict[str, Any]) -> dict[str, Any]:
    old_definitions = _require_dict(old_data.get("definitions"), "definitions")
    old_annotations = _require_list(old_data.get("annotations"), "annotations")
    annotation_map: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(old_annotations):
        ann = _require_dict(item, f"annotations[{idx}]")
        ann_id = _require_str(ann.get("id"), f"annotations[{idx}].id")
        annotation_map[ann_id] = ann

    new_definitions: dict[str, dict[str, Any]] = {}
    for def_id, raw_def in old_definitions.items():
        definition = _require_dict(raw_def, f"definitions.{def_id}")
        def_type = _require_str(definition.get("type"), f"definitions.{def_id}.type")
        name = _require_str(definition.get("name"), f"definitions.{def_id}.name")
        annotation_id = _require_str(
            definition.get("annotationId"), f"definitions.{def_id}.annotationId"
        )
        annotation = _require_dict(annotation_map.get(annotation_id), f"annotations[{annotation_id}]")
        ann_type = _require_str(annotation.get("type"), f"annotations[{annotation_id}].type")
        ann_data = _require_dict(annotation.get("data"), f"annotations[{annotation_id}].data")

        out_def: dict[str, Any] = {
            "type": def_type,
            "name": name,
            "props": {},
        }
        if "displayName" in definition:
            out_def["displayName"] = definition["displayName"]
        if "description" in definition:
            out_def["description"] = definition["description"]

        if def_type == "template":
            if ann_type != "rect":
                raise MigrationError(f"Definition '{def_id}' expects rect annotation.")
            out_def["type"] = "prefab"
            out_def["prefab_id"] = "TemplateMatchPrefab"
            out_def["props"]["template"] = _build_image_rect(ann_data)
        elif def_type == "prefab":
            if ann_type != "rect":
                raise MigrationError(f"Definition '{def_id}' expects rect annotation.")
            prefab = _require_dict(definition.get("prefab"), f"definitions.{def_id}.prefab")
            class_name = _require_str(
                prefab.get("className"), f"definitions.{def_id}.prefab.className"
            )
            out_def["prefab_id"] = class_name
            out_def["props"]["templateImage"] = _build_image_rect(ann_data)
        elif def_type == "hint-box":
            if ann_type != "rect":
                raise MigrationError(f"Definition '{def_id}' expects rect annotation.")
            out_def["props"]["region"] = _build_rect(ann_data)
        elif def_type == "hint-point":
            if ann_type != "point":
                raise MigrationError(f"Definition '{def_id}' expects point annotation.")
            out_def["props"]["point"] = _build_point(ann_data)
        else:
            raise MigrationError(f"Unsupported definition type: '{def_type}' in '{def_id}'.")

        new_definitions[def_id] = out_def

    return {"version": 2, "definitions": new_definitions}


def _convert_simple(old_data: dict[str, Any], png_path: Path) -> dict[str, Any]:
    definition = _require_dict(old_data.get("definition"), "definition")
    def_type = _require_str(definition.get("type"), "definition.type")
    name = _require_str(definition.get("name"), "definition.name")
    width, height = _read_png_size(png_path)
    full_image = {"kind": "image", "x1": 0, "y1": 0, "x2": width, "y2": height}
    full_rect = {"kind": "rect", "x1": 0, "y1": 0, "x2": width, "y2": height}

    out_def: dict[str, Any] = {"type": def_type, "name": name, "props": {}}
    if "displayName" in definition:
        out_def["displayName"] = definition["displayName"]
    if "description" in definition:
        out_def["description"] = definition["description"]

    if def_type == "template":
        out_def["type"] = "prefab"
        out_def["prefab_id"] = "TemplateMatchPrefab"
        out_def["props"]["template"] = full_image
    elif def_type == "prefab":
        prefab = _require_dict(definition.get("prefab"), "definition.prefab")
        class_name = _require_str(prefab.get("className"), "definition.prefab.className")
        out_def["prefab_id"] = class_name
        out_def["props"]["templateImage"] = full_image
    elif def_type == "hint-box":
        out_def["props"]["region"] = full_rect
    else:
        raise MigrationError(f"Unsupported simple definition type: '{def_type}'.")

    return {"version": 2, "definitions": {"migrated_definition": out_def}}


def migrate_meta_file(input_path: Path, output_path: Path) -> None:
    raw = input_path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise MigrationError("Meta JSON root must be an object.")

    format_name = _parse_old_format(data)
    png_path = Path(str(input_path)[:-5])
    if not png_path.exists():
        raise MigrationError(f"PNG file not found for meta: {png_path}")

    if format_name == "complex":
        migrated = _convert_complex(data)
    else:
        migrated = _convert_simple(data, png_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _iter_meta_files(path: Path) -> list[Path]:
    if path.is_file():
        if not path.name.endswith(".png.json"):
            raise MigrationError(f"Input file must end with '.png.json': {path}")
        return [path]
    if path.is_dir():
        return sorted(path.rglob("*.png.json"))
    raise MigrationError(f"Input path not found: {path}")


def _output_path(input_file: Path, root: Path, in_place: bool) -> Path:
    if in_place:
        return input_file
    rel = input_file.relative_to(root) if root.is_dir() else Path(input_file.name)
    return rel.with_suffix("").with_suffix(".png.v2.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate old v1 meta (.png.json) to v2 format.")
    parser.add_argument("path", help="Input .png.json file or directory.")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite source .png.json files.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory when not using --in-place. Defaults to input root.",
    )
    args = parser.parse_args()

    input_root = Path(args.path).resolve()
    files = _iter_meta_files(input_root)
    if not files:
        raise MigrationError(f"No .png.json files found under: {input_root}")

    if args.in_place and args.output_dir is not None:
        raise MigrationError("--output-dir cannot be used together with --in-place.")

    if args.in_place:
        output_root = input_root
    else:
        output_root = Path(args.output_dir).resolve() if args.output_dir else input_root
        output_root.mkdir(parents=True, exist_ok=True)

    migrated_count = 0
    for src in files:
        dst = _output_path(src, input_root, args.in_place)
        if not args.in_place:
            dst = output_root / dst
        migrate_meta_file(src, dst)
        print(f"[OK] {src} -> {dst}")
        migrated_count += 1

    print(f"Migrated {migrated_count} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
