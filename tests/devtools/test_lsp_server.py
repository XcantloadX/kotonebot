from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.server_commands.commands import SERVER_COMMAND_META_REFETCH
from kotonebot.devtools.server_commands.types import parse_server_command_request
from kotonebot.devtools.lsp.server import (
    _first_argument_dict,
    DevtoolsLspServer,
)
from tests.devtools._testkit import in_cwd, write_png_with_meta, write_pyproject


def _server(tmp_path: Path) -> DevtoolsLspServer:
    resources = tmp_path / "resources"
    resources.mkdir()
    write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
    with in_cwd(tmp_path):
        return DevtoolsLspServer(workspace=tmp_path.as_posix())


def test_first_argument_dict_accepts_empty():
    assert _first_argument_dict(tuple()) == {}


def test_first_argument_dict_rejects_multiple():
    try:
        _first_argument_dict(({}, {}))
    except ValueError as exc:
        assert "at most one object" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_first_argument_dict_requires_object():
    try:
        _first_argument_dict(("x",))
    except ValueError as exc:
        assert "must be object" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_server_execute_server_command_smoke():
    with TemporaryDirectory() as tmp:
        server = _server(Path(tmp))
        result = server.execute_server_command(SERVER_COMMAND_META_REFETCH, tuple())
        assert "index" in result
        assert "diagnostics" in result


def test_parse_server_command_request_requires_command():
    try:
        parse_server_command_request({"args": {}})
    except ValueError as exc:
        assert "command" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_server_symbol_tree_groups_name_and_variant():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
        write_png_with_meta(
            tmp_path / "resources",
            "base.png",
            {
                "version": 2,
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
            server = DevtoolsLspServer(workspace=tmp_path.as_posix())
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

