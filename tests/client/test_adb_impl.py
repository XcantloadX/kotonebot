import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image
from adbutils.errors import AdbError

from kotonebot.client.host.adb_common import CommonAdbCreateDeviceMixin
from kotonebot.client.host.protocol import AdbHostConfig
from kotonebot.client.implements.adb import AdbImpl


class FakeAdbInstance(CommonAdbCreateDeviceMixin):
    def __init__(self) -> None:
        super().__init__()
        self.adb_ip = '127.0.0.1'
        self.adb_port = 5555
        self.adb_name = None
        self.adb_serial = None


class TestAdbImpl(unittest.TestCase):
    def _mock_connection(self) -> MagicMock:
        connection = MagicMock()
        image = np.zeros((2, 3, 3), dtype=np.uint8)
        connection.screenshot.return_value = Image.fromarray(image)
        return connection

    def test_screenshot_uses_display_id(self):
        connection = self._mock_connection()
        impl = AdbImpl(connection, display_id=2)

        image = impl.screenshot()

        connection.screenshot.assert_called_once_with(display_id=2, error_ok=False)
        self.assertEqual(image.shape, (2, 3, 3))

    def test_screenshot_error_mentions_display_id(self):
        connection = self._mock_connection()
        connection.screenshot.side_effect = AdbError('capture failed')
        impl = AdbImpl(connection, display_id=3)

        with self.assertRaisesRegex(AdbError, 'display_id=3'):
            impl.screenshot()

    def test_screen_size_uses_display_specific_wm_size_and_landscape_sorting(self):
        connection = self._mock_connection()
        connection.shell.return_value = 'Physical size: 1080x1920'
        impl = AdbImpl(connection, display_id=4)

        with patch.object(impl, 'detect_orientation', return_value='landscape'):
            size = impl.screen_size

        connection.shell.assert_called_once_with(['wm', 'size', '-d', '4'])
        self.assertEqual(size, (1920, 1080))

    def test_invalid_screen_size_mentions_display_id(self):
        connection = self._mock_connection()
        connection.shell.return_value = 'unexpected output'
        impl = AdbImpl(connection, display_id=4)

        with self.assertRaisesRegex(ValueError, 'display_id=4'):
            _ = impl.screen_size

    def test_click_keeps_legacy_command_for_default_display(self):
        connection = self._mock_connection()
        impl = AdbImpl(connection)

        impl.click(10, 20)

        connection.shell.assert_called_once_with(['input', 'tap', '10', '20'])

    def test_click_uses_display_flag(self):
        connection = self._mock_connection()
        impl = AdbImpl(connection, display_id=1)

        impl.click(10, 20)

        connection.shell.assert_called_once_with(['input', '-d', '1', 'tap', '10', '20'])

    def test_swipe_places_display_flag_after_source(self):
        connection = self._mock_connection()
        impl = AdbImpl(connection, display_id=1)

        impl.swipe(1, 2, 3, 4)

        connection.shell.assert_called_once_with(['input', 'touchscreen', '-d', '1', 'swipe', '1', '2', '3', '4'])


class TestCommonAdbCreateDeviceMixin(unittest.TestCase):
    def test_create_device_passes_display_id_to_adb_impl(self):
        instance = FakeAdbInstance()
        config = AdbHostConfig(timeout=5, display_id=7)
        connection = object()
        device = MagicMock()
        impl = MagicMock()

        with (
            patch('kotonebot.client.host.adb_common.connect_adb', return_value=connection),
            patch('kotonebot.client.host.adb_common.AndroidDevice', return_value=device),
            patch('kotonebot.client.implements.adb.AdbImpl', return_value=impl) as mock_adb_impl,
        ):
            result = instance.create_device('adb', config)

        mock_adb_impl.assert_called_once_with(connection, display_id=7)
        device.setup.assert_called_once_with(screenshot=impl, touch=impl, commands=impl)
        self.assertIs(result, device)


if __name__ == '__main__':
    unittest.main()
