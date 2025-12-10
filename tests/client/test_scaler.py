import unittest

import numpy as np
from typing import Any

from kotonebot.client.scaler import ProportionalScaler, LandscapeGameScaler, PortraitGameScaler
from kotonebot.primitives.geometry import Point, PointF, Rect
from kotonebot.errors import UnscalableResolutionError


class TestProportionalScaler(unittest.TestCase):
    def test_basic_point_scaling(self):
        """测试基本的点缩放功能"""
        # 创建一个 2:1 的缩放器 (物理分辨率是逻辑分辨率的2倍)
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 测试逻辑到物理的点转换
        logic_point = Point(100, 50)
        physical_point = scaler.logic_to_physical(logic_point)
        self.assertEqual(physical_point.x, 200)
        self.assertEqual(physical_point.y, 100)
        
        # 测试物理到逻辑的点转换
        physical_point2 = Point(400, 200)
        logic_point2 = scaler.physical_to_logic(physical_point2)
        self.assertEqual(logic_point2.x, 200)
        self.assertEqual(logic_point2.y, 100)
    
    def test_basic_rect_scaling(self):
        """测试基本的矩形缩放功能"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 测试逻辑到物理的矩形转换
        logic_rect = Rect(10, 20, 100, 50)
        physical_rect = scaler.logic_to_physical(logic_rect)
        self.assertEqual(physical_rect.x1, 20)
        self.assertEqual(physical_rect.y1, 40)
        self.assertEqual(physical_rect.w, 200)
        self.assertEqual(physical_rect.h, 100)
        
        # 测试物理到逻辑的矩形转换
        physical_rect2 = Rect(40, 80, 200, 100)
        logic_rect2 = scaler.physical_to_logic(physical_rect2)
        self.assertEqual(logic_rect2.x1, 20)
        self.assertEqual(logic_rect2.y1, 40)
        self.assertEqual(logic_rect2.w, 100)
        self.assertEqual(logic_rect2.h, 50)
    
    def test_fractional_to_physical(self):
        """测试比例坐标到物理坐标的转换"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 测试点转换
        fractional_point = PointF(0.5, 0.5)
        physical_point = scaler.fractional_to_physical(fractional_point)
        self.assertEqual(physical_point.x, 960.0)
        self.assertEqual(physical_point.y, 540.0)
        
        # 测试矩形转换
        fractional_rect = Rect(0, 0, 1, 1)  # 注意：这里输入的是整数，会被当作像素值，但在比例转换中被视为比例
        # 修正：根据 scaler.py 的实现 logic:
        # fractional_to_physical 对 Rect 的处理是: 
        # new_x = int(rect.x1 * physical_w)
        # 所以 Rect(0, 0, 1, 1) -> x=0, y=0, w=1920, h=1080
        physical_rect = scaler.fractional_to_physical(fractional_rect)
        self.assertEqual(physical_rect.x1, 0)
        self.assertEqual(physical_rect.y1, 0)
        self.assertEqual(physical_rect.w, 1920)
        self.assertEqual(physical_rect.h, 1080)
    
    def test_physical_to_fractional(self):
        """测试物理坐标到比例坐标的转换"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 测试点转换
        physical_point = Point(960, 540)
        fractional_point = scaler.physical_to_fractional(physical_point)
        self.assertEqual(fractional_point.x, 0.5)
        self.assertEqual(fractional_point.y, 0.5)
        self.assertIsInstance(fractional_point, PointF)  # 比例坐标总是返回 PointF
        
        # 测试矩形转换 - 根据新实现，矩形会返回乘以10000的整数
        physical_rect = Rect(960, 540, 1920, 1080)  # 物理坐标
        fractional_rect = scaler.physical_to_fractional(physical_rect)
        # 期望: x=960/1920=0.5, y=540/1080=0.5, w=1920/1920=1.0, h=1080/1080=1.0
        # 乘以10000: x=5000, y=5000, w=10000, h=10000
        self.assertEqual(fractional_rect.x1, 5000)
        self.assertEqual(fractional_rect.y1, 5000)
        self.assertEqual(fractional_rect.w, 10000)
        self.assertEqual(fractional_rect.h, 10000)
    
    def test_rotation_matching(self):
        """测试旋转匹配功能"""
        # 物理分辨率是横屏，逻辑分辨率是竖屏，但宽高比一致
        scaler = ProportionalScaler(match_rotation=True)
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (1080, 1920)  # 竖屏
        
        # 测试点转换是否正确（应该自动调整为横屏）
        logic_point = Point(960, 540)
        physical_point = scaler.logic_to_physical(logic_point)
        self.assertEqual(physical_point.x, 960)
        self.assertEqual(physical_point.y, 540)
        
        # 测试点转换是否正确
        logic_point = Point(960, 540)
        physical_point = scaler.logic_to_physical(logic_point)
        self.assertEqual(physical_point.x, 960)
        self.assertEqual(physical_point.y, 540)
    
    def test_no_rotation_matching(self):
        """测试禁用旋转匹配时的行为"""
        # 当 match_rotation=False 且方向不一致时，应该抛出异常
        with self.assertRaises(UnscalableResolutionError):
            scaler = ProportionalScaler(match_rotation=False)
            scaler.physical_resolution = (1920, 1080)
            scaler.logic_resolution = (1080, 1920)
            # 尝试进行坐标转换应该触发异常
            scaler.logic_to_physical(Point(100, 100))
    
    def test_no_scaling(self):
        """测试不缩放的情况"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = None  # 不缩放
        
        # 点转换应该返回原值
        point = Point(100, 200)
        result = scaler.logic_to_physical(point)
        self.assertEqual(result.x, 100)
        self.assertEqual(result.y, 200)
        
        # 矩形转换应该返回原值
        rect = Rect(10, 20, 100, 50)
        result_rect = scaler.logic_to_physical(rect)
        self.assertEqual(result_rect.x1, 10)
        self.assertEqual(result_rect.y1, 20)
        self.assertEqual(result_rect.w, 100)
        self.assertEqual(result_rect.h, 50)
    
    def test_tuple_input_point(self):
        """测试点元组输入"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 整数元组
        point_tuple = (100, 50)
        result = scaler.logic_to_physical(point_tuple)
        self.assertEqual(result.x, 200)
        self.assertEqual(result.y, 100)
        self.assertIsInstance(result, Point)
        
        # 浮点数元组
        point_tuple_f = (100.5, 50.5)
        result_f = scaler.logic_to_physical(point_tuple_f)
        self.assertIsInstance(result_f, PointF)
    
    def test_tuple_input_rect(self):
        """测试矩形元组输入"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 矩形元组 (x, y, w, h)
        rect_tuple = (10, 20, 100, 50)
        result_rect = scaler.logic_to_physical(rect_tuple)
        self.assertEqual(result_rect.x1, 20)
        self.assertEqual(result_rect.y1, 40)
        self.assertEqual(result_rect.w, 200)
        self.assertEqual(result_rect.h, 100)
        self.assertIsInstance(result_rect, Rect)
    
    def test_pointf_scaling(self):
        """测试 PointF 类型的缩放"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # PointF 应该保持浮点精度
        logic_point = PointF(100.5, 50.25)
        physical_point = scaler.logic_to_physical(logic_point)
        self.assertIsInstance(physical_point, PointF)
        self.assertEqual(physical_point.x, 201.0)
        self.assertEqual(physical_point.y, 100.5)

    def test_aspect_ratio_tolerance(self):
        """测试宽高比容差"""
        # 宽高比略有差异但在容差范围内
        scaler = ProportionalScaler(aspect_ratio_tolerance=0.1)
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (1900, 1070)  # 略有差异
        # 应该成功创建
        self.assertIsNotNone(scaler.logic_resolution)
        
        # 宽高比差异超出容差
        with self.assertRaises(UnscalableResolutionError):
            scaler2 = ProportionalScaler(aspect_ratio_tolerance=0.01)
            scaler2.physical_resolution = (1920, 1080)
            scaler2.logic_resolution = (1000, 1000)  # 正方形，差异太大
            # 尝试进行坐标转换应该触发异常
            scaler2.logic_to_physical(Point(100, 100))
    
    def test_transform_screenshot(self):
        """测试截图缩放功能"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 创建一个模拟的截图 (1920x1080)
        screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
        
        # 缩放到逻辑分辨率
        scaled = scaler.transform_screenshot(screenshot)
        
        # 检查缩放后的尺寸
        self.assertEqual(scaled.shape[0], 540)  # height
        self.assertEqual(scaled.shape[1], 960)  # width
        self.assertEqual(scaled.shape[2], 3)    # channels
    
    def test_transform_screenshot_no_scaling(self):
        """测试不缩放时的截图处理"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = None
        
        screenshot = np.zeros((1080, 1920, 3), dtype=np.uint8)
        scaled = scaler.transform_screenshot(screenshot)
        
        # 应该返回原始截图
        self.assertEqual(scaled.shape, screenshot.shape)
        self.assertTrue(np.array_equal(scaled, screenshot))
    
    def test_preserve_name_attribute(self):
        """测试转换时保留 name 属性"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        # 点的 name 属性
        point = Point(100, 50, name="test_point")
        result = scaler.logic_to_physical(point)
        self.assertEqual(result.name, "test_point")
        
        # 矩形的 name 属性
        rect = Rect(10, 20, 100, 50, name="test_rect")
        result_rect = scaler.logic_to_physical(rect)
        self.assertEqual(result_rect.name, "test_rect")


class TestLandscapeGameScaler(unittest.TestCase):
    def test_landscape_scaling_by_long_edge(self):
        """测试横屏游戏根据长边缩放"""
        scaler = LandscapeGameScaler()
        scaler.physical_resolution = (1920, 1080)  # 横屏
        scaler.logic_resolution = (1280, 720)  # 横屏
        
        # 长边比例: 1920/1280 = 1.5
        # 测试点缩放
        logic_point = Point(100, 50)
        physical_point = scaler.logic_to_physical(logic_point)
        self.assertEqual(physical_point.x, 150)  # 100 * 1.5
        self.assertEqual(physical_point.y, 75)   # 50 * 1.5
        
        # 测试矩形缩放
        logic_rect = Rect(10, 20, 100, 50)
        physical_rect = scaler.logic_to_physical(logic_rect)
        self.assertEqual(physical_rect.x1, 15)   # 10 * 1.5
        self.assertEqual(physical_rect.y1, 30)   # 20 * 1.5
        self.assertEqual(physical_rect.w, 150)   # 100 * 1.5
        self.assertEqual(physical_rect.h, 75)    # 50 * 1.5
    
    def test_landscape_rotation_support(self):
        """测试横屏游戏支持旋转"""
        scaler = LandscapeGameScaler()
        # 物理是横屏，逻辑是竖屏，但应该支持旋转
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (720, 1280)  # 竖屏
        
        # 应该能正常缩放
        logic_point = Point(100, 50)
        physical_point = scaler.logic_to_physical(logic_point)
        # 长边比例: 1920/1280 = 1.5
        self.assertEqual(physical_point.x, 150)
        self.assertEqual(physical_point.y, 75)


class TestPortraitGameScaler(unittest.TestCase):
    def test_portrait_scaling_by_short_edge(self):
        """测试竖屏游戏根据短边缩放"""
        scaler = PortraitGameScaler()
        scaler.physical_resolution = (1080, 1920)  # 竖屏
        scaler.logic_resolution = (720, 1280)  # 竖屏
        
        # 短边比例: 1080/720 = 1.5
        # 测试点缩放
        logic_point = Point(100, 50)
        physical_point = scaler.logic_to_physical(logic_point)
        self.assertEqual(physical_point.x, 150)  # 100 * 1.5
        self.assertEqual(physical_point.y, 75)   # 50 * 1.5
        
        # 测试矩形缩放
        logic_rect = Rect(10, 20, 100, 50)
        physical_rect = scaler.logic_to_physical(logic_rect)
        self.assertEqual(physical_rect.x1, 15)   # 10 * 1.5
        self.assertEqual(physical_rect.y1, 30)   # 20 * 1.5
        self.assertEqual(physical_rect.w, 150)   # 100 * 1.5
        self.assertEqual(physical_rect.h, 75)    # 50 * 1.5
    
    def test_portrait_rotation_support(self):
        """测试竖屏游戏支持旋转"""
        scaler = PortraitGameScaler()
        # 物理是竖屏，逻辑是横屏，但应该支持旋转
        scaler.physical_resolution = (1080, 1920)
        scaler.logic_resolution = (1280, 720)  # 横屏
        
        # 应该能正常缩放
        logic_point = Point(100, 50)
        physical_point = scaler.logic_to_physical(logic_point)
        # 短边比例: 1080/720 = 1.5
        self.assertEqual(physical_point.x, 150)
        self.assertEqual(physical_point.y, 75)


class TestScalerEdgeCases(unittest.TestCase):
    def test_scale_ratio_errors_and_match_rotation_false(self):
        """测试 scale_ratio 在无物理分辨率时抛出，以及 match_rotation=False 的路径"""
        scaler = ProportionalScaler()
        # 未设置 physical_resolution 时应抛出
        with self.assertRaises(RuntimeError):
            _ = scaler.scale_ratio

        # match_rotation=False 时按宽度计算比例
        scaler2 = ProportionalScaler(match_rotation=False)
        scaler2.physical_resolution = (1920, 1080)
        scaler2.logic_resolution = (960, 540)
        self.assertEqual(scaler2.scale_ratio, 1920 / 960)

    def test_aspect_ratio_compatible_invalid_sizes(self):
        """测试 _aspect_ratio_compatible 在非正尺寸时抛出 ValueError"""
        scaler = ProportionalScaler()
        # src 尺寸包含非正值
        with self.assertRaises(ValueError):
            scaler._aspect_ratio_compatible((0, 1080), (1920, 1080))

        # tgt 尺寸包含非正值
        with self.assertRaises(ValueError):
            scaler._aspect_ratio_compatible((1920, 1080), (1920, 0))

    def test_fractional_and_physical_fractional_no_physical(self):
        """当 physical_resolution 未设置时应抛出 RuntimeError"""
        scaler = ProportionalScaler()
        with self.assertRaises(RuntimeError):
            scaler.fractional_to_physical(PointF(0.5, 0.5))
        with self.assertRaises(RuntimeError):
            scaler.physical_to_fractional(Point(10, 10))

    def test_logic_and_physical_pass_through_for_unsupported_types(self):
        """传入不支持的类型应原样返回 (pass-through)"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        # 当 logic_resolution 为 None 时，logic_to_physical 应直接返回输入对象
        scaler.logic_resolution = None
        obj: Any = "unsupported"
        self.assertIs(scaler.logic_to_physical(obj), obj)

        # 当 logic_resolution 为 None 时，physical_to_logic 也应直接返回输入对象
        obj2: Any = {"a": 1}
        self.assertIs(scaler.physical_to_logic(obj2), obj2)
    
    def test_pass_through_unknown_types_with_resolution_set(self):
        """测试当分辨率已设置时，未知类型的直通 (Pass-through)"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1000, 1000)
        scaler.logic_resolution = (500, 500)
        
        obj: Any = "some_string_or_unknown_obj"
        
        # logic_to_physical
        self.assertIs(scaler.logic_to_physical(obj), obj)
        
        # physical_to_logic
        self.assertIs(scaler.physical_to_logic(obj), obj)
        
        # fractional_to_physical
        self.assertIs(scaler.fractional_to_physical(obj), obj)
        
        # physical_to_fractional
        self.assertIs(scaler.physical_to_fractional(obj), obj)

    def test_aspect_ratio_incompatible_even_with_rotation(self):
        """测试即使开启旋转匹配，宽高比也完全不兼容的情况"""
        # 1:1 vs 5:1 (旋转后 1:5)
        # 容差 0.1
        scaler = ProportionalScaler(match_rotation=True, aspect_ratio_tolerance=0.1)
        scaler.physical_resolution = (100, 100)
        scaler.logic_resolution = (1000, 200)
        
        with self.assertRaises(UnscalableResolutionError):
             # 触发检查
             scaler.logic_to_physical(Point(10, 10))

    def test_subclass_scale_ratio_defaults(self):
        """测试子类在未设置逻辑分辨率时的默认返回值"""
        # Landscape
        l_scaler = LandscapeGameScaler()
        l_scaler.physical_resolution = (1920, 1080)
        self.assertEqual(l_scaler.scale_ratio, 1.0)
        
        # Portrait
        p_scaler = PortraitGameScaler()
        p_scaler.physical_resolution = (1080, 1920)
        self.assertEqual(p_scaler.scale_ratio, 1.0)
    
    def test_pointf_physical_to_logic(self):
        """测试 PointF 的物理到逻辑转换 (覆盖 PointF 分支)"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1920, 1080)
        scaler.logic_resolution = (960, 540)
        
        phy_point = PointF(200.0, 100.0, name="pt")
        log_point = scaler.physical_to_logic(phy_point)
        self.assertIsInstance(log_point, PointF)
        self.assertEqual(log_point.x, 100.0)
        self.assertEqual(log_point.y, 50.0)
        self.assertEqual(log_point.name, "pt")

    def test_point_fractional_to_physical(self):
        """测试 Point (非PointF) 的比例到物理转换 (覆盖 Point 分支)"""
        scaler = ProportionalScaler()
        scaler.physical_resolution = (1000, 1000)
        
        # Point(0, 0)
        frac_point = Point(0, 0, name="pt")
        phy_point = scaler.fractional_to_physical(frac_point)
        # 应该返回 Point (int)
        self.assertIsInstance(phy_point, Point)
        self.assertEqual(phy_point.x, 0)
        self.assertEqual(phy_point.name, "pt")

if __name__ == '__main__':
    unittest.main()
