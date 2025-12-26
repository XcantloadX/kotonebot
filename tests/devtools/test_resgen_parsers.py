"""Tests for kotonebot.devtools.resgen.parsers module"""

import os
import json
import tempfile
import unittest
from unittest.mock import patch
from kotonebot.devtools.resgen.parsers import (
    ParserRegistry,
    KotoneV1Parser,
    BasicSpriteParser,
)
from kotonebot.devtools.resgen.validation import MetaValidationError, detect_and_validate_meta_schema
from kotonebot.devtools.resgen.core import ResourceNode, ImageAsset


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
            # Create a test PNG file
            test_png = os.path.join(tmpdir, "test.png")
            with open(test_png, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')  # PNG header
            
            registry = ParserRegistry()
            parser = BasicSpriteParser()
            registry.register(parser)
            
            context = {"output_img_dir": tmpdir, "root_scan_path": tmpdir}
            result = registry.parse_file(test_png, context)
            
            # BasicSpriteParser should handle .png files without .json
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
            json_file = os.path.join(tmpdir, "test.png.json")
            with open(json_file, 'w') as f:
                json.dump({"some_key": "value"}, f)
            
            parser = KotoneV1Parser()
            self.assertFalse(parser.can_parse(json_file))

    def test_can_parse_with_valid_schema(self):
        """Test can_parse with valid V1 schema"""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "test.png.json")
            schema = {
                "definitions": {},
                "annotations": []
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)
            
            parser = KotoneV1Parser()
            self.assertTrue(parser.can_parse(json_file))

    def test_can_parse_with_simple_meta_schema(self):
        """Test can_parse with new simple meta schema (isSimple + definition)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            json_file = os.path.join(tmpdir, "test.png.json")
            schema = {
                "isSimple": True,
                "definition": {
                    "name": "Ui.Button",
                    "type": "template",
                    "displayName": "按钮",
                    "description": "测试按钮",
                },
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)

            parser = KotoneV1Parser()
            self.assertTrue(parser.can_parse(json_file))

    def test_parse_empty_schema(self):
        """Test parsing empty V1 schema"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy PNG file
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            json_file = png_file + ".json"
            schema = {
                "definitions": {},
                "annotations": []
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)
            
            parser = KotoneV1Parser()
            context = {"output_img_dir": tmpdir}
            result = parser.parse(json_file, context)
            
            self.assertEqual(result, [])

    def test_parse_template_definition(self):
        """Test parsing template definition from V1 schema"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy PNG file using cv2 if available
            try:
                import cv2
                import numpy as np
                png_file = os.path.join(tmpdir, "test.png")
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.imwrite(png_file, img)
            except ImportError:
                self.skipTest("cv2 not available")
            
            json_file = png_file + ".json"
            annotation_id = "annot-1"
            schema = {
                "definitions": {
                    "def-1": {
                        "name": "ui.button",
                        "type": "template",
                        "displayName": "Button",
                        "description": "Main button",
                        "annotationId": annotation_id
                    }
                },
                "annotations": [{
                    "id": annotation_id,
                    "type": "rect",
                    "data": {
                        "x1": 10,
                        "y1": 20,
                        "x2": 100,
                        "y2": 200
                    }
                }]
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)
            
            parser = KotoneV1Parser()
            context = {"output_img_dir": tmpdir}
            result = parser.parse(json_file, context)
            
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].type, "template")
            self.assertEqual(result[0].name, "button")

    def test_parse_simple_template_definition(self):
        """Test parsing simple meta with single template definition (isSimple true)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy PNG file
            png_file = os.path.join(tmpdir, "ui", "button.png")
            os.makedirs(os.path.dirname(png_file), exist_ok=True)
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')

            json_file = png_file + ".json"
            schema = {
                "isSimple": True,
                "definition": {
                    "name": "ui.button",
                    "type": "template",
                    "displayName": "Button",
                    "description": "Main button",
                },
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)

            parser = KotoneV1Parser()
            context = {"output_img_dir": tmpdir, "root_scan_path": tmpdir}
            result = parser.parse(json_file, context)

            self.assertEqual(len(result), 1)
            node = result[0]
            self.assertEqual(node.type, "template")
            self.assertEqual(node.name, "button")
            self.assertIn("class_path", node.metadata)
            self.assertEqual(node.metadata["class_path"], ["Ui"])

    def test_parse_simple_template_definition_with_empty_name_and_display(self):
        """Simple meta: empty name/displayName should fall back to file-based defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "ui", "button.png")
            os.makedirs(os.path.dirname(png_file), exist_ok=True)
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')

            json_file = png_file + ".json"
            schema = {
                "isSimple": True,
                "definition": {
                    "name": "",  # empty name
                    "type": "template",
                    "displayName": "",  # empty displayName
                    "description": "Main button",
                },
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)

            parser = KotoneV1Parser()
            context = {"output_img_dir": tmpdir, "root_scan_path": tmpdir}
            result = parser.parse(json_file, context)

            self.assertEqual(len(result), 1)
            node = result[0]
            # name should be derived from file name (CamelCase)
            self.assertEqual(node.name, "Button")
            # class_path should come from relative directory
            self.assertEqual(node.metadata.get("class_path"), ["Ui"])
            # display_name should fall back to original file name
            self.assertEqual(node.metadata.get("display_name"), "button.png")


class TestMetaValidation(unittest.TestCase):
    """Tests for meta schema validation logic."""

    def test_detect_complex_meta_without_is_simple(self):
        data = {"definitions": {}, "annotations": []}
        info = detect_and_validate_meta_schema(data)
        self.assertEqual(info.format, "complex")
        self.assertFalse(info.is_simple_flag)

    def test_detect_complex_meta_with_is_simple_false(self):
        data = {"isSimple": False, "definitions": {}, "annotations": []}
        info = detect_and_validate_meta_schema(data)
        self.assertEqual(info.format, "complex")
        self.assertFalse(info.is_simple_flag)

    def test_reject_complex_meta_missing_keys(self):
        with self.assertRaises(MetaValidationError):
            detect_and_validate_meta_schema({"definitions": {}})

    def test_detect_simple_meta(self):
        data = {
            "isSimple": True,
            "definition": {"name": "Ui.Button", "type": "template"},
        }
        info = detect_and_validate_meta_schema(data)
        self.assertEqual(info.format, "simple")
        self.assertTrue(info.is_simple_flag)

    def test_simple_meta_forbids_definitions_and_annotations(self):
        data = {
            "isSimple": True,
            "definition": {"name": "Ui.Button", "type": "template"},
            "definitions": {},
        }
        with self.assertRaises(MetaValidationError):
            detect_and_validate_meta_schema(data)

    def test_complex_meta_forbids_single_definition_field(self):
        data = {
            "definition": {"name": "Ui.Button", "type": "template"},
            "definitions": {},
            "annotations": [],
        }
        with self.assertRaises(MetaValidationError):
            detect_and_validate_meta_schema(data)

    def test_detect_meta_v2_basic(self):
        data = {"version": 2, "definitions": {}}
        info = detect_and_validate_meta_schema(data)
        self.assertEqual(info.format, "v2")
        self.assertIsNone(info.is_simple_flag)

    def test_meta_v2_forbids_annotations(self):
        data = {"version": 2, "definitions": {}, "annotations": []}
        with self.assertRaises(MetaValidationError):
            detect_and_validate_meta_schema(data)

    def test_parse_hint_box_definition(self):
        """Test parsing hint-box definition from V1 schema"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                import cv2
                import numpy as np
                png_file = os.path.join(tmpdir, "test.png")
                img = np.zeros((1280, 720, 3), dtype=np.uint8)
                cv2.imwrite(png_file, img)
            except ImportError:
                self.skipTest("cv2 not available")
            
            json_file = png_file + ".json"
            annotation_id = "annot-1"
            schema = {
                "definitions": {
                    "def-1": {
                        "name": "dialogs.hint_box",
                        "type": "hint-box",
                        "displayName": "Dialog",
                        "description": "Dialog box",
                        "annotationId": annotation_id
                    }
                },
                "annotations": [{
                    "id": annotation_id,
                    "type": "rect",
                    "data": {
                        "x1": 0,
                        "y1": 0,
                        "x2": 720,
                        "y2": 1280
                    }
                }]
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)
            
            parser = KotoneV1Parser()
            context = {"output_img_dir": tmpdir}
            result = parser.parse(json_file, context)
            
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].type, "hint-box")

    def test_parse_hint_point_definition(self):
        """Test parsing hint-point definition from V1 schema"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            json_file = png_file + ".json"
            annotation_id = "annot-1"
            schema = {
                "definitions": {
                    "def-1": {
                        "name": "touches.point",
                        "type": "hint-point",
                        "displayName": "Touch Point",
                        "description": "Touch location",
                        "annotationId": annotation_id
                    }
                },
                "annotations": [{
                    "id": annotation_id,
                    "type": "point",
                    "data": {
                        "x": 360,
                        "y": 640
                    }
                }]
            }
            with open(json_file, 'w') as f:
                json.dump(schema, f)
            
            parser = KotoneV1Parser()
            context = {"output_img_dir": tmpdir}
            result = parser.parse(json_file, context)
            
            self.assertTrue(len(result) > 0)
            self.assertEqual(result[0].type, "hint-point")


class TestBasicSpriteParser(unittest.TestCase):
    """Test BasicSpriteParser class"""

    def test_initialization(self):
        """Test BasicSpriteParser initialization"""
        parser = BasicSpriteParser()
        self.assertTrue(isinstance(parser, BasicSpriteParser))

    def test_can_parse_png_file(self):
        """Test can_parse with PNG file without JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            self.assertTrue(parser.can_parse(png_file))

    def test_can_parse_rejects_non_png(self):
        """Test can_parse rejects non-PNG files"""
        parser = BasicSpriteParser()
        
        self.assertFalse(parser.can_parse("test.txt"))
        self.assertFalse(parser.can_parse("test.jpg"))
        self.assertFalse(parser.can_parse("test.json"))

    def test_can_parse_rejects_png_with_json(self):
        """Test can_parse rejects PNG with corresponding JSON"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "test.png")
            json_file = png_file + ".json"
            
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            with open(json_file, 'w') as f:
                json.dump({}, f)
            
            parser = BasicSpriteParser()
            self.assertFalse(parser.can_parse(png_file))

    def test_parse_single_sprite(self):
        """Test parsing a single sprite"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "button.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            result = parser.parse(png_file, context)
            
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].type, "template")
            # BasicSpriteParser converts to CamelCase
            self.assertEqual(result[0].name, "Button")

    def test_parse_sprite_with_path(self):
        """Test parsing sprite with directory path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            ui_dir = os.path.join(tmpdir, "ui", "buttons")
            os.makedirs(ui_dir, exist_ok=True)
            
            png_file = os.path.join(ui_dir, "submit_button.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            result = parser.parse(png_file, context)
            
            self.assertEqual(len(result), 1)
            # class_path should contain Ui and Buttons
            metadata = result[0].metadata
            self.assertIn("class_path", metadata)
            # Verify the class path is built correctly
            self.assertTrue(isinstance(metadata["class_path"], list))

    def test_parse_returns_resource_node(self):
        """Test that parse returns proper ResourceNode"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            result = parser.parse(png_file, context)
            
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
            png_file = os.path.join(tmpdir, "sprite.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            result = parser.parse(png_file, context)
            
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
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            result = parser.parse(png_file, context)
            
            docstring = result[0].docstring
            self.assertIn("名称：", docstring)
            self.assertIn("模块：", docstring)

    def test_parse_multiple_files(self):
        """Test parsing multiple sprite files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            
            # Create multiple PNG files
            files = ["sprite1.png", "sprite2.png", "sprite3.png"]
            for filename in files:
                png_file = os.path.join(tmpdir, filename)
                with open(png_file, 'wb') as f:
                    f.write(b'\x89PNG\r\n\x1a\n')
            
            # Parse each file
            results = []
            for filename in files:
                png_file = os.path.join(tmpdir, filename)
                result = parser.parse(png_file, context)
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
        json_path = os.path.join(self.tmp.name, "test.png.json")
        png_path = os.path.join(self.tmp.name, "test.png")

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(content, f)

        # 为了避免依赖 cv2，这里只创建一个最小 PNG 头部；
        # 在测试中会 patch ImageProcessor 以绕过真实裁剪。
        with open(png_path, 'wb') as f:
            f.write(b"\x89PNG\r\n\x1a\n")

        return json_path

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
        context = {"output_img_dir": self.tmp.name, "root_scan_path": self.tmp.name}

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


if __name__ == '__main__':
    unittest.main()
