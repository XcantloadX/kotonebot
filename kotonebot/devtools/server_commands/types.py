from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from kotonebot.devtools.indexing.document_index_view import (
    RenameDocumentExecuteResultModel,
    RenameDocumentPrecheckResultModel,
)
from kotonebot.devtools.indexing.symbol_index_view import (
    MetaDiagnosticsSnapshotModel,
    SymbolSnapshotLiteModel,
    SymbolUpdateResultModel,
)

from .commands import (
    SERVER_COMMAND_META_REFETCH,
    SERVER_COMMAND_META_UPDATE_FILE,
    SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE,
    SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK,
    SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
    SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
    SERVER_COMMAND_VARIANT_CLONE_TO_IMAGE,
    SERVER_COMMAND_VARIANT_COPY_SELECTED_PREFAB_PRECHECK,
    SERVER_COMMAND_VARIANT_IMPORT_IMAGE,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ServerCommandSpec(StrictModel):

    id: str
    title: str
    args_schema: dict[str, str]


class MetaRefetchResult(StrictModel):

    index: SymbolSnapshotLiteModel
    diagnostics: MetaDiagnosticsSnapshotModel


class VariantCloneToImageResult(StrictModel):

    targetMetaPath: str
    definitionCount: int


class VariantImportImageResult(StrictModel):

    targetImagePath: str
    size: int


class VariantCopySelectedPrefabPrecheckResult(StrictModel):

    targetImagePath: str
    targetImageExists: bool
    targetMetaPath: str
    targetMetaExists: bool
    targetDefinitionExists: bool
    sourceDefinitionId: str
    sourceDefinitionName: str
    targetDefinition: dict[str, Any]


class RenameSymbolTargetModel(StrictModel):

    symbolKey: str
    metaPath: str
    imagePath: str
    definitionId: str
    variant: str | None
    type: str
    oldName: str
    newName: str


class RenameSymbolPrecheckResult(StrictModel):

    sourceMetaPath: str
    sourceDefinitionId: str
    oldName: str
    newName: str
    targets: list[RenameSymbolTargetModel]
    affectedMetaCount: int
    affectedDefinitionCount: int


class RenameSymbolExecuteResult(StrictModel):

    sourceMetaPath: str
    sourceDefinitionId: str
    oldName: str
    newName: str
    targets: list[RenameSymbolTargetModel]
    affectedMetaCount: int
    affectedDefinitionCount: int
    updatedIndexVersion: int
    updatedContentHash: str


class EmptyArgs(StrictModel):
    pass

class MetaUpdateFileArgs(StrictModel):

    metaPath: str


class RenameDocumentArgs(StrictModel):

    sourceImagePath: str
    targetImagePath: str


class RenameSymbolArgs(StrictModel):

    metaPath: str
    definitionId: str
    newName: str


class VariantCloneToImageArgs(StrictModel):

    sourceMetaPath: str
    targetImagePath: str
    variant: str
    forceOverwrite: bool = False


class VariantImportImageArgs(StrictModel):

    baseImagePath: str
    variant: str
    imageDataBase64: str
    deleteExistingTarget: bool = False


class VariantCopySelectedPrefabPrecheckArgs(StrictModel):

    sourceMetaPath: str
    sourceDefinitionId: str
    baseImagePath: str
    variant: str


class MetaRefetchCommand(StrictModel):

    command: Literal["server.meta.refetch"] = Field(default=SERVER_COMMAND_META_REFETCH, frozen=True)
    args: EmptyArgs = Field(default_factory=EmptyArgs)


class MetaUpdateFileCommand(StrictModel):

    command: Literal["server.meta.updateFile"] = Field(default=SERVER_COMMAND_META_UPDATE_FILE, frozen=True)
    args: MetaUpdateFileArgs


class RenameDocumentPrecheckCommand(StrictModel):

    command: Literal["server.document.rename.precheck"] = Field(default=SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK, frozen=True)
    args: RenameDocumentArgs


class RenameDocumentExecuteCommand(StrictModel):

    command: Literal["server.document.rename.execute"] = Field(default=SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE, frozen=True)
    args: RenameDocumentArgs


class RenameSymbolPrecheckCommand(StrictModel):

    command: Literal["server.symbol.rename.precheck"] = Field(default=SERVER_COMMAND_RENAME_SYMBOL_PRECHECK, frozen=True)
    args: RenameSymbolArgs


class RenameSymbolExecuteCommand(StrictModel):

    command: Literal["server.symbol.rename.execute"] = Field(default=SERVER_COMMAND_RENAME_SYMBOL_EXECUTE, frozen=True)
    args: RenameSymbolArgs


class VariantCloneToImageCommand(StrictModel):

    command: Literal["server.variant.cloneToImage"] = Field(default=SERVER_COMMAND_VARIANT_CLONE_TO_IMAGE, frozen=True)
    args: VariantCloneToImageArgs


class VariantImportImageCommand(StrictModel):

    command: Literal["server.variant.importImage"] = Field(default=SERVER_COMMAND_VARIANT_IMPORT_IMAGE, frozen=True)
    args: VariantImportImageArgs


class VariantCopySelectedPrefabPrecheckCommand(StrictModel):

    command: Literal["server.variant.copySelectedPrefab.precheck"] = Field(
        default=SERVER_COMMAND_VARIANT_COPY_SELECTED_PREFAB_PRECHECK,
        frozen=True,
    )
    args: VariantCopySelectedPrefabPrecheckArgs


ServerCommandRequest: TypeAlias = Annotated[
    MetaRefetchCommand
    | MetaUpdateFileCommand
    | RenameDocumentPrecheckCommand
    | RenameDocumentExecuteCommand
    | RenameSymbolPrecheckCommand
    | RenameSymbolExecuteCommand
    | VariantCloneToImageCommand
    | VariantImportImageCommand
    | VariantCopySelectedPrefabPrecheckCommand,
    Field(discriminator="command"),
]

_SERVER_COMMAND_REQUEST_ADAPTER = TypeAdapter(ServerCommandRequest)

ServerCommandResponse: TypeAlias = (
    MetaRefetchResult
    | SymbolUpdateResultModel
    | RenameDocumentPrecheckResultModel
    | RenameDocumentExecuteResultModel
    | RenameSymbolPrecheckResult
    | RenameSymbolExecuteResult
    | VariantCloneToImageResult
    | VariantImportImageResult
    | VariantCopySelectedPrefabPrecheckResult
)


def parse_server_command_request(payload: dict[str, Any]) -> ServerCommandRequest:
    try:
        return _SERVER_COMMAND_REQUEST_ADAPTER.validate_python(payload)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
