import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project
from tests.devtools._testkit import in_cwd, write_pyproject


class TestProject(unittest.TestCase):
    def test_load_with_existing_resource_path(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(tmp_path / "pyproject.toml", resource_path="resources")
            with in_cwd(tmp_path):
                project = Project(conf_path=str(conf_path))

            self.assertEqual(project.conf.editor.resource_path, str(resource_dir.absolute()))

    def test_load_with_missing_resource_path_raises(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing_path = tmp_path / "missing-resources"
            conf_path = write_pyproject(tmp_path / "pyproject.toml", resource_path="missing-resources")
            with in_cwd(tmp_path):
                with self.assertRaises(FileNotFoundError) as context:
                    Project(conf_path=str(conf_path))

            message = str(context.exception)
            self.assertIn(str(missing_path.absolute()), message)
            self.assertIn("[tool.kotonebot.editor.resource_path]", message)

    def test_load_with_variant_variants(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en", "jp"],
                variant_base="base",
            )
            with in_cwd(tmp_path):
                project = Project(conf_path=str(conf_path))

            if project.conf.variant is None:
                raise AssertionError("variant config must exist")
            self.assertEqual(project.conf.variant.variants, ["en", "jp"])

    def test_load_with_duplicate_variant_variants_raises(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en", "en"],
                variant_base="base",
            )
            with in_cwd(tmp_path):
                with self.assertRaises(ValueError):
                    Project(conf_path=str(conf_path))

    def test_load_with_variant_path_nest(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en"],
                variant_base="base",
                variant_path_pattern="nest",
            )
            with in_cwd(tmp_path):
                project = Project(conf_path=str(conf_path))

            if project.conf.variant is None:
                raise AssertionError("variant config must exist")
            self.assertEqual(project.conf.variant.path_pattern, "nest")

    def test_load_with_variant_path_flat(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en"],
                variant_base="base",
                variant_path_pattern="flat",
            )
            with in_cwd(tmp_path):
                project = Project(conf_path=str(conf_path))

            if project.conf.variant is None:
                raise AssertionError("variant config must exist")
            self.assertEqual(project.conf.variant.path_pattern, "flat")

    def test_load_with_variant_path_template(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en"],
                variant_base="base",
                variant_path_pattern="pattern: {file_dir}/{variant_name}/{file_name_ext}",
            )
            with in_cwd(tmp_path):
                project = Project(conf_path=str(conf_path))

            if project.conf.variant is None:
                raise AssertionError("variant config must exist")
            self.assertEqual(project.conf.variant.path_pattern, "pattern: {file_dir}/{variant_name}/{file_name_ext}")

    def test_load_with_empty_variant_path_raises(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en"],
                variant_base="base",
                variant_path_pattern="   ",
            )
            with in_cwd(tmp_path):
                with self.assertRaises(ValueError):
                    Project(conf_path=str(conf_path))

    def test_load_with_invalid_variant_path_raises(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["en"],
                variant_base="base",
                variant_path_pattern="{file_dir}/{variant_name}/{file_name_ext}",
            )
            with in_cwd(tmp_path):
                with self.assertRaises(ValueError):
                    Project(conf_path=str(conf_path))

    def test_load_with_variant_base(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["jp", "tw"],
                variant_base="base",
            )
            with in_cwd(tmp_path):
                project = Project(conf_path=str(conf_path))

            if project.conf.variant is None:
                raise AssertionError("variant config must exist")
            self.assertEqual(project.conf.variant.base, "base")

    def test_load_with_variant_base_in_variants_raises(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path="resources",
                variant_variants=["jp", "tw"],
                variant_base="jp",
            )
            with in_cwd(tmp_path):
                with self.assertRaises(ValueError):
                    Project(conf_path=str(conf_path))
