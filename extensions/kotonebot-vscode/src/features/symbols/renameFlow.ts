import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";
import {
  executeServerCommand,
  RenameSymbolPrecheckResult,
} from "../../lsp/executeCommand";
import { getDevtoolsServerConfig } from "../../lsp/client";
import { fetchProjectEditorRFile } from "../../shared/kotonebotApi";
import {
  SERVER_COMMAND_RENAME_SYMBOL_EXECUTE,
  SERVER_COMMAND_RENAME_SYMBOL_PRECHECK,
} from "./constants";
import { SymbolTreeRefresher } from "./provider";
import { FileNode, PythonRenamePreview, SymbolNode, SymbolTreeNode } from "./types";

/** 校验并返回合法的 Python 标识符片段。 */
function toIdentifierSegment(raw: string): string {
  if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(raw)) {
    throw new Error(`Unsupported name segment for Python rename: ${raw}`);
  }
  return raw;
}

/** 将绝对路径转成更易读的工作区相对路径。 */
function toDisplayPath(path: string): string {
  const folder = vscode.workspace.workspaceFolders?.[0];
  if (!folder) {
    return path;
  }
  const rel = vscode.workspace.asRelativePath(vscode.Uri.file(path), false);
  if (rel === "") {
    return path;
  }
  return rel;
}

/** 向详情文本追加一个“路径分组”区块。 */
function appendPathSection(lines: string[], title: string, paths: string[], maxShow: number): void {
  lines.push(title);
  if (paths.length === 0) {
    lines.push("- (none)");
    return;
  }
  for (const path of paths.slice(0, maxShow)) {
    lines.push(`- ${toDisplayPath(path)}`);
  }
  const omitted = paths.length - Math.min(paths.length, maxShow);
  if (omitted > 0) {
    lines.push(`- ... and ${String(omitted)} more file(s)`);
  }
}

/** 构建符号重命名确认弹窗详情文本。 */
function buildRenameConfirmDetail(precheck: RenameSymbolPrecheckResult, pythonFiles: string[]): string {
  const uniqueMetaPaths = Array.from(new Set(precheck.targets.map((item) => item.metaPath))).sort();
  const lines: string[] = [];
  appendPathSection(lines, "Affected meta files:", uniqueMetaPaths, 20);
  lines.push("");
  appendPathSection(lines, "Affected python files:", pythonFiles, 20);
  return lines.join("\n");
}

/** 从项目配置读取 `r_file`。 */
async function getRFilePathFromProjectRoot(): Promise<string> {
  const server = getDevtoolsServerConfig();
  return fetchProjectEditorRFile(server);
}

/** 预演 Python 重命名并返回受影响文件列表。 */
async function buildPythonRenamePreview(oldName: string, newName: string): Promise<PythonRenamePreview> {
  const oldParts = oldName.split(".").filter((part) => part.trim() !== "");
  const newParts = newName.split(".").filter((part) => part.trim() !== "");
  if (oldParts.length === 0 || newParts.length === 0) {
    throw new Error("Symbol name cannot be empty");
  }
  if (oldParts.length !== newParts.length) {
    throw new Error("Phase 2 rename only supports terminal segment rename with unchanged path depth");
  }
  const prefixOld = oldParts.slice(0, -1).join(".");
  const prefixNew = newParts.slice(0, -1).join(".");
  if (prefixOld !== prefixNew) {
    throw new Error("Phase 2 rename only supports terminal segment rename with unchanged path prefix");
  }
  const oldTerminal = toIdentifierSegment(oldParts[oldParts.length - 1]);
  const newTerminal = toIdentifierSegment(newParts[newParts.length - 1]);
  if (oldTerminal === newTerminal) {
    return { edit: null, pythonFiles: [] };
  }

  const rFilePath = await getRFilePathFromProjectRoot();
  const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(rFilePath));
  const text = doc.getText();
  const pattern = new RegExp(`\\b${oldTerminal}\\b`, "g");
  const match = pattern.exec(text);
  if (match === null) {
    throw new Error(`Cannot find symbol token '${oldTerminal}' in r_file: ${rFilePath}`);
  }
  const at = doc.positionAt(match.index);
  const edit = await vscode.commands.executeCommand<vscode.WorkspaceEdit | null>(
    "vscode.executeDocumentRenameProvider",
    doc.uri,
    at,
    newTerminal,
  );
  if (edit === null) {
    throw new Error("No rename provider result from vscode.executeDocumentRenameProvider");
  }
  const pythonFiles = edit
    .entries()
    .map(([uri]) => uri.fsPath)
    .filter((path) => {
      const lowered = path.toLowerCase();
      return lowered.endsWith(".py") || lowered.endsWith(".pyi");
    })
    .sort();
  return {
    edit,
    pythonFiles: Array.from(new Set(pythonFiles)),
  };
}

/** 应用 Python 重命名预演得到的编辑。 */
async function applyPythonRenameEdit(preview: PythonRenamePreview): Promise<void> {
  if (preview.edit === null) {
    return;
  }
  const applied = await vscode.workspace.applyEdit(preview.edit);
  if (!applied) {
    throw new Error("Failed to apply python rename workspace edit");
  }
}

/** 从符号节点中提取可执行重命名的代表文件节点。 */
function firstFileNodeForSymbol(node: SymbolNode): FileNode {
  const firstVariant = node.children[0];
  if (firstVariant === undefined) {
    throw new Error(`No variant node found for symbol: ${node.fullName}`);
  }
  const firstFile = firstVariant.children[0];
  if (firstFile === undefined) {
    throw new Error(`No file node found for symbol: ${node.fullName}`);
  }
  return firstFile;
}

/** 类型守卫：判断节点是否为 symbol 节点。 */
export function isSymbolNode(node: SymbolTreeNode): node is SymbolNode {
  return node.kind === "symbol";
}

/** 基于 symbol 树节点执行重命名流程。 */
export async function renameSymbolByNode(
  client: LanguageClient,
  provider: SymbolTreeRefresher,
  node: SymbolNode,
): Promise<void> {
  const target = firstFileNodeForSymbol(node);
  const input = await vscode.window.showInputBox({
    prompt: "Rename symbol (meta name)",
    value: node.fullName,
  });
  if (input === undefined) {
    return;
  }
  const newName = input.trim();
  if (newName === "") {
    throw new Error("newName cannot be empty");
  }
  if (newName === node.fullName) {
    return;
  }
  const precheck = await executeServerCommand(client, SERVER_COMMAND_RENAME_SYMBOL_PRECHECK, {
    metaPath: target.metaPath,
    definitionId: target.definitionId,
    newName,
  });
  const pythonRenamePreview = await buildPythonRenamePreview(precheck.oldName, precheck.newName);
  const confirm = await vscode.window.showWarningMessage(
    `Rename '${precheck.oldName}' -> '${precheck.newName}' in ${String(precheck.affectedDefinitionCount)} definition(s) across ${String(precheck.affectedMetaCount)} file(s)?`,
    { modal: true, detail: buildRenameConfirmDetail(precheck, pythonRenamePreview.pythonFiles) },
    "Rename",
  );
  if (confirm !== "Rename") {
    return;
  }
  const result = await executeServerCommand(client, SERVER_COMMAND_RENAME_SYMBOL_EXECUTE, {
    metaPath: target.metaPath,
    definitionId: target.definitionId,
    newName,
  });
  await applyPythonRenameEdit(pythonRenamePreview);
  await provider.refresh();
  vscode.window.showInformationMessage(
    `Kotonebot symbol renamed: ${result.oldName} -> ${result.newName} (${String(result.affectedDefinitionCount)} definitions).`,
  );
}
