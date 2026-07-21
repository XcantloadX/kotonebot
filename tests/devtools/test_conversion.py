"""转换服务单元测试。"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import cv2
import numpy as np

from kotonebot.devtools.conversion.service import ConversionService
from kotonebot.devtools.conversion.types import (
    ConfirmedMatch,
    ConversionMatch,
    ScanProgress,
)
from kotonebot.devtools.project.project import Project
from tests.devtools._testkit import in_cwd, write_pyproject


def _make_single_meta(
    type_: str = "template", image_rect: tuple[int, int, int, int] | None = None
) -> dict[str, Any]:
    """构造 single 格式的 meta 数据。"""
    defn: dict[str, Any] = {"type": type_}
    if image_rect:
        x1, y1, x2, y2 = image_rect
        defn["props"] = {
            "image": {"kind": "image", "x1": x1, "y1": y1, "x2": x2, "y2": y2}
        }
    return {"isSimple": True, "definition": defn}


def _make_multi_meta(defs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """构造 multi 格式的 meta 数据。"""
    return {"version": 3, "definitions": defs or {}}


def _make_checkerboard_image(
    path: Path,
    width: int = 100,
    height: int = 80,
    tile_size: int = 10,
    color1: tuple = (200, 200, 200),
    color2: tuple = (50, 50, 50),
) -> None:
    """生成棋盘格纹理图片。"""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        for x in range(width):
            if (x // tile_size + y // tile_size) % 2 == 0:
                img[y, x] = color1
            else:
                img[y, x] = color2
    cv2.imwrite(str(path), img)


def _make_target_with_template(
    path: Path,
    canvas_w: int = 200,
    canvas_h: int = 200,
    template_x: int = 10,
    template_y: int = 10,
    template_w: int = 100,
    template_h: int = 80,
) -> None:
    """生成带棋盘格特征的图片，用于模拟包含模板的场景。"""
    img = np.full((canvas_h, canvas_w, 3), 180, dtype=np.uint8)
    # 在指定位置画一个棋盘格矩形（模板特征）
    for y in range(template_y, template_y + template_h):
        for x in range(template_x, template_x + template_w):
            if (x // 10 + y // 10) % 2 == 0:
                img[y, x] = (200, 200, 200)
            else:
                img[y, x] = (50, 50, 50)
    cv2.imwrite(str(path), img)


def _make_no_match_image(path: Path, width: int = 200, height: int = 200) -> None:
    """生成纯灰色图片，与棋盘格模板不匹配。"""
    img = np.full((height, width, 3), 128, dtype=np.uint8)
    cv2.imwrite(str(path), img)


class TestPathToDefinitionName(unittest.TestCase):
    """名称转换逻辑测试。"""

    def test_flat_path(self):
        result = ConversionService.path_to_definition_name("button.png")
        self.assertEqual(result, "Button")

    def test_snake_case_name(self):
        result = ConversionService.path_to_definition_name("claim_button.png")
        self.assertEqual(result, "ClaimButton")

    def test_nested_path(self):
        result = ConversionService.path_to_definition_name(
            "activities/daily_quest/claim_button.png"
        )
        self.assertEqual(result, "Activities.DailyQuest.ClaimButton")

    def test_deeply_nested(self):
        result = ConversionService.path_to_definition_name(
            "ui/main_menu/settings/volume_slider.png"
        )
        self.assertEqual(result, "Ui.MainMenu.Settings.VolumeSlider")

    def test_no_extension(self):
        result = ConversionService.path_to_definition_name("my_button")
        self.assertEqual(result, "MyButton")


class TestClassifyMetas(unittest.TestCase):
    """Meta 文件分类测试。"""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        (self.tmp_path / "resources").mkdir()
        write_pyproject(self.tmp_path / "pyproject.toml", resource_path="resources")
        with in_cwd(self.tmp_path):
            self.project = Project(conf_path=str(self.tmp_path / "pyproject.toml"))
        self.service = ConversionService(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def _create_single(self, rel_path: str) -> Path:
        png, meta = Path(self.tmp_path / "resources" / rel_path), Path(
            self.tmp_path / "resources" / f"{rel_path}.json"
        )
        png.parent.mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(png)
        meta.write_text(
            json.dumps(_make_single_meta(image_rect=(0, 0, 100, 80))), encoding="utf-8"
        )
        return meta

    def _create_multi(self, rel_path: str) -> Path:
        png, meta = Path(self.tmp_path / "resources" / rel_path), Path(
            self.tmp_path / "resources" / f"{rel_path}.json"
        )
        png.parent.mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(png)
        meta.write_text(json.dumps(_make_multi_meta()), encoding="utf-8")
        return meta

    def test_only_single(self):
        self._create_single("foo/bar.png")
        singles, multis = self.service.classify_metas()
        self.assertEqual(len(singles), 1)
        self.assertEqual(len(multis), 0)

    def test_only_multi(self):
        self._create_multi("foo/multi.png")
        singles, multis = self.service.classify_metas()
        self.assertEqual(len(singles), 0)
        self.assertEqual(len(multis), 1)

    def test_mixed(self):
        self._create_single("single/btn.png")
        self._create_multi("multi/doc.png")
        singles, multis = self.service.classify_metas()
        self.assertEqual(len(singles), 1)
        self.assertEqual(len(multis), 1)

    def test_bare_png_classified_as_single(self):
        png = self.tmp_path / "resources" / "bare" / "image.png"
        png.parent.mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(png)
        singles, multis = self.service.classify_metas()
        self.assertEqual(len(singles), 1)
        self.assertEqual(len(multis), 0)
        self.assertIn("bare/image.png", singles[0][0].image_path)
        self.assertIsNone(singles[0][0].json_path)

    def test_skips_invalid(self):
        meta = self.tmp_path / "resources" / "bad.png.json"
        meta.parent.mkdir(parents=True, exist_ok=True)
        meta.write_text("not json", encoding="utf-8")
        singles, multis = self.service.classify_metas()
        self.assertEqual(len(singles), 0)
        self.assertEqual(len(multis), 0)


class TestComputeMatchResults(unittest.TestCase):
    """模板匹配测试。"""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        (self.tmp_path / "resources").mkdir()
        write_pyproject(self.tmp_path / "pyproject.toml", resource_path="resources")
        with in_cwd(self.tmp_path):
            self.project = Project(conf_path=str(self.tmp_path / "pyproject.toml"))
        self.service = ConversionService(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def _create_single_and_ref(
        self, image_rel_path: str, meta_data: dict
    ) -> tuple[Any, Any]:
        """创建 single 文档并返回 (DocRef, SingleMetaModel)。"""
        png_abs = self.tmp_path / "resources" / image_rel_path
        png_abs.parent.mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(png_abs)
        meta_abs = Path(str(png_abs) + ".json")
        meta_abs.write_text(json.dumps(meta_data), encoding="utf-8")

        from kotonebot.devtools.meta.models import SingleMetaModel
        from kotonebot.devtools.meta.scanner import DocRef

        ref = DocRef(
            image_path=png_abs.as_posix(),
            abs_image_path=png_abs,
            json_path=meta_abs.as_posix(),
            abs_json_path=meta_abs,
            mtime_ns=int(png_abs.stat().st_mtime_ns),
            size=png_abs.stat().st_size,
        )
        model = SingleMetaModel.model_validate(meta_data)
        return ref, model

    def _target_rel(self, name: str) -> str:
        return f"resources/multi/{name}"

    def test_match_found(self):
        ref, model = self._create_single_and_ref(
            "single/btn.png",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )
        res = self.tmp_path / "resources"
        target = res / "multi" / "scene.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        _make_target_with_template(target)

        results = self.service.compute_match_results(
            [(ref, model)],
            [(self._target_rel("scene.png"), None)],
        )
        self.assertEqual(len(results), 1)
        self.assertGreaterEqual(results[0].matchScore, 0.95)

    def test_no_match(self):
        ref, model = self._create_single_and_ref(
            "single/btn.png",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )
        res = self.tmp_path / "resources"
        target = res / "multi" / "scene.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        _make_no_match_image(target)

        results = self.service.compute_match_results(
            [(ref, model)],
            [(self._target_rel("scene.png"), None)],
        )
        self.assertEqual(len(results), 0)

    def test_skips_unknown_type(self):
        ref, model = self._create_single_and_ref(
            "single/hint.png",
            _make_single_meta(type_="unknown"),
        )
        res = self.tmp_path / "resources"
        target = res / "multi" / "scene.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        _make_target_with_template(target)

        results = self.service.compute_match_results(
            [(ref, model)],
            [(self._target_rel("scene.png"), None)],
        )
        self.assertEqual(len(results), 0)


def _wait_for_scan(
    service: ConversionService, task_id: str, timeout: float = 10.0
) -> ScanProgress:
    """轮询等待后台扫描任务完成，返回最终 progress。"""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        prog = service.get_scan_progress(task_id)
        if prog is None:
            time.sleep(0.1)
            continue
        if prog.state in ("completed", "cancelled", "error"):
            return prog
        time.sleep(0.1)
    raise TimeoutError(f"扫描任务 {task_id} 在 {timeout}s 内未完成")


    def test_bare_png_matches(self):
        png_abs = self.tmp_path / "resources" / "bare" / "btn.png"
        png_abs.parent.mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(png_abs)

        from kotonebot.devtools.meta.scanner import DocRef
        from kotonebot.devtools.meta.models import SingleMetaModel

        ref = DocRef(
            image_path=png_abs.as_posix(),
            abs_image_path=png_abs,
            mtime_ns=int(png_abs.stat().st_mtime_ns),
            size=png_abs.stat().st_size,
        )
        model = SingleMetaModel(isSimple=True, definition={"type": "template"})

        res = self.tmp_path / "resources"
        target = res / "multi" / "scene.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        _make_target_with_template(target)

        results = self.service.compute_match_results(
            [(ref, model)],
            [(self._target_rel("scene.png"), None)],
        )
        self.assertEqual(len(results), 1)
        self.assertGreaterEqual(results[0].matchScore, 0.95)
        self.assertIsNone(results[0].singleMetaPath)


class TestScanIntegration(unittest.TestCase):
    """三种扫描模式的集成测试。"""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        (self.tmp_path / "resources").mkdir()
        write_pyproject(self.tmp_path / "pyproject.toml", resource_path="resources")
        with in_cwd(self.tmp_path):
            self.project = Project(conf_path=str(self.tmp_path / "pyproject.toml"))
        self.service = ConversionService(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_all(self):
        res = self.tmp_path / "resources"
        (res / "single").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "single" / "btn.png")
        write_json(
            res / "single" / "btn.png.json",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )
        (res / "multi").mkdir(parents=True, exist_ok=True)
        _make_target_with_template(res / "multi" / "scene.png")
        write_json(res / "multi" / "scene.png.json", _make_multi_meta())

        task_id = self.service.start_scan_all()
        progress = _wait_for_scan(self.service, task_id)
        self.assertEqual(progress.state, "completed")
        self.assertEqual(len(progress.matches), 1)

    def test_scan_files(self):
        res = self.tmp_path / "resources"
        (res / "single").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "single" / "btn.png")
        write_json(
            res / "single" / "btn.png.json",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )
        target = res / "multi" / "scene.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        _make_target_with_template(target)
        write_json(res / "multi" / "scene.png.json", _make_multi_meta())

        task_id = self.service.start_scan_files(["resources/multi/scene.png"])
        progress = _wait_for_scan(self.service, task_id)
        self.assertEqual(progress.state, "completed")
        self.assertEqual(len(progress.matches), 1)

    def test_scan_device(self):
        res = self.tmp_path / "resources"
        (res / "single").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "single" / "btn.png")
        write_json(
            res / "single" / "btn.png.json",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )
        screenshot = (
            self.tmp_path
            / ".kotonebot"
            / "cache"
            / "device_captures"
            / "screenshot.png"
        )
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        _make_target_with_template(screenshot)

        task_id = self.service.start_scan_device(
            screenshot.relative_to(self.tmp_path).as_posix(),
        )
        progress = _wait_for_scan(self.service, task_id)
        self.assertEqual(progress.state, "completed")
        self.assertEqual(len(progress.matches), 1)


class TestExecute(unittest.TestCase):
    """转换执行测试。"""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        (self.tmp_path / "resources").mkdir()
        write_pyproject(self.tmp_path / "pyproject.toml", resource_path="resources")
        with in_cwd(self.tmp_path):
            self.project = Project(conf_path=str(self.tmp_path / "pyproject.toml"))
        self.service = ConversionService(self.project)

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_new_definition_in_existing_multi(self):
        res = self.tmp_path / "resources"
        # 已有的 multi 文档
        (res / "multi").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "multi" / "scene.png")
        write_json(
            res / "multi" / "scene.png.json",
            _make_multi_meta(
                {"existing_def": {"type": "template", "name": "ExistingDef"}}
            ),
        )
        # 待删除的 single 文档
        (res / "single").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "single" / "btn.png")
        write_json(
            res / "single" / "btn.png.json",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )

        result = self.service.execute(
            [
                ConfirmedMatch(
                    singleMetaPath="resources/single/btn.png.json",
                    singleImagePath="resources/single/btn.png",
                    matchedImagePath="resources/multi/scene.png",
                    matchX=10,
                    matchY=10,
                    matchW=100,
                    matchH=80,
                    definitionType="template",
                    definitionName="Single.Btn",
                    definitionDisplayName="btn.png",
                ),
            ]
        )

        # 验证：multi 文档包含新旧两个定义
        multi_meta = json.loads(
            (res / "multi" / "scene.png.json").read_text(encoding="utf-8")
        )
        self.assertIn("existing_def", multi_meta["definitions"])
        self.assertIn("Single.Btn", multi_meta["definitions"]["auto_Btn"]["name"])
        # 验证：single 文档被删除
        self.assertFalse((res / "single" / "btn.png.json").exists())
        self.assertFalse((res / "single" / "btn.png").exists())
        # 验证返回值
        self.assertIn("resources/multi/scene.png.json", result.modifiedMetaPaths)
        self.assertIn("resources/single/btn.png.json", result.deletedSingleMetaPaths)
        self.assertIn("resources/single/btn.png", result.deletedSingleImagePaths)

    def test_uses_target_meta_path_override(self):
        res = self.tmp_path / "resources"
        # 目标 multi 文档在指定位置
        (res / "target").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "target" / "doc.png")
        write_json(res / "target" / "doc.png.json", _make_multi_meta({}))
        # single 文档
        (res / "single").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "single" / "btn.png")
        write_json(
            res / "single" / "btn.png.json",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )

        result = self.service.execute(
            [
                ConfirmedMatch(
                    singleMetaPath="resources/single/btn.png.json",
                    singleImagePath="resources/single/btn.png",
                    matchedImagePath="device_screenshot.png",
                    matchX=0,
                    matchY=0,
                    matchW=100,
                    matchH=80,
                    definitionType="template",
                    definitionName="Single.Btn",
                    definitionDisplayName="btn.png",
                    targetMetaPath="resources/target/doc.png.json",
                ),
            ]
        )

        self.assertIn("resources/target/doc.png.json", result.modifiedMetaPaths)
        meta = json.loads((res / "target" / "doc.png.json").read_text(encoding="utf-8"))
        self.assertIn("auto_Btn", meta["definitions"])

    def test_creates_new_multi_when_not_exists(self):
        """当目标 meta 文件不存在时，应创建新的 multi 文档。"""
        res = self.tmp_path / "resources"
        (res / "single").mkdir(parents=True, exist_ok=True)
        _make_checkerboard_image(res / "single" / "btn.png")
        write_json(
            res / "single" / "btn.png.json",
            _make_single_meta(image_rect=(0, 0, 100, 80)),
        )

        result = self.service.execute(
            [
                ConfirmedMatch(
                    singleMetaPath="resources/single/btn.png.json",
                    singleImagePath="resources/single/btn.png",
                    matchedImagePath="new_multi/doc.png",
                    matchX=0,
                    matchY=0,
                    matchW=100,
                    matchH=80,
                    definitionType="template",
                    definitionName="NewMulti.Doc",
                    definitionDisplayName="doc.png",
                ),
            ]
        )

        self.assertIn("new_multi/doc.png.json", result.modifiedMetaPaths)
        # meta 文件创建在 pyproject_root 下
        meta_abs = self.tmp_path / "new_multi" / "doc.png.json"
        self.assertTrue(meta_abs.exists())


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
