import asyncio
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.diagnostics.codes import (
    INDEX_DEF_PARSE_ERROR,
    INDEX_VARIANT_INHERIT_DISABLED,
    INDEX_VARIANT_INVALID,
)
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.web.server.rest_api import (
    CloneVariantToImageRequest,
    PreviewVariantImportPathRequest,
    UpdateIndexRequest,
    create_rest_router,
)
from starlette.datastructures import UploadFile
from tests.devtools._testkit import in_cwd, write_json, write_min_png, write_pyproject


def _build_router(pyproject_path: Path):
    with in_cwd(pyproject_path.parent):
        project = Project(conf_path=str(pyproject_path))
    return create_rest_router(project)


def _prepare_project(
    tmp_path: Path,
    variant_variants: list[str] | None = None,
    variant_base: str | None = None,
    variant_path_pattern: str | None = None,
):
    resources = tmp_path / "resources"
    resources.mkdir()
    pyproject_path = write_pyproject(
        tmp_path / "pyproject.toml",
        resource_path="resources",
        variant_variants=variant_variants,
        variant_base=variant_base,
        variant_path_pattern=variant_path_pattern,
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


def test_meta_index_snapshot_and_diagnostics():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path)
        meta_path = resources / "button.png.json"
        write_json(
            meta_path,
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
            },
        )

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
        assert diagnostics_by_file[diag_key_map[resolved_meta]][0]["code"] == INDEX_DEF_PARSE_ERROR.code


def test_meta_index_incremental_update():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path)
        meta_path = resources / "button.png.json"
        write_json(
            meta_path,
            {
                "version": 2,
                "definitions": {
                    "before": {
                        "type": "template",
                        "name": "before",
                        "props": {"box": {"kind": "rect", "x1": 1, "y1": 2, "x2": 3, "y2": 4}},
                    }
                },
            },
        )

        get_meta_index = _route_endpoint(router, "/api/meta/index", "GET")
        update_meta_index = _route_endpoint(router, "/api/meta/index/update", "POST")

        first = _json_body(asyncio.run(get_meta_index()))
        assert first["success"] is True
        assert first["data"]["stats"]["symbolCount"] == 1

        write_json(
            meta_path,
            {
                "version": 2,
                "definitions": {
                    "after": {
                        "type": "template",
                        "name": "after",
                        "props": {"pt": {"kind": "point", "x": 10, "y": 20}},
                    }
                },
            },
        )

        update_payload = _json_body(
            asyncio.run(update_meta_index(body=UpdateIndexRequest(metaPath=meta_path.as_posix())))
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
        resources, router = _prepare_project(tmp_path, variant_variants=["en"], variant_base="base")
        meta_path = resources / "button.png.json"
        write_json(
            meta_path,
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
            },
        )

        get_meta_index = _route_endpoint(router, "/api/meta/index", "GET")
        payload = _json_body(asyncio.run(get_meta_index()))
        symbols = payload["data"]["symbols"]
        by_def = {s["definitionId"]: s for s in symbols}
        assert by_def["base"]["variant"] is None
        assert by_def["en"]["variant"] == "en"


def test_meta_index_variant_missing_base_diagnostic():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path, variant_variants=["en"], variant_base="base")
        meta_path = resources / "button.png.json"
        write_json(
            meta_path,
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
            },
        )

        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")
        payload = _json_body(asyncio.run(get_meta_diagnostics()))
        diagnostics = payload["data"]["diagnosticsByFile"]
        all_codes = [item["code"] for entries in diagnostics.values() for item in entries]
        assert INDEX_VARIANT_INVALID.code in all_codes


def test_meta_index_variant_inherit_warning_when_variant_configured():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path, variant_variants=["en"], variant_base="base")
        meta_path = resources / "button.png.json"
        write_json(
            meta_path,
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    },
                },
            },
        )

        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")
        payload = _json_body(asyncio.run(get_meta_diagnostics()))
        diagnostics_by_file = payload["data"]["diagnosticsByFile"]
        diag_key_map = {_norm_path(k): k for k in diagnostics_by_file.keys()}
        resolved_meta = _norm_path(meta_path.as_posix())
        assert resolved_meta in diag_key_map
        entries = diagnostics_by_file[diag_key_map[resolved_meta]]
        warning = next((item for item in entries if item["code"] == INDEX_VARIANT_INHERIT_DISABLED.code), None)
        assert warning is not None
        assert warning["severity"] == "warning"


def test_meta_index_variant_inherit_no_warning_when_enabled_or_variant_not_configured():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path, variant_variants=["en"], variant_base="base")
        enabled_meta = resources / "enabled.png.json"
        write_json(
            enabled_meta,
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button.enabled",
                        "variant_inherit": True,
                        "props": {},
                    },
                },
            },
        )
        plain_meta = resources / "plain.png.json"
        write_json(
            plain_meta,
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button.plain",
                        "props": {},
                    },
                },
            },
        )

        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")
        configured_payload = _json_body(asyncio.run(get_meta_diagnostics()))
        configured_entries = [
            item
            for entries in configured_payload["data"]["diagnosticsByFile"].values()
            for item in entries
            if item["code"] == INDEX_VARIANT_INHERIT_DISABLED.code
        ]
        assert len(configured_entries) == 1

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path, variant_variants=["en"], variant_base="base")
        explicit_false_meta = resources / "explicit_false.png.json"
        write_json(
            explicit_false_meta,
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button.false",
                        "variant_inherit": False,
                        "props": {},
                    },
                },
            },
        )

        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")
        payload = _json_body(asyncio.run(get_meta_diagnostics()))
        entries = [
            item
            for file_entries in payload["data"]["diagnosticsByFile"].values()
            for item in file_entries
        ]
        assert all(item["code"] != INDEX_VARIANT_INHERIT_DISABLED.code for item in entries)

    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path)
        meta_path = resources / "button.png.json"
        write_json(
            meta_path,
            {
                "version": 2,
                "definitions": {
                    "base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {},
                    },
                },
            },
        )

        get_meta_diagnostics = _route_endpoint(router, "/api/meta/diagnostics", "GET")
        payload = _json_body(asyncio.run(get_meta_diagnostics()))
        entries = [
            item
            for file_entries in payload["data"]["diagnosticsByFile"].values()
            for item in file_entries
        ]
        assert all(item["code"] != INDEX_VARIANT_INHERIT_DISABLED.code for item in entries)


def test_meta_variant_clone_to_image():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path, variant_variants=["en", "jp"], variant_base="base")

        source_image = write_min_png(resources / "source.png")
        target_image = write_min_png(resources / "target.png")

        source_meta = resources / "source.png.json"
        write_json(
            source_meta,
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
            },
        )

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
        assert "tpl" not in data["definitions"]
        assert data["definitions"]["base"]["variant"] == "en"
        assert data["definitions"]["base"]["props"] == {}


def test_meta_variant_import_preview_path():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="base",
            variant_path_pattern="nest",
        )
        base_image = write_min_png(resources / "ui" / "home" / "button.png")
        preview_api = _route_endpoint(router, "/api/meta/variant/import/preview_path", "POST")
        payload = _json_body(
            asyncio.run(
                preview_api(
                    body=PreviewVariantImportPathRequest(
                        baseImagePath=base_image.as_posix(),
                        variant="en",
                    )
                )
            )
        )
        assert payload["success"] is True
        expected_target = resources / "en" / "ui" / "home" / "button.png"
        assert _norm_path(payload["data"]["targetImagePath"]) == _norm_path(expected_target.as_posix())


def test_meta_variant_import_image_writes_target_file():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="base",
            variant_path_pattern="flat",
        )
        base_image = write_min_png(resources / "ui" / "home" / "button.png")
        import_api = _route_endpoint(router, "/api/meta/variant/import_image", "POST")
        image_payload = b"\x89PNG\r\n\x1a\nimported"
        upload = UploadFile(filename="clipboard.png", file=io.BytesIO(image_payload))
        payload = _json_body(
            asyncio.run(
                import_api(
                    baseImagePath=base_image.as_posix(),
                    variant="en",
                    image=upload,
                )
            )
        )
        assert payload["success"] is True
        target_image_path = Path(payload["data"]["targetImagePath"])
        assert _norm_path(target_image_path.as_posix()) == _norm_path((resources / "ui" / "home" / "button_en.png").as_posix())
        assert target_image_path.read_bytes() == image_payload


def test_meta_variant_import_image_replaces_existing_target_when_requested():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="base",
            variant_path_pattern="flat",
        )
        base_image = write_min_png(resources / "ui" / "home" / "button.png")
        target_image_path = resources / "ui" / "home" / "button_en.png"
        write_min_png(target_image_path)
        target_meta_path = Path(target_image_path.as_posix() + ".json")
        write_json(target_meta_path, {"version": 2, "definitions": {"old": {"type": "template", "name": "old", "props": {}}}})

        import_api = _route_endpoint(router, "/api/meta/variant/import_image", "POST")

        first_upload = UploadFile(filename="clipboard.png", file=io.BytesIO(b"\x89PNG\r\n\x1a\nfirst"))
        first_payload = _json_body(
            asyncio.run(
                import_api(
                    baseImagePath=base_image.as_posix(),
                    variant="en",
                    image=first_upload,
                    deleteExistingTarget=False,
                )
            )
        )
        assert first_payload["success"] is False
        assert "Target image already exists" in first_payload["message"]

        second_image_payload = b"\x89PNG\r\n\x1a\nsecond"
        second_upload = UploadFile(filename="clipboard.png", file=io.BytesIO(second_image_payload))
        second_payload = _json_body(
            asyncio.run(
                import_api(
                    baseImagePath=base_image.as_posix(),
                    variant="en",
                    image=second_upload,
                    deleteExistingTarget=True,
                )
            )
        )
        assert second_payload["success"] is True
        assert target_image_path.read_bytes() == second_image_payload
        assert not target_meta_path.exists()


def test_meta_variant_import_preview_path_custom_pattern():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="base",
            variant_path_pattern="pattern: {file_dir}/{variant_name}/{file_name_ext}",
        )
        base_image = write_min_png(resources / "ui" / "home" / "button.png")
        preview_api = _route_endpoint(router, "/api/meta/variant/import/preview_path", "POST")
        payload = _json_body(
            asyncio.run(
                preview_api(
                    body=PreviewVariantImportPathRequest(
                        baseImagePath=base_image.as_posix(),
                        variant="en",
                    )
                )
            )
        )
        assert payload["success"] is True
        expected_target = resources / "ui" / "home" / "en" / "button.png"
        assert _norm_path(payload["data"]["targetImagePath"]) == _norm_path(expected_target.as_posix())


def test_meta_variant_import_preview_requires_variant_path():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(tmp_path, variant_variants=["en"], variant_base="base")
        base_image = write_min_png(resources / "button.png")
        preview_api = _route_endpoint(router, "/api/meta/variant/import/preview_path", "POST")
        payload = _json_body(
            asyncio.run(
                preview_api(
                    body=PreviewVariantImportPathRequest(
                        baseImagePath=base_image.as_posix(),
                        variant="en",
                    )
                )
            )
        )
        assert payload["success"] is False
        assert "variant.path_pattern" in payload["message"]


def test_meta_variant_import_preview_rejects_non_base_variant_prefixed_path():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, router = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="jp",
            variant_path_pattern="nest",
        )
        base_image = write_min_png(resources / "en" / "ui" / "home" / "button.png")
        preview_api = _route_endpoint(router, "/api/meta/variant/import/preview_path", "POST")
        payload = _json_body(
            asyncio.run(
                preview_api(
                    body=PreviewVariantImportPathRequest(
                        baseImagePath=base_image.as_posix(),
                        variant="en",
                    )
                )
            )
        )
        assert payload["success"] is False
        assert "must use variant.base prefix" in payload["message"]
