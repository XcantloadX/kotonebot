from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from kotonebot.devtools.errors import CommandError
from kotonebot.devtools.path_utils import unify_path
from kotonebot.devtools.commands.commands import SERVER_COMMAND_IDS, ServerCommandId
from kotonebot.devtools.commands.types import parse_server_command_request
from kotonebot.devtools.indexing.symbol_index_view import DiagnosticPayloadModel
from kotonebot.devtools.services.context import DevtoolsContext

METHOD_SYMBOL_TREE = "kotonebot/symbolTree"


def path_to_uri(path: str) -> str:
    return Path(path).resolve().as_uri()


def uri_to_normalized_path(uri: str) -> str | None:
    parsed = urlparse(uri)
    if parsed.scheme != "file":
        return None
    raw_path = unquote(parsed.path)
    if raw_path.startswith("/") and len(raw_path) >= 3 and raw_path[2] == ":":
        raw_path = raw_path[1:]
    return unify_path(raw_path)


def diagnostic_severity_to_lsp(severity: str) -> lsp.DiagnosticSeverity:
    if severity == "error":
        return lsp.DiagnosticSeverity.Error
    if severity == "warning":
        return lsp.DiagnosticSeverity.Warning
    return lsp.DiagnosticSeverity.Information


def to_lsp_diagnostic(item: DiagnosticPayloadModel) -> lsp.Diagnostic:
    line = item.line - 1
    column = item.column - 1
    end_line = item.endLine - 1
    end_column = item.endColumn - 1
    if end_line < line:
        end_line = line
    if end_column <= column:
        end_column = column + 1
    return lsp.Diagnostic(
        range=lsp.Range(
            start=lsp.Position(line=line, character=column),
            end=lsp.Position(line=end_line, character=end_column),
        ),
        severity=diagnostic_severity_to_lsp(item.severity),
        code=item.code,
        source="kotonebot",
        message=item.message,
    )


class DevtoolsLspServer(LanguageServer):
    def __init__(self, ctx: DevtoolsContext) -> None:
        super().__init__("kotonebot-devtools-lsp", "0.1.0")
        self.ctx = ctx
        self.open_documents: set[str] = set()

    def publish_all_diagnostics(self) -> None:
        snapshot = self.ctx.workspace.get_meta_diagnostics()
        by_file = snapshot.diagnosticsByFile
        opened_by_path: dict[str, str] = {}
        for uri in self.open_documents:
            normalized = uri_to_normalized_path(uri)
            if normalized is not None:
                opened_by_path[normalized] = uri
        published_paths: set[str] = set()

        for meta_path, items in by_file.items():
            normalized = unify_path(meta_path)
            published_paths.add(normalized)
            uri = opened_by_path.get(normalized, path_to_uri(meta_path))
            diagnostics = [to_lsp_diagnostic(item) for item in items]
            self.text_document_publish_diagnostics(
                lsp.PublishDiagnosticsParams(
                    uri=uri,
                    diagnostics=diagnostics,
                )
            )
        for normalized, uri in opened_by_path.items():
            if normalized in published_paths:
                continue
            self.text_document_publish_diagnostics(
                lsp.PublishDiagnosticsParams(
                    uri=uri,
                    diagnostics=[],
                )
            )

    def execute_server_command(self, command_id: ServerCommandId, args: tuple[Any, ...]) -> dict[str, Any]:
        payload = _first_argument_dict(args)
        request = parse_server_command_request({"command": command_id, "args": payload})
        dispatcher = self.ctx.command_dispatcher
        result = dispatcher.execute(request)
        self.publish_all_diagnostics()
        return result.model_dump()

    def get_symbol_tree(self):
        """委托给 WorkspaceService 的统一符号树构建。"""
        return self.ctx.workspace.get_symbol_tree()


def _first_argument_dict(args: tuple[Any, ...]) -> dict[str, Any]:
    if len(args) == 0:
        return {}
    if len(args) != 1:
        raise CommandError("workspace/executeCommand arguments supports at most one object")
    payload = args[0]
    if not isinstance(payload, dict):
        raise CommandError("workspace/executeCommand argument must be object")
    return payload


def _register_features(server: DevtoolsLspServer) -> None:
    @server.feature(lsp.INITIALIZED)
    def _on_initialized(ls: DevtoolsLspServer, _params: lsp.InitializedParams) -> None:
        ls.publish_all_diagnostics()

    @server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
    def _on_did_open(ls: DevtoolsLspServer, params: lsp.DidOpenTextDocumentParams) -> None:
        ls.open_documents.add(params.text_document.uri)
        ls.publish_all_diagnostics()

    @server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
    def _on_did_save(ls: DevtoolsLspServer, params: lsp.DidSaveTextDocumentParams) -> None:
        ls.open_documents.add(params.text_document.uri)
        ls.publish_all_diagnostics()

    @server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
    def _on_did_close(ls: DevtoolsLspServer, params: lsp.DidCloseTextDocumentParams) -> None:
        uri = params.text_document.uri
        ls.open_documents.discard(uri)
        ls.text_document_publish_diagnostics(
            lsp.PublishDiagnosticsParams(
                uri=uri,
                diagnostics=[],
            )
        )

    @server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
    def _on_did_change(_ls: DevtoolsLspServer, _params: lsp.DidChangeTextDocumentParams) -> None:
        return

    @server.feature(METHOD_SYMBOL_TREE)
    def _on_symbol_tree(ls: DevtoolsLspServer, _params: Any = None):
        return [node.model_dump(mode="json") for node in ls.get_symbol_tree()]

    for command in SERVER_COMMAND_IDS:
        def _make_handler(command_id: ServerCommandId):
            @server.command(command_id)
            def _command_handler(ls: DevtoolsLspServer, *args: Any) -> dict[str, Any]:
                return ls.execute_server_command(command_id, cast(tuple[Any, ...], args))

            return _command_handler

        _make_handler(command)


def run_lsp(ctx: DevtoolsContext) -> None:
    """启动 LSP 服务（stdio 阻塞）。"""
    server = DevtoolsLspServer(ctx)
    _register_features(server)
    server.start_io()
