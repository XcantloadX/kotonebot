import unittest

from kotonebot.interop.window import (
    WindowInfo,
    WindowQuery,
    WindowsNativeQuery,
    MacOSNativeQuery,
    UnsupportedQueryFieldError,
)
from kotonebot.interop.window.model import match_common
from kotonebot.interop.window.windows import WindowsWindowBackend
from kotonebot.interop.window.macos import MacOSWindowBackend
from kotonebot.primitives import Rect


class TestMatchCommonFields(unittest.TestCase):
    def setUp(self):
        self.info = WindowInfo(
            id=1,
            platform="windows",
            title="Game Window",
            app_name="PlayCover",
            process_id=100,
            bounds=Rect(0, 0, 800, 600),
            is_visible=True,
        )

    def test_exact_title(self):
        self.assertTrue(match_common(self.info, WindowQuery(title="Game Window")))

    def test_title_contains(self):
        self.assertTrue(match_common(self.info, WindowQuery(title_contains="Game")))

    def test_app_name_contains(self):
        self.assertTrue(match_common(self.info, WindowQuery(app_name_contains="Play")))

    def test_wrong_title(self):
        self.assertFalse(match_common(self.info, WindowQuery(title="Other")))

    def test_wrong_process_id(self):
        self.assertFalse(match_common(self.info, WindowQuery(process_id=999)))


class TestBackendQueryValidation(unittest.TestCase):
    def test_windows_backend_rejects_macos_native_query(self):
        backend = WindowsWindowBackend()
        query = WindowQuery(native=MacOSNativeQuery(bundle_id="io.example.app"))
        with self.assertRaises(UnsupportedQueryFieldError):
            backend.validate_query(query)

    def test_macos_backend_rejects_windows_native_query(self):
        backend = MacOSWindowBackend()
        query = WindowQuery(native=WindowsNativeQuery(executable="Game.exe"))
        with self.assertRaises(UnsupportedQueryFieldError):
            backend.validate_query(query)


if __name__ == "__main__":
    unittest.main()
