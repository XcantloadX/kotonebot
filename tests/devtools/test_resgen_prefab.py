"""Tests for resgen prefab support"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from kotonebot.devtools.resgen.codegen import EntityGenerator
from kotonebot.devtools.resgen.core import ImageAsset, PrefabData, ResourceNode
from kotonebot.devtools.resgen.parsers import KotoneV1Parser
from kotonebot.devtools.resgen.validation import MetaValidationError


class TestPrefabParser(unittest.TestCase):
    def setUp(self):
        self.parser = KotoneV1Parser()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.output_dir = os.path.join(self.tmp_dir.name, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def create_test_files(self, json_content):
        json_path = os.path.join(self.tmp_dir.name, "test.png.json")
        png_path = os.path.join(self.tmp_dir.name, "test.png")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_content, f)
        with open(png_path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        return json_path

    def test_parse_valid_prefab_v2(self):
        data = {
            "version": 2,
            "definitions": {
                "def1": {
                    "name": "ui.MyPrefab",
                    "type": "prefab",
                    "prefab_id": "MyBaseClass",
                    "props": {
                        "templateImage": {"kind": "image", "x1": 0, "y1": 0, "x2": 10, "y2": 10}
                    },
                }
            },
        }

        json_path = self.create_test_files(data)
        context = {"output_img_dir": self.output_dir}
        with patch("kotonebot.devtools.resgen.parsers.ImageProcessor") as mock_proc:
            mock_proc.save_crop_to_path.return_value = os.path.join(self.output_dir, "def1_templateImage.png")
            nodes = self.parser.parse(json_path, context)

        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.name, "MyPrefab")
        self.assertEqual(node.type, "prefab")
        self.assertIsInstance(node.value, PrefabData)
        assert isinstance(node.value, PrefabData)
        self.assertEqual(node.value.prefab_id, "MyBaseClass")
        self.assertIsInstance(node.value.image, ImageAsset)

    def test_parse_simple_prefab_missing_prefab_id(self):
        data = {
            "isSimple": True,
            "definition": {
                "name": "MyPrefab",
                "type": "prefab",
            },
        }
        json_path = self.create_test_files(data)
        context = {"output_img_dir": self.output_dir, "root_scan_path": self.tmp_dir.name}
        with self.assertRaises(MetaValidationError) as cm:
            self.parser.parse(json_path, context)
        self.assertIn("missing prefab_id", str(cm.exception))

    def test_parse_simple_prefab(self):
        data = {
            "isSimple": True,
            "definition": {
                "name": "MyPrefab",
                "type": "prefab",
                "prefab_id": "MyBaseClass",
            },
        }
        json_path = self.create_test_files(data)
        context = {"output_img_dir": self.output_dir, "root_scan_path": self.tmp_dir.name}

        nodes = self.parser.parse(json_path, context)
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.name, "MyPrefab")
        self.assertEqual(node.type, "prefab")
        self.assertIsInstance(node.value, PrefabData)
        assert isinstance(node.value, PrefabData)
        self.assertEqual(node.value.prefab_id, "MyBaseClass")
        self.assertIsInstance(node.value.image, ImageAsset)


class TestPrefabCodegen(unittest.TestCase):
    def test_render_custom_prefab_class(self):
        generator = EntityGenerator(production=True)

        prefab_data = PrefabData(
            image=ImageAsset(path="path/to/image.png", rect=(0, 0, 10, 10)),
            prefab_id="CustomBaseClass",
            props={
                "templateImage": ImageAsset(path="path/to/image.png", rect=(0, 0, 10, 10)),
            },
        )
        node = ResourceNode(
            name="MyPrefab",
            type="prefab",
            value=prefab_data,
            metadata={"display_name": "My Display Name"},
        )

        generator.render_attribute(node)
        content = generator.writer.get_content()

        self.assertIn("class MyPrefab(CustomBaseClass):", content)
        self.assertIn(
            'templateImage = ImageSlice(file_path="path/to/image.png", name="My Display Name", slice_rect=Rect(x=0, y=0, w=10, h=10))',
            content,
        )
        self.assertIn('display_name = "My Display Name"', content)

    def test_render_custom_prefab_class_no_rect(self):
        generator = EntityGenerator(production=True)

        prefab_data = PrefabData(
            image=ImageAsset(path="path/to/image.png", rect=None),
            prefab_id="CustomBaseClass",
            props={
                "templateImage": ImageAsset(path="path/to/image.png", rect=None),
            },
        )
        node = ResourceNode(
            name="MyPrefab",
            type="prefab",
            value=prefab_data,
        )

        generator.render_attribute(node)
        content = generator.writer.get_content()

        self.assertIn("class MyPrefab(CustomBaseClass):", content)
        self.assertIn(
            'templateImage = ImageSlice(file_path="path/to/image.png", name="MyPrefab", slice_rect=None)',
            content,
        )


if __name__ == "__main__":
    unittest.main()
