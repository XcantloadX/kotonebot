import tempfile
import unittest
from pathlib import Path

import numpy as np

from kotonebot.primitives import Frame, Rect


class TestFrame(unittest.TestCase):
    def test_basic_properties(self):
        mat = np.zeros((20, 30, 3), dtype=np.uint8)
        frame = Frame(mat, name='test_frame')

        self.assertEqual(frame.width, 30)
        self.assertEqual(frame.height, 20)
        self.assertEqual(frame.size.as_tuple(), (30, 20))
        self.assertEqual(frame.shape, (20, 30, 3))

    def test_crop_keeps_source_and_rect(self):
        mat = np.arange(10 * 12 * 3, dtype=np.uint8).reshape((10, 12, 3))
        frame = Frame(mat, name='root')
        rect = Rect(2, 3, 4, 5)

        cropped = frame.crop(rect)

        self.assertEqual(cropped.shape, (5, 4, 3))
        self.assertIs(cropped.source, frame)
        self.assertEqual(cropped.rect, rect)
        self.assertEqual(cropped.name, 'root.crop')

    def test_crop_ratio(self):
        mat = np.zeros((100, 200, 3), dtype=np.uint8)
        frame = Frame(mat, name='ratio')

        cropped = frame.crop_ratio(0.25, 0.10, 0.75, 0.60)

        self.assertEqual(cropped.shape, (50, 100, 3))
        assert cropped.rect is not None
        self.assertEqual(cropped.rect.xywh, (50, 10, 100, 50))

    def test_resize_and_scale(self):
        mat = np.zeros((20, 30, 3), dtype=np.uint8)
        frame = Frame(mat, name='resize')

        resized = frame.resize(15, 10)
        scaled = frame.scale(fx=2.0)

        self.assertEqual(resized.shape, (10, 15, 3))
        self.assertEqual(resized.name, 'resize.resize')
        self.assertEqual(scaled.shape, (40, 60, 3))
        self.assertEqual(scaled.name, 'resize.scale')

    def test_scale_validation(self):
        frame = Frame(np.zeros((10, 10, 3), dtype=np.uint8))

        with self.assertRaises(ValueError):
            frame.scale()
        with self.assertRaises(ValueError):
            frame.scale(fx=2.0, size=(20, 20))

    def test_draw_methods_return_new_frame(self):
        frame = Frame(np.zeros((20, 20, 3), dtype=np.uint8), name='draw')

        rect_frame = frame.draw_rect(Rect(2, 2, 5, 5))
        point_frame = frame.draw_point(10, 10)
        text_frame = frame.draw_text('A', 3, 15)

        self.assertFalse(np.array_equal(frame.mat, rect_frame.mat))
        self.assertFalse(np.array_equal(frame.mat, point_frame.mat))
        self.assertFalse(np.array_equal(frame.mat, text_frame.mat))
        self.assertEqual(rect_frame.name, 'draw.draw_rect')
        self.assertEqual(point_frame.name, 'draw.draw_point')
        self.assertEqual(text_frame.name, 'draw.draw_text')

    def test_save(self):
        frame = Frame(np.full((8, 9, 3), 255, dtype=np.uint8), name='save')

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'frame.png'
            saved_path = frame.save(path)

            self.assertEqual(saved_path, str(path))
            self.assertTrue(path.exists())

    def test_repr_contains_useful_info(self):
        source = Frame(np.zeros((10, 10, 3), dtype=np.uint8), name='source')
        frame = Frame(np.zeros((4, 5, 3), dtype=np.uint8), name='child', source=source, rect=Rect(1, 2, 5, 4))

        text = repr(frame)

        self.assertIn('child', text)
        self.assertIn('5x4', text)
        self.assertIn('source=source', text)
        self.assertIn('rect=', text)


if __name__ == '__main__':
    unittest.main()
