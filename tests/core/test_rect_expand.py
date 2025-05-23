import unittest

from kotonebot.primitives import Rect
from kotonebot.backend.context import rect_expand

class TestRectExpand(unittest.TestCase):
    def test_rect_expand(self):
        cases = [
            # 基本扩展
            (Rect(100, 100, 200, 200), Rect(90, 90, 220, 220), {'top': 10, 'right': 10, 'bottom': 10, 'left': 10}),
            # 只扩展顶部
            (Rect(100, 100, 200, 200), Rect(100, 90, 200, 210), {'top': 10}),
            # 只扩展右侧
            (Rect(100, 100, 200, 200), Rect(100, 100, 210, 200), {'right': 10}),
            # 只扩展底部
            (Rect(100, 100, 200, 200), Rect(100, 100, 200, 210), {'bottom': 10}),
            # 只扩展左侧
            (Rect(100, 100, 200, 200), Rect(90, 100, 210, 200), {'left': 10}),
        ]
        for case in cases:
            rect, expected, kwargs = case
            msg = f'rect={rect} kwargs={kwargs}'
            self.assertEqual(rect_expand(rect, **kwargs), expected, msg)

    def test_rect_expand_with_negative_value(self):
        cases = [
            # 负值收缩
            (Rect(100, 100, 200, 200), Rect(110, 110, 180, 180), {'top': -10, 'right': -10, 'bottom': -10, 'left': -10}),
            # 只收缩顶部
            (Rect(100, 100, 200, 200), Rect(100, 110, 200, 190), {'top': -10}),
            # 只收缩右侧
            (Rect(100, 100, 200, 200), Rect(100, 100, 190, 200), {'right': -10}),
            # 只收缩底部
            (Rect(100, 100, 200, 200), Rect(100, 100, 200, 190), {'bottom': -10}),
            # 只收缩左侧
            (Rect(100, 100, 200, 200), Rect(110, 100, 190, 200), {'left': -10}),
        ]
        for case in cases:
            rect, expected, kwargs = case
            msg = f'rect={rect} kwargs={kwargs}'
            self.assertEqual(rect_expand(rect, **kwargs), expected, msg)
