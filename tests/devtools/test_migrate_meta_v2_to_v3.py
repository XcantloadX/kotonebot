import json
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.devtools._testkit import write_png_with_meta, write_pyproject


SCRIPT_PATH = Path("tools/migrate_meta_v2_to_v3.py").resolve()


def _run_script(args: list[str]) -> tuple[int, str, str]:
    import subprocess
    import sys

    process = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    return process.returncode, process.stdout, process.stderr


def test_migrate_v2_to_v3_dry_run_with_variant_resolution_from_pyproject():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = root / "resources"
        resources.mkdir(parents=True, exist_ok=True)
        write_pyproject(
            root / "pyproject.toml",
            resource_path="resources",
            variant_variants=["base", "en", "jp"],
            variant_base="base",
            variant_path_pattern="nest",
        )
        _, meta_path = write_png_with_meta(
            resources,
            "ui/button.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_inherit": True,
                        "props": {},
                    }
                },
            },
        )

        report_path = root / "migration_report.json"
        code, stdout, stderr = _run_script([
            "--root",
            resources.as_posix(),
            "--pyproject",
            (root / "pyproject.toml").as_posix(),
            "--report",
            report_path.as_posix(),
        ])
        assert stderr == ""
        assert code == 0
        assert '"migrated": 1' in stdout

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["summary"]["migrated"] == 1
        assert report["mode"] == "dry-run"
        assert report["variants"] == ["base", "en", "jp"]

        original_payload = json.loads(meta_path.read_text(encoding="utf-8"))
        assert original_payload["version"] == 2
        assert "variant_inherit" in original_payload["definitions"]["base"]


def test_migrate_v2_to_v3_write_mode_updates_file_and_creates_backup():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = root / "resources"
        resources.mkdir(parents=True, exist_ok=True)
        _, meta_path = write_png_with_meta(
            resources,
            "ui/button.png",
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant_inherit": False,
                        "props": {},
                    }
                },
            },
        )

        code, _, stderr = _run_script([
            "--root",
            resources.as_posix(),
            "--variants",
            "en,jp",
            "--write",
            "--backup",
            ".bak",
        ])
        assert code == 0
        assert stderr == ""

        migrated = json.loads(meta_path.read_text(encoding="utf-8"))
        assert migrated["version"] == 3
        base = migrated["definitions"]["base"]
        assert "variant_inherit" not in base
        assert base["variant_policy"] == {"en": "require", "jp": "require"}

        backup = Path(meta_path.as_posix() + ".bak")
        assert backup.exists()
        backup_payload = json.loads(backup.read_text(encoding="utf-8"))
        assert backup_payload["version"] == 2
