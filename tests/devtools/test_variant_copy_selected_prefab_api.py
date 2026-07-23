import json
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.services.context import DevtoolsContext
from tests.devtools._testkit import build_test_app, in_cwd, write_json, write_min_png, write_pyproject


def _prepare_project(tmp_path: Path):
    resources = tmp_path / "resources"
    resources.mkdir()
    pyproject_path = write_pyproject(
        tmp_path / "pyproject.toml",
        resource_path="resources",
        variant_variants=["en"],
        variant_base="base",
        variant_path_pattern="nest",
    )
    with in_cwd(pyproject_path.parent):
        project = Project(conf_path=str(pyproject_path))
    ctx = DevtoolsContext(project)
    client = build_test_app(ctx)
    return resources, client


def _norm_path(path: str) -> str:
    return Path(path).resolve().as_posix().lower()


def test_copy_selected_prefab_to_variant_precheck_and_execute():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, client = _prepare_project(tmp_path)
        source_image = write_min_png(resources / "base" / "ui" / "button.png")
        target_image = write_min_png(resources / "en" / "ui" / "button.png")
        source_meta = Path(source_image.as_posix() + ".json")
        write_json(
            source_meta,
            {
                "version": 3,
                "definitions": {
                    "btn": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {
                            "template": {"kind": "image", "x1": 0, "y1": 0, "x2": 1, "y2": 1},
                            "threshold": 0.91,
                        },
                    },
                },
            },
        )

        precheck_payload = client.post(
            "/api/meta/variant/copy_selected_prefab/precheck",
            json={
                "sourceMetaPath": source_meta.as_posix(),
                "sourceDefinitionId": "btn",
                "baseImagePath": source_image.as_posix(),
                "variant": "en",
            },
        ).json()
        assert precheck_payload["success"] is True
        assert _norm_path(str(tmp_path / precheck_payload["data"]["targetImagePath"])) == _norm_path(target_image.as_posix())
        assert precheck_payload["data"]["targetDefinitionExists"] is False

        copy_payload = client.post(
            "/api/meta/variant/copy_selected_prefab",
            json={
                "sourceMetaPath": source_meta.as_posix(),
                "sourceDefinitionId": "btn",
                "baseImagePath": source_image.as_posix(),
                "variant": "en",
                "forceOverwrite": False,
            },
        ).json()
        assert copy_payload["success"] is True
        target_meta = Path(target_image.as_posix() + ".json")
        target_data = json.loads(target_meta.read_text(encoding="utf-8"))
        assert target_data["definitions"]["btn"]["variant"] == "en"
        assert target_data["definitions"]["btn"]["name"] == "ui.button"


def test_copy_selected_prefab_to_variant_requires_overwrite_flag():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, client = _prepare_project(tmp_path)
        source_image = write_min_png(resources / "base" / "ui" / "button.png")
        target_image = write_min_png(resources / "en" / "ui" / "button.png")
        source_meta = Path(source_image.as_posix() + ".json")
        target_meta = Path(target_image.as_posix() + ".json")
        write_json(
            source_meta,
            {
                "version": 3,
                "definitions": {
                    "btn": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    },
                },
            },
        )
        write_json(
            target_meta,
            {
                "version": 3,
                "definitions": {
                    "btn": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {"threshold": 0.5},
                    }
                },
            },
        )

        first_payload = client.post(
            "/api/meta/variant/copy_selected_prefab",
            json={
                "sourceMetaPath": source_meta.as_posix(),
                "sourceDefinitionId": "btn",
                "baseImagePath": source_image.as_posix(),
                "variant": "en",
                "forceOverwrite": False,
            },
        ).json()
        assert first_payload["success"] is False
        assert "Target definition already exists" in first_payload["message"]

        second_payload = client.post(
            "/api/meta/variant/copy_selected_prefab",
            json={
                "sourceMetaPath": source_meta.as_posix(),
                "sourceDefinitionId": "btn",
                "baseImagePath": source_image.as_posix(),
                "variant": "en",
                "forceOverwrite": True,
            },
        ).json()
        assert second_payload["success"] is True
        rewritten = json.loads(target_meta.read_text(encoding="utf-8"))
        assert rewritten["definitions"]["btn"]["props"] == {}
