from typing import Final, Literal, cast


SERVER_COMMAND_META_REFETCH: Final[Literal["server.meta.refetch"]] = "server.meta.refetch"
SERVER_COMMAND_META_UPDATE_FILE: Final[Literal["server.meta.updateFile"]] = "server.meta.updateFile"
SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE: Final[Literal["server.document.rename.execute"]] = "server.document.rename.execute"
SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK: Final[Literal["server.document.rename.precheck"]] = "server.document.rename.precheck"
SERVER_COMMAND_RENAME_SYMBOL_PRECHECK: Final[Literal["server.symbol.rename.precheck"]] = "server.symbol.rename.precheck"
SERVER_COMMAND_RENAME_SYMBOL_EXECUTE: Final[Literal["server.symbol.rename.execute"]] = "server.symbol.rename.execute"
SERVER_COMMAND_VARIANT_CLONE_TO_IMAGE: Final[Literal["server.variant.cloneToImage"]] = "server.variant.cloneToImage"
SERVER_COMMAND_VARIANT_IMPORT_IMAGE: Final[Literal["server.variant.importImage"]] = "server.variant.importImage"
SERVER_COMMAND_VARIANT_COPY_SELECTED_PREFAB_PRECHECK: Final[
    Literal["server.variant.copySelectedPrefab.precheck"]
] = "server.variant.copySelectedPrefab.precheck"

ServerCommandId = Literal[
    "server.meta.refetch",
    "server.meta.updateFile",
    "server.document.rename.execute",
    "server.document.rename.precheck",
    "server.symbol.rename.precheck",
    "server.symbol.rename.execute",
    "server.variant.cloneToImage",
    "server.variant.importImage",
    "server.variant.copySelectedPrefab.precheck",
]

SERVER_COMMAND_IDS: Final[frozenset[ServerCommandId]] = frozenset(
    {
        SERVER_COMMAND_META_REFETCH,
        SERVER_COMMAND_META_UPDATE_FILE,
        SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE,
        SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK,
        SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
        SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
        SERVER_COMMAND_VARIANT_CLONE_TO_IMAGE,
        SERVER_COMMAND_VARIANT_IMPORT_IMAGE,
        SERVER_COMMAND_VARIANT_COPY_SELECTED_PREFAB_PRECHECK,
    }
)


def ensure_server_command_id(command: str) -> ServerCommandId:
    if command not in SERVER_COMMAND_IDS:
        raise ValueError(f"Unsupported server command: {command}")
    return cast(ServerCommandId, command)
