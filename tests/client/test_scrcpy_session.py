import io
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from kotonebot.client.implements.scrcpy import ScrcpyConfig, ScrcpySession, VirtualDisplayConfig
from kotonebot.client.implements.scrcpy.frame_store import LatestFrameStore


class FakeThread:
    def __init__(self, *args, **kwargs) -> None:
        self.started = False

    def start(self) -> None:
        self.started = True

    def join(self, timeout=None) -> None:
        return

    def is_alive(self) -> bool:
        return False


class TestLatestFrameStore(unittest.TestCase):
    def test_store_supports_multiple_local_consumers(self):
        store = LatestFrameStore()
        calls: list[tuple[str, int]] = []

        token1 = store.subscribe(lambda snapshot: calls.append(('a', snapshot.seq)))
        token2 = store.subscribe(lambda snapshot: calls.append(('b', snapshot.seq)))

        store.update(np.zeros((2, 3, 3), dtype=np.uint8))

        snapshot = store.get_latest_frame()
        assert snapshot is not None
        self.assertEqual((snapshot.width, snapshot.height, snapshot.seq), (3, 2, 1))
        self.assertEqual(calls, [('a', 1), ('b', 1)])

        store.unsubscribe(token1)
        store.unsubscribe(token2)

    def test_clear_keeps_subscribers(self):
        store = LatestFrameStore()
        calls: list[int] = []
        store.subscribe(lambda snapshot: calls.append(snapshot.seq))

        store.clear()
        store.update(np.zeros((1, 1, 3), dtype=np.uint8))

        self.assertEqual(calls, [1])


class TestScrcpySession(unittest.TestCase):
    def _connection(self) -> MagicMock:
        connection = MagicMock()
        connection.serial = '127.0.0.1:5555'
        connection.sync = MagicMock()
        return connection

    def _config(self, **kwargs) -> ScrcpyConfig:
        return ScrcpyConfig(server_jar_path=__file__, server_version='3.3.1', **kwargs)

    def test_auto_scid_is_generated_when_not_provided(self):
        session = ScrcpySession(self._connection(), self._config())

        with (
            patch('kotonebot.client.implements.scrcpy.session.subprocess.Popen', return_value=MagicMock(stdout=io.StringIO(''), poll=lambda: None)),
            patch('kotonebot.client.implements.scrcpy.session.threading.Thread', side_effect=lambda *args, **kwargs: FakeThread()),
            patch.object(session, '_push_server'),
            patch.object(session, '_setup_forward', return_value=27183),
            patch.object(session, '_wait_for_socket_ready'),
            patch.object(session.video, 'start'),
            patch.object(session.video, 'wait_until_ready'),
            patch.object(session, '_connect_forward_socket', side_effect=[MagicMock(), MagicMock()]),
        ):
            session.start()

        self.assertNotEqual(session.scid, -1)
        self.assertIsInstance(session.scid, int)

    def test_start_and_stop_use_reference_count(self):
        session = ScrcpySession(self._connection(), self._config(scid=123))

        with (
            patch('kotonebot.client.implements.scrcpy.session.subprocess.Popen', return_value=MagicMock(stdout=io.StringIO(''), poll=lambda: None)),
            patch('kotonebot.client.implements.scrcpy.session.threading.Thread', side_effect=lambda *args, **kwargs: FakeThread()),
            patch.object(session, '_push_server'),
            patch.object(session, '_setup_forward', return_value=27183),
            patch.object(session, '_wait_for_socket_ready'),
            patch.object(session.video, 'start'),
            patch.object(session.video, 'wait_until_ready'),
            patch.object(session, '_connect_forward_socket', side_effect=[MagicMock(), MagicMock()]),
            patch.object(session, '_remove_forward') as mock_remove_forward,
        ):
            session.start()
            session.start()
            self.assertEqual(session.start_count, 2)
            session.stop()
            self.assertEqual(session.start_count, 1)
            mock_remove_forward.assert_not_called()
            session.stop()
            mock_remove_forward.assert_called_once_with()

    def test_aggressive_cleanup_kills_all_scrcpy_processes(self):
        session = ScrcpySession(self._connection(), self._config(cleanup_strategy='aggressive', scid=456))

        with (
            patch('kotonebot.client.implements.scrcpy.session.subprocess.Popen', return_value=MagicMock(stdout=io.StringIO(''), poll=lambda: None)),
            patch('kotonebot.client.implements.scrcpy.session.threading.Thread', side_effect=lambda *args, **kwargs: FakeThread()),
            patch.object(session, '_push_server'),
            patch.object(session, '_setup_forward', return_value=27183),
            patch.object(session, '_wait_for_socket_ready'),
            patch.object(session.video, 'start'),
            patch.object(session.video, 'wait_until_ready'),
            patch.object(session, '_connect_forward_socket', side_effect=[MagicMock(), MagicMock()]),
            patch.object(session, '_kill_all_scrcpy_processes') as mock_kill_all,
        ):
            session.start()

        mock_kill_all.assert_called_once_with()

    def test_owned_only_cleanup_does_not_kill_all_scrcpy_processes(self):
        session = ScrcpySession(self._connection(), self._config(scid=789))

        with (
            patch('kotonebot.client.implements.scrcpy.session.subprocess.Popen', return_value=MagicMock(stdout=io.StringIO(''), poll=lambda: None)),
            patch('kotonebot.client.implements.scrcpy.session.threading.Thread', side_effect=lambda *args, **kwargs: FakeThread()),
            patch.object(session, '_push_server'),
            patch.object(session, '_setup_forward', return_value=27183),
            patch.object(session, '_wait_for_socket_ready'),
            patch.object(session.video, 'start'),
            patch.object(session.video, 'wait_until_ready'),
            patch.object(session, '_connect_forward_socket', side_effect=[MagicMock(), MagicMock()]),
            patch.object(session, '_remove_forward'),
            patch.object(session, '_kill_all_scrcpy_processes') as mock_kill_all,
        ):
            session.start()
            session.stop()

        mock_kill_all.assert_not_called()

    def test_virtual_display_launch_package_uses_control_message(self):
        session = ScrcpySession(
            self._connection(),
            self._config(virtual_display=VirtualDisplayConfig(width=1280, height=720, launch_package='com.android.settings')),
        )
        fake_control = MagicMock()

        with (
            patch('kotonebot.client.implements.scrcpy.session.subprocess.Popen', return_value=MagicMock(stdout=io.StringIO(''), poll=lambda: None)),
            patch('kotonebot.client.implements.scrcpy.session.threading.Thread', side_effect=lambda *args, **kwargs: FakeThread()),
            patch.object(session, '_push_server'),
            patch.object(session, '_setup_forward', return_value=27183),
            patch.object(session, '_wait_for_socket_ready'),
            patch.object(session.video, 'start'),
            patch.object(session.video, 'wait_until_ready'),
            patch.object(session, '_connect_forward_socket', side_effect=[MagicMock(), MagicMock()]),
            patch('kotonebot.client.implements.scrcpy.session.ScrcpyControlChannel', return_value=fake_control),
        ):
            session.start()

        fake_control.start_app.assert_called_once_with('com.android.settings')

    def test_reuse_existing_display_skips_start_app_and_uses_display_id(self):
        session = ScrcpySession(
            self._connection(),
            self._config(virtual_display=VirtualDisplayConfig(width=1280, height=720, launch_package='com.android.settings')),
        )
        fake_control = MagicMock()

        with (
            patch('kotonebot.client.implements.scrcpy.session.find_reusable_display', return_value=MagicMock(display_id=7, width=1280, height=720, top_package='com.android.settings')),
            patch('kotonebot.client.implements.scrcpy.session.subprocess.Popen', return_value=MagicMock(stdout=io.StringIO(''), poll=lambda: None)),
            patch('kotonebot.client.implements.scrcpy.session.threading.Thread', side_effect=lambda *args, **kwargs: FakeThread()),
            patch.object(session, '_push_server'),
            patch.object(session, '_setup_forward', return_value=27183),
            patch.object(session, '_wait_for_socket_ready'),
            patch.object(session.video, 'start'),
            patch.object(session.video, 'wait_until_ready'),
            patch.object(session, '_connect_forward_socket', side_effect=[MagicMock(), MagicMock()]),
            patch('kotonebot.client.implements.scrcpy.session.ScrcpyControlChannel', return_value=fake_control),
        ):
            session._effective_scid = session._resolve_scid()
            params, _ = session._build_server_params()
            self.assertIn('display_id=7', params)
            self.assertFalse(any(p.startswith('new_display=') for p in params))
            session.start()

        fake_control.start_app.assert_not_called()
        self.assertEqual(session._attached_display_id, 7)
        self.assertFalse(session._created_new_display)

    def test_reuse_existing_false_always_creates_new_display(self):
        session = ScrcpySession(
            self._connection(),
            self._config(
                virtual_display=VirtualDisplayConfig(
                    reuse_existing=False,
                    width=1280,
                    height=720,
                    launch_package='com.android.settings',
                )
            ),
        )

        with patch('kotonebot.client.implements.scrcpy.session.find_reusable_display') as mock_probe:
            session._effective_scid = session._resolve_scid()
            params, _ = session._build_server_params()

        self.assertTrue(any(p.startswith('new_display=') for p in params))
        mock_probe.assert_not_called()


if __name__ == '__main__':
    unittest.main()
