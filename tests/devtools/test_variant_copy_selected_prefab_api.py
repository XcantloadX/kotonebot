import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.web.server.rest_api import (
    CopySelectedPrefabToVariantRequest,
    PrecheckCopySelectedPrefabToVariantRequest,
    create_rest_router,
)
from tests.devtools._testkit import in_cwd, write_json, write_min_png, write_pyproject


def _build_router(pyproject_path: Path):
    with in_cwd(pyproject_path.parent):
        project = Project(conf_path=str(pyproject_path))
    return create_rest_router(project)


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
    return resources, _build_router(pyproject_path)


def _route_endpoint(router, path: str, method: str):
    for route in router.routes:
        if route.path == path and method in route.methods:
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


def _json_body(response):
    return json.loads(response.body.decode("utf-8"))


def _norm_path(path: str) -> str:
    return Path(path).resolve().as_posix().lower()


def test_copy_selected_prefab_to_variant_precheck_and_execute():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path)
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

        precheck_api = _route_endpoint(router, "/api/meta/variant/copy_selected_prefab/precheck", "POST")
        precheck_payload = _json_body(
            asyncio.run(
                precheck_api(
                    body=PrecheckCopySelectedPrefabToVariantRequest(
                        sourceMetaPath=source_meta.as_posix(),
                        sourceDefinitionId="btn",
                        baseImagePath=source_image.as_posix(),
                        variant="en",
                    )
                )
            )
        )
        assert precheck_payload["success"] is True
        assert _norm_path(precheck_payload["data"]["targetImagePath"]) == _norm_path(target_image.as_posix())
        assert precheck_payload["data"]["targetDefinitionExists"] is False

        copy_api = _route_endpoint(router, "/api/meta/variant/copy_selected_prefab", "POST")
        copy_payload = _json_body(
            asyncio.run(
                copy_api(
                    body=CopySelectedPrefabToVariantRequest(
                        sourceMetaPath=source_meta.as_posix(),
                        sourceDefinitionId="btn",
                        baseImagePath=source_image.as_posix(),
                        variant="en",
                        forceOverwrite=False,
                    )
                )
            )
        )
        assert copy_payload["success"] is True
        target_meta = Path(target_image.as_posix() + ".json")
        target_data = json.loads(target_meta.read_text(encoding="utf-8"))
        assert target_data["definitions"]["btn"]["variant"] == "en"
        assert target_data["definitions"]["btn"]["name"] == "ui.button"


def test_copy_selected_prefab_to_variant_requires_overwrite_flag():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path)
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

        copy_api = _route_endpoint(router, "/api/meta/variant/copy_selected_prefab", "POST")

        first_payload = _json_body(
            asyncio.run(
                copy_api(
                    body=CopySelectedPrefabToVariantRequest(
                        sourceMetaPath=source_meta.as_posix(),
                        sourceDefinitionId="btn",
                        baseImagePath=source_image.as_posix(),
                        variant="en",
                        forceOverwrite=False,
                    )
                )
            )
        )
        assert first_payload["success"] is False
        assert "Target definition already exists" in first_payload["message"]

        second_payload = _json_body(
            asyncio.run(
                copy_api(
                    body=CopySelectedPrefabToVariantRequest(
                        sourceMetaPath=source_meta.as_posix(),
                        sourceDefinitionId="btn",
                        baseImagePath=source_image.as_posix(),
                        variant="en",
                        forceOverwrite=True,
                    )
                )
            )
        )
        assert second_payload["success"] is True
        rewritten = json.loads(target_meta.read_text(encoding="utf-8"))
        assert rewritten["definitions"]["btn"]["props"] == {}
