import shutil
import subprocess
from pathlib import Path

from setuptools.build_meta import (
    build_editable as _build_editable,
    build_sdist as _build_sdist,
    build_wheel as _build_wheel,
    get_requires_for_build_editable,
    get_requires_for_build_sdist,
    get_requires_for_build_wheel,
    prepare_metadata_for_build_editable,
    prepare_metadata_for_build_wheel,
)

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "kotonebot-devtools2"
FRONTEND_DIST = FRONTEND_DIR / "dist"
PACKAGE_DIST = ROOT / "kotonebot" / "devtools" / "web" / "dist"


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def _resolve_npm_command() -> str:
    npm = shutil.which("npm")
    if npm:
        return npm
    npm_cmd = shutil.which("npm.cmd")
    if npm_cmd:
        return npm_cmd
    raise FileNotFoundError("npm executable not found in PATH")


def _build_frontend() -> None:
    lock_file = FRONTEND_DIR / "package-lock.json"
    if not lock_file.exists():
        raise FileNotFoundError(f"Missing lock file: {lock_file}")

    npm = _resolve_npm_command()
    _run([npm, "install"], cwd=FRONTEND_DIR)
    _run([npm, "run", "build"], cwd=FRONTEND_DIR)

    if not FRONTEND_DIST.exists():
        raise FileNotFoundError(f"Frontend build output not found: {FRONTEND_DIST}")

    if PACKAGE_DIST.exists():
        shutil.rmtree(PACKAGE_DIST)
    shutil.copytree(FRONTEND_DIST, PACKAGE_DIST)

def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    can_build_frontend = (FRONTEND_DIR / "package-lock.json").exists()
    if can_build_frontend:
        _build_frontend()
    if not PACKAGE_DIST.exists():
        raise FileNotFoundError(f"Packaged frontend dist not found: {PACKAGE_DIST}")
    return _build_wheel(wheel_directory, config_settings, metadata_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    can_build_frontend = (FRONTEND_DIR / "package-lock.json").exists()
    if can_build_frontend:
        _build_frontend()
    if not PACKAGE_DIST.exists():
        raise FileNotFoundError(f"Packaged frontend dist not found: {PACKAGE_DIST}")
    return _build_editable(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    _build_frontend()
    return _build_sdist(sdist_directory, config_settings)


__all__ = [
    "build_wheel",
    "build_editable",
    "build_sdist",
    "get_requires_for_build_editable",
    "get_requires_for_build_wheel",
    "get_requires_for_build_sdist",
    "prepare_metadata_for_build_editable",
    "prepare_metadata_for_build_wheel",
]
