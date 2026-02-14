import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from kotonebot.devtools.project.project import Project


class TestProject(unittest.TestCase):
    def test_load_with_existing_resource_path(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            resource_dir = tmp_path / "resources"
            resource_dir.mkdir()
            conf_path = tmp_path / "pyproject.toml"
            conf_path.write_text(
                """
[tool.kotonebot.editor]
resource_path = "resources"
""".strip(),
                encoding="utf-8",
            )

            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp_path)
                project = Project(conf_path=str(conf_path))
            finally:
                os.chdir(cwd)

            self.assertEqual(project.conf.editor.resource_path, str(resource_dir.absolute()))

    def test_load_with_missing_resource_path_raises(self):
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            missing_path = tmp_path / "missing-resources"
            conf_path = tmp_path / "pyproject.toml"
            conf_path.write_text(
                """
[tool.kotonebot.editor]
resource_path = "missing-resources"
""".strip(),
                encoding="utf-8",
            )

            cwd = Path.cwd()
            try:
                import os

                os.chdir(tmp_path)
                with self.assertRaises(FileNotFoundError) as context:
                    Project(conf_path=str(conf_path))
            finally:
                os.chdir(cwd)

            message = str(context.exception)
            self.assertIn(str(missing_path.absolute()), message)
            self.assertIn("[tool.kotonebot.editor.resource_path]", message)
