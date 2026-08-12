import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kotonebot.devtools.diagnostics.codes import META_VARIANT_INVALID
from kotonebot.devtools.diagnostics.models import Diagnostic
from kotonebot.devtools.errors import CommandError
from kotonebot.devtools.resgen import StandardGenerator
from kotonebot.devtools.resgen.parsers import ResgenProjectContext
from kotonebot.devtools.resgen.runner import generate_resources
from tests.devtools._testkit import write_min_png, write_png_with_meta, write_pyproject


class TestResgenRunner(unittest.TestCase):
    def test_generate_resources_basic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            resources = tmp_path / "resources"
            resources.mkdir()
            write_min_png(resources / "ui" / "button.png")
            pyproject = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path=resources.as_posix(),
            )

            output_img_dir = tmp_path / "out_img"
            output_code_file = tmp_path / "out_code" / "R.py"
            result = generate_resources(
                output_code_file=output_code_file.as_posix(),
                output_img_dir=output_img_dir.as_posix(),
                conf_path=pyproject.as_posix(),
                generator_factory=lambda _: StandardGenerator(production=True),
                show_progress=False,
            )

            self.assertEqual(Path(result.root_scan_path).as_posix(), resources.as_posix())
            self.assertEqual(result.parsed_file_count, 1)
            self.assertGreaterEqual(result.resource_count, 1)
            self.assertEqual(result.variant_names, None)
            self.assertTrue(output_code_file.exists())
            self.assertTrue((output_img_dir / "__init__.py").exists())

    def test_generate_resources_aborts_when_meta_has_error_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            resources = tmp_path / "resources"
            resources.mkdir()
            write_png_with_meta(
                resources,
                "ui/button.png",
                {
                    "version": 3,
                    "definitions": {
                        "base": {
                            "type": "prefab",
                            "name": "ui.button",
                            "prefab_id": "TemplateMatchPrefab",
                            "variant_policy": {
                                "en": "require",
                            },
                            "props": {
                                "templateImage": {"kind": "image", "x1": 0, "y1": 0, "x2": 1, "y2": 1},
                            },
                        },
                    },
                },
            )
            pyproject = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path=resources.as_posix(),
                variant_variants=["en"],
                variant_base="base",
                variant_path_pattern="nest",
            )

            output_img_dir = tmp_path / "out_img"
            output_code_file = tmp_path / "out_code" / "R.py"
            with self.assertRaisesRegex(CommandError, "resgen aborted due to 1 error\\(s\\)"):
                generate_resources(
                    output_code_file=output_code_file.as_posix(),
                    output_img_dir=output_img_dir.as_posix(),
                    conf_path=pyproject.as_posix(),
                    generator_factory=lambda _: StandardGenerator(production=True),
                    show_progress=False,
                    show_diagnostics=False,
                )

    def test_generate_resources_continues_when_meta_has_error_diagnostics_and_ignore_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            resources = tmp_path / "resources_empty"
            resources.mkdir()

            output_img_dir = tmp_path / "out_img"
            output_code_file = tmp_path / "out_code" / "R.py"
            runtime_context = ResgenProjectContext(
                parser_context={
                    "output_img_dir": output_img_dir.as_posix(),
                    "root_scan_path": resources.as_posix(),
                },
                default_variant="",
                diagnostics=[
                    Diagnostic(
                        code=META_VARIANT_INVALID.code,
                        severity="error",
                        message="synthetic error",
                        meta_path=(resources / "dummy.png.json").as_posix(),
                        line=1,
                        column=1,
                        end_line=1,
                        end_column=2,
                    ),
                ],
            )
            with patch("kotonebot.devtools.resgen.runner.load_resgen_runtime_context", return_value=runtime_context):
                result = generate_resources(
                    output_code_file=output_code_file.as_posix(),
                    output_img_dir=output_img_dir.as_posix(),
                    conf_path=(tmp_path / "pyproject.toml").as_posix(),
                    generator_factory=lambda _: StandardGenerator(production=True),
                    show_progress=False,
                    show_diagnostics=False,
                    ignore_error=True,
                )

            self.assertEqual(Path(result.root_scan_path).as_posix(), resources.as_posix())
            self.assertEqual(result.parsed_file_count, 0)
            self.assertEqual(result.resource_count, 0)
            self.assertTrue(output_code_file.exists())
            self.assertTrue((output_img_dir / "__init__.py").exists())


if __name__ == "__main__":
    unittest.main()
