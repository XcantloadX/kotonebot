import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from kotonebot.devtools.meta import parse_meta_file, scan_meta_files


def test_scan_meta_files():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a").mkdir()
        (root / "b").mkdir()
        (root / "a" / "x.png.json").write_text("{}", encoding="utf-8")
        (root / "b" / "y.png.json").write_text("{}", encoding="utf-8")

        refs = scan_meta_files(root)
        assert len(refs) == 2
        assert refs[0].meta_path.endswith("a/x.png.json")
        assert refs[0].image_path.endswith("a/x.png")
        assert refs[1].meta_path.endswith("b/y.png.json")
        assert refs[1].image_path.endswith("b/y.png")


def test_parse_meta_file():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.png.json"
        path.write_text(
            json.dumps(
                {
                    "version": 3,
                    "definitions": {
                        "x": {
                            "type": "template",
                            "props": {},
                        },
                        "p": {
                            "type": "prefab",
                            "name": "ui.button",
                            "variant": "en",
                            "props": {},
                        },
                    },
                }
            ),
            encoding="utf-8",
        )
        data = parse_meta_file(path)
        assert data.version == 3
        assert "x" in data.definitions
        assert data.definitions["p"].variant == "en"


def test_parse_meta_file_rejects_invalid():
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "a.png.json"
        path.write_text(json.dumps({"version": 1, "definitions": {}}), encoding="utf-8")
        with pytest.raises(ValueError):
            parse_meta_file(path)
