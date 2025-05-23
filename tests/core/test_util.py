import logging
import unittest
from typing import Literal
from unittest.mock import Mock, patch

from kotonebot.util import measure_time

class TestMeasureTime(unittest.TestCase):
    def setUp(self):
        # 设置测试用的 logger
        self.test_logger = logging.getLogger('test_logger')
        self.test_logger.setLevel(logging.DEBUG)
        self.mock_handler = Mock()
        # Add level attribute to mock handler
        self.mock_handler.level = logging.DEBUG
        self.test_logger.addHandler(self.mock_handler)

    @patch('time.time')
    def test_custom_logger(self, mock_time):
        # Set up mock to return enough time values
        mock_time.side_effect = [0, 2] + [0] * 20  # More values for logging operations

        # 测试函数
        @measure_time(logger=self.test_logger)
        def test_func():
            return "test"

        # 执行测试
        result = test_func()

        # 验证结果
        self.assertEqual(result, "test")
        self.mock_handler.handle.assert_called()
        log_record = self.mock_handler.handle.call_args[0][0]
        self.assertIn("Function test_func execution time: 2.000秒", log_record.getMessage())

    @patch('time.time')
    def test_different_log_levels(self, mock_time):
        levels: list[Literal['debug', 'info', 'warning', 'error', 'critical']] = ['debug', 'info', 'warning', 'error', 'critical']
        
        for level in levels:
            # Reset mock for each iteration with enough values
            mock_time.side_effect = [0, 1] + [0] * 20

            @measure_time(logger=self.test_logger, level=level)
            def test_func():
                return "test"

            result = test_func()
            self.assertEqual(result, "test")
            
            # 验证日志级别
            log_record = self.mock_handler.handle.call_args[0][0]
            self.assertEqual(log_record.levelname, level.upper())

    def test_decorated_function_arguments(self):
        # Set up mock handler properly
        self.mock_handler = Mock(spec=logging.Handler)  # Use proper spec
        self.mock_handler.level = logging.DEBUG
        self.test_logger.handlers = [self.mock_handler]

        @measure_time(logger=self.test_logger)
        def test_func(a, b, *, c=None):
            return a + b + (c or 0)

        result = test_func(1, 2, c=3)
        self.assertEqual(result, 6)

if __name__ == '__main__':
    unittest.main()