import unittest
from typing import Any
from kotonebot.primitives.geometry import (
    Vector2D, Vector3D, Vector4D, Point, PointF, Rect,
    is_point, is_point_f, is_any_point, is_rect,
    unify_point, unify_pointf, unify_rect
)

class TestVector(unittest.TestCase):
    """测试 Vector 类"""

    def test_vector2d(self) -> None:
        """测试 Vector2D 初始化和索引"""
        v = Vector2D(10, 20, name="test_vec")
        self.assertEqual(v.x, 10)
        self.assertEqual(v.y, 20)
        self.assertEqual(v.name, "test_vec")
        self.assertEqual(v[0], 10)
        self.assertEqual(v[1], 20)
        with self.assertRaises(IndexError):
            _ = v[2]
        self.assertEqual(repr(v), 'Point<"test_vec" at (10, 20)>')
        self.assertEqual(str(v), '(10, 20)')
        self.assertEqual(tuple(v), (10, 20))
        x, y = v
        self.assertEqual((x, y), (10, 20))

    def test_vector3d(self) -> None:
        """测试 Vector3D 初始化和索引"""
        v = Vector3D(1, 2, 3)
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, 2)
        self.assertEqual(v.z, 3)
        self.assertEqual(v[0], 1)
        self.assertEqual(v[1], 2)
        self.assertEqual(v[2], 3)
        with self.assertRaises(IndexError):
            _ = v[3]
        self.assertEqual(v.xyz, (1, 2, 3))
        self.assertEqual(v.xy, (1, 2))
        self.assertEqual(tuple(v), (1, 2, 3))
        x, y, z = v
        self.assertEqual((x, y, z), (1, 2, 3))

    def test_vector4d(self) -> None:
        """测试 Vector4D 初始化和索引"""
        v = Vector4D(1, 2, 3, 4)
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, 2)
        self.assertEqual(v.z, 3)
        self.assertEqual(v.w, 4)
        self.assertEqual(v[0], 1)
        self.assertEqual(v[1], 2)
        self.assertEqual(v[2], 3)
        self.assertEqual(v[3], 4)
        with self.assertRaises(IndexError):
            _ = v[4]
        self.assertEqual(tuple(v), (1, 2, 3, 4))
        x, y, z, w = v
        self.assertEqual((x, y, z, w), (1, 2, 3, 4))

class TestPoint(unittest.TestCase):
    """测试 Point 和 _BasePoint 类"""

    def test_point_creation(self) -> None:
        """测试 Point 对象的创建"""
        p = Point(3, 4, name="start")
        self.assertIsInstance(p, Point)
        self.assertEqual(p.x, 3)
        self.assertEqual(p.y, 4)
        self.assertEqual(p.name, "start")

    def test_point_properties(self) -> None:
        """测试 Point 的属性"""
        p = Point(3, 4)
        self.assertEqual(p.xy, (3, 4))
        self.assertAlmostEqual(p.length, 5.0)

    def test_distance_to(self) -> None:
        """测试点之间的距离计算"""
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        p3 = PointF(3.0, 4.0)
        p4_tuple = (3, 4)
        self.assertAlmostEqual(p1.distance_to(p2), 5.0)
        self.assertAlmostEqual(p1.distance_to(p3), 5.0)
        self.assertAlmostEqual(p1.distance_to(p4_tuple), 5.0)

    def test_equality(self) -> None:
        """测试点的相等性判断"""
        p1 = Point(1, 2)
        p2 = Point(1, 2)
        p3 = Point(2, 1)
        p4 = PointF(1.0, 2.0)
        self.assertEqual(p1, p2)
        self.assertNotEqual(p1, p3)
        self.assertEqual(p1, p4) # _BasePoint __eq__ handles this

    def test_normalized(self) -> None:
        """测试单位向量"""
        p = Point(3, 4)
        norm_p = p.normalized()
        self.assertIsInstance(norm_p, PointF)
        self.assertAlmostEqual(norm_p.x, 0.6)
        self.assertAlmostEqual(norm_p.y, 0.8)
        self.assertAlmostEqual(norm_p.length, 1.0)
        
        p_zero = Point(0, 0)
        norm_zero = p_zero.normalized()
        self.assertEqual(norm_zero, PointF(0.0, 0.0))

    def test_division(self) -> None:
        """测试点的标量除法"""
        p = Point(10, 20)
        res = p / 2
        self.assertIsInstance(res, PointF)
        self.assertEqual(res, PointF(5.0, 10.0))
        with self.assertRaises(ValueError):
            _ = p / 0

    def test_offset(self) -> None:
        """测试 Point 的偏移"""
        p = Point(5, 5)
        p_offset = p.offset(1, -1)
        self.assertIsInstance(p_offset, Point)
        self.assertEqual(p_offset, Point(6, 4))
        self.assertEqual(p, Point(5, 5)) # 确保原点不变

    def test_addition(self) -> None:
        """测试 Point 的加法和类型提升"""
        p_int = Point(1, 2)
        # Point + Point -> Point
        res1 = p_int + Point(10, 20)
        self.assertIsInstance(res1, Point)
        self.assertEqual(res1, Point(11, 22))
        # Point + PointF -> PointF
        res2 = p_int + PointF(10.5, 20.5)
        self.assertIsInstance(res2, PointF)
        self.assertEqual(res2, PointF(11.5, 22.5))
        # Point + tuple[int] -> Point
        res3 = p_int + (10, 20)
        self.assertIsInstance(res3, Point)
        self.assertEqual(res3, Point(11, 22))
        # Point + tuple[float] -> PointF
        res4 = p_int + (10.5, 20.5)
        self.assertIsInstance(res4, PointF)
        self.assertEqual(res4, PointF(11.5, 22.5))

    def test_subtraction(self) -> None:
        """测试 Point 的减法和类型提升"""
        p_int = Point(10, 20)
        # Point - Point -> Point
        res1 = p_int - Point(1, 2)
        self.assertIsInstance(res1, Point)
        self.assertEqual(res1, Point(9, 18))
        # Point - PointF -> PointF
        res2 = p_int - PointF(0.5, 0.5)
        self.assertIsInstance(res2, PointF)
        self.assertEqual(res2, PointF(9.5, 19.5))

    def test_multiplication(self) -> None:
        """测试 Point 的标量乘法和类型提升"""
        p_int = Point(2, 3)
        # Point * int -> Point
        res1 = p_int * 3
        self.assertIsInstance(res1, Point)
        self.assertEqual(res1, Point(6, 9))
        # Point * float -> PointF
        res2 = p_int * 1.5
        self.assertIsInstance(res2, PointF)
        self.assertEqual(res2, PointF(3.0, 4.5))

class TestPointF(unittest.TestCase):
    """测试 PointF 类"""

    def test_pointf_creation(self) -> None:
        """测试 PointF 对象的创建"""
        pf = PointF(1.5, 2.5, name="target")
        self.assertIsInstance(pf, PointF)
        self.assertEqual(pf.x, 1.5)
        self.assertEqual(pf.y, 2.5)
        self.assertEqual(pf.name, "target")

    def test_pointf_ops(self) -> None:
        """测试 PointF 的算术运算"""
        pf1 = PointF(10.5, 20.5)
        # offset
        self.assertEqual(pf1.offset(1.0, 1.0), PointF(11.5, 21.5))
        # add
        self.assertEqual(pf1 + PointF(0.5, 0.5), PointF(11.0, 21.0))
        self.assertEqual(pf1 + Point(1, 1), PointF(11.5, 21.5))
        # sub
        self.assertEqual(pf1 - PointF(0.5, 0.5), PointF(10.0, 20.0))
        # mul
        self.assertEqual(pf1 * 2, PointF(21.0, 41.0))
        self.assertEqual(pf1 * 2.0, PointF(21.0, 41.0))

class TestRect(unittest.TestCase):
    """测试 Rect 类"""

    def test_rect_creation(self) -> None:
        """测试 Rect 对象的创建"""
        # from x, y, w, h
        r1 = Rect(10, 20, 30, 40, name="rect1")
        self.assertEqual((r1.x1, r1.y1, r1.w, r1.h), (10, 20, 30, 40))
        self.assertEqual(r1.name, "rect1")
        # from xywh
        r2 = Rect(xywh=(10, 20, 30, 40))
        self.assertEqual(r2.xywh, (10, 20, 30, 40))
        # from from_xyxy
        r3 = Rect.from_xyxy(10, 20, 40, 60)
        self.assertEqual(r3.xywh, (10, 20, 30, 40))
        # incomplete args
        with self.assertRaises(ValueError):
            Rect(x=10, y=20)
        self.assertEqual(repr(r1), 'Rect<"rect1" at (x=10, y=20, w=30, h=40)>')
        self.assertEqual(str(r1), '(x=10, y=20, w=30, h=40)')

    def test_rect_properties(self) -> None:
        """测试 Rect 的各种属性"""
        r = Rect(10, 20, 100, 200)
        # x2, y2
        self.assertEqual(r.x2, 110)
        self.assertEqual(r.y2, 220)
        r.x2 = 120
        r.y2 = 230
        self.assertEqual(r.w, 110)
        self.assertEqual(r.h, 210)
        # xywh, xyxy
        r = Rect(10, 20, 100, 200)
        self.assertEqual(r.xywh, (10, 20, 100, 200))
        self.assertEqual(r.xyxy, (10, 20, 110, 220))
        # corners
        self.assertEqual(r.top_left, Point(10, 20))
        self.assertEqual(r.bottom_right, Point(110, 220))
        self.assertEqual(r.left_bottom, Point(10, 220))
        self.assertEqual(r.right_top, Point(110, 20))
        # center
        self.assertEqual(r.center, Point(60, 120))
        # size
        self.assertEqual(r.size, (100, 200))
        r.size = (150, 250)
        self.assertEqual(r.w, 150)
        self.assertEqual(r.h, 250)



    def test_copy(self) -> None:
        """测试 Rect 的复制"""
        r1 = Rect(0, 0, 10, 10, name="original")
        r2 = r1.copy()
        self.assertEqual(r1.xywh, r2.xywh)
        self.assertEqual(r1.name, r2.name)
        self.assertIsNot(r1, r2)

    def test_move(self) -> None:
        """测试 Rect 的移动（原地和非原地）"""
        r1 = Rect(10, 20, 30, 40)
        # moved
        r2 = r1.moved(5, 10)
        self.assertEqual(r1.xywh, (10, 20, 30, 40)) # 确保 r1 不变
        self.assertEqual(r2.xywh, (15, 30, 30, 40))
        # move
        r1.move(5, 10)
        self.assertEqual(r1.xywh, (15, 30, 30, 40)) # 确保 r1 改变

    def test_inflate(self) -> None:
        """测试 Rect 的缩放（原地和非原地）"""
        r1 = Rect(10, 20, 30, 40)
        # inflated
        r2 = r1.inflated(5, 10)
        self.assertEqual(r1.xywh, (10, 20, 30, 40)) # 确保 r1 不变
        self.assertEqual(r2.xywh, (5, 10, 40, 60))
        # inflate
        r1.inflate(5, 10)
        self.assertEqual(r1.xywh, (5, 10, 40, 60)) # 确保 r1 改变

    def test_normalize(self) -> None:
        """测试 Rect 的标准化"""
        r1 = Rect(x=100, y=100, w=-20, h=-30)
        # normalized
        r2 = r1.normalized()
        self.assertEqual(r1.xywh, (100, 100, -20, -30)) # 确保 r1 不变
        self.assertEqual(r2.xywh, (80, 70, 20, 30))
        # normalize
        r1.normalize()
        self.assertEqual(r1.xywh, (80, 70, 20, 30)) # 确保 r1 改变

    def test_contains_point(self) -> None:
        """测试 Rect 是否包含某个点"""
        r = Rect(0, 0, 10, 10)
        self.assertTrue(r.contains_point(Point(0, 0)))
        self.assertTrue(r.contains_point(Point(5, 5)))
        self.assertTrue(r.contains_point(Point(9, 9)))
        self.assertFalse(r.contains_point(Point(10, 9))) # x 边界不包含
        self.assertFalse(r.contains_point(Point(9, 10))) # y 边界不包含
        self.assertFalse(r.contains_point(Point(-1, 5)))
        self.assertFalse(r.contains_point(Point(5, -1)))

    def test_intersects_with(self) -> None:
        """测试 Rect 之间的相交判断"""
        r1 = Rect(0, 0, 10, 10)
        # a contains b
        r2 = Rect(2, 2, 5, 5)
        self.assertTrue(r1.intersects_with(r2))
        self.assertTrue(r2.intersects_with(r1))
        # overlap
        r3 = Rect(5, 5, 10, 10)
        self.assertTrue(r1.intersects_with(r3))
        # touch
        r4 = Rect(10, 0, 5, 5)
        self.assertFalse(r1.intersects_with(r4)) # 边界接触不算相交
        # separate
        r5 = Rect(20, 20, 5, 5)
        self.assertFalse(r1.intersects_with(r5))

    def test_union_of(self) -> None:
        """测试 Rect 的并集"""
        r1 = Rect(0, 0, 10, 10)
        r2 = Rect(5, 5, 10, 10)
        union_r = r1.union_of(r2)
        self.assertEqual(union_r.xyxy, (0, 0, 15, 15))

    def test_intersection_of(self) -> None:
        """测试 Rect 的交集"""
        r1 = Rect(0, 0, 10, 10)
        # has intersection
        r2 = Rect(5, 5, 10, 10)
        inter_r = r1.intersection_of(r2)
        assert inter_r is not None
        self.assertEqual(inter_r.xyxy, (5, 5, 10, 10))
        # no intersection
        r3 = Rect(20, 20, 5, 5)
        inter_r_none = r1.intersection_of(r3)
        self.assertIsNone(inter_r_none)

    def test_is_empty(self) -> None:
        """测试 Rect 是否为空"""
        self.assertFalse(Rect(0, 0, 1, 1).is_empty())
        self.assertTrue(Rect(0, 0, 0, 1).is_empty())
        self.assertTrue(Rect(0, 0, 1, 0).is_empty())
        self.assertTrue(Rect(0, 0, -1, 1).is_empty())

    def test_rect_contains_operator(self) -> None:
        """测试 Rect 的 in 运算符 (contains)"""
        r = Rect(0, 0, 10, 10)
        # Inside
        self.assertTrue(Point(5, 5) in r)
        self.assertTrue(PointF(5.7, 5.05) in r)
        # On boundaries (inclusive for x1, y1; exclusive for x2, y2)
        self.assertTrue(Point(0, 0) in r)
        self.assertTrue(Point(9, 9) in r)
        self.assertFalse(Point(10, 9) in r) # x2 is exclusive
        self.assertFalse(Point(9, 10) in r) # y2 is exclusive
        # Outside
        self.assertFalse(Point(-1, -1) in r)
        self.assertFalse(Point(10, 10) in r)
        self.assertFalse(Point(11, 5) in r)
        self.assertFalse(Point(5, 11) in r)

class TestTypeGuards(unittest.TestCase):
    """测试类型守卫函数"""

    def test_type_guards(self) -> None:
        """测试 is_point, is_point_f, is_any_point, is_rect"""
        p = Point(1, 1)
        pf = PointF(1.0, 1.0)
        r = Rect(0, 0, 1, 1)
        other: Any = "string"

        self.assertTrue(is_point(p))
        self.assertFalse(is_point(pf))
        self.assertFalse(is_point(r))
        self.assertFalse(is_point(other))

        self.assertTrue(is_point_f(pf))
        self.assertFalse(is_point_f(p))

        self.assertTrue(is_any_point(p))
        self.assertTrue(is_any_point(pf))
        self.assertFalse(is_any_point(r))

        self.assertTrue(is_rect(r))
        self.assertFalse(is_rect(p))

class TestUnifyFunctions(unittest.TestCase):
    """测试 unify_point, unify_pointf, unify_rect 函数"""

    def test_unify_point_from_point(self) -> None:
        """测试从 Point 转换为 Point"""
        p = Point(10, 20, name="test")
        result = unify_point(p)
        # 应该返回同一个对象
        self.assertIs(result, p)
        self.assertEqual(result.x, 10)
        self.assertEqual(result.y, 20)
        self.assertEqual(result.name, "test")

    def test_unify_point_from_pointf(self) -> None:
        """测试从 PointF 转换为 Point"""
        pf = PointF(10.7, 20.3, name="float_point")
        result = unify_point(pf)
        # 应该转换为整数坐标
        self.assertIsInstance(result, Point)
        self.assertEqual(result.x, 10)
        self.assertEqual(result.y, 20)
        self.assertEqual(result.name, "float_point")

    def test_unify_point_from_tuple(self) -> None:
        """测试从元组转换为 Point"""
        # 整数元组
        result1 = unify_point((5, 15))
        self.assertIsInstance(result1, Point)
        self.assertEqual(result1.x, 5)
        self.assertEqual(result1.y, 15)
        self.assertIsNone(result1.name)

        # 浮点数元组（应该转换为整数）
        result2 = unify_point((5.9, 15.1))
        self.assertIsInstance(result2, Point)
        self.assertEqual(result2.x, 5)
        self.assertEqual(result2.y, 15)

    def test_unify_point_from_list(self) -> None:
        """测试从列表转换为 Point"""
        result = unify_point([100, 200])
        self.assertIsInstance(result, Point)
        self.assertEqual(result.x, 100)
        self.assertEqual(result.y, 200)

    def test_unify_point_invalid_input(self) -> None:
        """测试 unify_point 的无效输入"""
        # 错误的元组长度
        with self.assertRaises(TypeError):
            unify_point((1, 2, 3))  # type: ignore
        
        # 非数值元组
        with self.assertRaises(TypeError):
            unify_point(("a", "b"))  # type: ignore
        
        # 完全错误的类型
        with self.assertRaises(TypeError):
            unify_point("invalid")  # type: ignore
        
        with self.assertRaises(TypeError):
            unify_point(123)  # type: ignore

    def test_unify_pointf_from_pointf(self) -> None:
        """测试从 PointF 转换为 PointF"""
        pf = PointF(10.5, 20.7, name="test")
        result = unify_pointf(pf)
        # 应该返回同一个对象
        self.assertIs(result, pf)
        self.assertEqual(result.x, 10.5)
        self.assertEqual(result.y, 20.7)
        self.assertEqual(result.name, "test")

    def test_unify_pointf_from_point(self) -> None:
        """测试从 Point 转换为 PointF"""
        p = Point(10, 20, name="int_point")
        result = unify_pointf(p)
        # 应该转换为浮点数坐标
        self.assertIsInstance(result, PointF)
        self.assertEqual(result.x, 10.0)
        self.assertEqual(result.y, 20.0)
        self.assertEqual(result.name, "int_point")

    def test_unify_pointf_from_tuple(self) -> None:
        """测试从元组转换为 PointF"""
        # 浮点数元组
        result1 = unify_pointf((5.5, 15.3))
        self.assertIsInstance(result1, PointF)
        self.assertEqual(result1.x, 5.5)
        self.assertEqual(result1.y, 15.3)
        self.assertIsNone(result1.name)

        # 整数元组（应该转换为浮点数）
        result2 = unify_pointf((5, 15))
        self.assertIsInstance(result2, PointF)
        self.assertEqual(result2.x, 5.0)
        self.assertEqual(result2.y, 15.0)

    def test_unify_pointf_from_list(self) -> None:
        """测试从列表转换为 PointF"""
        result = unify_pointf([100.5, 200.7])
        self.assertIsInstance(result, PointF)
        self.assertEqual(result.x, 100.5)
        self.assertEqual(result.y, 200.7)

    def test_unify_pointf_invalid_input(self) -> None:
        """测试 unify_pointf 的无效输入"""
        # 错误的元组长度
        with self.assertRaises(TypeError):
            unify_pointf((1.0, 2.0, 3.0))  # type: ignore
        
        # 非数值元组
        with self.assertRaises(TypeError):
            unify_pointf(("a", "b"))  # type: ignore
        
        # 完全错误的类型
        with self.assertRaises(TypeError):
            unify_pointf("invalid")  # type: ignore
        
        with self.assertRaises(TypeError):
            unify_pointf(123.45)  # type: ignore

    def test_unify_rect_from_rect(self) -> None:
        """测试从 Rect 转换为 Rect"""
        r = Rect(10, 20, 30, 40, name="test")
        result = unify_rect(r)
        # 应该返回同一个对象
        self.assertIs(result, r)
        self.assertEqual(result.xywh, (10, 20, 30, 40))
        self.assertEqual(result.name, "test")

    def test_unify_rect_from_tuple(self) -> None:
        """测试从元组转换为 Rect"""
        # 整数元组
        result1 = unify_rect((5, 10, 100, 200))
        self.assertIsInstance(result1, Rect)
        self.assertEqual(result1.xywh, (5, 10, 100, 200))
        self.assertIsNone(result1.name)

        # 浮点数元组（应该转换为整数）
        result2 = unify_rect((5.9, 10.1, 100.7, 200.3))
        self.assertIsInstance(result2, Rect)
        self.assertEqual(result2.xywh, (5, 10, 100, 200))

    def test_unify_rect_from_list(self) -> None:
        """测试从列表转换为 Rect"""
        result = unify_rect([50, 60, 150, 250])
        self.assertIsInstance(result, Rect)
        self.assertEqual(result.xywh, (50, 60, 150, 250))

    def test_unify_rect_invalid_input(self) -> None:
        """测试 unify_rect 的无效输入"""
        # 错误的元组长度
        with self.assertRaises(TypeError):
            unify_rect((1, 2, 3))  # type: ignore
        
        with self.assertRaises(TypeError):
            unify_rect((1, 2, 3, 4, 5))  # type: ignore
        
        # 非数值元组
        with self.assertRaises(TypeError):
            unify_rect(("a", "b", "c", "d"))  # type: ignore
        
        # 完全错误的类型
        with self.assertRaises(TypeError):
            unify_rect("invalid")  # type: ignore
        
        with self.assertRaises(TypeError):
            unify_rect(123)  # type: ignore

    def test_unify_functions_edge_cases(self) -> None:
        """测试边界情况"""
        # 零值
        p_zero = unify_point((0, 0))
        self.assertEqual(p_zero.xy, (0, 0))
        
        pf_zero = unify_pointf((0.0, 0.0))
        self.assertEqual(pf_zero.xy, (0.0, 0.0))
        
        r_zero = unify_rect((0, 0, 0, 0))
        self.assertEqual(r_zero.xywh, (0, 0, 0, 0))
        
        # 负值
        p_neg = unify_point((-10, -20))
        self.assertEqual(p_neg.xy, (-10, -20))
        
        pf_neg = unify_pointf((-10.5, -20.7))
        self.assertEqual(pf_neg.xy, (-10.5, -20.7))
        
        r_neg = unify_rect((-10, -20, 30, 40))
        self.assertEqual(r_neg.xywh, (-10, -20, 30, 40))

 
if __name__ == '__main__':
    unittest.main()
