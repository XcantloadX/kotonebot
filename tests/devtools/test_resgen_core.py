"""Tests for kotonebot.devtools.resgen.core module"""

import unittest
from kotonebot.devtools.resgen.core import (
    BoxData,
    ClassNode,
    CodeWriter,
    ImageAsset,
    ResourceNode,
)


class TestCodeWriter(unittest.TestCase):
    """Test CodeWriter class"""

    def test_initialization(self):
        """Test CodeWriter initialization"""
        writer = CodeWriter()
        self.assertEqual(writer.get_content(), "")
        self.assertEqual(writer._indent_level, 0)
        self.assertEqual(writer._indent_str, "    ")

    def test_write_single_line(self):
        """Test writing a single line"""
        writer = CodeWriter()
        writer.write("x = 1")
        self.assertEqual(writer.get_content(), "x = 1")

    def test_write_multiple_lines(self):
        """Test writing multiple lines"""
        writer = CodeWriter()
        writer.write("x = 1")
        writer.write("y = 2")
        self.assertEqual(writer.get_content(), "x = 1\ny = 2")

    def test_write_with_indentation(self):
        """Test writing with indentation"""
        writer = CodeWriter()
        writer.write("class MyClass:")
        with writer.indent():
            writer.write("x = 1")
            writer.write("y = 2")
        self.assertEqual(writer.get_content(), "class MyClass:\n    x = 1\n    y = 2")

    def test_write_nested_indentation(self):
        """Test nested indentation"""
        writer = CodeWriter()
        writer.write("if True:")
        with writer.indent():
            writer.write("if True:")
            with writer.indent():
                writer.write("x = 1")
        expected = "if True:\n    if True:\n        x = 1"
        self.assertEqual(writer.get_content(), expected)

    def test_write_empty_line(self):
        """Test writing empty lines"""
        writer = CodeWriter()
        writer.write("x = 1")
        writer.write_empty_line()
        writer.write("y = 2")
        self.assertEqual(writer.get_content(), "x = 1\n\ny = 2")

    def test_indent_context_manager(self):
        """Test indent context manager functionality"""
        writer = CodeWriter()
        self.assertEqual(writer._indent_level, 0)
        
        with writer.indent():
            self.assertEqual(writer._indent_level, 1)
            with writer.indent():
                self.assertEqual(writer._indent_level, 2)
            self.assertEqual(writer._indent_level, 1)
        
        self.assertEqual(writer._indent_level, 0)

    def test_custom_indent_string(self):
        """Test custom indent string"""
        writer = CodeWriter()
        writer._indent_str = "  "  # 2 spaces instead of 4
        writer.write("class A:")
        with writer.indent():
            writer.write("x = 1")
        self.assertEqual(writer.get_content(), "class A:\n  x = 1")

    def test_empty_codewriter(self):
        """Test empty CodeWriter content"""
        writer = CodeWriter()
        self.assertEqual(writer.get_content(), "")

    def test_write_complex_structure(self):
        """Test writing complex code structure"""
        writer = CodeWriter()
        writer.write("def foo():")
        with writer.indent():
            writer.write("if True:")
            with writer.indent():
                writer.write("return 42")
        
        expected = "def foo():\n    if True:\n        return 42"
        self.assertEqual(writer.get_content(), expected)


class TestResourceNode(unittest.TestCase):
    """Test ResourceNode dataclass"""

    def test_resource_node_creation(self):
        """Test basic ResourceNode creation"""
        node = ResourceNode(
            name="test_sprite",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
        )
        self.assertEqual(node.name, "test_sprite")
        self.assertEqual(node.type, "template")
        self.assertEqual(node.value, ImageAsset(path="test.png", rect=None))
        self.assertEqual(node.docstring, "")
        self.assertEqual(node.metadata, {})

    def test_resource_node_with_docstring(self):
        """Test ResourceNode with docstring"""
        node = ResourceNode(
            name="test_sprite",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
            docstring="This is a test sprite",
        )
        self.assertEqual(node.docstring, "This is a test sprite")

    def test_resource_node_with_metadata(self):
        """Test ResourceNode with metadata"""
        metadata = {
            "class_path": ["Ui", "Button"],
            "origin_file": "/path/to/file.png",
            "display_name": "Test Button",
        }
        node = ResourceNode(
            name="test_sprite",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
            metadata=metadata,
        )
        self.assertEqual(node.metadata, metadata)
        self.assertEqual(node.metadata["class_path"], ["Ui", "Button"])

    def test_resource_node_different_types(self):
        """Test ResourceNode with different types"""
        types = ["template", "hint-box", "hint-point"]
        
        for node_type in types:
            node = ResourceNode(
                name=f"test_{node_type}",
                type=node_type,
                value=ImageAsset(path="test.png", rect=None),
            )
            self.assertEqual(node.type, node_type)

    def test_resource_node_equality(self):
        """Test ResourceNode equality"""
        node1 = ResourceNode(
            name="test",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
        )
        node2 = ResourceNode(
            name="test",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
        )
        # Dataclass with same values should be equal
        self.assertEqual(node1, node2)

    def test_resource_node_with_complex_value(self):
        """Test ResourceNode with complex value"""
        value = BoxData(x1=10, y1=20, x2=100, y2=200)
        node = ResourceNode(
            name="hint_box",
            type="hint-box",
            value=value,
        )
        self.assertEqual(node.value, value)


class TestClassNode(unittest.TestCase):
    """Test ClassNode dataclass"""

    def test_class_node_creation(self):
        """Test basic ClassNode creation"""
        node = ClassNode(name="TestClass")
        self.assertEqual(node.name, "TestClass")
        self.assertEqual(node.children, [])
        self.assertEqual(node.attributes, [])

    def test_class_node_with_attributes(self):
        """Test ClassNode with attributes"""
        attr = ResourceNode(
            name="sprite1",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
        )
        node = ClassNode(name="TestClass", attributes=[attr])
        self.assertEqual(len(node.attributes), 1)
        self.assertEqual(node.attributes[0].name, "sprite1")

    def test_class_node_with_children(self):
        """Test ClassNode with child classes"""
        child = ClassNode(name="ChildClass")
        parent = ClassNode(name="ParentClass", children=[child])
        
        self.assertEqual(len(parent.children), 1)
        self.assertEqual(parent.children[0].name, "ChildClass")

    def test_class_node_is_empty(self):
        """Test is_empty method"""
        empty_node = ClassNode(name="Empty")
        self.assertTrue(empty_node.is_empty())
        
        node_with_attr = ClassNode(
            name="NotEmpty",
            attributes=[
                ResourceNode(name="attr", type="template", value=ImageAsset(path="test.png", rect=None))
            ]
        )
        self.assertFalse(node_with_attr.is_empty())
        
        node_with_child = ClassNode(
            name="NotEmpty",
            children=[ClassNode(name="Child")]
        )
        self.assertFalse(node_with_child.is_empty())

    def test_class_node_nested_structure(self):
        """Test nested ClassNode structure"""
        grandchild = ClassNode(name="GrandChild")
        child = ClassNode(name="Child", children=[grandchild])
        parent = ClassNode(name="Parent", children=[child])
        
        self.assertEqual(len(parent.children), 1)
        self.assertEqual(len(parent.children[0].children), 1)
        self.assertEqual(parent.children[0].children[0].name, "GrandChild")

    def test_class_node_mixed_content(self):
        """Test ClassNode with both children and attributes"""
        attr = ResourceNode(name="attr1", type="template", value=ImageAsset(path="test.png", rect=None))
        child = ClassNode(name="Child")
        
        node = ClassNode(
            name="Mixed",
            attributes=[attr],
            children=[child]
        )
        
        self.assertFalse(node.is_empty())
        self.assertEqual(len(node.attributes), 1)
        self.assertEqual(len(node.children), 1)


class TestSchemaParserProtocol(unittest.TestCase):
    """Test SchemaParser protocol implementation"""

    class DummyParser:
        """Dummy parser for testing protocol compliance"""
        
        def can_parse(self, file_path: str) -> bool:
            return file_path.endswith(".dummy")
        
        def parse(self, file_path: str, context):
            return []

    def test_schema_parser_protocol(self):
        """Test that DummyParser implements SchemaParser protocol"""
        parser = self.DummyParser()
        
        # Should have required methods
        self.assertTrue(hasattr(parser, 'can_parse'))
        self.assertTrue(hasattr(parser, 'parse'))
        
        # Should return correct types
        self.assertTrue(parser.can_parse("test.dummy"))
        self.assertFalse(parser.can_parse("test.txt"))
        self.assertEqual(parser.parse("test.dummy", {}), [])

    def test_schema_parser_with_context(self):
        """Test SchemaParser with context parameter"""
        parser = self.DummyParser()
        context = {
            "output_img_dir": "/tmp",
            "root_scan_path": "/data"
        }
        result = parser.parse("test.dummy", context)
        self.assertEqual(result, [])
