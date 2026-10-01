"""设备异常统一转译的单测。"""

import unittest

from adbutils import AdbTimeout
from adbutils.errors import AdbError

from kotonebot.client._translate import translate_device_error
from kotonebot.client.device import device_operation
from kotonebot.client.implements.nemu_ipc.nemu_ipc import (
    NemuIpcDisplayNotFoundError,
    NemuIpcError,
)
from kotonebot.errors import (
    DeviceConnectRefusedError,
    DeviceConnectTimeoutError,
    DeviceConnectionError,
    DeviceNotReadyError,
)


class TestTranslateDeviceError(unittest.TestCase):
    """测试 translate_device_error 的映射关系。"""

    def test_connection_error_passthrough(self) -> None:
        original = DeviceNotReadyError("offline")
        self.assertIs(translate_device_error(original), original)

    def test_nemu_ipc_error_to_not_ready(self) -> None:
        translated = translate_device_error(NemuIpcError("nemu_capture_display failed"))
        self.assertIsInstance(translated, DeviceNotReadyError)

    def test_nemu_display_not_found_not_translated(self) -> None:
        self.assertIsNone(translate_device_error(NemuIpcDisplayNotFoundError("pkg", 1.0)))

    def test_adb_error_variants_to_not_ready(self) -> None:
        messages = [
            "device offline",
            "closed",
            "device '127.0.0.1:5555' not found",
            "screencap error",
            "adb read timeout",
            "('wm size output unexpected', 'cmd: Failure calling service window: Broken pipe (32)')",
        ]
        for message in messages:
            with self.subTest(message=message):
                translated = translate_device_error(AdbError(message))
                self.assertIsInstance(translated, DeviceNotReadyError)

    def test_adb_timeout_to_timeout_error(self) -> None:
        translated = translate_device_error(AdbTimeout("timed out"))
        self.assertIsInstance(translated, DeviceConnectTimeoutError)

    def test_connection_refused_to_refused(self) -> None:
        translated = translate_device_error(ConnectionRefusedError(10061, "拒绝"))
        self.assertIsInstance(translated, DeviceConnectRefusedError)

    def test_connection_reset_to_not_ready(self) -> None:
        for error in (
            ConnectionResetError(10054, "强迫关闭"),
            ConnectionAbortedError("aborted"),
            BrokenPipeError(32, "Broken pipe"),
        ):
            with self.subTest(error=repr(error)):
                self.assertIsInstance(translate_device_error(error), DeviceNotReadyError)

    def test_value_error_cannot_connect_to_refused(self) -> None:
        translated = translate_device_error(
            ValueError("cannot connect to 127.0.0.1:5555: 由于目标计算机积极拒绝，无法连接。 (10061)")
        )
        self.assertIsInstance(translated, DeviceConnectRefusedError)
        assert isinstance(translated, DeviceConnectRefusedError)
        self.assertIn("127.0.0.1:5555", str(translated))

    def test_value_error_device_not_found_to_not_ready(self) -> None:
        translated = translate_device_error(ValueError("Device 127.0.0.1:5555 not found"))
        self.assertIsInstance(translated, DeviceNotReadyError)

    def test_value_error_config_not_translated(self) -> None:
        self.assertIsNone(translate_device_error(ValueError("Neither adb_serial nor adb_port is set.")))
        self.assertIsNone(translate_device_error(ValueError("Invalid screen size: foo")))

    def test_runtime_lifecycle_text_not_translated(self) -> None:
        # 各实现已在源头抛出 DeviceNotReadyError，裸 RuntimeError 不再按文本匹配转译
        self.assertIsNone(translate_device_error(RuntimeError("NemuIpcImpl lifecycle is not started.")))

    def test_unrelated_error_not_translated(self) -> None:
        self.assertIsNone(translate_device_error(RuntimeError("boom")))
        self.assertIsNone(translate_device_error(KeyError("key")))


class TestDeviceOperation(unittest.TestCase):
    """测试 device_operation 装饰器的转译与透传行为。"""

    def test_wraps_adb_error_with_cause(self) -> None:
        @device_operation
        def _op() -> None:
            raise AdbError("device offline")

        with self.assertRaises(DeviceNotReadyError) as ctx:
            _op()
        self.assertIsInstance(ctx.exception.__cause__, AdbError)

    def test_passthrough_connection_error(self) -> None:
        original = DeviceNotReadyError("offline")

        @device_operation
        def _op() -> None:
            raise original

        with self.assertRaises(DeviceConnectionError) as ctx:
            _op()
        self.assertIs(ctx.exception, original)

    def test_passthrough_unrelated_error(self) -> None:
        @device_operation
        def _op() -> None:
            raise ValueError("Invalid screen size: foo")

        with self.assertRaises(ValueError):
            _op()


if __name__ == "__main__":
    unittest.main()
