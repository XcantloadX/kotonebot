#!/usr/bin/env python3
"""Migrate devtools meta schema from v2 to v3.

Usage examples:
  python tools/migrate_meta_v2_to_v3.py --root ./resources
  python tools/migrate_meta_v2_to_v3.py --root ./resources --write --backup .bak --report migration_report.json
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

try:
    import tomllib  # type: ignore[attr-defined]
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

VariantPolicy = Literal["inherit", "require", "exclude"]


@dataclass
class FileResult:
    meta_path: str
    status: Literal["migrated", "skipped", "error"]
    message: str
    changes: dict[str, Any] = field(default_factory=dict)


def _to_policy(value: Any, none_default: VariantPolicy) -> VariantPolicy:
    if value is True:
        return "inherit"
    if value is False:
        return "require"
    return none_default


def _iter_meta_files(root: Path) -> list[Path]:
    return sorted([p for p in root.rglob("*.json") if p.is_file()])


def _looks_like_meta(payload: dict[str, Any]) -> bool:
    return isinstance(payload.get("definitions"), dict) and isinstance(payload.get("version"), int)


def _migrate_payload(payload: dict[str, Any], *, none_default: VariantPolicy) -> tuple[dict[str, Any], dict[str, Any]]:
    if payload.get("version") != 2:
        raise ValueError(f"expected version=2, got {payload.get('version')}")

    definitions = payload.get("definitions")
    if not isinstance(definitions, dict):
        raise ValueError("definitions must be an object")

    migrated = {
        "version": 3,
        "definitions": {},
    }

    stats = {
        "total_definitions": 0,
        "base_prefabs_migrated": 0,
        "variant_prefabs": 0,
        "inferred_require": 0,
        "inferred_inherit": 0,
    }

    for definition_id, definition in definitions.items():
        if not isinstance(definition, dict):
            raise ValueError(f"definition must be object: {definition_id}")
        stats["total_definitions"] += 1

        updated = dict(definition)
        is_prefab = updated.get("type") == "prefab"
        is_base_prefab = is_prefab and updated.get("variant") is None

        if is_prefab and not is_base_prefab:
            stats["variant_prefabs"] += 1

        if is_base_prefab:
            old = updated.pop("variant_inherit", None)
            policy = _to_policy(old, none_default)
            variant_policy: dict[str, VariantPolicy] = {}
            updated["variant_policy"] = variant_policy
            updated["_migrated_policy_hint"] = policy
            stats["base_prefabs_migrated"] += 1
            if policy == "inherit":
                stats["inferred_inherit"] += 1
            else:
                stats["inferred_require"] += 1

        migrated["definitions"][definition_id] = updated

    return migrated, stats


def _resolve_variant_config(
    *,
    root: Path,
    pyproject_path: Path | None,
    variants_arg: str | None,
) -> tuple[list[str], str | None]:
    if variants_arg:
        variants = [item.strip() for item in variants_arg.split(",") if item.strip()]
        return variants, None

    if pyproject_path is None:
        candidate = root / "pyproject.toml"
        if candidate.exists():
            pyproject_path = candidate

    if pyproject_path is None or not pyproject_path.exists():
        return [], None

    payload = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    tool = payload.get("tool")
    if not isinstance(tool, dict):
        return [], None
    kotonebot = tool.get("kotonebot")
    if not isinstance(kotonebot, dict):
        return [], None
    variant = kotonebot.get("variant")
    if not isinstance(variant, dict):
        return [], None

    variants = variant.get("variants")
    base_variant = variant.get("base")
    if not isinstance(variants, list):
        return [], base_variant if isinstance(base_variant, str) else None
    normalized = [item for item in variants if isinstance(item, str) and item.strip()]
    return normalized, base_variant if isinstance(base_variant, str) else None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_migration(
    *,
    root: Path,
    write: bool,
    backup_suffix: str,
    report_path: Path | None,
    none_default: VariantPolicy,
    variants: list[str],
    base_variant: str | None,
) -> int:
    files = _iter_meta_files(root)
    results: list[FileResult] = []

    for file_path in files:
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive path
            results.append(FileResult(file_path.as_posix(), "error", f"invalid json: {exc}"))
            continue

        if not isinstance(payload, dict) or not _looks_like_meta(payload):
            continue

        version = payload.get("version")
        if version != 2:
            results.append(FileResult(file_path.as_posix(), "skipped", f"version={version}"))
            continue

        try:
            migrated_payload, stats = _migrate_payload(payload, none_default=none_default)
            if variants:
                for definition in migrated_payload["definitions"].values():
                    if not isinstance(definition, dict):
                        continue
                    if definition.get("type") != "prefab" or definition.get("variant") is not None:
                        continue
                    policy = definition.pop("_migrated_policy_hint", none_default)
                    populated: dict[str, VariantPolicy] = {}
                    for item in variants:
                        if base_variant is not None and item == base_variant:
                            continue
                        populated[item] = policy
                    definition["variant_policy"] = populated
            for definition in migrated_payload["definitions"].values():
                if isinstance(definition, dict):
                    definition.pop("_migrated_policy_hint", None)
            if write:
                backup = file_path.with_name(file_path.name + backup_suffix)
                if backup.exists():
                    raise ValueError(f"backup file already exists: {backup.as_posix()}")
                backup.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")
                _write_json(file_path, migrated_payload)
            results.append(
                FileResult(
                    file_path.as_posix(),
                    "migrated",
                    "ok" if write else "dry-run",
                    changes=stats,
                )
            )
        except Exception as exc:
            results.append(FileResult(file_path.as_posix(), "error", str(exc)))

    migrated_count = sum(1 for item in results if item.status == "migrated")
    error_count = sum(1 for item in results if item.status == "error")
    skipped_count = sum(1 for item in results if item.status == "skipped")

    report = {
        "root": root.as_posix(),
        "mode": "write" if write else "dry-run",
        "none_default": none_default,
        "variants": variants,
        "base_variant": base_variant,
        "summary": {
            "migrated": migrated_count,
            "skipped": skipped_count,
            "errors": error_count,
        },
        "results": [
            {
                "meta_path": item.meta_path,
                "status": item.status,
                "message": item.message,
                "changes": item.changes,
            }
            for item in results
        ],
    }

    print(json.dumps(report["summary"], ensure_ascii=False))
    if report_path is not None:
        _write_json(report_path, report)
        print(f"report saved: {report_path.as_posix()}")

    if error_count > 0:
        return 2
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate meta schema from v2 to v3")
    parser.add_argument("--root", required=True, help="Resource root directory to scan")
    parser.add_argument("--write", action="store_true", help="Write migrated payloads in-place")
    parser.add_argument("--backup", default=".bak", help="Backup suffix used with --write")
    parser.add_argument("--report", default=None, help="Optional path to save migration report json")
    parser.add_argument("--pyproject", default=None, help="Optional pyproject.toml path for variant config")
    parser.add_argument("--variants", default=None, help="Comma-separated variant list. Overrides pyproject lookup")
    parser.add_argument(
        "--none-default",
        choices=["inherit", "require", "exclude"],
        default="require",
        help="Mapping policy when variant_inherit is null or absent",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        print(f"invalid root directory: {root.as_posix()}")
        return 2
    report_path = Path(args.report).resolve() if args.report else None
    pyproject_path = Path(args.pyproject).resolve() if args.pyproject else None
    variants, base_variant = _resolve_variant_config(
        root=root,
        pyproject_path=pyproject_path,
        variants_arg=args.variants,
    )

    return run_migration(
        root=root,
        write=args.write,
        backup_suffix=args.backup,
        report_path=report_path,
        none_default=args.none_default,
        variants=variants,
        base_variant=base_variant,
    )


if __name__ == "__main__":
    raise SystemExit(main())
