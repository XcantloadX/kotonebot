"""Integration tests for kotonebot.devtools.resgen module"""

import os
import json
import tempfile
import unittest
from kotonebot.devtools.resgen import (
    CodeWriter,
    ResourceNode,
    ClassNode,
    SchemaParser,
    StandardGenerator,
    ParserRegistry,
    KotoneV1Parser,
    BasicSpriteParser,
    to_camel_case,
    unify_path,
    build_class_tree,
    ImageProcessor,
)


class TestIntegrationFullWorkflow(unittest.TestCase):
    """Integration tests for complete resgen workflow"""

    def test_basic_sprite_parsing_and_generation(self):
        """Test complete workflow: parse sprite -> generate code"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test PNG file with subdirectory to get proper class path
            ui_dir = os.path.join(tmpdir, "ui")
            os.makedirs(ui_dir, exist_ok=True)
            png_file = os.path.join(ui_dir, "button.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            # Parse
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            resources = parser.parse(png_file, context)
            
            # Build tree
            tree = build_class_tree(resources)
            
            # Generate code
            gen = StandardGenerator(production=True)
            code = gen.generate(tree)
            
            self.assertIn("from kotonebot.backend.core import Image, HintBox, HintPoint", code)
            self.assertIn("class Ui:", code)
            # Attribute name is CamelCase from filename
            self.assertIn("Button = Image(path=", code)

    def test_parse_registry_integration(self):
        """Test ParserRegistry with multiple parsers"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            png_file = os.path.join(tmpdir, "sprite.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            json_file = os.path.join(tmpdir, "data.png.json")
            schema = {"definitions": {}, "annotations": []}
            with open(json_file, 'w') as f:
                json.dump(schema, f)
            
            # Create registry and register parsers
            registry = ParserRegistry()
            registry.register(KotoneV1Parser())
            registry.register(BasicSpriteParser())
            
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            
            # Parse with registry
            result1 = registry.parse_file(json_file, context)
            result2 = registry.parse_file(png_file, context)
            
            # Both should parse successfully
            self.assertTrue(isinstance(result1, list))
            self.assertTrue(isinstance(result2, list))

    def test_nested_class_tree_generation(self):
        """Test generation of nested class structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple resources with nested paths
            resources = [
                ResourceNode(
                    name="submit",
                    type="template",
                    value='Image(path="submit.png")',
                    metadata={"class_path": ["Ui", "Buttons"]}
                ),
                ResourceNode(
                    name="cancel",
                    type="template",
                    value='Image(path="cancel.png")',
                    metadata={"class_path": ["Ui", "Buttons"]}
                ),
                ResourceNode(
                    name="dialog",
                    type="template",
                    value='Image(path="dialog.png")',
                    metadata={"class_path": ["Ui", "Dialogs"]}
                ),
                ResourceNode(
                    name="background",
                    type="template",
                    value='Image(path="bg.png")',
                    metadata={"class_path": ["Images"]}
                ),
            ]
            
            # Build tree
            tree = build_class_tree(resources)
            
            # Generate code
            gen = StandardGenerator(production=True)
            code = gen.generate(tree)
            
            # Verify structure
            self.assertIn("class Ui:", code)
            self.assertIn("class Buttons:", code)
            self.assertIn("class Dialogs:", code)
            self.assertIn("class Images:", code)
            
            # Verify attributes
            self.assertIn("submit = Image(path=\"submit.png\")", code)
            self.assertIn("cancel = Image(path=\"cancel.png\")", code)
            self.assertIn("dialog = Image(path=\"dialog.png\")", code)
            self.assertIn("background = Image(path=\"bg.png\")", code)

    def test_hint_resources_integration(self):
        """Test integration with HintBox and HintPoint resources"""
        resources = [
            ResourceNode(
                name="dialog_area",
                type="hint-box",
                value='HintBox(x1=10, y1=20, x2=710, y2=1270, source_resolution=(720, 1280))',
                metadata={"class_path": ["Hints"]}
            ),
            ResourceNode(
                name="button_touch",
                type="hint-point",
                value='HintPoint(x=360, y=640)',
                metadata={"class_path": ["Hints"]}
            ),
        ]
        
        tree = build_class_tree(resources)
        gen = StandardGenerator(production=True)
        code = gen.generate(tree)
        
        self.assertIn("class Hints:", code)
        self.assertIn("HintBox(x1=10, y1=20, x2=710, y2=1270, source_resolution=(720, 1280))", code)
        self.assertIn("HintPoint(x=360, y=640)", code)

    def test_name_conversion_integration(self):
        """Test snake_case to CamelCase conversion in class_path"""
        resources = [
            ResourceNode(
                name="my_button",
                type="template",
                value='Image(path="test.png")',
                metadata={"class_path": ["Ui", "MainButtons"]}  # Already CamelCase in metadata
            ),
        ]
        
        tree = build_class_tree(resources)
        gen = StandardGenerator(production=True)
        code = gen.generate(tree)
        
        # Class names should be as provided in metadata
        self.assertIn("class Ui:", code)
        self.assertIn("class MainButtons:", code)

    def test_code_writer_indentation_in_generation(self):
        """Test that CodeWriter properly indents generated code"""
        resources = [
            ResourceNode(
                name="attr1",
                type="template",
                value="val1",
                metadata={"class_path": ["Level1", "Level2", "Level3"]}
            ),
        ]
        
        tree = build_class_tree(resources)
        gen = StandardGenerator(production=True)
        code = gen.generate(tree)
        
        lines = code.split('\n')
        
        # Find class definitions and check indentation
        class_level1_idx = next(i for i, line in enumerate(lines) if "class Level1:" in line)
        class_level2_idx = next(i for i, line in enumerate(lines) if "class Level2:" in line)
        class_level3_idx = next(i for i, line in enumerate(lines) if "class Level3:" in line)
        attr_idx = next(i for i, line in enumerate(lines) if "attr1 =" in line)
        
        # Check indentation increases with nesting
        level1_indent = len(lines[class_level1_idx]) - len(lines[class_level1_idx].lstrip())
        level2_indent = len(lines[class_level2_idx]) - len(lines[class_level2_idx].lstrip())
        level3_indent = len(lines[class_level3_idx]) - len(lines[class_level3_idx].lstrip())
        attr_indent = len(lines[attr_idx]) - len(lines[attr_idx].lstrip())
        
        self.assertEqual(level1_indent, 0)
        self.assertTrue(level2_indent > level1_indent)
        self.assertTrue(level3_indent > level2_indent)
        self.assertTrue(attr_indent > level3_indent)

    def test_metadata_preservation_through_pipeline(self):
        """Test that metadata is preserved through parsing and generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            parser = BasicSpriteParser()
            context = {
                "output_img_dir": tmpdir,
                "root_scan_path": tmpdir
            }
            resources = parser.parse(png_file, context)
            
            # Verify metadata is present
            self.assertTrue(len(resources) > 0)
            metadata = resources[0].metadata
            self.assertIn("class_path", metadata)
            self.assertIn("origin_file", metadata)
            self.assertIn("abs_path", metadata)
            self.assertIn("display_name", metadata)
            
            # Metadata should have absolute paths
            self.assertTrue(os.path.isabs(metadata["origin_file"]))
            self.assertTrue(os.path.isabs(metadata["abs_path"]))

    def test_production_vs_development_mode_generation(self):
        """Test differences between production and development code generation"""
        resources = [
            ResourceNode(
                name="test",
                type="template",
                value="Image()",
                docstring="Test sprite",
                metadata={}
            ),
        ]
        
        tree = build_class_tree(resources)
        
        # Development mode
        gen_dev = StandardGenerator(production=False)
        code_dev = gen_dev.generate(tree)
        
        # Production mode
        gen_prod = StandardGenerator(production=True)
        code_prod = gen_prod.generate(tree)
        
        # Development should have comments
        self.assertIn("#######", code_dev)
        self.assertIn("此文件为自动生成", code_dev)
        
        # Production should not have comments
        self.assertNotIn("#######", code_prod)
        self.assertNotIn("此文件为自动生成", code_prod)

    def test_ide_specific_image_tag_generation(self):
        """Test IDE-specific image tag generation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            png_file = os.path.join(tmpdir, "test.png")
            with open(png_file, 'wb') as f:
                f.write(b'\x89PNG\r\n\x1a\n')
            
            img_path = "/path/to/image.png"
            
            # VSCode
            gen_vscode = StandardGenerator(ide_type="vscode")
            tag_vscode = gen_vscode._make_img_tag(img_path, "Test")
            self.assertIn("vscode-file://vscode-app/", tag_vscode)
            
            # PyCharm
            gen_pycharm = StandardGenerator(ide_type="pycharm")
            tag_pycharm = gen_pycharm._make_img_tag(img_path, "Test")
            self.assertIn("http://localhost:6532/image", tag_pycharm)
            
            # Default
            gen_default = StandardGenerator(ide_type=None)
            tag_default = gen_default._make_img_tag(img_path, "Test")
            self.assertIn("file:///", tag_default)

    def test_empty_class_tree_handling(self):
        """Test generation with empty class tree"""
        gen = StandardGenerator(production=True)
        code = gen.generate([])
        
        # Should at least have imports
        self.assertIn("from kotonebot.backend.core import Image, HintBox, HintPoint", code)

    def test_large_nested_structure(self):
        """Test generation with large nested structure"""
        resources = []
        for i in range(10):
            resources.append(
                ResourceNode(
                    name=f"sprite{i}",
                    type="template",
                    value=f"Image(path=\"sprite{i}.png\")",
                    metadata={"class_path": ["Ui", f"Section{i}"]}
                )
            )
        
        tree = build_class_tree(resources)
        gen = StandardGenerator(production=True)
        code = gen.generate(tree)
        
        # Verify all sprites are in code
        for i in range(10):
            self.assertIn(f"sprite{i} = Image(path=\"sprite{i}.png\")", code)
            self.assertIn(f"class Section{i}:", code)

    def test_special_characters_in_docstring(self):
        """Test handling of special characters in docstrings"""
        resource = ResourceNode(
            name="test",
            type="template",
            value="Image()",
            docstring="Test with special chars: <>&\"'",
            metadata={"class_path": ["Test"]}  # Need class_path for tree building
        )
        
        gen = StandardGenerator(production=False)
        tree = build_class_tree([resource])
        code = gen.generate(tree)
        
        # Code should still generate even with special characters
        self.assertIn("class Test:", code)

    def test_path_unification_consistency(self):
        """Test that path unification is consistent across types"""
        paths = [
            "C:\\path\\to\\file.png",
            "C:/path/to/file.png",
            "/path/to/file.png"
        ]
        
        unified = [unify_path(p) for p in paths]
        
        # Should all use forward slashes
        self.assertTrue(all("/" in p or "\\" not in p for p in unified))


if __name__ == '__main__':
    unittest.main()
