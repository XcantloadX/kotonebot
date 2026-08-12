"""Tests for kotonebot.devtools.resgen.utils module"""

import os
import tempfile
import unittest
from pathlib import Path
from kotonebot.devtools.resgen.utils import (
    to_camel_case,
    unify_path,
    build_class_tree,
    ImageProcessor,
)
from kotonebot.devtools.errors import InvalidImageError
from kotonebot.devtools.resgen.core import ImageAsset, ResourceNode


class TestToCamelCase(unittest.TestCase):
    """Test to_camel_case function"""

    def test_single_word(self):
        """Test single word conversion"""
        self.assertEqual(to_camel_case("hello"), "Hello")
        self.assertEqual(to_camel_case("world"), "World")

    def test_snake_case_two_words(self):
        """Test snake_case with two words"""
        self.assertEqual(to_camel_case("hello_world"), "HelloWorld")
        self.assertEqual(to_camel_case("my_class"), "MyClass")

    def test_snake_case_multiple_words(self):
        """Test snake_case with multiple words"""
        self.assertEqual(to_camel_case("hello_world_foo"), "HelloWorldFoo")
        self.assertEqual(to_camel_case("my_long_class_name"), "MyLongClassName")

    def test_already_camel_case(self):
        """Test already camelCase input"""
        # 如果输入中没有分隔符，应保持原始字符串不变
        self.assertEqual(to_camel_case("HelloWorld"), "HelloWorld")

    def test_empty_string(self):
        """Test empty string"""
        self.assertEqual(to_camel_case(""), "")

    def test_single_underscore(self):
        """Test single underscore"""
        self.assertEqual(to_camel_case("_"), "")
        self.assertEqual(to_camel_case("a_"), "A")
        self.assertEqual(to_camel_case("_a"), "A")

    def test_multiple_underscores(self):
        """Test multiple consecutive underscores"""
        self.assertEqual(to_camel_case("hello__world"), "HelloWorld")
        self.assertEqual(to_camel_case("a___b"), "AB")

    def test_uppercase_preservation(self):
        """Test that first letter is capitalized"""
        self.assertEqual(to_camel_case("test"), "Test")
        self.assertEqual(to_camel_case("test_case"), "TestCase")

    def test_numbers_in_name(self):
        """Test names with numbers"""
        self.assertEqual(to_camel_case("test_2_name"), "Test2Name")
        self.assertEqual(to_camel_case("2_test"), "2Test")

    def test_special_characters(self):
        """Test names with special characters (splits on underscore only)"""
        # 特殊字符将作为分隔符处理
        self.assertEqual(to_camel_case("test-case"), "TestCase")
        self.assertEqual(to_camel_case("test.case"), "TestCase")


class TestUnifyPath(unittest.TestCase):
    """Test unify_path function"""

    def test_windows_path(self):
        """Test Windows path conversion"""
        self.assertEqual(unify_path("C:\\path\\to\\file.txt"), "C:/path/to/file.txt")
        self.assertEqual(unify_path("D:\\data\\images\\sprite.png"), "D:/data/images/sprite.png")

    def test_unix_path(self):
        """Test Unix path (should remain unchanged)"""
        self.assertEqual(unify_path("/path/to/file.txt"), "/path/to/file.txt")
        self.assertEqual(unify_path("/home/user/images/sprite.png"), "/home/user/images/sprite.png")

    def test_mixed_slashes(self):
        """Test mixed slashes conversion"""
        self.assertEqual(unify_path("C:\\path/to\\file.txt"), "C:/path/to/file.txt")

    def test_empty_string(self):
        """Test empty string"""
        self.assertEqual(unify_path(""), "")

    def test_relative_path(self):
        """Test relative path"""
        self.assertEqual(unify_path("..\\path\\file.txt"), "../path/file.txt")
        self.assertEqual(unify_path(".\\path\\file.txt"), "./path/file.txt")

    def test_network_path(self):
        """Test UNC network path"""
        self.assertEqual(unify_path("\\\\server\\share\\file.txt"), "//server/share/file.txt")

    def test_single_slash(self):
        """Test single slash paths"""
        self.assertEqual(unify_path("path\\file"), "path/file")
        self.assertEqual(unify_path("file"), "file")

    def test_trailing_slash(self):
        """Test trailing slash"""
        self.assertEqual(unify_path("path\\to\\dir\\"), "path/to/dir/")


class TestBuildClassTree(unittest.TestCase):
    """Test build_class_tree function"""

    def test_empty_resources(self):
        """Test with empty resource list"""
        result = build_class_tree([])
        self.assertEqual(result, [])

    def test_single_resource_no_class_path(self):
        """Test single resource without class path"""
        resource = ResourceNode(
            name="sprite",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
            metadata={}
        )
        result = build_class_tree([resource])
        self.assertEqual(result, [])

    def test_single_resource_single_level_class(self):
        """Test single resource with single-level class path"""
        resource = ResourceNode(
            name="sprite",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
            metadata={"class_path": ["Images"]}
        )
        result = build_class_tree([resource])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Images")
        self.assertEqual(len(result[0].attributes), 1)
        self.assertEqual(result[0].attributes[0].name, "sprite")

    def test_single_resource_nested_class_path(self):
        """Test single resource with nested class path"""
        resource = ResourceNode(
            name="button",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
            metadata={"class_path": ["Ui", "Buttons"]}
        )
        result = build_class_tree([resource])
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Ui")
        self.assertEqual(len(result[0].children), 1)
        
        child = result[0].children[0]
        self.assertEqual(child.name, "Buttons")
        self.assertEqual(len(child.attributes), 1)
        self.assertEqual(child.attributes[0].name, "button")

    def test_multiple_resources_same_class(self):
        """Test multiple resources in same class"""
        resources = [
            ResourceNode(name="sprite1", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Images"]}),
            ResourceNode(name="sprite2", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Images"]}),
        ]
        result = build_class_tree(resources)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Images")
        self.assertEqual(len(result[0].attributes), 2)

    def test_multiple_resources_different_classes(self):
        """Test multiple resources in different classes"""
        resources = [
            ResourceNode(name="sprite1", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Ui"]}),
            ResourceNode(name="sprite2", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Images"]}),
        ]
        result = build_class_tree(resources)
        
        # Should have two root nodes
        self.assertEqual(len(result), 2)
        names = {node.name for node in result}
        self.assertIn("Ui", names)
        self.assertIn("Images", names)

    def test_multiple_resources_shared_parent(self):
        """Test multiple resources sharing parent class"""
        resources = [
            ResourceNode(name="button", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Ui", "Controls"]}),
            ResourceNode(name="checkbox", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Ui", "Controls"]}),
            ResourceNode(name="textbox", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Ui", "Controls"]}),
        ]
        result = build_class_tree(resources)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, "Ui")
        self.assertEqual(len(result[0].children), 1)
        
        controls_class = result[0].children[0]
        self.assertEqual(controls_class.name, "Controls")
        self.assertEqual(len(controls_class.attributes), 3)

    def test_deeply_nested_class_path(self):
        """Test deeply nested class path"""
        resource = ResourceNode(
            name="sprite",
            type="template",
            value=ImageAsset(path="test.png", rect=None),
            metadata={"class_path": ["Level1", "Level2", "Level3", "Level4"]}
        )
        result = build_class_tree([resource])
        
        self.assertEqual(len(result), 1)
        level1 = result[0]
        self.assertEqual(level1.name, "Level1")
        self.assertEqual(len(level1.children), 1)
        
        level2 = level1.children[0]
        self.assertEqual(level2.name, "Level2")
        self.assertEqual(len(level2.children), 1)
        
        level3 = level2.children[0]
        self.assertEqual(level3.name, "Level3")
        self.assertEqual(len(level3.children), 1)
        
        level4 = level3.children[0]
        self.assertEqual(level4.name, "Level4")
        self.assertEqual(len(level4.attributes), 1)

    def test_complex_tree_structure(self):
        """Test complex tree with multiple branches"""
        resources = [
            ResourceNode(name="btn", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Ui", "Buttons"]}),
            ResourceNode(name="check", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Ui", "Checkboxes"]}),
            ResourceNode(name="dialog", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Dialogs"]}),
        ]
        result = build_class_tree(resources)
        
        self.assertEqual(len(result), 2)
        root_names = {node.name for node in result}
        self.assertIn("Ui", root_names)
        self.assertIn("Dialogs", root_names)
        
        ui_node = next(n for n in result if n.name == "Ui")
        self.assertEqual(len(ui_node.children), 2)

    def test_no_duplicate_parent_nodes(self):
        """Test that parent nodes are not duplicated"""
        resources = [
            ResourceNode(name="sprite1", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Parent", "Child"]}),
            ResourceNode(name="sprite2", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Parent", "Child"]}),
            ResourceNode(name="sprite3", type="template", value=ImageAsset(path="test.png", rect=None),
                        metadata={"class_path": ["Parent", "OtherChild"]}),
        ]
        result = build_class_tree(resources)
        
        self.assertEqual(len(result), 1)
        parent = result[0]
        self.assertEqual(len(parent.children), 2)


class TestImageProcessor(unittest.TestCase):
    """Test ImageProcessor utility class"""

    def test_save_crop_basic(self):
        """Test basic image cropping and saving"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test image file with cv2
            try:
                import cv2
                import numpy as np
                
                source_path = os.path.join(tmpdir, "source.png")
                
                # Create a simple 100x100 image
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                img[20:80, 30:70] = 255  # White rectangle
                cv2.imwrite(source_path, img)
                
                output_dir = os.path.join(tmpdir, "output")
                
                # Crop from (20, 30) to (80, 70)
                result_path = ImageProcessor.save_crop(
                    source_path,
                    (30, 20, 70, 80),  # x1, y1, x2, y2
                    output_dir,
                    "cropped"
                )
                
                self.assertTrue(os.path.exists(result_path))
                self.assertTrue(Path(result_path).is_relative_to(Path(output_dir).resolve()))
                self.assertTrue(result_path.endswith(".png"))
                
            except ImportError:
                self.skipTest("cv2 not available")

    def test_save_crop_boundary_checking(self):
        """Test that save_crop handles boundary correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                import cv2
                import numpy as np
                
                source_path = os.path.join(tmpdir, "source.png")
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.imwrite(source_path, img)
                
                output_dir = os.path.join(tmpdir, "output")
                
                # Crop with coordinates outside image bounds
                result_path = ImageProcessor.save_crop(
                    source_path,
                    (-10, -10, 150, 150),  # Larger than image
                    output_dir,
                    "cropped"
                )
                
                self.assertTrue(os.path.exists(result_path))
                
            except ImportError:
                self.skipTest("cv2 not available")

    def test_save_crop_creates_output_dir(self):
        """Test that save_crop creates output directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                import cv2
                import numpy as np
                
                source_path = os.path.join(tmpdir, "source.png")
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.imwrite(source_path, img)
                
                output_dir = os.path.join(tmpdir, "nonexistent", "output")
                
                result_path = ImageProcessor.save_crop(
                    source_path,
                    (10, 10, 50, 50),
                    output_dir,
                    "cropped"
                )
                
                self.assertTrue(os.path.exists(output_dir))
                self.assertTrue(os.path.exists(result_path))
                
            except ImportError:
                self.skipTest("cv2 not available")

    def test_copy_image_basic(self):
        """Test basic image copying"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.txt")
            with open(source_path, 'w') as f:
                f.write("test content")
            
            output_dir = os.path.join(tmpdir, "output")
            result_path = ImageProcessor.copy_image(source_path, output_dir)
            
            self.assertTrue(os.path.exists(result_path))
            self.assertTrue(Path(result_path).is_relative_to(Path(output_dir).resolve()))
            self.assertEqual(os.path.basename(result_path), "source.txt")

    def test_copy_image_with_new_name(self):
        """Test copying image with new name"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.txt")
            with open(source_path, 'w') as f:
                f.write("test content")
            
            output_dir = os.path.join(tmpdir, "output")
            new_name = "renamed.txt"
            result_path = ImageProcessor.copy_image(source_path, output_dir, new_name)
            
            self.assertTrue(os.path.exists(result_path))
            self.assertEqual(os.path.basename(result_path), new_name)

    def test_copy_image_creates_output_dir(self):
        """Test that copy_image creates output directory if it doesn't exist"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.txt")
            with open(source_path, 'w') as f:
                f.write("test content")
            
            output_dir = os.path.join(tmpdir, "nonexistent", "output")
            result_path = ImageProcessor.copy_image(source_path, output_dir)
            
            self.assertTrue(os.path.exists(output_dir))
            self.assertTrue(os.path.exists(result_path))

    def test_copy_image_preserves_content(self):
        """Test that copy_image preserves file content"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.txt")
            content = "test content 12345"
            with open(source_path, 'w') as f:
                f.write(content)
            
            output_dir = os.path.join(tmpdir, "output")
            result_path = ImageProcessor.copy_image(source_path, output_dir)
            
            with open(result_path, 'r') as f:
                result_content = f.read()
            
            self.assertEqual(result_content, content)

    def test_copy_image_returns_absolute_path(self):
        """Test that copy_image returns absolute path"""
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = os.path.join(tmpdir, "source.txt")
            with open(source_path, 'w') as f:
                f.write("test")
            
            output_dir = os.path.join(tmpdir, "output")
            result_path = ImageProcessor.copy_image(source_path, output_dir)
            
            self.assertTrue(os.path.isabs(result_path))

    def test_save_crop_invalid_source_file(self):
        """Test save_crop with non-existent source file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = os.path.join(tmpdir, "output")
            
            with self.assertRaises(InvalidImageError):
                ImageProcessor.save_crop(
                    "/nonexistent/file.png",
                    (10, 10, 50, 50),
                    output_dir,
                    "cropped"
                )


if __name__ == '__main__':
    unittest.main()
