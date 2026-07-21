"""Single 文档 → Multi 文档转换服务。"""

import json
import logging
import threading
from collections import defaultdict
from typing import Any, Callable

import cv2

from kotonebot.devtools.conversion.task_manager import ScanTaskManager
from kotonebot.devtools.conversion.types import (
    ConfirmedMatch,
    ConversionExecuteResponse,
    ConversionMatch,
    ScanProgress,
    ScanTaskState,
)
from kotonebot.devtools.meta.models import (
    DefinitionMultiModel,
    MetaMultiModel,
    SingleMetaModel,
)
from kotonebot.devtools.meta.parser import parse_meta_file
from kotonebot.devtools.meta.scanner import MetaFileRef, scan_meta_files
from kotonebot.devtools.path_utils import get_safe_path
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.resgen.utils import to_camel_case
from kotonebot.devtools.resgen.validation import detect_and_validate_meta_schema

logger = logging.getLogger(__name__)


class ConversionService:
    """Single 文档 → Multi 文档转换服务。"""

    def __init__(self, project: Project):
        self.project = project
        self.project_root = project.allowed_roots[0]
        self.pyproject_root = project.pyproject_root
        self._task_manager = ScanTaskManager()

    # ======== 名称转换 ========

    @staticmethod
    def path_to_definition_name(image_rel_path: str) -> str:
        """根据图片相对路径生成定义名称（/ → ., 下划线 → 大驼峰）。

        :param image_rel_path: 相对 resource_root 的图片路径，如 ``activities/daily_quest/claim_button.png``
        :returns: ``Activities.DailyQuest.ClaimButton``
        """
        path = image_rel_path.replace("\\", "/")
        if "." in path:
            path = path.rsplit(".", 1)[0]
        parts = path.split("/")
        return ".".join(to_camel_case(p) for p in parts if p)

    # ======== 扫描分类 ========

    def classify_metas(
        self,
    ) -> tuple[list[tuple[MetaFileRef, SingleMetaModel]], list[MetaFileRef]]:
        """扫描所有 meta 文件并分类为 single 和 multi。

        :returns: (singles, multis)
            - singles: list of (MetaFileRef, SingleMetaModel)
            - multis: list of MetaFileRef
        """
        all_refs = scan_meta_files(self.project_root)
        singles: list[tuple[MetaFileRef, SingleMetaModel]] = []
        multis: list[MetaFileRef] = []
        for ref in all_refs:
            try:
                data = json.loads(ref.abs_meta_path.read_text(encoding="utf-8"))
                info = detect_and_validate_meta_schema(data)
                if info.format == "single":
                    singles.append((ref, SingleMetaModel.model_validate(data)))
                elif info.format == "multi":
                    multis.append(ref)
            except Exception:
                logger.warning(
                    "无法解析 meta 文件: %s", ref.abs_meta_path, exc_info=True
                )
                continue
        
        for s in singles:
            logger.debug("Single meta: %s", s[0].abs_meta_path)
        return singles, multis

    def compute_match_results(
        self,
        singles: list[tuple[MetaFileRef, SingleMetaModel]],
        target_image_infos: list[tuple[str, str | None]],
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> list[ConversionMatch]:
        """遍历每个 single 文档，在目标图片上做模板匹配。

        :param singles: list of (MetaFileRef, SingleMetaModel)
        :param target_image_infos: list of (image_rel_path, meta_rel_path_or_None)
        :param progress_callback: 进度回调，参数 (current, total, current_file)
        :param cancel_event: 取消事件，检查后应退出
        """
        results: list[ConversionMatch] = []
        total = len(singles)
        for idx, (single_ref, single_meta) in enumerate(singles):
            if cancel_event and cancel_event.is_set():
                logger.info("扫描任务被取消")
                return results

            defn = single_meta.definition
            def_type = defn.type
            if def_type not in ("template", "prefab"):
                if progress_callback:
                    progress_callback(idx + 1, total, single_ref.image_path)
                continue

            single_img_abs = single_ref.abs_meta_path.with_suffix("")
            single_img = cv2.imread(str(single_img_abs))
            if single_img is None:
                logger.warning("无法读取 single 图片: %s", single_img_abs)
                if progress_callback:
                    progress_callback(idx + 1, total, single_ref.image_path)
                continue

            props = defn.props or {}
            image_prop = props.get("template") or props.get("image", {})
            use_full_image = False
            if isinstance(image_prop, dict) and image_prop.get("kind") == "image":
                x1 = image_prop.get("x1")
                y1 = image_prop.get("y1")
                x2 = image_prop.get("x2")
                y2 = image_prop.get("y2")
                if (
                    isinstance(x1, (int, float))
                    and isinstance(y1, (int, float))
                    and isinstance(x2, (int, float))
                    and isinstance(y2, (int, float))
                ):
                    tx1, ty1, tx2, ty2 = int(x1), int(y1), int(x2), int(y2)
                else:
                    use_full_image = True
            else:
                use_full_image = True

            if use_full_image:
                tx1, ty1 = 0, 0
                tx2, ty2 = single_img.shape[1], single_img.shape[0]

            tw = tx2 - tx1
            th = ty2 - ty1
            if tw <= 0 or th <= 0:
                if progress_callback:
                    progress_callback(idx + 1, total, single_ref.image_path)
                continue
            if ty2 > single_img.shape[0] or tx2 > single_img.shape[1]:
                if progress_callback:
                    progress_callback(idx + 1, total, single_ref.image_path)
                continue
            template = single_img[ty1:ty2, tx1:tx2]

            for target_img_rel, _ in target_image_infos:
                if cancel_event and cancel_event.is_set():
                    logger.info("扫描任务被取消")
                    return results

                target_abs = get_safe_path(target_img_rel, self.project)
                target_img = cv2.imread(str(target_abs))
                if target_img is None:
                    logger.warning("无法读取目标图片: %s", target_img_rel)
                    continue
                th_i, tw_i = template.shape[:2]
                if th_i > target_img.shape[0] or tw_i > target_img.shape[1]:
                    logger.warning("模板大于目标图片: %s", target_img_rel)
                    continue

                match_result = cv2.matchTemplate(
                    target_img, template, cv2.TM_CCOEFF_NORMED
                )
                _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(match_result)
                if max_val >= 0.95:
                    mx, my = max_loc
                    definition_name = self.path_to_definition_name(
                        single_ref.image_path
                    )
                    file_name = single_ref.abs_meta_path.with_suffix("").name

                    results.append(
                        ConversionMatch(
                            singleMetaPath=single_ref.meta_path,
                            singleImagePath=single_ref.image_path,
                            matchedImagePath=target_img_rel,
                            matchScore=round(float(max_val), 4),
                            matchX=mx,
                            matchY=my,
                            matchW=tw_i,
                            matchH=th_i,
                            definitionType=def_type,
                            definitionName=definition_name,
                            definitionDisplayName=file_name,
                        )
                    )

            if progress_callback:
                progress_callback(idx + 1, total, single_ref.image_path)

        return results

    # ======== 异步扫描 ========

    def start_scan_all(self) -> str:
        """在后台线程启动全量扫描，返回 task_id。"""
        task_id = self._task_manager.create_task()
        thread = threading.Thread(
            target=self._run_scan_task,
            args=(task_id, "all"),
            daemon=True,
        )
        thread.start()
        return task_id

    def start_scan_files(self, image_paths: list[str]) -> str:
        """在后台线程启动文件扫描，返回 task_id。"""
        task_id = self._task_manager.create_task()
        thread = threading.Thread(
            target=self._run_scan_task,
            args=(task_id, "files"),
            kwargs={"image_paths": image_paths},
            daemon=True,
        )
        thread.start()
        return task_id

    def start_scan_device(self, screenshot_path: str) -> str:
        """在后台线程启动设备截图扫描，返回 task_id。"""
        task_id = self._task_manager.create_task()
        thread = threading.Thread(
            target=self._run_scan_task,
            args=(task_id, "device"),
            kwargs={"screenshot_path": screenshot_path},
            daemon=True,
        )
        thread.start()
        return task_id

    def _run_scan_task(
        self,
        task_id: str,
        mode: str,
        image_paths: list[str] | None = None,
        screenshot_path: str | None = None,
    ):
        """后台扫描任务入口。"""
        mgr = self._task_manager
        cancel_event = mgr.get_cancel_event(task_id)
        try:
            if cancel_event and cancel_event.is_set():
                mgr.update_progress(task_id, state=ScanTaskState.CANCELLED)
                return

            mgr.update_progress(task_id, state=ScanTaskState.CLASSIFYING)
            singles, multis = self.classify_metas()

            if cancel_event and cancel_event.is_set():
                mgr.update_progress(task_id, state=ScanTaskState.CANCELLED)
                return

            if not singles:
                mgr.update_progress(task_id, state=ScanTaskState.COMPLETED, matches=[])
                return

            if mode == "all":
                target_infos = [(m.image_path, m.meta_path) for m in multis]
            elif mode == "files" and image_paths is not None:
                target_infos = [(ip, ip + ".json") for ip in image_paths]
            elif mode == "device" and screenshot_path is not None:
                target_infos = [(screenshot_path, None)]
            else:
                mgr.update_progress(
                    task_id,
                    state=ScanTaskState.ERROR,
                    error=f"Unknown scan mode: {mode}",
                )
                return

            mgr.update_progress(
                task_id, state=ScanTaskState.SCANNING, total=len(singles), current=0
            )

            def _on_progress(current: int, total: int, file: str):
                mgr.update_progress(
                    task_id, current=current, total=total, current_file=file
                )

            matches = self.compute_match_results(
                singles,
                target_infos,
                progress_callback=_on_progress,
                cancel_event=cancel_event,
            )

            if cancel_event and cancel_event.is_set():
                mgr.update_progress(task_id, state=ScanTaskState.CANCELLED)
                return

            mgr.update_progress(
                task_id,
                state=ScanTaskState.COMPLETED,
                matches=matches,
                current=len(singles),
            )

        except Exception as e:
            logger.exception("扫描任务 %s 失败", task_id)
            mgr.update_progress(task_id, state=ScanTaskState.ERROR, error=str(e))

    def get_scan_progress(self, task_id: str) -> ScanProgress | None:
        """获取指定任务的进度。"""
        return self._task_manager.get_progress(task_id)

    def cancel_scan(self, task_id: str) -> bool:
        """取消指定任务。返回是否成功取消。"""
        return self._task_manager.cancel_task(task_id)

    # ======== 执行转换 ========

    def execute(self, matches: list[ConfirmedMatch]) -> ConversionExecuteResponse:
        """执行转换：为每个已确认的匹配在目标 multi 文档中创建/修改定义，
        然后删除对应的 single 文档。

        :param matches: 用户确认的匹配项
        """
        modified_metas: set[str] = set()
        deleted_single_metas: list[str] = []
        deleted_single_images: list[str] = []

        by_target: dict[str, list[ConfirmedMatch]] = defaultdict(list)
        for m in matches:
            target_meta = m.targetMetaPath
            if not target_meta:
                target_meta = m.matchedImagePath + ".json"
            by_target[target_meta].append(m)

        for target_meta_rel, group in by_target.items():
            target_meta_abs = get_safe_path(target_meta_rel, self.project)
            if target_meta_abs.exists():
                meta_model = parse_meta_file(target_meta_abs)
                existing_defs: dict[str, dict[str, Any]] = {
                    def_id: defn.model_dump(by_alias=True, exclude_none=True)
                    for def_id, defn in meta_model.definitions.items()
                }
            else:
                existing_defs = {}

            for match in group:
                last_part = (
                    match.definitionName.rsplit(".", 1)[-1]
                    if "." in match.definitionName
                    else match.definitionName
                )
                def_id = f"auto_{last_part}"
                if def_id in existing_defs:
                    idx = 1
                    while f"{def_id}_{idx}" in existing_defs:
                        idx += 1
                    def_id = f"{def_id}_{idx}"

                new_def = DefinitionMultiModel(
                    type=match.definitionType,
                    name=match.definitionName,
                    displayName=match.definitionDisplayName,
                    props={
                        "image": {
                            "kind": "image",
                            "x1": match.matchX,
                            "y1": match.matchY,
                            "x2": match.matchX + match.matchW,
                            "y2": match.matchY + match.matchH,
                        }
                    },
                )
                existing_defs[def_id] = new_def.model_dump(
                    by_alias=True, exclude_none=True
                )
                modified_metas.add(target_meta_rel)

            target_meta_abs.parent.mkdir(parents=True, exist_ok=True)
            # 通过 MetaMultiModel 反序列化再序列化确保数据一致性
            meta_to_write = MetaMultiModel(
                version=3,
                definitions={
                    def_id: DefinitionMultiModel(**def_data)
                    for def_id, def_data in existing_defs.items()
                },
            )
            target_meta_abs.write_text(
                json.dumps(
                    meta_to_write.model_dump(by_alias=True, exclude_none=True),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        seen_singles: set[str] = set()
        for m in matches:
            if m.singleMetaPath not in seen_singles:
                seen_singles.add(m.singleMetaPath)
                single_meta_abs = get_safe_path(m.singleMetaPath, self.project)
                if single_meta_abs.exists():
                    single_meta_abs.unlink()
                    deleted_single_metas.append(m.singleMetaPath)
            if m.singleImagePath not in seen_singles:
                seen_singles.add(m.singleImagePath)
                single_img_abs = get_safe_path(m.singleImagePath, self.project)
                if single_img_abs.exists():
                    single_img_abs.unlink()
                    deleted_single_images.append(m.singleImagePath)

        return ConversionExecuteResponse(
            modifiedMetaPaths=sorted(modified_metas),
            deletedSingleMetaPaths=deleted_single_metas,
            deletedSingleImagePaths=deleted_single_images,
        )
