import json
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.web.server.rest_api import CloneVariantToImageRequest, UpdateIndexRequest, create_rest_router


def _build_router(pyproject_path: Path):
    cwd = Path.cwd()
    try:
        os.chdir(pyproject_path.parent)
        project = Project(conf_path=str(pyproject_path))
        return create_rest_router(project)
    finally:
        os.chdir(cwd)


def _route_endpoint(router, path: str, method: str):
    for route in router.routes:
        if route.path == path and method in route.methods:
            return route.endpoint
    raise AssertionError(f"Route not found: {method} {path}")


def _json_body(response):
    return json.loads(response.body.decode("utf-8"))


def _norm_path(path: str) -> str:
    return Path(path).resolve().as_posix().lower()


def test_meta_index_snapshot_and_diagnostics():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources = tmp_path / "resources"
        resources.mkdir()

        meta_path = resources / "button.png.json"
        meta_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "definitions": {
                        "ok": {
                            "type": "template",
                            "name": "ui.home.button",
                            "displayName": "Home Button",
                            "props": {
                                "tap": {"kind": "rect", "x1": 1, "y1": 2, "x2": 3, "y2": 4}
                            },
                        },
                        "bad": {
                            "type": "template",
                            "name": "broken",
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            '[tool.kotonebot.editor]\nresource_path = "resources"\n',
            encoding="utf-8",
        )

        router = _build_router(pyproject_path)
        get_meta_index = _route_endpoint(router, "/api/meta/index", "GET")
        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")

        payload = _json_body(asyncio.run(get_meta_index()))

        assert payload["success"] is True
        assert payload["data"]["stats"]["fileCount"] == 1
        assert payload["data"]["stats"]["symbolCount"] == 1
        assert payload["data"]["stats"]["diagnosticCount"] == 1
        assert payload["data"]["symbols"][0]["definitionId"] == "ok"

        diag_payload = _json_body(asyncio.run(get_meta_diagnostics()))
        assert diag_payload["success"] is True
        diagnostics_by_file = diag_payload["data"]["diagnosticsByFile"]
        diag_key_map = {_norm_path(k): k for k in diagnostics_by_file.keys()}
        resolved_meta = _norm_path(meta_path.as_posix())
        assert resolved_meta in diag_key_map
        assert diagnostics_by_file[diag_key_map[resolved_meta]][0]["code"] == "INDEX_DEF_PARSE_ERROR"


def test_meta_index_incremental_update():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources = tmp_path / "resources"
        resources.mkdir()

        meta_path = resources / "button.png.json"
        meta_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "definitions": {
                        "before": {
                            "type": "template",
                            "name": "before",
                            "props": {"box": {"kind": "rect", "x1": 1, "y1": 2, "x2": 3, "y2": 4}},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            '[tool.kotonebot.editor]\nresource_path = "resources"\n',
            encoding="utf-8",
        )
        router = _build_router(pyproject_path)
        get_meta_index = _route_endpoint(router, "/api/meta/index", "GET")
        update_meta_index = _route_endpoint(router, "/api/meta/index/update", "POST")

        first = _json_body(asyncio.run(get_meta_index()))
        assert first["success"] is True
        assert first["data"]["stats"]["symbolCount"] == 1

        meta_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "definitions": {
                        "after": {
                            "type": "template",
                            "name": "after",
                            "props": {"pt": {"kind": "point", "x": 10, "y": 20}},
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

        update_payload = _json_body(
            asyncio.run(
                update_meta_index(
                    body=UpdateIndexRequest(metaPath=meta_path.as_posix())
                )
            )
        )
        assert update_payload["success"] is True
        assert _norm_path(update_payload["data"]["updatedMetaPath"]) == _norm_path(meta_path.as_posix())
        removed = update_payload["data"]["removedSymbolKeys"]
        assert len(removed) == 1
        assert removed[0].endswith("::before")
        assert update_payload["data"]["upsertedSymbols"][0]["definitionId"] == "after"


def test_meta_index_symbol_contains_variant():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources = tmp_path / "resources"
        resources.mkdir()

        meta_path = resources / "button.png.json"
        meta_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "definitions": {
                        "base": {
                            "type": "prefab",
                            "name": "ui.button",
                            "props": {},
                        },
                        "en": {
                            "type": "prefab",
                            "name": "ui.button",
                            "variant": "en",
                            "props": {},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            '[tool.kotonebot]\nresource_variants=["en"]\n[tool.kotonebot.editor]\nresource_path = "resources"\n',
            encoding="utf-8",
        )
        router = _build_router(pyproject_path)
        get_meta_index = _route_endpoint(router, "/api/meta/index", "GET")

        payload = _json_body(asyncio.run(get_meta_index()))
        symbols = payload["data"]["symbols"]
        by_def = {s["definitionId"]: s for s in symbols}
        assert by_def["base"]["variant"] is None
        assert by_def["en"]["variant"] == "en"


def test_meta_index_variant_missing_base_diagnostic():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources = tmp_path / "resources"
        resources.mkdir()

        meta_path = resources / "button.png.json"
        meta_path.write_text(
            json.dumps(
                {
                    "version": 2,
                    "definitions": {
                        "en": {
                            "type": "prefab",
                            "name": "ui.button",
                            "variant": "en",
                            "props": {},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            '[tool.kotonebot]\nresource_variants=["en"]\n[tool.kotonebot.editor]\nresource_path = "resources"\n',
            encoding="utf-8",
        )
        router = _build_router(pyproject_path)
        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")
        payload = _json_body(asyncio.run(get_meta_diagnostics()))
        diagnostics = payload["data"]["diagnosticsByFile"]
        all_codes = [item["code"] for entries in diagnostics.values() for item in entries]
        assert "INDEX_VARIANT_INVALID" in all_codes


def test_meta_variant_clone_to_image():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources = tmp_path / "resources"
        resources.mkdir()

        source_image = resources / "source.png"
        source_image.write_bytes(b"\x89PNG\r\n\x1a\n")
        target_image = resources / "target.png"
        target_image.write_bytes(b"\x89PNG\r\n\x1a\n")

        source_meta = resources / "source.png.json"
        source_meta.write_text(
            json.dumps(
                {
                    "version": 2,
                    "definitions": {
                        "base": {
                            "type": "prefab",
                            "name": "ui.button",
                            "displayName": "Button",
                            "props": {
                                "threshold": 0.8,
                                "enabled": True,
                            },
                        },
                        "tpl": {
                            "type": "template",
                            "name": "ui.template",
                            "props": {},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        pyproject_path = tmp_path / "pyproject.toml"
        pyproject_path.write_text(
            '[tool.kotonebot]\nresource_variants=["en","jp"]\n[tool.kotonebot.editor]\nresource_path = "resources"\n',
            encoding="utf-8",
        )
        router = _build_router(pyproject_path)
        clone_api = _route_endpoint(router, "/api/meta/variant/clone_to_image", "POST")

        payload = _json_body(
            asyncio.run(
                clone_api(
                    body=CloneVariantToImageRequest(
                        sourceMetaPath=source_meta.as_posix(),
                        targetImagePath=target_image.as_posix(),
                        variant="en",
                        forceOverwrite=False,
                    )
                )
            )
        )
        assert payload["success"] is True
        target_meta = Path(target_image.as_posix() + ".json")
        data = json.loads(target_meta.read_text(encoding="utf-8"))
        assert data["definitions"]["tpl"]["type"] == "template"
        assert data["definitions"]["base"]["variant"] == "en"
        assert data["definitions"]["base"]["props"] == {}
