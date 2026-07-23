from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.commands.commands import SERVER_COMMAND_META_REFETCH, SERVER_COMMAND_META_UPDATE_FILE
from kotonebot.devtools.commands.types import parse_server_command_request
from kotonebot.devtools.errors import CommandError
from kotonebot.devtools.path_utils import to_rel
from kotonebot.devtools.services.workspace_service import WorkspaceService
from kotonebot.devtools.services.context import DevtoolsContext
from kotonebot.devtools.commands.dispatch import CommandDispatcher
from kotonebot.devtools.project.project import Project
from tests.devtools._testkit import in_cwd, write_json, write_min_png, write_pyproject


def _create_service(tmp_path: Path) -> tuple[WorkspaceService, Path, DevtoolsContext]:
    resources = tmp_path / "resources"
    resources.mkdir()
    pyproject_path = write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
    with in_cwd(tmp_path):
        project = Project(conf_path=str(pyproject_path))
    ctx = DevtoolsContext(project)
    return ctx.workspace, resources, ctx


def test_workspace_service_meta_refetch_and_update():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        service, resources, ctx = _create_service(tmp_path)
        image_path = write_min_png(resources / "button.png")
        meta_path = Path(str(image_path) + ".json")
        write_json(
            meta_path,
            {
                "version": 3,
                "definitions": {
                    "ok": {
                        "type": "template",
                        "name": "ui.button",
                        "props": {"tap": {"kind": "rect", "x1": 1, "y1": 2, "x2": 3, "y2": 4}},
                    }
                },
            },
        )

        refetch_result = service.get_meta_index()
        assert refetch_result is not None
        diagnostics_result = service.get_meta_diagnostics()
        assert diagnostics_result is not None

        update_result = service.update_meta_index(meta_path=meta_path.as_posix())
        assert update_result.updatedMetaPath == to_rel(meta_path.resolve(), service.project.pyproject_root)



def test_workspace_service_lists_server_commands():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        service, _, _ = _create_service(tmp_path)
        commands = service.list_server_commands()
        assert any(item.id == SERVER_COMMAND_META_REFETCH for item in commands)
        assert any(item.id == SERVER_COMMAND_META_UPDATE_FILE for item in commands)


def test_workspace_service_server_command_args_validation():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        _, _, _ = _create_service(tmp_path)
        try:
            parse_server_command_request({"command": SERVER_COMMAND_META_UPDATE_FILE, "args": {}})
        except CommandError as exc:
            assert "metaPath" in str(exc)
        else:
            raise AssertionError("expected CommandError")
