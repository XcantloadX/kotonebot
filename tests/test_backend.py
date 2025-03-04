import unittest
import numpy as np
from kotonebot.util import crop

class TestBackendUtils(unittest.TestCase):
    def setUp(self):
        # 创建一个10x10的测试图像
        self.test_img = np.zeros((10, 10, 3), dtype=np.uint8)
        
    def test_crop(self):
        # 测试普通裁剪
        result = crop(self.test_img, 0.2, 0.2, 0.8, 0.8)
        self.assertEqual(result.shape, (6, 6, 3))
        
        # 测试边界值
        result = crop(self.test_img, 0, 0, 1, 1)
        self.assertEqual(result.shape, (10, 10, 3))
        
        # 测试最小裁剪
        result = crop(self.test_img, 0.4, 0.4, 0.6, 0.6)
        self.assertEqual(result.shape, (2, 2, 3))
        
    def test_crop_y(self):
        # 测试垂直裁剪
        result = crop(self.test_img, y1=0.2, y2=0.8)
        self.assertEqual(result.shape, (6, 10, 3))
        
        # 测试边界值
        result = crop(self.test_img, y1=0, y2=1)
        self.assertEqual(result.shape, (10, 10, 3))
        
    def test_crop_x(self):
        # 测试水平裁剪
        result = crop(self.test_img, x1=0.2, x2=0.8)
        self.assertEqual(result.shape, (10, 6, 3))
        
        # 测试边界值
        result = crop(self.test_img, x1=0, x2=1)
        self.assertEqual(result.shape, (10, 10, 3))
