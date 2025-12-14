"""Tests for kotonebot.devtools.resgen.codegen module"""

import unittest
from kotonebot.devtools.resgen.codegen import StandardGenerator
from kotonebot.devtools.resgen.core import ClassNode, ResourceNode


class TestStandardGenerator(unittest.TestCase):
    """Test StandardGenerator class"""

    def test_initialization_default(self):
        """Test StandardGenerator initialization with default parameters"""
        gen = StandardGenerator()
        self.assertFalse(gen.production)
        self.assertIsNone(gen.ide_type)
        self.assertIsNotNone(gen.writer)

    def test_initialization_with_parameters(self):
        """Test StandardGenerator initialization with custom parameters"""
        gen = StandardGenerator(production=True, ide_type="vscode")
        self.assertTrue(gen.production)
        self.assertEqual(gen.ide_type, "vscode")

    def test_render_header_development(self):
        """Test render_header in development mode"""
        gen = StandardGenerator(production=False)
        gen.render_header()
        content = gen.writer.get_content()
        
        self.assertIn("#######", content)
        self.assertIn("此文件为自动生成", content)
        self.assertIn("from kotonebot.backend.core import Image, HintBox, HintPoint", content)

    def test_render_header_production(self):
        """Test render_header in production mode"""
        gen = StandardGenerator(production=True)
        gen.render_header()
        content = gen.writer.get_content()
        
        self.assertNotIn("#######", content)
        self.assertNotIn("此文件为自动生成", content)
        self.assertIn("from kotonebot.backend.core import Image, HintBox, HintPoint", content)

    def test_render_empty_class(self):
        """Test rendering empty class node"""
        gen = StandardGenerator()
        node = ClassNode(name="EmptyClass")
        gen.render_class(node)
        content = gen.writer.get_content()
        
        self.assertIn("class EmptyClass:", content)
        self.assertIn("pass", content)

    def test_render_class_with_attributes(self):
        """Test rendering class with attributes"""
        gen = StandardGenerator(production=True)
        
        attr1 = ResourceNode(
            name="sprite1",
            type="template",
            value='Image(path="test1.png")',
        )
        attr2 = ResourceNode(
            name="sprite2",
            type="template",
            value='Image(path="test2.png")',
        )
        
        node = ClassNode(name="TestClass", attributes=[attr1, attr2])
        gen.render_class(node)
        content = gen.writer.get_content()
        
        self.assertIn("class TestClass:", content)
        self.assertIn("sprite1 = Image(path=\"test1.png\")", content)
        self.assertIn("sprite2 = Image(path=\"test2.png\")", content)

    def test_render_nested_classes(self):
        """Test rendering nested class structure"""
        gen = StandardGenerator(production=True)
        
        child = ClassNode(name="ChildClass")
        parent = ClassNode(name="ParentClass", children=[child])
        gen.render_class(parent)
        content = gen.writer.get_content()
        
        self.assertIn("class ParentClass:", content)
        self.assertIn("class ChildClass:", content)

    def test_render_class_with_attributes_and_children(self):
        """Test rendering class with both attributes and children"""
        gen = StandardGenerator(production=True)
        
        attr = ResourceNode(
            name="sprite",
            type="template",
            value='Image(path="test.png")',
        )
        child = ClassNode(name="SubClass")
        parent = ClassNode(
            name="MainClass",
            attributes=[attr],
            children=[child]
        )
        
        gen.render_class(parent)
        content = gen.writer.get_content()
        
        self.assertIn("class MainClass:", content)
        self.assertIn("sprite = Image(path=\"test.png\")", content)
        self.assertIn("class SubClass:", content)

    def test_render_attribute_without_docstring(self):
        """Test rendering attribute without docstring in production mode"""
        gen = StandardGenerator(production=True)
        attr = ResourceNode(
            name="test_attr",
            type="template",
            value="test_value",
        )
        
        gen.render_attribute(attr)
        content = gen.writer.get_content()
        
        self.assertIn("test_attr = test_value", content)
        # Should not have docstring in production
        self.assertNotIn('"""', content)

    def test_generate_simple_structure(self):
        """Test generate method with simple structure"""
        gen = StandardGenerator(production=True)
        node = ClassNode(name="Resources")
        
        content = gen.generate([node])
        
        self.assertIn("from kotonebot.backend.core import Image, HintBox, HintPoint", content)
        self.assertIn("class Resources:", content)
        self.assertIn("pass", content)

    def test_generate_complex_structure(self):
        """Test generate method with complex structure"""
        gen = StandardGenerator(production=True)
        
        attr1 = ResourceNode(
            name="button",
            type="template",
            value='Image(path="button.png")',
        )
        attr2 = ResourceNode(
            name="background",
            type="template",
            value='Image(path="bg.png")',
        )
        
        ui_class = ClassNode(name="Ui", attributes=[attr1, attr2])
        root = ClassNode(name="Resources", children=[ui_class])
        
        content = gen.generate([root])
        
        self.assertIn("from kotonebot.backend.core import Image, HintBox, HintPoint", content)
        self.assertIn("class Resources:", content)
        self.assertIn("class Ui:", content)
        self.assertIn("button = Image(path=\"button.png\")", content)
        self.assertIn("background = Image(path=\"bg.png\")", content)

    def test_generate_multiple_root_nodes(self):
        """Test generate with multiple root nodes"""
        gen = StandardGenerator(production=True)
        
        root1 = ClassNode(name="Images")
        root2 = ClassNode(name="Hints")
        
        content = gen.generate([root1, root2])
        
        self.assertIn("class Images:", content)
        self.assertIn("class Hints:", content)

    def test_docstring_in_development_mode(self):
        """Test docstring rendering in development mode"""
        gen = StandardGenerator(production=False)
        
        attr = ResourceNode(
            name="test",
            type="template",
            value="val",
            docstring="Test docstring",
            metadata={}
        )
        
        gen.render_attribute(attr)
        content = gen.writer.get_content()
        
        self.assertIn('"""', content)
        self.assertIn("Test docstring", content)

    def test_make_img_tag_default(self):
        """Test _make_img_tag with default IDE type"""
        gen = StandardGenerator(ide_type=None)
        tag = gen._make_img_tag("/path/to/image.png", "TestImg")
        
        self.assertIn('<img src="file:///', tag)
        self.assertIn('title="TestImg"', tag)

    def test_make_img_tag_vscode(self):
        """Test _make_img_tag with VSCode IDE type"""
        gen = StandardGenerator(ide_type="vscode")
        tag = gen._make_img_tag("C:\\path\\to\\image.png", "TestImg")
        
        self.assertIn("vscode-file://vscode-app/", tag)
        # Path gets unified to use forward slashes
        self.assertIn("C:/path/to/image.png", tag)

    def test_make_img_tag_pycharm(self):
        """Test _make_img_tag with PyCharm IDE type"""
        gen = StandardGenerator(ide_type="pycharm")
        tag = gen._make_img_tag("/path/to/image.png", "TestImg")
        
        self.assertIn("http://localhost:6532/image?path=", tag)

    def test_hint_box_rendering(self):
        """Test rendering HintBox resource"""
        gen = StandardGenerator(production=True)
        
        attr = ResourceNode(
            name="dialog_box",
            type="hint-box",
            value='HintBox(x1=10, y1=20, x2=100, y2=200, source_resolution=(720, 1280))',
        )
        node = ClassNode(name="Hints", attributes=[attr])
        
        gen.render_class(node)
        content = gen.writer.get_content()
        
        self.assertIn("dialog_box = HintBox(x1=10, y1=20, x2=100, y2=200, source_resolution=(720, 1280))", content)

    def test_hint_point_rendering(self):
        """Test rendering HintPoint resource"""
        gen = StandardGenerator(production=True)
        
        attr = ResourceNode(
            name="touch_point",
            type="hint-point",
            value='HintPoint(x=360, y=640)',
        )
        node = ClassNode(name="Hints", attributes=[attr])
        
        gen.render_class(node)
        content = gen.writer.get_content()
        
        self.assertIn("touch_point = HintPoint(x=360, y=640)", content)

    def test_deeply_nested_structure(self):
        """Test rendering deeply nested class structure"""
        gen = StandardGenerator(production=True)
        
        level3 = ClassNode(name="Level3")
        level2 = ClassNode(name="Level2", children=[level3])
        level1 = ClassNode(name="Level1", children=[level2])
        root = ClassNode(name="Root", children=[level1])
        
        content = gen.generate([root])
        
        self.assertIn("class Root:", content)
        self.assertIn("class Level1:", content)
        self.assertIn("class Level2:", content)
        self.assertIn("class Level3:", content)

    def test_empty_line_between_attributes(self):
        """Test empty lines between attributes"""
        gen = StandardGenerator(production=True)
        
        attr1 = ResourceNode(name="attr1", type="template", value="val1")
        attr2 = ResourceNode(name="attr2", type="template", value="val2")
        node = ClassNode(name="Test", attributes=[attr1, attr2])
        
        gen.render_class(node)
        content = gen.writer.get_content()
        
        # Should have empty lines between attributes
        lines = content.split('\n')
        self.assertTrue(any(line == '' for line in lines))


if __name__ == '__main__':
    unittest.main()
