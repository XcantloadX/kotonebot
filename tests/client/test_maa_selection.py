"""Maa 方法选择调试日志的单测（纯函数，不碰真实设备与动态库）。"""

import unittest

from kotonebot.client.maa_backend._selection import (
    _adb_input_name,
    _parse_fastest,
    _win32_input_name,
    capture_maa_logs,
    report_adb_selection,
)


class TestParseFastest(unittest.TestCase):
    def test_winner_parsed(self):
        text = (
            '[2026-10-05 14:53:16.707][INF][Px55200][Tx2034][ScreencapAgent.cpp][L237]'
            '[MaaNS::CtrlUnitNs::ScreencapAgent::speed_test] Testing Encode \n'
            '[2026-10-05 14:53:19.351][INF][Px55200][Tx2034][ScreencapAgent.cpp][L251]'
            '[MaaNS::CtrlUnitNs::ScreencapAgent::speed_test] The fastest method is RawWithGzip [cost=434ms] \n'
        )
        self.assertEqual(_parse_fastest(text), 'RawWithGzip')

    def test_winner_with_underscores_parsed(self):
        text = (
            '[2026-10-05 14:53:19.351][INF][Px55200][Tx2034][Win32ControlUnitMgr.cpp][L223]'
            '[MaaNS::CtrlUnitNs::Win32ControlUnitMgr::speed_test] '
            'The fastest method is DXGI_DesktopDup_Window [cost=12ms] \n'
        )
        self.assertEqual(_parse_fastest(text), 'DXGI_DesktopDup_Window')

    def test_missing_line_returns_none(self):
        self.assertIsNone(_parse_fastest('some unrelated log'))


class TestInputNames(unittest.TestCase):
    def test_adb_priority_extras_first(self):
        from maa.define import MaaAdbInputMethodEnum

        mask = int(MaaAdbInputMethodEnum.EmulatorExtras) | int(MaaAdbInputMethodEnum.Maatouch)
        self.assertEqual(_adb_input_name(mask), 'EmulatorExtras')

    def test_adb_falls_back_without_extras(self):
        from maa.define import MaaAdbInputMethodEnum

        mask = int(MaaAdbInputMethodEnum.AdbShell)
        self.assertEqual(_adb_input_name(mask), 'AdbShell')
        self.assertEqual(_adb_input_name(0), 'unknown')

    def test_win32_names_and_defaults(self):
        from maa.define import MaaWin32InputMethodEnum

        self.assertEqual(
            _win32_input_name(int(MaaWin32InputMethodEnum.PostMessage), default='Seize'),
            'PostMessage',
        )
        self.assertEqual(_win32_input_name(None, default='Seize'), 'Seize')
        self.assertEqual(_win32_input_name(9999, default='Seize'), 'unknown(9999)')


class TestReportAdbSelection(unittest.TestCase):
    def test_debug_line_contains_selection(self):
        from maa.define import MaaAdbInputMethodEnum

        text = 'The fastest method is MuMuPlayerExtras [cost=45ms] \n'
        mask = int(MaaAdbInputMethodEnum.EmulatorExtras)
        with self.assertLogs('kotonebot.client.maa_backend._selection', level='DEBUG') as logs:
            report_adb_selection(text, address='127.0.0.1:16384', input_methods=mask)
        self.assertEqual(len(logs.output), 1)
        line = logs.output[0]
        self.assertIn('address=127.0.0.1:16384', line)
        self.assertIn('screencap=MuMuPlayerExtras', line)
        self.assertIn('input=EmulatorExtras', line)

    def test_unknown_when_no_winner(self):
        with self.assertLogs('kotonebot.client.maa_backend._selection', level='DEBUG') as logs:
            report_adb_selection('', address='127.0.0.1:16384', input_methods=0)
        self.assertIn('screencap=unknown', logs.output[0])


class TestCaptureMaaLogs(unittest.TestCase):
    def test_body_runs_without_maa_activity(self):
        ran = []
        with capture_maa_logs() as capture:
            ran.append(True)
        self.assertEqual(ran, [True])
        # Maa 会把 set_log_dir 本身记一行，文本非空但不含胜选行。
        self.assertIsInstance(capture.text(), str)
        self.assertIsNone(_parse_fastest(capture.text()))

    def test_body_exception_propagates(self):
        class Boom(Exception):
            pass

        with self.assertRaises(Boom):
            with capture_maa_logs():
                raise Boom()


if __name__ == '__main__':
    unittest.main()
