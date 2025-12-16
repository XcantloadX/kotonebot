import unittest
import time
from unittest.mock import patch, MagicMock
from kotonebot.backend.loop import Loop
from kotonebot.backend.context.context import init_context, manual_context
from kotonebot.client.device import Device

class TestLoop(unittest.TestCase):
    def setUp(self):
        self.mock_device = MagicMock(spec=Device)
        # Provide a dummy screenshot so Context/image operations do not fail
        self.mock_device.screenshot.return_value = object()
        init_context(target_device=self.mock_device)
        # Ensure no leftover global callbacks from other tests
        from kotonebot.config.config import conf
        conf().loop.loop_callbacks.clear()

    def tearDown(self):
        from kotonebot.config.config import conf
        conf().loop.loop_callbacks.clear()

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

    def test_loop_callbacks_called(self):
        """Ensure callbacks in conf().loop.loop_callbacks are invoked with Loop."""
        from kotonebot.config.config import conf
        called = MagicMock()
        conf().loop.loop_callbacks.append(called)

        with manual_context():
            loop = Loop(interval=0.01, skip_first_wait=True)
            next(loop)

        called.assert_called_once_with(loop)

    def test_loop_callbacks_multiple(self):
        """Multiple callbacks are all called and receive the loop instance."""
        from kotonebot.config.config import conf
        cb1 = MagicMock()
        cb2 = MagicMock()
        conf().loop.loop_callbacks.extend([cb1, cb2])

        with manual_context():
            loop = Loop(interval=0.01, skip_first_wait=True)
            next(loop)

        cb1.assert_called_once()
        cb2.assert_called_once()
        self.assertIs(cb1.call_args[0][0], loop)
        self.assertIs(cb2.call_args[0][0], loop)

if __name__ == '__main__':
    unittest.main()
