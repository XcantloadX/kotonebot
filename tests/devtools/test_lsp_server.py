from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.server_commands.commands import SERVER_COMMAND_META_REFETCH
from kotonebot.devtools.server_commands.types import parse_server_command_request
from kotonebot.devtools.lsp.server import _first_argument_dict, DevtoolsLspServer
from tests.devtools._testkit import in_cwd, write_pyproject


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
