from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project
from kotonebot.devtools.services.context import DevtoolsContext
from tests.devtools._testkit import build_test_app, in_cwd, write_json, write_min_png, write_pyproject


def _prepare_project(
    tmp_path: Path,
    *,
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
    with in_cwd(pyproject_path.parent):
        project = Project(conf_path=str(pyproject_path))
    ctx = DevtoolsContext(project)
    client = build_test_app(ctx)
    return resources, client


def _norm_path(path: str) -> str:
    return Path(path).resolve().as_posix().lower()


def _write_png_with_meta(path: Path) -> None:
    write_min_png(path)
    write_json(Path(path.as_posix() + ".json"), {"version": 3, "definitions": {}})


def test_rename_document_precheck_nest_includes_related_variants():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, client = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="jp",
            variant_path_pattern="nest",
        )
        _write_png_with_meta(resources / "jp" / "story" / "screen_a.png")
        _write_png_with_meta(resources / "en" / "story" / "screen_a.png")

        payload = client.post(
            "/api/fs/rename_document/precheck",
            json={
                "sourceImagePath": (resources / "jp" / "story" / "screen_a.png").as_posix(),
                "targetImagePath": (resources / "jp" / "story" / "screen_b.png").as_posix(),
            },
        ).json()
        assert payload["success"] is True
        assert payload["data"]["hasConflicts"] is False
        docs = payload["data"]["documents"]
        assert len(docs) == 2
        variants = sorted(item["variant"] for item in docs)
        assert variants == ["base", "en"]


def test_rename_document_execute_moves_image_and_meta_for_group():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, client = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="jp",
            variant_path_pattern="nest",
        )
        base_source = resources / "jp" / "story" / "screen_a.png"
        variant_source = resources / "en" / "story" / "screen_a.png"
        _write_png_with_meta(base_source)
        _write_png_with_meta(variant_source)

        payload = client.post(
            "/api/fs/rename_document/execute",
            json={
                "sourceImagePath": base_source.as_posix(),
                "targetImagePath": (resources / "jp" / "story" / "screen_b.png").as_posix(),
            },
        ).json()
        assert payload["success"] is True
        assert payload["data"]["renamedDocumentCount"] == 2

        base_target = resources / "jp" / "story" / "screen_b.png"
        variant_target = resources / "en" / "story" / "screen_b.png"
        assert not base_source.exists()
        assert not Path(base_source.as_posix() + ".json").exists()
        assert not variant_source.exists()
        assert not Path(variant_source.as_posix() + ".json").exists()
        assert base_target.exists()
        assert Path(base_target.as_posix() + ".json").exists()
        assert variant_target.exists()
        assert Path(variant_target.as_posix() + ".json").exists()


def test_rename_document_precheck_reports_target_conflict():
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        resources, client = _prepare_project(
            tmp_path,
            variant_variants=["en"],
            variant_base="jp",
            variant_path_pattern="nest",
        )
        _write_png_with_meta(resources / "jp" / "story" / "screen_a.png")
        _write_png_with_meta(resources / "en" / "story" / "screen_a.png")
        _write_png_with_meta(resources / "jp" / "story" / "screen_b.png")

        payload = client.post(
            "/api/fs/rename_document/precheck",
            json={
                "sourceImagePath": (resources / "jp" / "story" / "screen_a.png").as_posix(),
                "targetImagePath": (resources / "jp" / "story" / "screen_b.png").as_posix(),
            },
        ).json()
        assert payload["success"] is True
        assert payload["data"]["hasConflicts"] is True
        conflicts = payload["data"]["conflicts"]
        assert any("Target path already exists" in item for item in conflicts)
