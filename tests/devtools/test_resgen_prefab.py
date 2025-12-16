"""Tests for resgen prefab support"""

import os
import json
import unittest
import tempfile
from unittest.mock import patch

from kotonebot.devtools.resgen.parsers import KotoneV1Parser
from kotonebot.devtools.resgen.codegen import EntityGenerator
from kotonebot.devtools.resgen.core import ResourceNode, ImageAsset, PrefabData


class TestPrefabParser(unittest.TestCase):
    """Test parsing of prefab definitions"""

    def setUp(self):
        self.parser = KotoneV1Parser()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.output_dir = os.path.join(self.tmp_dir.name, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def create_test_files(self, json_content):
        """Helper to create test json and png files"""
        json_path = os.path.join(self.tmp_dir.name, "test.png.json")
        png_path = os.path.join(self.tmp_dir.name, "test.png")
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_content, f)
            
        # Create dummy png
        with open(png_path, 'wb') as f:
            # Minimal valid PNG header
            f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89')
            
        return json_path

    def test_parse_valid_prefab(self):
        """Test parsing a valid prefab definition"""
        data = {
            "definitions": {
                "def1": {
                    "name": "MyPrefab",
                    "type": "prefab",
                    "annotationId": "annot1",
                    "prefab": {
                        "className": "MyBaseClass"
                    }
                }
            },
            "annotations": [
                {
                    "id": "annot1",
                    "type": "rect",
                    "data": {"x1": 0, "y1": 0, "x2": 10, "y2": 10}
                }
            ]
        }
        
        json_path = self.create_test_files(data)
        context = {"output_img_dir": self.output_dir}
        
        # Mock ImageProcessor to avoid actual image processing
        with patch('kotonebot.devtools.resgen.parsers.ImageProcessor') as mock_proc:
            mock_proc.save_crop.return_value = os.path.join(self.output_dir, "annot1.png")
            
            nodes = self.parser.parse(json_path, context)
            
            self.assertEqual(len(nodes), 1)
            node = nodes[0]
            self.assertEqual(node.name, "MyPrefab")
            self.assertEqual(node.type, "prefab")
            self.assertIsInstance(node.value, PrefabData)
            assert isinstance(node.value, PrefabData) # make pylance happy
            self.assertEqual(node.value.class_name, "MyBaseClass")
            self.assertIsInstance(node.value.image, ImageAsset)

    def test_parse_prefab_missing_classname(self):
        """Test parsing a prefab definition missing className"""
        data = {
            "definitions": {
                "def1": {
                    "name": "MyPrefab",
                    "type": "prefab",
                    "annotationId": "annot1",
                    "prefab": {
                        # Missing className
                    }
                }
            },
            "annotations": []
        }
        
        json_path = self.create_test_files(data)
        context = {"output_img_dir": self.output_dir}
        
        with self.assertRaises(ValueError) as cm:
            self.parser.parse(json_path, context)
        
        self.assertIn("missing className", str(cm.exception))

    def test_parse_prefab_missing_prefab_block(self):
        """Test parsing a prefab definition missing the prefab block"""
        data = {
            "definitions": {
                "def1": {
                    "name": "MyPrefab",
                    "type": "prefab",
                    "annotationId": "annot1"
                    # Missing prefab block
                }
            },
            "annotations": []
        }
        
        json_path = self.create_test_files(data)
        context = {"output_img_dir": self.output_dir}
        
        with self.assertRaises(ValueError) as cm:
            self.parser.parse(json_path, context)
            
        self.assertIn("missing className", str(cm.exception))


class TestPrefabCodegen(unittest.TestCase):
    """Test code generation for prefab definitions"""

    def test_render_custom_prefab_class(self):
        """Test rendering a prefab class with custom base class"""
        generator = EntityGenerator(production=True)
        
        prefab_data = PrefabData(
            image=ImageAsset(path="path/to/image.png", rect=(0, 0, 10, 10)),
            class_name="CustomBaseClass"
        )
        
        node = ResourceNode(
            name="MyPrefab",
            type="prefab",
            value=prefab_data,
            metadata={"display_name": "My Display Name"}
        )
        
        # We need to wrap it in a ClassNode or call render_attribute directly
        # render_attribute writes to the writer
        generator.render_attribute(node)
        
        content = generator.writer.get_content()
        
        # Check for class definition with custom base
        self.assertIn("class MyPrefab(CustomBaseClass):", content)
        
        # Check for attributes
        self.assertIn('template = Image(file_path="path/to/image.png")', content)
        self.assertIn('display_name = "My Display Name"', content)
        self.assertIn('_orig_rect = Rect(x=0, y=0, w=10, h=10)', content)

    def test_render_custom_prefab_class_no_rect(self):
        """Test rendering a prefab class without rect info"""
        generator = EntityGenerator(production=True)
        
        prefab_data = PrefabData(
            image=ImageAsset(path="path/to/image.png", rect=None),
            class_name="CustomBaseClass"
        )
        
        node = ResourceNode(
            name="MyPrefab",
            type="prefab",
            value=prefab_data
        )
        
        generator.render_attribute(node)
        content = generator.writer.get_content()
        
        self.assertIn("class MyPrefab(CustomBaseClass):", content)
        self.assertIn("_orig_rect = None", content)

if __name__ == '__main__':
    unittest.main()
