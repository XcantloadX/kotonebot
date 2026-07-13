from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from kotonebot.devtools.errors import ValidationError
from kotonebot.devtools.path_utils import unify_path
from kotonebot.devtools.server_commands.commands import SERVER_COMMAND_IDS, ServerCommandId
from kotonebot.devtools.server_commands.types import parse_server_command_request
from kotonebot.devtools.indexing.symbol_index_view import DiagnosticPayloadModel
from kotonebot.devtools.project.project import Project
from kotonebot.devtools.server_commands.workspace_service import WorkspaceService

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
    def __init__(self, *, workspace: str | None = None) -> None:
        super().__init__("kotonebot-devtools-lsp", "0.1.0")
        root = Path(workspace).resolve() if workspace else Path.cwd().resolve()
        conf_path = root / "pyproject.toml"
        project = Project(conf_path=str(conf_path))
        self.workspace_service = WorkspaceService(project)
        self.open_documents: set[str] = set()

    def publish_all_diagnostics(self) -> None:
        snapshot = self.workspace_service.get_meta_diagnostics()
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
        result = self.workspace_service.execute_server_command(request)
        self.publish_all_diagnostics()
        return result.model_dump()

    def get_symbol_tree(self) -> list[dict[str, Any]]:
        self.workspace_service.symbol_index_view.ensure_ready()
        symbols = list(self.workspace_service.symbol_index_view.snapshot.symbols.values())
        root: dict[str, Any] = {"kind": "group", "label": "__root__", "children": []}
        group_map: dict[str, dict[str, Any]] = {"": root}

        for symbol in symbols:
            parts = symbol.name.split(".")
            if len(parts) == 0:
                raise ValidationError(f"Invalid symbol name: {symbol.name}")
            for part in parts:
                if part.strip() == "":
                    raise ValidationError(f"Invalid symbol name segment: {symbol.name}")

            current_path = ""
            current_group = root
            for segment in parts[:-1]:
                current_path = segment if current_path == "" else f"{current_path}.{segment}"
                next_group = group_map.get(current_path)
                if next_group is None:
                    next_group = {"kind": "group", "label": segment, "children": []}
                    group_map[current_path] = next_group
                    current_group["children"].append(next_group)
                current_group = next_group

            leaf_label = parts[-1]
            full_name = ".".join(parts)
            symbol_node = None
            for node in current_group["children"]:
                if node["kind"] == "symbol" and node["fullName"] == full_name:
                    symbol_node = node
                    break
            if symbol_node is None:
                symbol_node = {
                    "kind": "symbol",
                    "label": leaf_label,
                    "fullName": full_name,
                    "displayName": symbol.display_name,
                    "children": [],
                }
                current_group["children"].append(symbol_node)
            elif symbol_node["displayName"] is None and symbol.display_name is not None:
                symbol_node["displayName"] = symbol.display_name

            variant_label = "base" if symbol.variant is None else symbol.variant
            variant_node = None
            for node in symbol_node["children"]:
                if node["label"] == variant_label:
                    variant_node = node
                    break
            if variant_node is None:
                variant_node = {"kind": "variant", "label": variant_label, "children": []}
                symbol_node["children"].append(variant_node)

            already_exists = any(
                item["metaPath"] == symbol.meta_path and item["definitionId"] == symbol.definition_id
                for item in variant_node["children"]
            )
            if not already_exists:
                variant_node["children"].append(
                    {
                        "kind": "file",
                        "label": Path(symbol.meta_path).name,
                        "metaPath": symbol.meta_path,
                        "imagePath": symbol.image_path,
                        "definitionId": symbol.definition_id,
                    }
                )

        def sort_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
            groups: list[dict[str, Any]] = []
            symbols_nodes: list[dict[str, Any]] = []
            for node in nodes:
                kind = node["kind"]
                if kind == "group":
                    node["children"] = sort_nodes(node["children"])
                    groups.append(node)
                    continue
                if kind == "symbol":
                    node["children"].sort(key=lambda item: item["label"])
                    for variant in node["children"]:
                        variant["children"].sort(key=lambda item: item["metaPath"])
                    symbols_nodes.append(node)
                    continue
                raise ValidationError(f"Unexpected root node kind: {kind}")
            groups.sort(key=lambda item: item["label"])
            symbols_nodes.sort(key=lambda item: item["fullName"])
            return [*groups, *symbols_nodes]

        return sort_nodes(root["children"])


def _first_argument_dict(args: tuple[Any, ...]) -> dict[str, Any]:
    if len(args) == 0:
        return {}
    if len(args) != 1:
        raise ValidationError("workspace/executeCommand arguments supports at most one object")
    payload = args[0]
    if not isinstance(payload, dict):
        raise ValidationError("workspace/executeCommand argument must be object")
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
    def _on_symbol_tree(ls: DevtoolsLspServer, _params: Any = None) -> list[dict[str, Any]]:
        return ls.get_symbol_tree()

    for command in SERVER_COMMAND_IDS:
        def _make_handler(command_id: ServerCommandId):
            @server.command(command_id)
            def _command_handler(ls: DevtoolsLspServer, *args: Any) -> dict[str, Any]:
                return ls.execute_server_command(command_id, cast(tuple[Any, ...], args))

            return _command_handler

        _make_handler(command)


def run_lsp_server(workspace: str | None = None) -> None:
    server = DevtoolsLspServer(workspace=workspace)
    _register_features(server)
    server.start_io()
