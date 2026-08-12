import importlib
import unittest
from unittest.mock import patch, MagicMock
import sys
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
    adbutils_mock.errors = MagicMock()
    sys.modules['adbutils'] = adbutils_mock
    sys.modules['adbutils._utils'] = adbutils_mock._utils
    sys.modules['adbutils._device'] = adbutils_mock._device
    sys.modules['adbutils.errors'] = adbutils_mock.errors
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
        if 'adbutils.errors' in sys.modules:
            del sys.modules['adbutils.errors']

    def test_import_all_kotonebot_modules(self):
        # A simple test to check if all modules can be imported
        # This is not a complete test, but it's a start
        with patch.dict('sys.modules', {
            'av': MagicMock(),
            'uvicorn': MagicMock(),
            'fastapi': MagicMock(),
            'fastapi.staticfiles': MagicMock(),
            'fastapi.responses': MagicMock(),
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
            import kotonebot.backend.color
            import kotonebot.backend.context
            import kotonebot.backend.core
            import kotonebot.backend.debug
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
            self.assertTrue(hasattr(kotonebot.client.implements, 'NemuIpcImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'NemuIpcImplConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'ExternalRendererIpc'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'AdbImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'AdbImplConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'ScrcpyImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'ScrcpyConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'VirtualDisplayConfig'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'ScrcpySession'))
            self.assertTrue(hasattr(kotonebot.client.implements, 'UiAutomator2Impl'))

            import kotonebot.client.implements.nemu_ipc
            # Test exports from kotonebot.client.implements.nemu_ipc
            self.assertTrue(hasattr(kotonebot.client.implements.nemu_ipc, 'ExternalRendererIpc'))
            self.assertTrue(hasattr(kotonebot.client.implements.nemu_ipc, 'NemuIpcImpl'))
            self.assertTrue(hasattr(kotonebot.client.implements.nemu_ipc, 'NemuIpcImplConfig'))

            import kotonebot.config
            import kotonebot.config.config
            import kotonebot.errors
            import kotonebot.logging
            import kotonebot.primitives
            import kotonebot.devtools
            import kotonebot.ui
            import kotonebot.util

    def test_dynamic_import_all(self):
        with patch.dict('sys.modules', {
            'av': MagicMock(),
            'uvicorn': MagicMock(),
            'fastapi': MagicMock(),
            'fastapi.staticfiles': MagicMock(),
            'fastapi.responses': MagicMock(),
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
                if 'kotonebot.tools' in name:
                    continue
                try:
                    importlib.import_module(name)
                except ImportError as e:
                    # some modules are windows only
                    if 'only available on Windows' not in str(e):
                        raise

    def test_optional_deps(self):
        # 保存待清除的模块，测试结束后恢复原状，避免污染后续测试
        saved_modules: dict[str, object] = {}
        for mod_name in [
            'adbutils',
            'adbutils._utils',
            'adbutils._device',
            'adbutils.errors',
            'kotonebot.client.host.adb_common',
            'kotonebot.client.implements.windows',
            'kotonebot.client.implements.uiautomator2',
        ]:
            if mod_name in sys.modules:
                saved_modules[mod_name] = sys.modules[mod_name]
                del sys.modules[mod_name]

        # Test optional dependencies
        try:
            with patch.dict('sys.modules', {'adbutils': None, 'adbutils._device': None, 'adbutils.errors': None}):
                with self.assertRaises(ImportError):
                    importlib.import_module('kotonebot.client.host.adb_common')

            with patch.dict('sys.modules', {'uiautomator2': None}):
                with self.assertRaises(ImportError):
                    importlib.import_module('kotonebot.client.implements.uiautomator2')
        finally:
            sys.modules.update(saved_modules)

    def test_windows_only_imports(self):
        # 保存并移除 sys.modules 中所有 kotonebot 模块，确保干净导入；
        # 测试结束后必须恢复原模块，否则后续测试持有的类引用会与重新导入的
        # 模块（如 conf() 的 ContextVar、Context 的 _c）产生双实例，导致状态泄漏。
        saved_modules: dict[str, object] = {}
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith('kotonebot'):
                saved_modules[mod_name] = sys.modules[mod_name]
                del sys.modules[mod_name]

        try:
            # Mock non-windows environment
            with patch('kotonebot.util.is_windows', return_value=False):
                from kotonebot.client.implements.scrcpy import ScrcpyConfig, ScrcpyImpl

                with self.assertRaisesRegex(NotImplementedError, 'only available on Windows'):
                    ScrcpyImpl(
                        MagicMock(serial='127.0.0.1:5555', sync=MagicMock(), shell=MagicMock()),
                        ScrcpyConfig(server_jar_path='scrcpy-server.jar', server_version='3.3.1'),
                    )

            # Mock windows environment
            with patch('kotonebot.util.is_windows', return_value=True):
                # These should succeed on windows (mocking dependencies)
                with patch.dict('sys.modules', {
                    'av': MagicMock(),
                    'win11toast': MagicMock(),
                    'ctypes': MagicMock(),
                    'ctypes.wintypes': MagicMock(),
                    'win32comext': MagicMock(),
                    'win32comext.shell': MagicMock(),
                    'pythoncom': MagicMock(),
                    'winreg': MagicMock(),
                    'win32ui': MagicMock(),
                    'win32gui': MagicMock(),
                    'win32api': MagicMock(),
                    'win32con': MagicMock(),
                    'ahk': MagicMock(),
                }):
                    importlib.import_module('kotonebot.interop.win.task_dialog')
                    importlib.import_module('kotonebot.client.implements.windows')
                    importlib.import_module('kotonebot.client.implements.nemu_ipc')
                    importlib.import_module('kotonebot.client.implements.scrcpy')
        finally:
            sys.modules.update(saved_modules)

if __name__ == '__main__':
    unittest.main()
