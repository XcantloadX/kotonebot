"""跨传输命令分发器。"""

from kotonebot.devtools.commands.types import (
    ServerCommandRequest,
    ServerCommandResponse,
    MetaRefetchCommand,
    MetaUpdateFileCommand,
    RenameDocumentPrecheckCommand,
    RenameDocumentExecuteCommand,
    RenameSymbolPrecheckCommand,
    RenameSymbolExecuteCommand,
    VariantCloneToImageCommand,
    VariantImportImageCommand,
    VariantCopySelectedPrefabPrecheckCommand,
    MetaRefetchResult,
    VariantCloneToImageResult,
    VariantImportImageResult,
    VariantCopySelectedPrefabPrecheckResult,
)
from kotonebot.devtools.errors import CommandError
from kotonebot.devtools.services.workspace_service import WorkspaceService


class CommandDispatcher:
    """跨传输命令分发器。

    将 ServerCommandRequest 分发到对应的 WorkspaceService 方法。
    """

    def __init__(self, workspace: WorkspaceService) -> None:
        self.workspace = workspace

    def execute(self, request: ServerCommandRequest) -> ServerCommandResponse:
        """分发命令请求到对应的服务方法。

        :param request: 服务端命令请求
        :returns: 服务端命令响应
        :raises CommandError: 不支持的命令
        """
        if isinstance(request, MetaRefetchCommand):
            return MetaRefetchResult(
                index=self.workspace.get_meta_index(),
                diagnostics=self.workspace.get_meta_diagnostics(),
            )
        if isinstance(request, MetaUpdateFileCommand):
            return self.workspace.update_meta_index(request.args.metaPath)
        if isinstance(request, RenameDocumentPrecheckCommand):
            return self.workspace.precheck_rename_document(
                source_image_path=request.args.sourceImagePath,
                target_image_path=request.args.targetImagePath,
            )
        if isinstance(request, RenameDocumentExecuteCommand):
            return self.workspace.execute_rename_document(
                source_image_path=request.args.sourceImagePath,
                target_image_path=request.args.targetImagePath,
            )
        if isinstance(request, RenameSymbolPrecheckCommand):
            return self.workspace.precheck_rename_symbol(
                source_meta_path=request.args.metaPath,
                source_definition_id=request.args.definitionId,
                new_name=request.args.newName,
            )
        if isinstance(request, RenameSymbolExecuteCommand):
            return self.workspace.execute_rename_symbol(
                source_meta_path=request.args.metaPath,
                source_definition_id=request.args.definitionId,
                new_name=request.args.newName,
            )
        if isinstance(request, VariantCloneToImageCommand):
            result = self.workspace.clone_variant_to_image(
                source_meta_path=request.args.sourceMetaPath,
                target_image_path=request.args.targetImagePath,
                variant=request.args.variant,
                force_overwrite=request.args.forceOverwrite,
            )
            return VariantCloneToImageResult(**result.model_dump())
        if isinstance(request, VariantImportImageCommand):
            result = self.workspace.import_variant_image(
                base_image_path=request.args.baseImagePath,
                variant=request.args.variant,
                image_data=request.args.imageDataBase64.encode(),
                delete_existing_target=request.args.deleteExistingTarget,
            )
            return VariantImportImageResult(**result.model_dump())
        if isinstance(request, VariantCopySelectedPrefabPrecheckCommand):
            result = self.workspace.precheck_copy_selected_prefab_to_variant(
                source_meta_path=request.args.sourceMetaPath,
                source_definition_id=request.args.sourceDefinitionId,
                base_image_path=request.args.baseImagePath,
                variant=request.args.variant,
            )
            return VariantCopySelectedPrefabPrecheckResult(**result.model_dump())
        raise CommandError(f"Unsupported server command: {request.command}")
