import importlib
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import pkgutil

def create_cv2_mock():
    cv2_mock = MagicMock()
    cv2_mock.typing = MagicMock()
    sys.modules['cv2'] = cv2_mock
    sys.modules['cv2.typing'] = cv2_mock.typing
    return cv2_mock

def create_skimage_mock():
    skimage_mock = MagicMock()
    skimage_mock.metrics = MagicMock()
    sys.modules['skimage'] = skimage_mock
    sys.modules['skimage.metrics'] = skimage_mock.metrics
    return skimage_mock

def create_adbutils_mock():
    adbutils_mock = MagicMock()
    adbutils_mock._utils = MagicMock()
    adbutils_mock._device = MagicMock()
    sys.modules['adbutils'] = adbutils_mock
    sys.modules['adbutils._utils'] = adbutils_mock._utils
    sys.modules['adbutils._device'] = adbutils_mock._device
    return adbutils_mock

class TestImportAll(unittest.TestCase):
    def setUp(self):
        self.cv2_mock = create_cv2_mock()
        self.skimage_mock = create_skimage_mock()
        self.adbutils_mock = create_adbutils_mock()

    def tearDown(self):
        if 'cv2' in sys.modules:
            del sys.modules['cv2']
        if 'cv2.typing' in sys.modules:
            del sys.modules['cv2.typing']
        if 'skimage' in sys.modules:
            del sys.modules['skimage']
        if 'skimage.metrics' in sys.modules:
            del sys.modules['skimage.metrics']
        if 'adbutils' in sys.modules:
            del sys.modules['adbutils']
        if 'adbutils._utils' in sys.modules:
            del sys.modules['adbutils._utils']
        if 'adbutils._device' in sys.modules:
            del sys.modules['adbutils._device']

    def test_import_all_kotonebot_modules(self):
        # A simple test to check if all modules can be imported
        # This is not a complete test, but it's a start
        with patch.dict('sys.modules', {
            'av': MagicMock(),
            'uvicorn': MagicMock(),
            'fastapi': MagicMock(),
            'thefuzz': MagicMock(),
            'psutil': MagicMock(),
            'win32ui': MagicMock(),
            'win32gui': MagicMock(),
            'ahk': MagicMock(),
            'uiautomator2': MagicMock(),
            'win11toast': MagicMock(),
            'ctypes': MagicMock(),
            'ctypes.wintypes': MagicMock(),
            'win32comext': MagicMock(),
            'win32comext.shell': MagicMock(),
            'pythoncom': MagicMock(),
            'winreg': MagicMock(),
            'wx': MagicMock(),
        }), patch('kotonebot.util.is_windows', return_value=True):
            import kotonebot
            import kotonebot.backend
            import kotonebot.backend.bot
            import kotonebot.backend.color
            import kotonebot.backend.context
            import kotonebot.backend.core
            # import kotonebot.backend.debug
            import kotonebot.backend.dispatch
            import kotonebot.backend.flow_controller
            import kotonebot.backend.image
            import kotonebot.backend.loop
            import kotonebot.backend.ocr
            import kotonebot.backend.preprocessor
            import kotonebot.client
            import kotonebot.client.device
            import kotonebot.client.fast_screenshot
            import kotonebot.client.protocol
            import kotonebot.client.registration
            # Test exports from kotonebot.client
            self.assertTrue(hasattr(kotonebot.client, 'Device'))
            self.assertTrue(hasattr(kotonebot.client, 'DeviceImpl'))

            import kotonebot.client.host
            # Test exports from kotonebot.client.host
            self.assertTrue(hasattr(kotonebot.client.host, 'HostProtocol'))
            self.assertTrue(hasattr(kotonebot.client.host, 'Instance'))
            self.assertTrue(hasattr(kotonebot.client.host, 'AdbHostConfig'))
            self.assertTrue(hasattr(kotonebot.client.host, 'WindowsHostConfig'))
            self.assertTrue(hasattr(kotonebot.client.host, 'RemoteWindowsHostConfig'))
            self.assertTrue(hasattr(kotonebot.client.host, 'CustomInstance'))
            self.assertTrue(hasattr(kotonebot.client.host, 'create_custom'))
            self.assertTrue(hasattr(kotonebot.client.host, 'Mumu12Host'))
            self.assertTrue(hasattr(kotonebot.client.host, 'Mumu12Instance'))
            self.assertTrue(hasattr(kotonebot.client.host, 'Mumu12V5Host'))
            self.assertTrue(hasattr(kotonebot.client.host, 'Mumu12V5Instance'))
            self.assertTrue(hasattr(kotonebot.client.host, 'LeidianHost'))
            self.assertTrue(hasattr(kotonebot.client.host, 'LeidianInstance'))

            import kotonebot.client.implements
            # Test exports from kotonebot.client.implements
            self.assertTrue(hasattr(kotonebot.client.implements, 'WindowsImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'WindowsImplConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'RemoteWindowsImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'RemoteWindowsImplConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'RemoteWindowsServer'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'NemuIpcImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'NemuIpcImplConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'ExternalRendererIpc'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'AdbImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'AdbImplConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'AdbRawImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'UiAutomator2Impl'))

            import kotonebot.client.implements.nemu_ipc
            # Test exports from kotonebot.client.implements.nemu_ipc
            self.assertTrue(hasattr(kotonebot.client.implements.nemu_ipc, 'ExternalRendererIpc'))
            self.assertTrue(hasattr(kotonebot.client.implements.nemu_ipc, 'NemuIpcImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements.nemu_ipc, 'NemuIpcImplConfig'))

            import kotonebot.config
            import kotonebot.config.base_config
            import kotonebot.config.manager
            import kotonebot.errors
            import kotonebot.logging
            import kotonebot.primitives
            import kotonebot.tools
            import kotonebot.ui
            import kotonebot.util

    def test_dynamic_import_all(self):
        with patch.dict('sys.modules', {
            'av': MagicMock(),
            'uvicorn': MagicMock(),
            'fastapi': MagicMock(),
            'thefuzz': MagicMock(),
            'psutil': MagicMock(),
            'win32ui': MagicMock(),
            'win32gui': MagicMock(),
            'ahk': MagicMock(),
            'uiautomator2': MagicMock(),
            'win11toast': MagicMock(),
            'ctypes': MagicMock(),
            'ctypes.wintypes': MagicMock(),
            'win32comext': MagicMock(),
            'win32comext.shell': MagicMock(),
            'pythoncom': MagicMock(),
            'winreg': MagicMock(),
            'wx': MagicMock(),
        }):
            import kotonebot
            for loader, name, is_pkg in pkgutil.walk_packages(kotonebot.__path__, kotonebot.__name__ + '.'):
                if 'kotonebot.backend.debug' in name or 'kotonebot.tools' in name:
                    continue
                try:
                    importlib.import_module(name)
                except ImportError as e:
                    # some modules are windows only
                    if 'only available on Windows' not in str(e):
                        raise

    def test_optional_deps(self):
        # Clear sys.modules for adbutils to ensure fresh import
        for mod_name in ['adbutils', 'adbutils._utils', 'adbutils._device']:
            if mod_name in sys.modules:
                del sys.modules[mod_name]

        # Test optional dependencies
        with patch.dict('sys.modules', {'psutil': None}):
            with self.assertRaises(ImportError):
                importlib.import_module('kotonebot.client.host.adb_common')

        with patch.dict('sys.modules', {'win32ui': None, 'win32gui': None, 'ahk': None}):
            with self.assertRaises(ImportError):
                importlib.import_module('kotonebot.client.implements.windows')

        with patch.dict('sys.modules', {'uiautomator2': None}):
            with self.assertRaises(ImportError):
                importlib.import_module('kotonebot.client.implements.uiautomator2')

    def test_windows_only_imports(self):
        # Clear sys.modules for all kotonebot modules to ensure fresh import
        # This is crucial for patches to take effect on module-level imports
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith('kotonebot'):
                del sys.modules[mod_name]

        # Mock non-windows environment
        with patch('kotonebot.util.is_windows', return_value=False):
            # These should fail on non-windows
            with self.assertRaisesRegex(ImportError, 'only available on Windows'):
                importlib.import_module('kotonebot.interop.win.task_dialog')
            with self.assertRaisesRegex(ImportError, 'only available on Windows'):
                importlib.import_module('kotonebot.client.implements.windows')
            with self.assertRaisesRegex(ImportError, 'only available on Windows'):
                importlib.import_module('kotonebot.client.implements.remote_windows')
            with self.assertRaisesRegex(ImportError, 'only available on Windows'):
                importlib.import_module('kotonebot.client.implements.nemu_ipc')
            with self.assertRaisesRegex(ImportError, 'only available on Windows'):
                importlib.import_module('kotonebot.client.host.mumu12_host')
            with self.assertRaisesRegex(ImportError, 'only available on Windows'):
                importlib.import_module('kotonebot.client.host.leidian_host')

        # Mock windows environment
        with patch('kotonebot.util.is_windows', return_value=True):
            # These should succeed on windows (mocking dependencies)
            with patch.dict('sys.modules', {
                'win11toast': MagicMock(),
                'ctypes': MagicMock(),
                'ctypes.wintypes': MagicMock(),
                'win32comext': MagicMock(),
                'win32comext.shell': MagicMock(),
                'pythoncom': MagicMock(),
                'winreg': MagicMock(),
                'win32ui': MagicMock(),
                'win32gui': MagicMock(),
                'ahk': MagicMock(),
            }):
                importlib.import_module('kotonebot.interop.win.task_dialog')
                importlib.import_module('kotonebot.client.implements.windows')
                importlib.import_module('kotonebot.client.implements.remote_windows')
                importlib.import_module('kotonebot.client.implements.nemu_ipc')

if __name__ == '__main__':
    unittest.main()