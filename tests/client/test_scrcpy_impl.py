import struct
import unittest
from unittest.mock import MagicMock

import numpy as np

from kotonebot.client.implements.scrcpy import ScrcpyConfig, ScrcpyImpl
from kotonebot.client.implements.scrcpy.control import (
    ACTION_DOWN,
    ACTION_HOVER_MOVE,
    ACTION_MOVE,
    ACTION_UP,
    ANDROID_KEYCODES,
    BUTTON_PRIMARY,
    CONTROL_MSG_INJECT_KEYCODE,
    CONTROL_MSG_INJECT_SCROLL_EVENT,
    CONTROL_MSG_INJECT_TEXT,
    CONTROL_MSG_INJECT_TOUCH_EVENT,
    SCRCPY_POINTER_ID_MOUSE,
    ScrcpyControlChannel,
)
from kotonebot.client.implements.scrcpy.frame_store import FrameSnapshot


class TestScrcpyControlChannel(unittest.TestCase):
    def _channel(self) -> tuple[ScrcpyControlChannel, MagicMock]:
        sock = MagicMock()
        channel = ScrcpyControlChannel(sock, lambda: (1080, 1920))
        return channel, sock

    def test_touch_down_serializes_scrcpy_touch_packet(self):
        channel, sock = self._channel()

        channel.send_touch_down(100, 200, contact_id=2)

        payload = sock.sendall.call_args[0][0]
        expected = struct.pack(
            '>BBQiiHHHII',
            CONTROL_MSG_INJECT_TOUCH_EVENT,
            ACTION_DOWN,
            2,
            100,
            200,
            1080,
            1920,
            0xFFFF,
            0,
            0,
        )
        self.assertEqual(payload, expected)

    def test_touch_down_supports_multi_touch_contact_ids(self):
        channel, sock = self._channel()

        channel.send_touch_down(100, 200, contact_id=5)

        payload = sock.sendall.call_args[0][0]
        message_type, action, pointer_id, x, y, width, height, pressure, action_button, buttons = struct.unpack(
            '>BBQiiHHHII',
            payload,
        )
        self.assertEqual(message_type, CONTROL_MSG_INJECT_TOUCH_EVENT)
        self.assertEqual(action, ACTION_DOWN)
        self.assertEqual(pointer_id, 5)
        self.assertEqual((x, y, width, height), (100, 200, 1080, 1920))
        self.assertEqual(pressure, 0xFFFF)
        self.assertEqual((action_button, buttons), (0, 0))

    def test_touch_down_rejects_negative_contact_id(self):
        channel, sock = self._channel()

        with self.assertRaisesRegex(ValueError, 'contact_id must be non-negative'):
            channel.send_touch_down(100, 200, contact_id=-1)

        sock.sendall.assert_not_called()

    def test_mouse_packets_use_scrcpy_mouse_pointer_and_button_state(self):
        channel, sock = self._channel()

        channel.move(10, 20)
        hover_payload = sock.sendall.call_args_list[0][0][0]
        channel.button_down('left')
        down_payload = sock.sendall.call_args_list[1][0][0]
        channel.move(30, 40)
        drag_payload = sock.sendall.call_args_list[2][0][0]
        channel.button_up('left')
        up_payload = sock.sendall.call_args_list[3][0][0]

        hover = struct.unpack('>BBQiiHHHII', hover_payload)
        down = struct.unpack('>BBQiiHHHII', down_payload)
        drag = struct.unpack('>BBQiiHHHII', drag_payload)
        up = struct.unpack('>BBQiiHHHII', up_payload)

        self.assertEqual(hover[:3], (CONTROL_MSG_INJECT_TOUCH_EVENT, ACTION_HOVER_MOVE, SCRCPY_POINTER_ID_MOUSE))
        self.assertEqual(down[1], ACTION_DOWN)
        self.assertEqual(down[8], BUTTON_PRIMARY)
        self.assertEqual(down[9], BUTTON_PRIMARY)
        self.assertEqual(drag[1], ACTION_MOVE)
        self.assertEqual(drag[9], BUTTON_PRIMARY)
        self.assertEqual(up[1], ACTION_UP)
        self.assertEqual(up[8], BUTTON_PRIMARY)
        self.assertEqual(up[9], 0)

    def test_scroll_serializes_scrcpy_scroll_packet(self):
        channel, sock = self._channel()
        channel.move(50, 60)

        channel.scroll(dy=1)

        payload = sock.sendall.call_args_list[-1][0][0]
        message_type, x, y, width, height, hscroll, vscroll, buttons = struct.unpack('>BiiHHhhI', payload)
        self.assertEqual(message_type, CONTROL_MSG_INJECT_SCROLL_EVENT)
        self.assertEqual((x, y, width, height), (50, 60, 1080, 1920))
        self.assertEqual(hscroll, 0)
        self.assertGreater(vscroll, 0)
        self.assertEqual(buttons, 0)

    def test_key_and_text_packets_are_serialized(self):
        channel, sock = self._channel()

        channel.key_down('enter')
        key_payload = sock.sendall.call_args_list[0][0][0]
        channel.type_text('abc')
        text_payload = sock.sendall.call_args_list[1][0][0]

        self.assertEqual(
            struct.unpack('>BBiii', key_payload),
            (CONTROL_MSG_INJECT_KEYCODE, ACTION_DOWN, ANDROID_KEYCODES['enter'], 0, 0),
        )
        self.assertEqual(text_payload[:5], struct.pack('>BI', CONTROL_MSG_INJECT_TEXT, 3))
        self.assertEqual(text_payload[5:], b'abc')

    def test_uppercase_key_uses_shift_metastate(self):
        channel, sock = self._channel()

        channel.key_down('A')

        payload = sock.sendall.call_args[0][0]
        _, _, keycode, _, metastate = struct.unpack('>BBiii', payload)
        self.assertEqual(keycode, ANDROID_KEYCODES['a'])
        self.assertNotEqual(metastate, 0)


class TestScrcpyImplFacade(unittest.TestCase):
    def _impl(self) -> tuple[ScrcpyImpl, MagicMock, MagicMock]:
        connection = MagicMock()
        connection.serial = '127.0.0.1:5555'
        session = MagicMock()
        session.video.get_latest_frame.return_value = FrameSnapshot(
            frame=np.zeros((2, 3, 3), dtype=np.uint8),
            width=3,
            height=2,
            seq=1,
            timestamp=1.0,
        )
        session.control = MagicMock()
        impl = ScrcpyImpl(connection, ScrcpyConfig(server_jar_path='x', server_version='3.3.1'), session=session)
        return impl, session, session.control

    def test_start_and_stop_delegate_to_session(self):
        impl, session, _ = self._impl()

        impl.start()
        impl.stop()

        session.start.assert_called_once_with()
        session.stop.assert_called_once_with()

    def test_screenshot_returns_frame_snapshot_copy(self):
        impl, _, _ = self._impl()

        image = impl.screenshot()

        self.assertEqual(image.shape, (2, 3, 3))

    def test_touch_methods_delegate_to_control_channel(self):
        impl, _, control = self._impl()

        impl.touch_down(1, 2, contact_id=3)
        impl.touch_move(4, 5, contact_id=6)
        impl.touch_up(7, 8, contact_id=9)

        control.send_touch_down.assert_called_once_with(1, 2, contact_id=3)
        control.send_touch_move.assert_called_once_with(4, 5, contact_id=6)
        control.send_touch_up.assert_called_once_with(7, 8, contact_id=9)

    def test_mouse_keyboard_delegate_to_control_channel(self):
        impl, _, control = self._impl()

        impl.move(10, 20)
        impl.button_down('left')
        impl.button_up('left')
        impl.scroll(dy=2)
        impl.key_down('enter')
        impl.key_up('enter')
        impl.type_text('abc')

        control.move.assert_called_once_with(10, 20)
        control.button_down.assert_called_once_with('left')
        control.button_up.assert_called_once_with('left')
        control.scroll.assert_called_once_with(dx=0, dy=2)
        control.key_down.assert_called_once_with('enter')
        control.key_up.assert_called_once_with('enter')
        control.type_text.assert_called_once_with('abc')


if __name__ == '__main__':
    unittest.main()
