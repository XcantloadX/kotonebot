from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.commands.commands import (
    SERVER_COMMAND_META_REFETCH,
    SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
    SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
)
from kotonebot.devtools.commands.types import parse_server_command_request
from kotonebot.devtools.transports.lsp.server import (
    _first_argument_dict,
    DevtoolsLspServer,
)
from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.project.project import Project
from tests.devtools._testkit import in_cwd, write_png_with_meta, write_pyproject
from kotonebot.devtools.errors import CommandError
from kotonebot.devtools.meta import parse_meta_file


def _server(tmp_path: Path) -> DevtoolsLspServer:
    resources = tmp_path / "resources"
    resources.mkdir(exist_ok=True)
    write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
    with in_cwd(tmp_path):
        project = Project(conf_path=str(tmp_path / "pyproject.toml"))
        ctx = DevtoolsContext(project)
    return DevtoolsLspServer(ctx)


def test_first_argument_dict_accepts_empty():
    assert _first_argument_dict(tuple()) == {}


def test_first_argument_dict_rejects_multiple():
    try:
        _first_argument_dict(({}, {}))
    except CommandError as exc:
        assert "at most one object" in str(exc)
    else:
        raise AssertionError("expected CommandError")


def test_first_argument_dict_requires_object():
    try:
        _first_argument_dict(("x",))
    except CommandError as exc:
        assert "must be object" in str(exc)
    else:
        raise AssertionError("expected CommandError")


def test_server_execute_server_command_smoke():
    with TemporaryDirectory() as tmp:
        server = _server(Path(tmp))
        result = server.execute_server_command(SERVER_COMMAND_META_REFETCH, tuple())
        assert "index" in result
        assert "diagnostics" in result


def test_parse_server_command_request_requires_command():
    try:
        parse_server_command_request({"args": {}})
    except CommandError as exc:
        assert "command" in str(exc)
    else:
        raise AssertionError("expected CommandError")


def test_server_symbol_tree_groups_name_and_variant():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
        write_png_with_meta(
            tmp_path / "resources",
            "base.png",
            {
                "version": 3,
                "definitions": {
                    "id1": {
                        "type": "prefab",
                        "name": "ui.button",
                        "displayName": "按钮",
                        "props": {"p": {"kind": "point", "x": 1, "y": 1}},
                    },
                    "id2": {"type": "prefab", "name": "ui.button", "variant": "jp", "props": {"p": {"kind": "point", "x": 1, "y": 1}}},
                },
            },
        )
        with in_cwd(tmp_path):
            server = _server(tmp_path)
            tree = server.get_symbol_tree()
            assert len(tree) == 1
            assert tree[0]["kind"] == "group"
            assert tree[0]["label"] == "ui"
            ui_children = tree[0]["children"]
            assert len(ui_children) == 1
            symbol_node = ui_children[0]
            assert symbol_node["kind"] == "symbol"
            assert symbol_node["fullName"] == "ui.button"
            assert symbol_node["displayName"] == "按钮"
            variants = symbol_node["children"]
            assert len(variants) == 2
            variant_labels = sorted([item["label"] for item in variants])
            assert variant_labels == ["base", "jp"]
            base_variant = next(item for item in variants if item["label"] == "base")
            base_file = base_variant["children"][0]
            assert base_file["metaPath"].endswith("base.png.json")
            assert base_file["imagePath"].endswith("base.png")
            assert base_file["definitionId"] == "id1"


def test_server_rename_symbol_precheck_collects_all_name_matches():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
        write_png_with_meta(
            tmp_path / "resources",
            "base.png",
            {
                "version": 3,
                "definitions": {
                    "id_base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {"p": {"kind": "point", "x": 1, "y": 1}},
                    },
                },
            },
        )
        write_png_with_meta(
            tmp_path / "resources",
            "en.png",
            {
                "version": 3,
                "definitions": {
                    "id_en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {"p": {"kind": "point", "x": 1, "y": 1}},
                    },
                },
            },
        )
        with in_cwd(tmp_path):
            server = _server(tmp_path)
            result = server.execute_server_command(
                SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
                (
                    {
                        "metaPath": (tmp_path / "resources" / "base.png.json").as_posix(),
                        "definitionId": "id_base",
                        "newName": "ui.button_new",
                    },
                ),
            )
            assert result["oldName"] == "ui.button"
            assert result["newName"] == "ui.button_new"
            assert result["affectedDefinitionCount"] == 2
            assert result["affectedMetaCount"] == 2


def test_server_rename_symbol_execute_updates_all_name_matches():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
        base_png, base_meta = write_png_with_meta(
            tmp_path / "resources",
            "base.png",
            {
                "version": 3,
                "definitions": {
                    "id_base": {
                        "type": "prefab",
                        "name": "ui.button",
                        "props": {"p": {"kind": "point", "x": 1, "y": 1}},
                    },
                },
            },
        )
        _, en_meta = write_png_with_meta(
            tmp_path / "resources",
            "en.png",
            {
                "version": 3,
                "definitions": {
                    "id_en": {
                        "type": "prefab",
                        "name": "ui.button",
                        "variant": "en",
                        "props": {"p": {"kind": "point", "x": 1, "y": 1}},
                    },
                },
            },
        )
        with in_cwd(tmp_path):
            server = _server(tmp_path)
            result = server.execute_server_command(
                SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
                (
                    {
                        "metaPath": base_meta.as_posix(),
                        "definitionId": "id_base",
                        "newName": "ui.button_new",
                    },
                ),
            )
            assert result["affectedDefinitionCount"] == 2
            assert result["updatedIndexVersion"] > 0
            base_data = parse_meta_file(base_meta)
            en_data = parse_meta_file(en_meta)
            assert base_data.definitions["id_base"].name == "ui.button_new"
            assert en_data.definitions["id_en"].name == "ui.button_new"
            tree = server.get_symbol_tree()
            assert tree[0]["label"] == "ui"
            symbol_node = tree[0]["children"][0]
            assert symbol_node["fullName"] == "ui.button_new"
            base_file = symbol_node["children"][0]["children"][0]
            assert base_file["imagePath"].endswith(base_png.name)
