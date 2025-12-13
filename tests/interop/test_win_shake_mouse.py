import unittest
from unittest.mock import MagicMock, patch

from kotonebot.interop.win.shake_mouse import ShakeMouse
from kotonebot.primitives.geometry import Point

class TestShakeMouse(unittest.TestCase):

    def setUp(self):
        """每个测试前重置状态"""
        ShakeMouse._enabled = False
        ShakeMouse.clear_callbacks()
        # 重置一些可能会被修改的类属性配置（如果需要）
        ShakeMouse.STROKE_THRESHOLD = 120
        ShakeMouse.REQUIRED_SHAKES = 4
        ShakeMouse.TIMEOUT_RESET = 0.5
        ShakeMouse.COOLDOWN = 2.0

    def tearDown(self):
        """清理状态"""
        ShakeMouse.stop()
        ShakeMouse.clear_callbacks()

    def run_loop_with_movements(self, points, mock_get_pos, mock_sleep):
        """
        辅助函数：
        1. 设置模拟的坐标序列。
        2. 开启 ShakeMouse。
        3. 运行监测循环。
        4. 当坐标耗尽时，自动停止循环。
        """
        # 定义一个 side_effect，每次调用返回列表中的下一个点
        # 当点用完时，关闭 enabled 以跳出 while 循环
        iterator = iter(points)

        def side_effect():
            try:
                return next(iterator)
            except StopIteration:
                ShakeMouse._enabled = False
                return points[-1]

        mock_get_pos.side_effect = side_effect
        
        # 必须先 enable 才能进入 loop
        ShakeMouse._enabled = True
        
        # 直接运行 loop，不通过 start() 起线程，保证测试是同步的
        ShakeMouse._monitor_loop()

    @patch('kotonebot.interop.win.shake_mouse.time.sleep')
    @patch('kotonebot.interop.win.shake_mouse.time.time')
    @patch('kotonebot.interop.win.shake_mouse.get_pos')
    def test_shake_trigger_success(self, mock_get_pos, mock_time, mock_sleep):
        """测试：标准的有效晃动应该触发回调"""
        callback = MagicMock()
        ShakeMouse.add_callback(callback)

        # 固定时间，避免超时
        mock_time.return_value = 1000.0 

        # 构造动作：左右晃动 (幅度 150 > 阈值 120)
        # 需要 4 次 shaken (方向改变)
        # 0 -> 150 (+150, Dir+) -> 0 (-150, Dir-) -> 150 (+150, Dir+) -> 0 (-150, Dir-) ...
        points = [
            Point(0, 0),    # 初始
            Point(150, 0),  # 右移 (Count 0 -> Acc积累)
            Point(0, 0),    # 左移 (Count 1)
            Point(150, 0),  # 右移 (Count 2)
            Point(0, 0),    # 左移 (Count 3)
            Point(150, 0),  # 右移 (Count 4 -> 触发!)
            Point(150, 0)   # 结束
        ]

        self.run_loop_with_movements(points, mock_get_pos, mock_sleep)

        # 验证回调是否被调用
        callback.assert_called_once()

    @patch('kotonebot.interop.win.shake_mouse.time.sleep')
    @patch('kotonebot.interop.win.shake_mouse.time.time')
    @patch('kotonebot.interop.win.shake_mouse.get_pos')
    def test_shake_insufficient_stroke(self, mock_get_pos, mock_time, mock_sleep):
        """测试：幅度不足的抖动不应触发"""
        callback = MagicMock()
        ShakeMouse.add_callback(callback)
        mock_time.return_value = 1000.0 

        # 幅度 100 (小于阈值 120)
        points = [
            Point(0, 0),
            Point(100, 0), 
            Point(0, 0),
            Point(100, 0),
            Point(0, 0),
            Point(100, 0),
        ]

        self.run_loop_with_movements(points, mock_get_pos, mock_sleep)
        callback.assert_not_called()

    @patch('kotonebot.interop.win.shake_mouse.time.sleep')
    @patch('kotonebot.interop.win.shake_mouse.time.time')
    @patch('kotonebot.interop.win.shake_mouse.get_pos')
    def test_shake_timeout_reset(self, mock_get_pos, mock_time, mock_sleep):
        """测试：晃动中间停顿时间过长，计数器应重置"""
        callback = MagicMock()
        ShakeMouse.add_callback(callback)

        # 定义时间序列
        # 初始时间 1000
        # 晃动两次后，时间跳变到 1005 (超过 0.5s 超时)
        # 然后继续晃动
        
        # 我们通过 side_effect 控制 time.time 的返回值
        # 逻辑：每次 get_pos 被调用时，我们假设是一个 tick
        
        # 动作序列
        points = [
            Point(0, 0),    # T=0
            Point(150, 0),  # T=0 (Shake 0)
            Point(0, 0),    # T=0 (Shake 1)
            Point(150, 0),  # T=0 (Shake 2)
            # --- 这里模拟停顿 ---
            Point(150, 0),  # T=5.0 (停顿检测)
            Point(0, 0),    # T=5.0 (Shake 1, 计数重置了)
            Point(150, 0)   # T=5.0 (Shake 2)
        ]

        # 配合 points 的长度，构造 time 的返回值
        # 前4个点时间是 1000.0，第5个点开始变成 1005.0
        times = [1000.0] * 4 + [1005.0] * 4
        mock_time.side_effect = times

        self.run_loop_with_movements(points, mock_get_pos, mock_sleep)
        
        # 因为中间断了，计数没达到4，所以不触发
        callback.assert_not_called()

    @patch('kotonebot.interop.win.shake_mouse.time.sleep')
    @patch('kotonebot.interop.win.shake_mouse.time.time')
    @patch('kotonebot.interop.win.shake_mouse.get_pos')
    def test_cooldown(self, mock_get_pos, mock_time, mock_sleep):
        """测试：触发一次后，冷却时间内即使晃动也不再次触发"""
        callback = MagicMock()
        ShakeMouse.add_callback(callback)
        ShakeMouse.COOLDOWN = 5.0 # 设置冷却 5秒
        
        # 第一次完全触发序列
        p_trigger = [
            Point(0, 0), Point(150, 0), Point(0, 0), 
            Point(150, 0), Point(0, 0), Point(150, 0) # 触发点
        ]
        
        # 紧接着继续晃动 (在冷却时间内)
        p_cooldown = [
            Point(0, 0), Point(150, 0), Point(0, 0), 
            Point(150, 0), Point(0, 0)
        ]
        
        points = p_trigger + p_cooldown
        
        # 时间设定：前一部分在 1000s，后一部分在 1002s (冷却未结束)
        times = [1000.0] * len(p_trigger) + [1002.0] * (len(p_cooldown) + 2)
        mock_time.side_effect = times

        self.run_loop_with_movements(points, mock_get_pos, mock_sleep)
        
        # 应该只调用了一次，第二次虽然动作够了，但时间在冷却内
        self.assertEqual(callback.call_count, 1)

    @patch('kotonebot.interop.win.shake_mouse.threading.Thread')
    def test_lifecycle(self, mock_thread_cls):
        """测试：Start/Stop 的基本逻辑"""
        # Start
        ShakeMouse.start()
        self.assertTrue(ShakeMouse._enabled)
        mock_thread_cls.assert_called_once() # 确保创建了线程
        
        # 重复 Start 不应重复创建
        ShakeMouse.start()
        self.assertEqual(mock_thread_cls.call_count, 1)
        
        # Stop
        ShakeMouse.stop()
        self.assertFalse(ShakeMouse._enabled)

    @patch('kotonebot.interop.win.shake_mouse.time.sleep')
    @patch('kotonebot.interop.win.shake_mouse.time.time')
    @patch('kotonebot.interop.win.shake_mouse.get_pos')
    def test_shake_trigger_success_vertical(self, mock_get_pos, mock_time, mock_sleep):
        """测试：标准的有效上下晃动应该触发回调"""
        callback = MagicMock()
        ShakeMouse.add_callback(callback)

        # 固定时间，避免超时
        mock_time.return_value = 1000.0

        # 构造动作：上下晃动 (幅度 150 > 阈值 120)
        # 需要 4 次 shaken (方向改变)
        points = [
            Point(0, 0),    # 初始
            Point(0, 150),  # 下移
            Point(0, 0),    # 上移
            Point(0, 150),  # 下移
            Point(0, 0),    # 上移
            Point(0, 150),  # 下移 (触发)
            Point(0, 150)   # 结束
        ]

        self.run_loop_with_movements(points, mock_get_pos, mock_sleep)

        # 验证回调是否被调用
        callback.assert_called_once()

if __name__ == '__main__':
    unittest.main()