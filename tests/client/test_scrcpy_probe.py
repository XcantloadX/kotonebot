import unittest

from kotonebot.client.implements.scrcpy.probe import (
    _extract_display_section,
    _parse_display_sizes,
    _parse_top_package_from_display_section,
    find_reusable_display,
)


DISPLAY_SAMPLE = """
DISPLAY MANAGER (dumpsys display)
Display States: size=3
  Display Id=0
  Display State=ON
  Display Id=7
  Display State=ON
  Display Id=8
  Display State=ON
  DisplayDeviceInfo{"Built-in", 1904 x 3040}
    mCurrentDisplayRect=Rect(0, 0 - 3040, 1904)
  DisplayDeviceInfo{"Virtual1", 1280 x 720}
    mCurrentDisplayRect=Rect(0, 0 - 1280, 720)
  DisplayDeviceInfo{"Virtual2", 1280 x 720}
    mCurrentDisplayRect=Rect(0, 0 - 1280, 720)
"""

ACTIVITIES_SAMPLE = """
ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)
Display #7 (activities from top to bottom):
  topResumedActivity=ActivityRecord{ x y com.sega.pjsekai/.MainActivity t1}
Display #8 (activities from top to bottom):
  topResumedActivity=ActivityRecord{ x y com.android.settings/.Settings t2}
"""


class TestScrcpyProbe(unittest.TestCase):
    def test_parse_display_sizes(self):
        parsed = _parse_display_sizes(DISPLAY_SAMPLE)
        self.assertIn((7, 1280, 720), parsed)
        self.assertIn((8, 1280, 720), parsed)

    def test_extract_display_section(self):
        section = _extract_display_section(ACTIVITIES_SAMPLE, 7)
        self.assertIsNotNone(section)
        assert section is not None
        self.assertIn('com.sega.pjsekai', section)

    def test_parse_top_package(self):
        section = _extract_display_section(ACTIVITIES_SAMPLE, 8)
        self.assertEqual(_parse_top_package_from_display_section(section), 'com.android.settings')

    def test_find_reusable_display(self):
        adb = type('FakeAdb', (), {'shell': lambda self, cmd: DISPLAY_SAMPLE if cmd == 'dumpsys display' else ACTIVITIES_SAMPLE})()
        reused = find_reusable_display(adb, target_package='com.sega.pjsekai', width=1280, height=720)
        self.assertIsNotNone(reused)
        assert reused is not None
        self.assertEqual(reused.display_id, 7)


if __name__ == '__main__':
    unittest.main()
