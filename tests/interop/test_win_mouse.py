import time
import unittest
from unittest.mock import Mock, patch, call, MagicMock

from kotonebot.primitives import Point
from kotonebot.interop.win import mouse


class TestApiExport(unittest.TestCase):
    def test_functions_utilities(self) -> None:
        from kotonebot.interop.win._mouse import high_precision_sleep # noqa: F401
        from kotonebot.interop.win._mouse import do_tween # noqa: F401
        from kotonebot.interop.win._mouse import set_pos # noqa: F401
        from kotonebot.interop.win._mouse import get_pos # noqa: F401
        from kotonebot.interop.win._mouse import down # noqa: F401
        from kotonebot.interop.win._mouse import up # noqa: F401
        from kotonebot.interop.win._mouse import click # noqa: F401
        from kotonebot.interop.win._mouse import drag # noqa: F401
        from kotonebot.interop.win._mouse import move # noqa: F401

    def test_config(self) -> None:
        from kotonebot.interop.win._mouse import default_speed # noqa: F401
        from kotonebot.interop.win._mouse import animation_args # noqa: F401

    def test_typing_and_classes(self) -> None:
        from kotonebot.interop.win._mouse import AnimationParams # noqa: F401
        from kotonebot.interop.win._mouse import MouseButton # noqa: F401
        from kotonebot.interop.win._mouse import TweenFunc # noqa: F401
        from kotonebot.interop.win._mouse import Tween # noqa: F401

class TestHighPrecisionSleep(unittest.TestCase):
    """测试高精度延时函数"""

    def test_actual_sleep(self) -> None:
        """测试实际延时时间 - 这个测试可能因系统负载而不稳定"""
        duration = 0.02  # 使用一个较短的时间以避免测试过慢
        start_time = time.perf_counter()
        mouse.high_precision_sleep(duration)
        elapsed = time.perf_counter() - start_time
        # 实际时间应该约等于或略大于请求的时间
        self.assertGreaterEqual(elapsed, duration * 0.9)

    @patch('kotonebot.interop.win.mouse.time.sleep')
    @patch('kotonebot.interop.win.mouse.time.perf_counter')
    def test_internal_logic(self, mock_perf_counter: Mock, mock_sleep: Mock) -> None:
        """测试延时函数的内部逻辑，通过模拟 time.perf_counter 的返回值"""
        # 模拟时间流逝：每次调用 perf_counter，时间就增加 0.01 秒
        mock_perf_counter.side_effect = [
            0.0,  # 初始时间
            0.01, # 循环第1次
            0.02, # 循环第2次
            0.03, # 循环第3次
            0.04, # 循环第4次
            0.05  # 循环第5次
        ]
        duration = 0.045
        mouse.high_precision_sleep(duration)

        # 预期行为:
        # 1. start=0. elapsed=0.01. remaining=0.035 (>0.02). sleep(0.035/2 = 0.0175)
        # 2. start=0. elapsed=0.02. remaining=0.025 (>0.02). sleep(0.025/2 = 0.0125)
        # 3. start=0. elapsed=0.03. remaining=0.015 (<=0.02). pass (忙等待)
        # 4. start=0. elapsed=0.04. remaining=0.005 (<=0.02). pass (忙等待)
        # 5. start=0. elapsed=0.05. remaining=-0.005. break
        self.assertEqual(mock_sleep.call_count, 2)
        call_args = mock_sleep.call_args_list
        self.assertAlmostEqual(call_args[0].args[0], 0.0175)
        self.assertAlmostEqual(call_args[1].args[0], 0.0125)


class TestMouseTweens(unittest.TestCase):
    """测试插值（Tween）函数"""

    def test_tween_linear(self) -> None:
        # 测试线性插值
        self.assertAlmostEqual(mouse._tween_linear(0), 0)
        self.assertAlmostEqual(mouse._tween_linear(0.5), 0.5)
        self.assertAlmostEqual(mouse._tween_linear(1), 1)

    def test_tween_ease_in(self) -> None:
        # 测试 ease-in 插值
        self.assertAlmostEqual(mouse._tween_ease_in(0), 0)
        self.assertAlmostEqual(mouse._tween_ease_in(0.5), 0.25)
        self.assertAlmostEqual(mouse._tween_ease_in(1), 1)

    def test_tween_ease_out(self) -> None:
        # 测试 ease-out 插值
        self.assertAlmostEqual(mouse._tween_ease_out(0), 0)
        self.assertAlmostEqual(mouse._tween_ease_out(0.5), 0.75)
        self.assertAlmostEqual(mouse._tween_ease_out(1), 1)

    def test_tween_ease_in_out(self) -> None:
        # 测试 ease-in-out 插值
        self.assertAlmostEqual(mouse._tween_ease_in_out(0), 0)
        self.assertAlmostEqual(mouse._tween_ease_in_out(0.5), 0.5)
        self.assertAlmostEqual(mouse._tween_ease_in_out(1), 1)


class TestGetAnimatedPoints(unittest.TestCase):
    """测试动画点生成器 `_get_animated_points`"""

    def test_returns_correct_points_linear(self) -> None:
        """测试线性插值是否生成正确的点序列"""
        start, end = Point(0, 0), Point(100, 100)
        steps = 10
        points = list(mouse._get_animated_points(start, end, steps, 'linear'))
        self.assertEqual(len(points), steps + 1)
        self.assertEqual(points[0], start)
        self.assertEqual(points[-1], end)
        self.assertEqual(points[5], Point(50, 50))  # 线性插值的中点

    def test_custom_tween_function(self) -> None:
        """测试是否支持自定义插值函数"""
        start, end = Point(0, 0), Point(100, 100)
        steps = 4
        # 一个效果为“减半”的插值函数
        points = list(mouse._get_animated_points(start, end, steps, lambda t: t * 0.5))
        self.assertEqual(len(points), steps + 1)
        self.assertEqual(points[0], Point(0, 0)) # progress=0, eased=0
        self.assertEqual(points[1], Point(12, 12)) # progress=0.25, eased=0.125
        self.assertEqual(points[2], Point(25, 25)) # progress=0.5, eased=0.25
        self.assertEqual(points[-1], Point(50, 50)) # progress=1, eased=0.5


@patch('kotonebot.interop.win.mouse.get_pos')
class TestDoTween(unittest.TestCase):
    """测试核心插值逻辑 `do_tween`"""
    start: Point
    end: Point
    args: mouse.AnimationParams

    def setUp(self) -> None:
        """为测试用例设置通用参数"""
        self.start, self.end = Point(0, 0), Point(100, 0)
        self.args: mouse.AnimationParams = {
            'duration': 0.1,
            'steps': 10,
            'tween': 'linear',
            'delay_func': lambda d: None,  # 禁用延时以加速测试
            'user_interrupt': None,
        }

    def test_generates_correct_points(self, mock_get_pos: Mock) -> None:
        """测试 `do_tween` 是否生成正确的点序列 (默认跳过第一个点)"""
        points = list(mouse.do_tween(self.start, self.end, self.args))
        self.assertEqual(len(points), self.args['steps']) # 默认 skip_first, 少一个
        self.assertEqual(points[0], Point(10, 0))
        self.assertEqual(points[-1], self.end)

    def test_with_skip_first_disabled(self, mock_get_pos: Mock) -> None:
        """测试当 `skip_first=False` 时是否包含起始点"""
        points = list(mouse.do_tween(self.start, self.end, self.args, skip_first=False))
        self.assertEqual(len(points), self.args['steps'] + 1)
        self.assertEqual(points[0], self.start)

    def test_speed_to_duration_calculation(self, mock_get_pos: Mock) -> None:
        """测试从 `speed` 参数到 `duration` 的转换是否正确"""
        mock_delay = Mock()
        args: mouse.AnimationParams = {
            'speed': 1000, 'steps': 10, 'tween': 'linear', 'delay_func': mock_delay,
        }
        # 距离是100, speed是1000, duration应为0.1s
        list(mouse.do_tween(self.start, self.end, args))
        # 总共10步，会调用10次延时
        self.assertEqual(mock_delay.call_count, 10)
        # 每次延时时间为 duration / steps = 0.1 / 10 = 0.01
        self.assertAlmostEqual(mock_delay.call_args[0][0], 0.01)

    def test_invalid_arguments(self, mock_get_pos: Mock) -> None:
        """测试传入无效参数时是否抛出异常"""
        with self.assertRaises(ValueError, msg="speed 为负数时应抛出异常"):
            list(mouse.do_tween(self.start, self.end, {'speed': -100}))
        with self.assertRaises(ValueError, msg="同时提供 duration 和 speed 时应抛出异常"):
            list(mouse.do_tween(self.start, self.end, {'duration': 1, 'speed': 100}))

    def test_user_interrupt_via_true(self, mock_get_pos: Mock) -> None:
        """测试 `user_interrupt=True` 时的用户中断逻辑"""
        # 模拟用户移动鼠标: 第二次 get_pos 时返回一个不同的位置
        mock_get_pos.side_effect = [
            Point(10, 0), # 检查点1: prev_pos=(10,0), 当前位置(10,0), 未移动
            Point(25, 5), # 检查点2: prev_pos=(20,0), 当前位置(25,5), 已移动 -> 中断
        ]
        args: mouse.AnimationParams = {**self.args, 'user_interrupt': True, 'user_interrupt_threshold': 1}
        points = list(mouse.do_tween(self.start, self.end, args))
        # 迭代1: yield Point(10, 0), prev_pos=Point(10,0)
        # 迭代2: 检查中断, get_pos()=(10,0), 未中断, yield Point(20,0), prev_pos=Point(20,0)
        # 迭代3: 检查中断, get_pos()=(25,5), 触发中断, 循环终止
        # 因此，应该只生成了2个点
        self.assertEqual(len(points), 2)

    def test_user_interrupt_via_callable(self, mock_get_pos: Mock) -> None:
        """测试 `user_interrupt` 为可调用对象时的中断逻辑"""
        mock_get_pos.return_value = Point(999, 999)  # 确保鼠标位置变化能被检测到
        interrupt_callback = Mock(return_value=False)  # 返回 False 表示确认中断
        args: mouse.AnimationParams = {**self.args, 'user_interrupt': interrupt_callback, 'user_interrupt_threshold': 1}
        points = list(mouse.do_tween(self.start, self.end, args))
        # 迭代1: yield Point(10, 0)
        # 迭代2: 检查中断, get_pos()与prev_pos不同, 调用 interrupt_callback(), 返回False, 中断
        self.assertEqual(len(points), 1) # 只生成了第一个点
        interrupt_callback.assert_called_once()


@patch('kotonebot.interop.win.mouse.time.sleep')
@patch('kotonebot.interop.win.mouse.mouse', new_callable=MagicMock)
class TestMouseActions(unittest.TestCase):
    """测试具体的鼠标动作函数"""

    def test_set_pos(self, mockmouse: MagicMock, mock_sleep: Mock) -> None:
        """测试 `set_pos` 是否能正确调用底层接口"""
        mouse.set_pos(Point(10, 20))
        mockmouse.move.assert_called_once_with(10, 20)
        mockmouse.reset_mock()

        mouse.set_pos((30, 40))
        mockmouse.move.assert_called_once_with(30, 40)
        mockmouse.reset_mock()

        mouse.set_pos(50, 60)
        mockmouse.move.assert_called_once_with(50, 60)

    def test_get_pos(self, mockmouse: MagicMock, mock_sleep: Mock) -> None:
        """测试 `get_pos` 是否能正确返回 `Point` 对象"""
        mockmouse.get_position.return_value = (123, 456)
        self.assertEqual(mouse.get_pos(), Point(123, 456))

    def test_down_and_up(self, mockmouse: MagicMock, mock_sleep: Mock) -> None:
        """测试 `down` 和 `up` 函数"""
        mouse.down('left')
        mockmouse.press.assert_called_once_with('left')
        mouse.up('right')
        mockmouse.release.assert_called_once_with('right')

    def test_click_call_order(self, mockmouse: MagicMock, mock_sleep: Mock) -> None:
        """测试 `click` 函数是否按照 press -> sleep -> release 的顺序执行"""
        manager = Mock()
        manager.attach_mock(mockmouse, 'mouse')
        manager.attach_mock(mock_sleep, 'sleep')

        mouse.click('middle', duration=0.5)

        expected_calls = [
            call.mouse.press('middle'),
            call.sleep(0.5),
            call.mouse.release('middle')
        ]
        self.assertEqual(manager.method_calls, expected_calls)


@patch('kotonebot.interop.win.mouse.time.sleep')
@patch('kotonebot.interop.win.mouse.up')
@patch('kotonebot.interop.win.mouse.down')
@patch('kotonebot.interop.win.mouse.set_pos')
@patch('kotonebot.interop.win.mouse.do_tween')
class TestDragAndMove(unittest.TestCase):
    """测试 `drag` 和 `move` 函数"""

    def test_move(self, mock_do_tween: Mock, mock_set_pos: Mock, mock_down: Mock, mock_up: Mock, mock_sleep: Mock) -> None:
        """测试 `move` 函数是否只移动光标而不产生按键"""
        start, end = Point(0, 0), Point(100, 100)
        tween_points = [Point(50, 50), Point(100, 100)]
        mock_do_tween.return_value = tween_points

        mouse.move(start, end, duration=1)

        # `move` 不应调用 down 或 up
        mock_down.assert_not_called()
        mock_up.assert_not_called()
        
        # 验证 `do_tween` 被正确调用
        mock_do_tween.assert_called_once()
        passed_args = mock_do_tween.call_args[0]
        self.assertEqual(passed_args[0], start)
        self.assertEqual(passed_args[1], end)
        self.assertIn('duration', passed_args[2])

        # 验证 set_pos 被每个插值点调用
        mock_set_pos.assert_has_calls([call(p) for p in tween_points])

    def test_drag_call_order(self, mock_do_tween: Mock, mock_set_pos: Mock, mock_down: Mock, mock_up: Mock, mock_sleep: Mock) -> None:
        """测试 `drag` 函数是否遵循正确的操作顺序"""
        start, end = Point(0, 0), Point(200, 200)
        tween_points = [Point(100, 100), Point(200, 200)]
        mock_do_tween.return_value = tween_points

        manager = Mock()
        manager.attach_mock(mock_set_pos, 'set_pos')
        manager.attach_mock(mock_sleep, 'sleep')
        manager.attach_mock(mock_down, 'down')
        manager.attach_mock(mock_up, 'up')

        mouse.drag(start, end, button='left', duration=1)

        # 预期的调用顺序
        expected_sequence = [
            call.set_pos(start),
            call.sleep(0.02),
            call.down('left'),
            call.sleep(0.02),
            call.set_pos(tween_points[0]), # 来自 do_tween 的模拟返回
            call.set_pos(tween_points[1]), # 来自 do_tween 的模拟返回
            call.up('left')                # finally 块中的调用
        ]
        self.assertEqual(manager.method_calls, expected_sequence)


if __name__ == '__main__':
    unittest.main()
