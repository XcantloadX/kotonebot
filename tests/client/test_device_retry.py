"""设备读操作重连重试的单测。"""

import unittest
from typing import Any
from unittest.mock import patch

from kotonebot.client.device import AndroidDevice, Device
from kotonebot.client.implements.nemu_ipc.nemu_ipc import NemuIpcError
from kotonebot.config.config import DeviceRetryConfig, conf
from kotonebot.errors import DeviceConnectRefusedError, DeviceNotReadyError
from kotonebot.primitives import Size


class _FlakyScreenshot:
    """前几次调用抛连接异常，之后返回固定哨兵对象。"""

    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0
        self.sentinel = object()

    @property
    def screen_size(self) -> tuple[int, int]:
        return (720, 1280)

    def detect_orientation(self) -> str | None:
        return "portrait"

    def screenshot(self) -> Any:
        self.calls += 1
        if self.calls <= self.failures:
            raise DeviceNotReadyError("device offline")
        return self.sentinel


class _FlakyTouch:
    """click 恒抛连接异常，用于验证写操作不重试。"""

    def __init__(self) -> None:
        self.calls = 0

    def click(self, x: int, y: int) -> None:
        self.calls += 1
        raise DeviceNotReadyError("device offline")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        raise DeviceNotReadyError("device offline")


class _FlakyCommands:
    """current_package 先失败一次，之后返回固定包名。"""

    def __init__(self) -> None:
        self.calls = 0

    def current_package(self) -> str | None:
        self.calls += 1
        if self.calls == 1:
            raise DeviceNotReadyError("device offline")
        return "com.example.game"


class _NemuFailingScreenshot(_FlakyScreenshot):
    """模拟 MuMu IPC 截图失败，前两次抛裸 NemuIpcError。"""

    def screenshot(self) -> Any:
        self.calls += 1
        if self.calls <= self.failures:
            raise NemuIpcError("nemu_capture_display screenshot failed, error code=1")
        return self.sentinel


class _BadScreenshot(_FlakyScreenshot):
    """抛出与连接无关异常的截图实现。"""

    def screenshot(self) -> Any:
        raise ValueError("Invalid screen size: foo")


class TestReadRetry(unittest.TestCase):
    """测试读操作的重连重试行为。"""

    def setUp(self) -> None:
        self._original_retry = conf().device.retry
        conf().device.retry = DeviceRetryConfig()

    def tearDown(self) -> None:
        conf().device.retry = self._original_retry

    def _make_device(self, screenshot: _FlakyScreenshot) -> Device:
        device = Device()
        device._screenshot = screenshot
        return device

    def test_screenshot_raw_retries_then_succeeds(self) -> None:
        fake = _FlakyScreenshot(failures=2)
        device = self._make_device(fake)
        with (
            patch.object(device, "stop") as mock_stop,
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            result = device.screenshot_raw()
        self.assertIs(result, fake.sentinel)
        self.assertEqual(fake.calls, 3)
        self.assertEqual(mock_stop.call_count, 2)
        self.assertEqual(mock_start.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_called_with(1.0)

    def test_screenshot_raw_exhausts_attempts(self) -> None:
        fake = _FlakyScreenshot(failures=99)
        device = self._make_device(fake)
        with (
            patch.object(device, "stop") as mock_stop,
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            with self.assertRaises(DeviceNotReadyError):
                device.screenshot_raw()
        self.assertEqual(fake.calls, 3)
        self.assertEqual(mock_stop.call_count, 2)
        self.assertEqual(mock_start.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_nemu_ipc_error_retried_after_translation(self) -> None:
        fake = _NemuFailingScreenshot(failures=2)
        device = self._make_device(fake)
        with (
            patch.object(device, "stop") as mock_stop,
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            result = device.screenshot_raw()
        self.assertIs(result, fake.sentinel)
        self.assertEqual(fake.calls, 3)
        self.assertEqual(mock_stop.call_count, 2)
        self.assertEqual(mock_start.call_count, 2)
        self.assertEqual(mock_sleep.call_count, 2)

    def test_unrelated_error_not_retried(self) -> None:
        device = self._make_device(_BadScreenshot(failures=0))
        with (
            patch.object(device, "stop") as mock_stop,
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            with self.assertRaises(ValueError):
                device.screenshot_raw()
        mock_stop.assert_not_called()
        mock_start.assert_not_called()
        mock_sleep.assert_not_called()

    def test_click_not_retried(self) -> None:
        device = Device()
        device._scaler.physical_resolution = Size(720, 1280)
        device._scaler.logic_resolution = Size(720, 1280)
        touch = _FlakyTouch()
        device.setup(screenshot=_FlakyScreenshot(failures=0), touch=touch)
        with (
            patch.object(device, "stop") as mock_stop,
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            with self.assertRaises(DeviceNotReadyError):
                device.click(10, 20)
        self.assertEqual(touch.calls, 1)
        mock_stop.assert_not_called()
        mock_start.assert_not_called()
        mock_sleep.assert_not_called()

    def test_current_package_retries(self) -> None:
        device = AndroidDevice()
        fake_commands = _FlakyCommands()
        device.commands = fake_commands
        with (
            patch.object(device, "stop") as mock_stop,
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            result = device.current_package()
        self.assertEqual(result, "com.example.game")
        self.assertEqual(fake_commands.calls, 2)
        mock_stop.assert_called_once()
        mock_start.assert_called_once()
        mock_sleep.assert_called_once_with(1.0)

    def test_reconnect_failure_aborts(self) -> None:
        fake = _FlakyScreenshot(failures=99)
        device = self._make_device(fake)
        with (
            patch.object(
                device, "stop", side_effect=DeviceConnectRefusedError("127.0.0.1:5555")
            ),
            patch.object(device, "start") as mock_start,
            patch("kotonebot.sleep") as mock_sleep,
        ):
            with self.assertRaises(DeviceConnectRefusedError):
                device.screenshot_raw()
        self.assertEqual(fake.calls, 1)
        mock_start.assert_not_called()
        mock_sleep.assert_not_called()


class TestDeviceRetryConfig(unittest.TestCase):
    """测试重试配置的默认值与校验。"""

    def test_defaults(self) -> None:
        config = DeviceRetryConfig()
        self.assertEqual(config.attempts, 3)
        self.assertEqual(config.interval, 1.0)

    def test_invalid_values_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DeviceRetryConfig(attempts=0)
        with self.assertRaises(ValueError):
            DeviceRetryConfig(interval=-1.0)


if __name__ == "__main__":
    unittest.main()
