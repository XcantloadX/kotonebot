import json
import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.web.server.rest_api import create_rest_router, UpdateIndexRequest


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
