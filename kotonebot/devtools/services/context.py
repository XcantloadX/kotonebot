"""Devtools 运行时上下文。

所有传输层共享同一个 Context 实例，确保状态一致。
"""

from pathlib import Path
from typing import Optional

from kotonebot.devtools.commands.dispatch import CommandDispatcher
from kotonebot.devtools.conversion.service import ConversionService
from kotonebot.devtools.project.project import Project

from .workspace_service import WorkspaceService
from .file_service import FileService
from .image_service import ImageService
from .ai_service import AiService
from .device_service import DeviceService
from .health_service import HealthService


class DevtoolsContext:
    """Devtools 运行时上下文，持有所有服务实例。

    所有传输层共享同一个 Context 实例，确保状态（索引缓存、prefab schema 等）一致。
    """

    def __init__(self, project: Project) -> None:
        self.project: Project = project
        self.workspace: WorkspaceService = WorkspaceService(project)
        self.files: FileService = FileService(project)
        self.images: ImageService = ImageService(project)
        self.ai: AiService = AiService(project, self.workspace)
        self.device: DeviceService = DeviceService(project)
        self.health: HealthService = HealthService()
        self._command_dispatcher = None
        self._conversion: Optional[ConversionService] = None

    @property
    def conversion(self) -> ConversionService:
        """格式转换服务，懒加载。"""
        if self._conversion is None:
            self._conversion = ConversionService(self.project)
        return self._conversion

    @property
    def command_dispatcher(self) -> CommandDispatcher:
        """命令分发器，懒加载。"""
        if self._command_dispatcher is None:
            self._command_dispatcher = CommandDispatcher(self.workspace)
        return self._command_dispatcher

    @classmethod
    def from_workspace(cls, workspace: str | None = None) -> "DevtoolsContext":
        """从工作区路径创建上下文。"""
        if workspace is None:
            project = Project()
        else:
            conf_path = (Path(workspace).resolve() / "pyproject.toml").as_posix()
            project = Project(conf_path=conf_path)
        return cls(project)
