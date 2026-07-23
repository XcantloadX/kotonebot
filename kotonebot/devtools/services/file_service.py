"""文件系统操作服务。

从 RestApiLogic 提取，将文件系统 CRUD 操作封装为独立服务。
"""

import os
import platform
import shutil
import subprocess
import uuid
from pathlib import Path

from kotonebot.devtools.errors import InvalidImageError, NotFoundError, ValidationError
from kotonebot.devtools.path_utils import get_safe_path, to_rel
from kotonebot.devtools.project.project import Project
from .types import DirEntry, FolderTreeNode, RenameResult, CopyResult, UploadResult


class FileService:
    """文件系统操作服务。"""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.project_root = Path(project.conf.editor.resource_path).resolve()
        self.pyproject_root = project.pyproject_root
        self.image_suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

    def _is_image_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.image_suffixes

    def list_dir(self, path: str) -> list[DirEntry]:
        """列出目录内容。

        :param path: 相对路径
        :returns: 目录条目列表
        :raises NotFoundError: 路径不存在
        :raises ValidationError: 路径不是目录
        """
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise NotFoundError("Path not found")
        if not safe_path.is_dir():
            raise ValidationError("Not a directory")

        root = self.pyproject_root
        items = []
        entries = sorted(list(safe_path.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
        for item in entries:
            is_image = self._is_image_file(item) if item.is_file() else False
            rel_item = to_rel(item, root)
            items.append(
                DirEntry(
                    name=item.name,
                    is_directory=item.is_dir(),
                    path=rel_item,
                    is_image=is_image,
                )
            )
        return items

    def read_text(self, path: str) -> str:
        """读取文本文件内容。

        :param path: 相对路径
        :returns: 文件内容
        :raises NotFoundError: 文件不存在
        :raises ValidationError: 路径不是文件
        """
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise NotFoundError("File not found")
        if not safe_path.is_file():
            raise ValidationError("Not a file")
        return safe_path.read_text(encoding="utf-8")

    def write_text(self, path: str, content: str) -> None:
        """写入文本文件（原子写入：tmp + os.replace）。

        :param path: 相对路径
        :param content: 文件内容
        :raises NotFoundError: 父目录不存在
        """
        safe_path = get_safe_path(path, self.project)
        if not safe_path.parent.exists():
            raise NotFoundError("Parent directory does not exist")
        temp_path = safe_path.with_suffix(safe_path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, safe_path)

    def rename_path(self, source_path: str, target_path: str) -> RenameResult:
        """重命名文件。

        :param source_path: 源路径
        :param target_path: 目标路径
        :returns: 重命名结果
        :raises NotFoundError: 源路径不存在或父目录不存在
        :raises ValidationError: 目标已存在或路径不是文件
        """
        safe_source = get_safe_path(source_path, self.project)
        safe_target = get_safe_path(target_path, self.project)
        if not safe_source.exists():
            raise NotFoundError(f"Source path not found: {safe_source}")
        if not safe_source.is_file():
            raise ValidationError(f"Source path is not a file: {safe_source}")
        if safe_target.exists():
            raise ValidationError(f"Target path already exists: {safe_target}")
        if not safe_target.parent.exists():
            raise NotFoundError(f"Target parent directory does not exist: {safe_target.parent}")
        os.replace(safe_source, safe_target)
        root = self.pyproject_root
        return RenameResult(
            source_path=to_rel(safe_source, root),
            target_path=to_rel(safe_target, root),
        )

    def copy_file(self, source_path: str, target_path: str) -> CopyResult:
        """拷贝文件（原子写入：tmp + os.replace）。

        :param source_path: 源路径
        :param target_path: 目标路径
        :returns: 拷贝结果
        :raises NotFoundError: 源文件或目标父目录不存在
        :raises InvalidImageError: 源文件或目标路径不是图片
        """
        safe_source = get_safe_path(source_path, self.project)
        safe_target = get_safe_path(target_path, self.project)
        if not safe_source.exists():
            raise NotFoundError(f"Source file not found: {safe_source}")
        if not safe_source.is_file():
            raise ValidationError(f"Source path is not a file: {safe_source}")
        if not self._is_image_file(safe_source):
            raise InvalidImageError(f"Source file is not an image: {safe_source}")
        if not safe_target.parent.exists():
            raise NotFoundError(f"Target parent directory does not exist: {safe_target.parent}")
        if not self._is_image_file(safe_target):
            raise InvalidImageError(f"Target path is not an image file: {safe_target}")
        temp_path = safe_target.with_name(f"{safe_target.name}.copy_tmp_{uuid.uuid4().hex}")
        try:
            shutil.copy2(safe_source, temp_path)
            os.replace(temp_path, safe_target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        root = self.pyproject_root
        return CopyResult(status="ok", target_path=to_rel(safe_target, root))

    def upload_file(self, target_path: str, file_data: bytes) -> UploadResult:
        """写入上传的文件数据（原子写入：tmp + os.replace）。

        :param target_path: 目标路径
        :param file_data: 文件数据
        :returns: 上传结果
        :raises NotFoundError: 目标父目录不存在
        :raises InvalidImageError: 目标路径不是图片
        :raises ValidationError: 上传数据为空
        """
        safe_target = get_safe_path(target_path, self.project)
        if not safe_target.parent.exists():
            raise NotFoundError(f"Target parent directory does not exist: {safe_target.parent}")
        if not self._is_image_file(safe_target):
            raise InvalidImageError(f"Target path is not an image file: {safe_target}")
        if len(file_data) == 0:
            raise ValidationError("Uploaded file data is empty")
        temp_path = safe_target.with_name(f"{safe_target.name}.upload_tmp_{uuid.uuid4().hex}")
        try:
            temp_path.write_bytes(file_data)
            os.replace(temp_path, safe_target)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise
        root = self.pyproject_root
        return UploadResult(status="ok", target_path=to_rel(safe_target, root))

    def get_folder_tree(self) -> list[FolderTreeNode]:
        """递归构建目录树（仅目录，不含文件）。

        :returns: 目录树节点列表
        """
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

    def reveal_in_explorer(self, path: str) -> None:
        """在系统文件管理器中显示文件。

        :param path: 相对路径
        :raises FileNotFoundError: 文件不存在
        """
        safe_path = get_safe_path(path, self.project)
        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        sys_platform = platform.system()
        if sys_platform == "Windows":
            subprocess.Popen(["explorer", "/select,", str(safe_path)])
        elif sys_platform == "Darwin":
            subprocess.Popen(["open", "-R", str(safe_path)])
        else:
            subprocess.Popen(["xdg-open", str(safe_path.parent)])
