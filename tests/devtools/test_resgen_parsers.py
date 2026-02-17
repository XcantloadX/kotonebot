"""Tests for kotonebot.devtools.resgen.parsers module"""

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kotonebot.devtools.resgen.parsers import (
    ParserRegistry,
    KotoneV1Parser,
    BasicSpriteParser,
    load_resgen_project_context,
    load_resgen_runtime_context,
)
from kotonebot.devtools.resgen.core import PrefabData, ResourceNode, ImageAsset
from tests.devtools._testkit import make_resgen_context, write_json, write_min_png, write_png_with_meta, write_pyproject


def _resgen_context(tmpdir: str, **overrides):
    context = make_resgen_context(Path(tmpdir), **overrides)
    if "resource_variants" in context and "_variant_base" not in context:
        context["_variant_base"] = "base"
    return context


class TestParserRegistry(unittest.TestCase):
    """Test ParserRegistry class"""

    def test_initialization(self):
        """Test ParserRegistry initialization"""
        registry = ParserRegistry()
        self.assertEqual(registry._parsers, [])

    def test_register_parser(self):
        """Test registering a parser"""
        registry = ParserRegistry()
        parser = KotoneV1Parser()
        
        registry.register(parser)
        self.assertEqual(len(registry._parsers), 1)
        self.assertTrue(registry._parsers[0] is parser)

    def test_register_multiple_parsers(self):
        """Test registering multiple parsers"""
        registry = ParserRegistry()
        parser1 = KotoneV1Parser()
        parser2 = BasicSpriteParser()
        
        registry.register(parser1)
        registry.register(parser2)
        
        self.assertEqual(len(registry._parsers), 2)

    def test_parse_file_with_matching_parser(self):
        """Test parse_file with a matching parser"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_png = write_min_png(Path(tmpdir) / "test.png")
            registry = ParserRegistry()
            parser = BasicSpriteParser()
            registry.register(parser)
            
            result = registry.parse_file(test_png.as_posix(), _resgen_context(tmpdir))
            
            self.assertTrue(isinstance(result, list))

    def test_parse_file_no_matching_parser(self):
        """Test parse_file with no matching parser"""
        registry = ParserRegistry()
        result = registry.parse_file("/path/to/unknown.xyz", {})
        
        self.assertEqual(result, [])

    def test_parse_file_priority_order(self):
        """Test that parsers are checked in registration order"""
        class MockParser1:
            def can_parse(self, file_path):
                return file_path.endswith(".test")
            
            def parse(self, file_path, context):
                return [ResourceNode(name="mock1", type="test", value="mock1")]
        
        class MockParser2:
            def can_parse(self, file_path):
                return file_path.endswith(".test")
            
            def parse(self, file_path, context):
                return [ResourceNode(name="mock2", type="test", value="mock2")]
        
        registry = ParserRegistry()
        registry.register(MockParser1())
        registry.register(MockParser2())
        
        result = registry.parse_file("test.test", {})
        
        # Should use first matching parser
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "mock1")


class TestKotoneV1Parser(unittest.TestCase):
    """Test KotoneV1Parser class"""

    def test_initialization(self):
        """Test KotoneV1Parser initialization"""
        parser = KotoneV1Parser()
        self.assertTrue(isinstance(parser, KotoneV1Parser))

    def test_can_parse_with_png_json_extension(self):
        """Test can_parse with .png.json extension"""
        parser = KotoneV1Parser()
        
        # Should return True for .png.json files with valid schema
        # But this needs actual file, so we test with real files
        self.assertFalse(parser.can_parse("test.txt"))

    def test_can_parse_with_non_json_file(self):
        """Test can_parse with non-JSON file"""
        parser = KotoneV1Parser()
        
        self.assertFalse(parser.can_parse("test.png"))
        self.assertFalse(parser.can_parse("test.txt"))

    def test_can_parse_with_invalid_json(self):
        """Test can_parse with invalid JSON file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "test.png.json")
            with open(json_file, 'w') as f:
                f.write("invalid json {")
            
            parser = KotoneV1Parser()
            self.assertFalse(parser.can_parse(json_file))

    def test_can_parse_with_missing_schema_keys(self):
        """Test can_parse with JSON missing required schema keys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test.png.json"
            write_json(json_file, {"some_key": "value"})
            
            parser = KotoneV1Parser()
            self.assertFalse(parser.can_parse(json_file.as_posix()))

    def test_can_parse_with_simple_meta_schema(self):
        """Test can_parse with new simple meta schema (isSimple + definition)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = Path(tmpdir) / "test.png.json"
            schema = {
                "isSimple": True,
                "definition": {
                    "name": "Ui.Button",
                    "type": "template",
                    "displayName": "按钮",
                    "description": "测试按钮",
                },
            }
            write_json(json_file, schema)

            parser = KotoneV1Parser()
            self.assertTrue(parser.can_parse(json_file.as_posix()))

    def test_parse_simple_template_definition(self):
        """Test parsing simple meta with single template definition (isSimple true)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema = {
                "isSimple": True,
                "definition": {
                    "name": "ui.button",
                    "type": "template",
                    "displayName": "Button",
                    "description": "Main button",
                },
            }
            _, json_file = write_png_with_meta(Path(tmpdir), "ui/button.png", schema)

            parser = KotoneV1Parser()
            result = parser.parse(json_file.as_posix(), _resgen_context(tmpdir))

            self.assertEqual(len(result), 1)
            node = result[0]
            self.assertEqual(node.type, "template")
            self.assertEqual(node.name, "button")
            self.assertIn("class_path", node.metadata)
            self.assertEqual(node.metadata["class_path"], ["Ui"])

    def test_parse_simple_template_definition_with_empty_name_and_display(self):
        """Simple meta: empty name/displayName should fall back to file-based defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            schema = {
                "isSimple": True,
                "definition": {
                    "name": "",  # empty name
                    "type": "template",
                    "displayName": "",  # empty displayName
                    "description": "Main button",
                },
            }
            _, json_file = write_png_with_meta(Path(tmpdir), "ui/button.png", schema)

            parser = KotoneV1Parser()
            result = parser.parse(json_file.as_posix(), _resgen_context(tmpdir))

            self.assertEqual(len(result), 1)
            node = result[0]
            # name should be derived from file name (CamelCase)
            self.assertEqual(node.name, "Button")
            # class_path should come from relative directory
            self.assertEqual(node.metadata.get("class_path"), ["Ui"])
            # display_name should fall back to original file name
            self.assertEqual(node.metadata.get("display_name"), "button.png")


class TestBasicSpriteParser(unittest.TestCase):
    """Test BasicSpriteParser class"""

    def test_initialization(self):
        """Test BasicSpriteParser initialization"""
        parser = BasicSpriteParser()
        self.assertTrue(isinstance(parser, BasicSpriteParser))

    def test_can_parse_png_file(self):
        """Test can_parse with PNG file without JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "test.png")
            
            parser = BasicSpriteParser()
            self.assertTrue(parser.can_parse(png_file.as_posix()))

    def test_can_parse_rejects_non_png(self):
        """Test can_parse rejects non-PNG files"""
        parser = BasicSpriteParser()
        
        self.assertFalse(parser.can_parse("test.txt"))
        self.assertFalse(parser.can_parse("test.jpg"))
        self.assertFalse(parser.can_parse("test.json"))

    def test_can_parse_rejects_png_with_json(self):
        """Test can_parse rejects PNG with corresponding JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "test.png")
            json_file = Path(png_file.as_posix() + ".json")
            write_json(json_file, {})
            
            parser = BasicSpriteParser()
            self.assertFalse(parser.can_parse(png_file.as_posix()))

    def test_parse_single_sprite(self):
        """Test parsing a single sprite"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "button.png")
            
            parser = BasicSpriteParser()
            result = parser.parse(png_file.as_posix(), _resgen_context(tmpdir))
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "template")
            # BasicSpriteParser converts to CamelCase
            self.assertEqual(result[0].name, "Button")

    def test_parse_sprite_with_path(self):
        """Test parsing sprite with directory path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "ui" / "buttons" / "submit_button.png")
            
            parser = BasicSpriteParser()
            result = parser.parse(png_file.as_posix(), _resgen_context(tmpdir))
            
            self.assertEqual(len(result), 1)
            # class_path should contain Ui and Buttons
            metadata = result[0].metadata
            self.assertIn("class_path", metadata)
            # Verify the class path is built correctly
            self.assertTrue(isinstance(metadata["class_path"], list))

    def test_parse_returns_resource_node(self):
        """Test that parse returns proper ResourceNode"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "test.png")
            
            parser = BasicSpriteParser()
            result = parser.parse(png_file.as_posix(), _resgen_context(tmpdir))
            
            self.assertEqual(len(result), 1)
            node = result[0]
            self.assertTrue(isinstance(node, ResourceNode))
            self.assertEqual(node.type, "template")
            self.assertTrue(isinstance(node.value, ImageAsset))
            # path 应该存在并指向输出目录
            self.assertTrue(os.path.exists(node.value.path))

    def test_parse_metadata_content(self):
        """Test that metadata is properly populated"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "sprite.png")
            
            parser = BasicSpriteParser()
            result = parser.parse(png_file.as_posix(), _resgen_context(tmpdir))
            
            metadata = result[0].metadata
            self.assertIn("class_path", metadata)
            self.assertIn("origin_file", metadata)
            self.assertIn("abs_path", metadata)
            self.assertIn("display_name", metadata)
            self.assertTrue(os.path.isabs(metadata["origin_file"]))
            self.assertTrue(os.path.isabs(metadata["abs_path"]))

    def test_parse_docstring_format(self):
        """Test that docstring has correct format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = write_min_png(Path(tmpdir) / "test.png")
            
            parser = BasicSpriteParser()
            result = parser.parse(png_file.as_posix(), _resgen_context(tmpdir))
            
            docstring = result[0].docstring
            self.assertIn("名称：", docstring)
            self.assertIn("模块：", docstring)

    def test_parse_multiple_files(self):
        """Test parsing multiple sprite files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = BasicSpriteParser()
            context = _resgen_context(tmpdir)
            
            files = ["sprite1.png", "sprite2.png", "sprite3.png"]
            for filename in files:
                write_min_png(Path(tmpdir) / filename)
            
            results = []
            for filename in files:
                png_file = Path(tmpdir) / filename
                result = parser.parse(png_file.as_posix(), context)
                results.extend(result)
            
            # Each file should produce one ResourceNode
            self.assertEqual(len(results), 3)
            names = {r.name for r in results}
            # BasicSpriteParser converts to CamelCase
            self.assertIn("Sprite1", names)
            self.assertIn("Sprite2", names)
            self.assertIn("Sprite3", names)


class TestKotoneV2Parser(unittest.TestCase):
    """Tests for KotoneV1Parser (V2 support) and Meta V2 slice naming."""

    def setUp(self) -> None:
        self.parser = KotoneV1Parser()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _create_meta_file(self, content: dict) -> str:
        _, json_path = write_png_with_meta(Path(self.tmp.name), "test.png", content)
        return json_path.as_posix()

    def test_v2_template_image_slice_naming(self):
        """ImageProp 应导出 <definitionId>_<propKey>.png 命名的切片。"""
        data = {
            "version": 2,
            "definitions": {
                "def1": {
                    "type": "template",
                    "name": "ui.button",
                    "displayName": "Button",
                    "description": "Main button",
                    "props": {
                        "templateImage": {
                            "kind": "image",
                            "x1": 1,
                            "y1": 2,
                            "x2": 10,
                            "y2": 20,
                        },
                        "threshold": 0.8,
                    },
                }
            },
        }

        json_path = self._create_meta_file(data)
        context = _resgen_context(self.tmp.name)

        expected_name = os.path.join(self.tmp.name, "def1_templateImage.png")

        # Mock ImageProcessor 以避免依赖实际的图像裁剪库
        with patch('kotonebot.devtools.resgen.parsers.ImageProcessor') as mock_proc:
            mock_proc.save_crop_to_path.return_value = expected_name
            mock_proc.copy_image.side_effect = lambda src, out_dir, new_name=None: os.path.join(out_dir, new_name or "copy.png")

            nodes = self.parser.parse(json_path, context)

        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.type, "template")
        self.assertTrue(isinstance(node.value, ImageAsset))
        assert isinstance(node.value, ImageAsset)
        self.assertEqual(os.path.basename(node.value.path), "def1_templateImage.png")

    def test_v2_prefab_variant_merge(self):
        data = {
            "version": 2,
            "definitions": {
                "base": {
                    "type": "prefab",
                    "name": "ui.button",
                    "prefab_id": "TemplateMatchPrefab",
                    "displayName": "Base",
                    "props": {
                        "templateImage": {"kind": "image", "x1": 1, "y1": 2, "x2": 10, "y2": 20},
                        "threshold": 0.8,
                    },
                },
                "en": {
                    "type": "prefab",
                    "name": "ui.button",
                    "variant": "en",
                    "props": {
                        "threshold": 0.9,
                    },
                },
            },
        }
        json_path = self._create_meta_file(data)
        context = _resgen_context(self.tmp.name, resource_variants=["en", "jp"])

        with patch('kotonebot.devtools.resgen.parsers.ImageProcessor') as mock_proc:
            mock_proc.save_crop_to_path.return_value = os.path.join(self.tmp.name, "base_templateImage.png")
            nodes = self.parser.parse(json_path, context)

        prefabs = [n for n in nodes if n.type == "prefab"]
        self.assertEqual(len(prefabs), 1)
        prefab = prefabs[0]
        self.assertIsInstance(prefab.value, PrefabData)
        assert isinstance(prefab.value, PrefabData)
        assert prefab.value.variant_props is not None
        self.assertIn("base", prefab.value.variant_props)
        self.assertIn("en", prefab.value.variant_props)
        self.assertIn("jp", prefab.value.variant_props)
        self.assertEqual(prefab.value.variant_props["base"]["threshold"], 0.8)
        self.assertEqual(prefab.value.variant_props["en"]["threshold"], 0.9)
        self.assertEqual(prefab.value.variant_props["jp"]["threshold"], 0.8)

    def test_v2_prefab_variant_merge_without_base_variant_key(self):
        data = {
            "version": 2,
            "definitions": {
                "base": {
                    "type": "prefab",
                    "name": "ui.button",
                    "prefab_id": "TemplateMatchPrefab",
                    "displayName": "Base",
                    "props": {
                        "templateImage": {"kind": "image", "x1": 1, "y1": 2, "x2": 10, "y2": 20},
                        "threshold": 0.8,
                    },
                },
                "en": {
                    "type": "prefab",
                    "name": "ui.button",
                    "variant": "en",
                    "props": {
                        "threshold": 0.9,
                    },
                },
            },
        }
        json_path = self._create_meta_file(data)
        context = _resgen_context(
            self.tmp.name,
            resource_variants=["en", "jp"],
            resgen_include_base_variant=False,
        )

        with patch('kotonebot.devtools.resgen.parsers.ImageProcessor') as mock_proc:
            mock_proc.save_crop_to_path.return_value = os.path.join(self.tmp.name, "base_templateImage.png")
            nodes = self.parser.parse(json_path, context)

        prefabs = [n for n in nodes if n.type == "prefab"]
        self.assertEqual(len(prefabs), 1)
        prefab = prefabs[0]
        self.assertIsInstance(prefab.value, PrefabData)
        assert isinstance(prefab.value, PrefabData)
        assert prefab.value.variant_props is not None
        self.assertNotIn("base", prefab.value.variant_props)
        self.assertIn("en", prefab.value.variant_props)
        self.assertIn("jp", prefab.value.variant_props)
        self.assertEqual(prefab.value.variant_props["en"]["threshold"], 0.9)
        self.assertEqual(prefab.value.variant_props["jp"]["threshold"], 0.8)


class TestResgenProjectContext(unittest.TestCase):
    def test_load_resgen_project_context_with_variant(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            resources = tmp_path / "resources"
            resources.mkdir()
            pyproject = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path=resources.as_posix(),
                variant_variants=["jp", "tw"],
                variant_base="base",
                variant_path_pattern="nest",
            )

            ctx = load_resgen_project_context(
                meta_files=[],
                conf_path=pyproject.as_posix(),
                include_base_variant=False,
            )

            self.assertEqual(ctx.default_variant, "base")
            self.assertEqual(ctx.parser_context["resource_variants"], ["jp", "tw"])
            self.assertEqual(ctx.parser_context["resgen_include_base_variant"], False)

    def test_load_resgen_project_context_without_variant(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            resources = tmp_path / "resources"
            resources.mkdir()
            pyproject = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path=resources.as_posix(),
            )

            ctx = load_resgen_project_context(
                meta_files=[],
                conf_path=pyproject.as_posix(),
            )

            self.assertEqual(ctx.default_variant, "")
            self.assertEqual(ctx.parser_context, {})

    def test_load_resgen_runtime_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            resources = tmp_path / "resources"
            resources.mkdir()
            pyproject = write_pyproject(
                tmp_path / "pyproject.toml",
                resource_path=resources.as_posix(),
                variant_variants=["jp", "tw"],
                variant_base="base",
                variant_path_pattern="nest",
            )

            ctx = load_resgen_runtime_context(
                output_img_dir="out-dir",
                conf_path=pyproject.as_posix(),
                include_base_variant=False,
            )

            self.assertEqual(ctx.default_variant, "base")
            self.assertEqual(ctx.parser_context["output_img_dir"], "out-dir")
            self.assertEqual(Path(ctx.parser_context["root_scan_path"]).as_posix(), resources.as_posix())
            self.assertEqual(ctx.parser_context["resource_variants"], ["jp", "tw"])
            self.assertEqual(ctx.parser_context["resgen_include_base_variant"], False)

            default_ctx = load_resgen_runtime_context(
                conf_path=pyproject.as_posix(),
                include_base_variant=False,
            )
            self.assertEqual(default_ctx.parser_context["output_img_dir"], "tmp")


if __name__ == '__main__':
    unittest.main()
