import re
import unittest

from kotonebot.backend.ocr import jp
from kotonebot.backend.ocr import OcrResult, OcrResultList, bounding_box
import cv2


class TestOcr(unittest.TestCase):
    def setUp(self):
        self.img = cv2.imread('tests/images/acquire_pdorinku.png')

    def test_bounding_box(self):
        # 测试基本情况
        # 矩形
        points = [(0, 0), (10, 0), (10, 10), (0, 10)]
        assert bounding_box(points) == (0, 0, 10, 10)
        # 三角形
        points = [(0, 0), (10, 0), (5, 10)]
        assert bounding_box(points) == (0, 0, 10, 10)
        # 不规则四边形
        points = [(0, 0), (5, 2), (8, 6), (2, 8)]
        assert bounding_box(points) == (0, 0, 8, 8)

        # 测试单点
        points = [(5, 5)]
        assert bounding_box(points) == (5, 5, 0, 0)

        # 测试负坐标
        points = [(-1, -1), (2, 3)]
        assert bounding_box(points) == (-1, -1, 3, 4)

        # 测试零宽度矩形
        points = [(0, 0), (0, 10)]
        assert bounding_box(points) == (0, 0, 0, 10)

        # 测试零高度矩形
        points = [(0, 0), (10, 0)]
        assert bounding_box(points) == (0, 0, 10, 0)

        # 测试大数值
        points = [(1000000, 1000000), (2000000, 2000000)]
        assert bounding_box(points) == (1000000, 1000000, 1000000, 1000000)

        # 测试点的无序排列
        points = [(10, 0), (0, 10), (0, 0), (10, 10)]
        assert bounding_box(points) == (0, 0, 10, 10)

        # 测试重复点
        points = [(5, 5), (5, 5), (5, 5)]
        assert bounding_box(points) == (5, 5, 0, 0)

    def test_ocr_ocr(self):
        result = jp.ocr(self.img)
        self.assertGreater(len(result), 0)

    def test_ocr_find(self):
        self.assertTrue(jp.find(self.img, '中間まで'))
        self.assertTrue(jp.find(self.img, '受け取るPドリンクを選んでください。'))
        self.assertTrue(jp.find(self.img, '受け取る'))


class TestOcrResult(unittest.TestCase):
    def test_regex(self):
        result = OcrResult(text='123dd4567rr890', rect=(0, 0, 100, 100), confidence=0.95)
        self.assertEqual(result.regex(r'\d+'), ['123', '4567', '890'])
        self.assertEqual(result.regex(re.compile(r'\d+')), ['123', '4567', '890'])

    def test_numbers(self):
        result = OcrResult(text='123dd4567rr890', rect=(0, 0, 100, 100), confidence=0.95)
        self.assertEqual(result.numbers(), [123, 4567, 890])
        result2 = OcrResult(text='aaa', rect=(0, 0, 100, 100), confidence=0.95)
        self.assertEqual(result2.numbers(), [])
        result3 = OcrResult(text='1234567890', rect=(0, 0, 100, 100), confidence=0.95)
        self.assertEqual(result3.numbers(), [1234567890])


class TestOcrResultList(unittest.TestCase):
    def test_list_compatibility(self):
        result = OcrResultList([
            OcrResult(text='abc', rect=(0, 0, 100, 100), confidence=0.95),
            OcrResult(text='def', rect=(0, 0, 100, 100), confidence=0.95),
            OcrResult(text='ghi', rect=(0, 0, 100, 100), confidence=0.95),
        ])
        
        self.assertEqual(result[0].text, 'abc')
        self.assertEqual(result[-1].text, 'ghi')
        self.assertEqual(len(result[1:]), 2)
        self.assertEqual(result[1:][0].text, 'def')
        self.assertEqual([r.text for r in result], ['abc', 'def', 'ghi'])
        self.assertEqual(len(result), 3)
        self.assertTrue(result[0] in result)

        # 空列表
        result = OcrResultList()
        self.assertEqual(result, [])
        self.assertEqual(bool(result), False)
        self.assertEqual(len(result), 0)
        with self.assertRaises(IndexError):
            result[0]
        with self.assertRaises(IndexError):
            result[-1]
        self.assertEqual(result[1:], [])
        self.assertEqual([r.text for r in result], [])

    def test_where(self):
        result = OcrResultList([
            OcrResult(text='123dd4567rr890', rect=(0, 0, 100, 100), confidence=0.95),
            OcrResult(text='aaa', rect=(0, 0, 100, 100), confidence=0.95),
            OcrResult(text='1234567890', rect=(0, 0, 100, 100), confidence=0.95),
        ])
        self.assertEqual(result.where(lambda x: x.startswith('123')), [result[0], result[2]])

    def test_first(self):
        result = OcrResultList([
            OcrResult(text='123dd4567rr890', rect=(0, 0, 100, 100), confidence=0.95),
            OcrResult(text='aaa', rect=(0, 0, 100, 100), confidence=0.95),
            OcrResult(text='1234567890', rect=(0, 0, 100, 100), confidence=0.95),
        ])
        self.assertEqual(result.first(), result[0])
        result2 = OcrResultList()
        self.assertIsNone(result2.first())
