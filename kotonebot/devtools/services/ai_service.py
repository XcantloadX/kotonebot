"""AI 辅助服务。

从 RestApiLogic 提取，封装 AI 路径建议和定义推断。
"""

import json
from pathlib import Path

from kotonebot.devtools.ai.ai_service import (
    infer_definitions as ai_infer_definitions,
    sample_name_tree,
    suggest_document_path as ai_suggest_document_path,
)
from kotonebot.devtools.ai.types import AiConfig
from kotonebot.devtools.path_utils import get_safe_path
from kotonebot.devtools.project.project import Project
from .types import FolderTreeNode, InferDefinitionsResult, SuggestPathResult
from .workspace_service import WorkspaceService


class AiService:
    """AI 辅助服务：路径建议、定义推断。"""

    def __init__(self, project: Project, workspace: WorkspaceService) -> None:
        self.project = project
        self.workspace = workspace
        self.project_root = Path(project.conf.editor.resource_path).resolve()
        self.pyproject_root = project.pyproject_root

    def get_folder_tree(self) -> list[FolderTreeNode]:
        """获取目录树（用于 AI 上下文）。"""
        root = self.project_root
        if not root.exists():
            return []

        def _build(node: Path) -> FolderTreeNode | None:
            if not node.is_dir():
                return None
            children = []
            for child in sorted(node.iterdir(), key=lambda x: x.name.lower()):
                if child.is_dir():
                    sub = _build(child)
                    if sub:
                        children.append(sub)
            return FolderTreeNode(name=node.name, children=children)

        tree = _build(root)
        return tree.children if tree else []

    def suggest_document_path(self, image_bytes: bytes, ai_config: AiConfig) -> SuggestPathResult:
        """AI 建议文档路径。"""
        folder_tree = self.get_folder_tree()
        return ai_suggest_document_path(image_bytes, folder_tree, ai_config)

    def _collect_existing_names(self, exclude_meta_path: str | None = None) -> list[str]:
        names: list[str] = []
        for meta_path in self.project_root.rglob("*.png.json"):
            if exclude_meta_path and str(meta_path) == exclude_meta_path:
                continue
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                defs = data.get("definitions", {})
                for def_id, definition in defs.items():
                    name = definition.get("name")
                    if name and isinstance(name, str) and "." in name:
                        names.append(name)
            except Exception:
                continue
        return names

    def _collect_current_doc_names(self, image_path: str) -> list[str]:
        meta_abs = get_safe_path(image_path, self.project).with_suffix(".png.json")
        if not meta_abs.exists():
            return []
        try:
            data = json.loads(meta_abs.read_text(encoding="utf-8"))
            return [
                d["name"] for d in data.get("definitions", {}).values()
                if d.get("name") and isinstance(d.get("name"), str) and "." in d["name"]
            ]
        except Exception:
            return []

    def infer_definitions(self, image_bytes: bytes, definitions_json: str,
                          image_path: str, ai_config: AiConfig) -> InferDefinitionsResult:
        """AI 推断定义。"""
        definitions = json.loads(definitions_json)
        folder_path = "/".join(image_path.replace("\\", "/").split("/")[:-1])
        image_filename = image_path.replace("\\", "/").split("/")[-1]
        current_names = self._collect_current_doc_names(image_path)
        other_names = self._collect_existing_names(
            exclude_meta_path=str(get_safe_path(image_path, self.project).with_suffix(".png.json"))
        )
        current_example = sample_name_tree(current_names, max_tokens=200)
        other_example = sample_name_tree(other_names, max_tokens=400)
        parts = []
        if current_example:
            parts.append("Current document:\n" + current_example)
        if other_example:
            parts.append("Other documents:\n" + other_example)
        name_examples = "\n\n".join(parts) if parts else None
        result = ai_infer_definitions(
            image_bytes=image_bytes,
            definitions=definitions,
            folder_path=folder_path,
            image_filename=image_filename,
            ai_config=ai_config,
            name_examples=name_examples,
        )
        return InferDefinitionsResult(definitions=result)
