from dataclasses import dataclass
import re

from adbutils._device import AdbDevice as AdbUtilsDevice


@dataclass(frozen=True, slots=True)
class ReusableDisplay:
    """可复用的虚拟显示信息。"""

    display_id: int
    """显示 ID。"""
    width: int
    """显示宽度。"""
    height: int
    """显示高度。"""
    top_package: str | None
    """当前顶层包名。"""


def _parse_display_sizes(dumpsys_display: str) -> list[tuple[int, int, int]]:
    """从 dumpsys display 中解析显示尺寸。"""
    pending_ids: list[int] = []
    results: list[tuple[int, int, int]] = []

    for line in dumpsys_display.splitlines():
        stripped = line.strip()
        if stripped.startswith('Display Id='):
            try:
                pending_ids.append(int(stripped.split('=', 1)[1].strip()))
            except ValueError:
                continue
            continue
        if not pending_ids:
            continue
        match = re.search(r'mCurrentDisplayRect=Rect\(0,\s*0\s*-\s*(\d+),\s*(\d+)\)', stripped)
        if match:
            display_id = pending_ids.pop(0)
            results.append((display_id, int(match.group(1)), int(match.group(2))))
    return results


def _extract_display_section(dumpsys_activities: str, display_id: int) -> str | None:
    """提取指定显示的 activity 段落。"""
    marker = f'Display #{display_id} '
    start = dumpsys_activities.find(marker)
    if start == -1:
        return None

    next_match = re.search(r'\nDisplay #\d+ ', dumpsys_activities[start + len(marker):])
    if next_match is None:
        return dumpsys_activities[start:]
    return dumpsys_activities[start:start + len(marker) + next_match.start()]


def _parse_top_package_from_display_section(section: str | None) -> str | None:
    """从显示段落中解析顶层包名。"""
    if not section:
        return None

    match = re.search(r'topResumedActivity=ActivityRecord\{.*?\s([A-Za-z0-9._]+)/', section)
    if match:
        return match.group(1)

    match = re.search(r'packageName=([A-Za-z0-9._]+)', section)
    if match:
        return match.group(1)

    return None


def find_reusable_display(
    adb_connection: AdbUtilsDevice,
    *,
    target_package: str,
    width: int,
    height: int,
) -> ReusableDisplay | None:
    """查找可复用的同尺寸虚拟显示。"""
    dumpsys_display = str(adb_connection.shell('dumpsys display'))
    dumpsys_activities = str(adb_connection.shell('dumpsys activity activities'))

    for display_id, display_width, display_height in _parse_display_sizes(dumpsys_display):
        if display_id == 0:
            continue
        if display_width != width or display_height != height:
            continue

        section = _extract_display_section(dumpsys_activities, display_id)
        top_package = _parse_top_package_from_display_section(section)
        if top_package == target_package:
            return ReusableDisplay(
                display_id=display_id,
                width=display_width,
                height=display_height,
                top_package=top_package,
            )

    return None
