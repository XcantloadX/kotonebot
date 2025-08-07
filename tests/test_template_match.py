import unittest

import cv2

from kotonebot.backend.image import template_match, find_all_crop
from kotonebot.primitives import Rect

def save(image, name: str):
    import os
    if not os.path.exists('./tests/output_images'):
        os.makedirs('./tests/output_images')
    cv2.imwrite(f'./tests/output_images/{name}.png', image)


class TestTemplateMatch(unittest.TestCase):
    def setUp(self):
        self.template = cv2.imread('tests/images/pdorinku.png')
        self.mask = cv2.imread('tests/images/pdorinku_mask.png')
        self.image = cv2.imread('tests/images/acquire_pdorinku.png')

    def __assert_pos(self, result, x, y, offset=10):
        self.assertGreater(result.position[0], x - offset)
        self.assertGreater(result.position[1], y - offset)
        self.assertLess(result.position[0], x + offset)
        self.assertLess(result.position[1], y + offset)

    def test_basic(self):
        result = template_match(self.template, self.image)
        # 圈出结果并保存
        cv2.rectangle(self.image, result[0].rect.xywh, (0, 0, 255), 2)
        save(self.image, 'TestTemplateMatch.basic')

        self.assertGreater(len(result), 0)
        self.assertGreater(result[0].score, 0.9)
        # 坐标位于 (167, 829) 附近
        self.__assert_pos(result[0], 167, 829)

    def test_masked(self):
        result = template_match(
            self.template,
            self.image,
            mask=self.mask,
            max_results=3,
            remove_duplicate=False,
            threshold=0.999,
        )
        # 圈出结果并保存
        for i, r in enumerate(result):
            cv2.rectangle(self.image, r.rect.xywh, (0, 0, 255), 2)
        save(self.image, 'TestTemplateMatch.masked')

        self.assertEqual(len(result), 3)
        self.assertGreater(result[0].score, 0.9)
        self.assertGreater(result[1].score, 0.9)
        self.assertGreater(result[2].score, 0.9)
        # 坐标位于 (167, 829) 附近
        self.__assert_pos(result[0], 167, 829)
        self.__assert_pos(result[1], 306, 829)
        self.__assert_pos(result[2], 444, 829)

    def test_crop(self):
        result = find_all_crop(
            self.image,
            self.template,
            self.mask,
            threshold=0.999,
        )
        for i, r in enumerate(result):
            cv2.imwrite(f'./tests/output_images/TestTemplateMatch.crop_{i}.png', r.image)

        self.assertEqual(len(result), 3)

    def test_rect_parameter(self):
        """测试 rect 参数是否将匹配限制在指定区域内"""
        # 使用一个包含第一个匹配的矩形区域（大约在 x=167, y=829 附近）
        rect_with_match = Rect(150, 810, 300, 300)
        result = template_match(
            self.template,
            self.image,
            mask=self.mask,
            rect=rect_with_match,
            threshold=0.999,
        )
        
        # 应该在矩形区域内找到至少一个匹配
        self.assertGreater(len(result), 0)
        
        # 验证匹配结果在指定的矩形区域内
        match = result[0]
        self.assertGreaterEqual(match.position[0], rect_with_match.x1)
        self.assertGreaterEqual(match.position[1], rect_with_match.y1)
        self.assertLessEqual(match.position[0] + match.size[0], rect_with_match.x1 + rect_with_match.w)
        self.assertLessEqual(match.position[1] + match.size[1], rect_with_match.y1 + rect_with_match.h)
        
        # 验证坐标已调整回原始图像空间
        self.__assert_pos(match, 167, 829)

    def test_rect_no_match(self):
        """测试当区域不包含模板时，rect 参数不返回匹配结果"""
        # 使用一个不包含任何匹配的矩形区域
        rect_without_match = Rect(0, 0, 300, 300)
        result = template_match(
            self.template,
            self.image,
            mask=self.mask,
            rect=rect_without_match,
            threshold=0.999,
        )
        
        # 应该找不到匹配
        self.assertEqual(len(result), 0)

    def test_rect_none_equivalent_to_no_rect(self):
        """测试 rect=None 与不指定 rect 参数产生相同结果"""
        # 不指定 rect 参数获取结果
        result_no_rect = template_match(
            self.template,
            self.image,
            mask=self.mask,
            threshold=0.999,
            max_results=10,
        )
        
        # 使用 rect=None 获取结果
        result_rect_none = template_match(
            self.template,
            self.image,
            mask=self.mask,
            rect=None,
            threshold=0.999,
            max_results=10,
        )
        
        # 应该有相同数量的结果
        self.assertEqual(len(result_no_rect), len(result_rect_none))
        
        # 结果应该完全相同
        for i in range(len(result_no_rect)):
            self.assertEqual(result_no_rect[i].position, result_rect_none[i].position)
            self.assertEqual(result_no_rect[i].score, result_rect_none[i].score)

    def test_rect_coordinate_adjustment(self):
        """测试使用 rect 时坐标是否正确调整"""
        # 定义一个从 (100, 100) 开始的矩形
        test_rect = Rect(100, 100, 400, 800)
        
        # 创建一个简单的测试用例：从图像中裁剪一个小区域作为模板
        # 我们将从图像中裁剪一个包含目标部分的小区域作为模板
        template_from_rect = self.image[820:860, 160:200]  # 这应该包含我们目标的一部分
        
        result = template_match(
            template_from_rect,
            self.image,
            rect=test_rect,
            threshold=0.8,
        )
        
        if len(result) > 0:
            # 结果位置应该调整回原始图像坐标
            # 如果模板在矩形内的 (x, y) 位置被找到，最终位置应该是 (100+x, 100+y)
            match = result[0]
            
            # 位置应该在原始图像边界内
            self.assertGreaterEqual(match.position[0], test_rect.x1)
            self.assertGreaterEqual(match.position[1], test_rect.y1)
            
            # 位置应该被调整（不是相对于矩形原点）
            self.assertGreater(match.position[0], test_rect.x1)
            self.assertGreater(match.position[1], test_rect.y1)
