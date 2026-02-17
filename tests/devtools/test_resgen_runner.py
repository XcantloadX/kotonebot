import tempfile
import unittest
from pathlib import Path

from kotonebot.devtools.resgen import StandardGenerator
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
                    "version": 2,
                    "definitions": {
                        "base": {
                            "type": "prefab",
                            "name": "ui.button",
                            "prefab_id": "TemplateMatchPrefab",
                            "variant_inherit": False,
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
            with self.assertRaisesRegex(ValueError, "resgen aborted due to 1 error\\(s\\)"):
                generate_resources(
                    output_code_file=output_code_file.as_posix(),
                    output_img_dir=output_img_dir.as_posix(),
                    conf_path=pyproject.as_posix(),
                    generator_factory=lambda _: StandardGenerator(production=True),
                    show_progress=False,
                    show_diagnostics=False,
                )


if __name__ == "__main__":
    unittest.main()
