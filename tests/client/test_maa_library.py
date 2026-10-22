"""Maa 动态库按需初始化的单测（使用真实 maafw 安装，仅验证 open 幂等）。"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class TestEnsureMaaLibrary(unittest.TestCase):
    def test_ensure_is_idempotent(self):
        from kotonebot.client.maa_backend._library import ensure_maa_library

        expected = {
            'win32': 'MaaFramework.dll',
            'darwin': 'libMaaFramework.dylib',
        }.get(sys.platform, 'libMaaFramework.so')
        first = ensure_maa_library()
        self.assertTrue((first / expected).is_file())
        second = ensure_maa_library()
        self.assertEqual(first, second)
        self.assertIsInstance(second, Path)

    def test_missing_library_raises(self):
        import maa
        from kotonebot.client.maa_backend.errors import MaaLibraryNotFoundError

        with patch.object(maa, '__file__', r'C:\no-such-dir\maa\__init__.py'):
            from kotonebot.client.maa_backend._library import ensure_maa_library

            with self.assertRaises(MaaLibraryNotFoundError) as ctx:
                ensure_maa_library()
        self.assertIn('MaaFramework native library not found', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
