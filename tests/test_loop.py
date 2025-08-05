import unittest
import time
from unittest.mock import patch, MagicMock
from kotonebot.backend.loop import Loop
from kotonebot.backend.context.context import init_context, manual_context
from kotonebot.client.device import Device

class TestLoop(unittest.TestCase):
    def setUp(self):
        self.mock_device = MagicMock(spec=Device)
        init_context(target_device=self.mock_device)

    def test_skip_first_wait(self):
        """测试 skip_first_wait 为 True 时，第一次循环不会等待"""
        with manual_context():
            # 第一次循环不等待
            start_time = time.time()
            loop = Loop(interval=1, skip_first_wait=True)
            next(loop)
            first_tick_time = time.time()
            self.assertLess(first_tick_time - start_time, 0.1)

            # 第二次循环会等待
            start_time = time.time()
            next(loop)
            second_tick_time = time.time()
            self.assertGreaterEqual(second_tick_time - start_time, 1)

    def test_no_skip_first_wait(self):
        """测试当 skip_first_wait 为 False 时，第一次循环会等待"""
        with manual_context():
            start_time = time.time()
            loop = Loop(interval=1, skip_first_wait=False)
            next(loop)
            first_tick_time = time.time()
            self.assertGreaterEqual(first_tick_time - start_time, 1)

if __name__ == '__main__':
    unittest.main()
