import * as http from "node:http";
import * as https from "node:https";
import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";
import { getDevtoolsServerConfig } from "../../lsp/client";

/** 获取全局符号树的 LSP 方法名。 */
const SYMBOL_TREE_METHOD = "kotonebot/symbolTree";
/** 符号树视图 ID。 */
const SYMBOL_TREE_VIEW_ID = "kotonebot.symbolsView";
/** 打开编辑器符号命令 ID。 */
const SYMBOL_TREE_OPEN_SYMBOL_COMMAND = "kotonebot.editor.openSymbol";
/** 手动刷新符号树命令 ID。 */
const SYMBOL_TREE_REFRESH_COMMAND = "kotonebot.symbolTree.refresh";
/** 符号树重命名命令 ID。 */
const SYMBOL_TREE_RENAME_COMMAND = "kotonebot.symbolTree.rename";
/** meta 文件匹配模式。 */
const META_PATTERN = "**/*.png.json";
/** 服务端符号重命名预检命令。 */
const SERVER_COMMAND_RENAME_SYMBOL_PRECHECK = "server.symbol.rename.precheck";
/** 服务端符号重命名执行命令。 */
const SERVER_COMMAND_RENAME_SYMBOL_EXECUTE = "server.symbol.rename.execute";

/** 符号树节点联合类型。 */
type SymbolTreeNode = GroupNode | SymbolNode | VariantNode | FileNode;

/** 命名空间分组节点，对应 name 点分路径中的中间层。 */
interface GroupNode {
  /** 节点类型标记。 */
  kind: "group";
  /** 当前分组段名。 */
  label: string;
  /** 子节点列表。 */
  children: SymbolTreeNode[];
}

/** 业务符号节点，同一个完整 name 在树中只保留一份。 */
interface SymbolNode {
  /** 节点类型标记。 */
  kind: "symbol";
  /** 显示名称（name 最后一段）。 */
  label: string;
  /** 完整符号名（点分形式）。 */
  fullName: string;
  /** 人类可读名称。 */
  displayName: string | null;
  /** variant 子节点列表。 */
  children: VariantNode[];
}

/** 变体节点，承载同一符号在不同 variant 下的文件入口。 */
interface VariantNode {
  /** 节点类型标记。 */
  kind: "variant";
  /** 变体名。 */
  label: string;
  /** 文件叶子节点列表。 */
  children: FileNode[];
}

/** 文件叶子节点，点击后仅打开文件。 */
interface FileNode {
  /** 节点类型标记。 */
  kind: "file";
  /** 展示名称（meta 文件名）。 */
  label: string;
  /** meta 文件绝对路径。 */
  metaPath: string;
  /** image 文件绝对路径。 */
  imagePath: string;
  /** definition 标识。 */
  definitionId: string;
}

/** 符号重命名影响目标。 */
interface RenameSymbolTarget {
  /** 唯一符号键。 */
  symbolKey: string;
  /** 所在 meta 文件路径。 */
  metaPath: string;
  /** 所在图片路径。 */
  imagePath: string;
  /** definition 标识。 */
  definitionId: string;
  /** variant 名称，base 为 null。 */
  variant: string | null;
  /** definition 类型。 */
  type: string;
  /** 原符号名。 */
  oldName: string;
  /** 目标符号名。 */
  newName: string;
}

/** 符号重命名预检结果。 */
interface RenameSymbolPrecheckResult {
  /** 触发重命名的源 meta。 */
  sourceMetaPath: string;
  /** 触发重命名的源 definition。 */
  sourceDefinitionId: string;
  /** 原符号名。 */
  oldName: string;
  /** 目标符号名。 */
  newName: string;
  /** 受影响目标列表。 */
  targets: RenameSymbolTarget[];
  /** 受影响 meta 文件数。 */
  affectedMetaCount: number;
  /** 受影响 definition 数。 */
  affectedDefinitionCount: number;
}

/** 符号重命名执行结果。 */
interface RenameSymbolExecuteResult extends RenameSymbolPrecheckResult {
  /** 执行后的索引版本。 */
  updatedIndexVersion: number;
  /** 执行后的索引哈希。 */
  updatedContentHash: string;
}

/** 通用 API 响应包装。 */
interface ApiEnvelope<T> {
  /** 请求是否成功。 */
  success: boolean;
  /** 错误信息。 */
  message: string | null;
  /** 返回数据。 */
  data: T | null;
}

/** 项目根配置响应（仅本功能需要的字段）。 */
interface ProjectRootData {
  editor: {
    /** pyproject 配置的 R 文件路径。 */
    r_file: string | null;
  } | null;
}

/** Python 重命名预演结果。 */
interface PythonRenamePreview {
  /** 预演得到的工作区编辑；无需改动时为 null。 */
  edit: vscode.WorkspaceEdit | null;
  /** 将被修改的 Python 文件列表。 */
  pythonFiles: string[];
}

/** 以 GET 方式请求并返回二进制内容。 */
function requestBuffer(url: string): Promise<Buffer> {
  const parsed = new URL(url);
  const sender = parsed.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = sender.request(
      parsed,
      {
        method: "GET",
        timeout: 8000,
      },
      (res) => {
        const status = res.statusCode;
        if (status === undefined || status < 200 || status >= 300) {
          reject(new Error(`Request failed with status ${String(status)}: ${url}`));
          res.resume();
          return;
        }
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => {
          chunks.push(chunk);
        });
        res.on("end", () => {
          resolve(Buffer.concat(chunks));
        });
      },
    );
    req.on("timeout", () => {
      req.destroy(new Error(`Request timeout: ${url}`));
    });
    req.on("error", (err: Error) => {
      reject(err);
    });
    req.end();
  });
}

/** 以 GET 方式请求并解析 JSON。 */
async function requestJson<T>(url: string): Promise<T> {
  const content = await requestBuffer(url);
  return JSON.parse(content.toString("utf-8")) as T;
}

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
  const rootEnvelope = await requestJson<ApiEnvelope<ProjectRootData>>(
    `http://${server.host}:${String(server.port)}/api/project/root`,
  );
  if (rootEnvelope.success !== true) {
    throw new Error(`project root request failed: ${String(rootEnvelope.message)}`);
  }
  if (rootEnvelope.data === null || rootEnvelope.data.editor === null) {
    throw new Error("project root response editor is null");
  }
  if (rootEnvelope.data.editor.r_file === null || rootEnvelope.data.editor.r_file.trim() === "") {
    throw new Error("Missing [tool.kotonebot.editor.r_file] in pyproject.toml");
  }
  return rootEnvelope.data.editor.r_file;
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
function isSymbolNode(node: SymbolTreeNode): node is SymbolNode {
  return node.kind === "symbol";
}

/** 通过 LSP `workspace/executeCommand` 调用服务端命令。 */
async function executeServerCommand(client: LanguageClient, command: string, args: Record<string, unknown>): Promise<unknown> {
  return client.sendRequest("workspace/executeCommand", { command, arguments: [args] });
}

/** 基于 symbol 树节点执行重命名流程。 */
async function renameSymbolByNode(client: LanguageClient, provider: SymbolTreeProvider, node: SymbolNode): Promise<void> {
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
  const precheck = (await executeServerCommand(client, SERVER_COMMAND_RENAME_SYMBOL_PRECHECK, {
    metaPath: target.metaPath,
    definitionId: target.definitionId,
    newName,
  })) as RenameSymbolPrecheckResult;
  const pythonRenamePreview = await buildPythonRenamePreview(precheck.oldName, precheck.newName);
  const confirm = await vscode.window.showWarningMessage(
    `Rename '${precheck.oldName}' -> '${precheck.newName}' in ${String(precheck.affectedDefinitionCount)} definition(s) across ${String(precheck.affectedMetaCount)} file(s)?`,
    { modal: true, detail: buildRenameConfirmDetail(precheck, pythonRenamePreview.pythonFiles) },
    "Rename",
  );
  if (confirm !== "Rename") {
    return;
  }
  const result = (await executeServerCommand(client, SERVER_COMMAND_RENAME_SYMBOL_EXECUTE, {
    metaPath: target.metaPath,
    definitionId: target.definitionId,
    newName,
  })) as RenameSymbolExecuteResult;
  await applyPythonRenameEdit(pythonRenamePreview);
  await provider.refresh();
  vscode.window.showInformationMessage(
    `Kotonebot symbol renamed: ${result.oldName} -> ${result.newName} (${String(result.affectedDefinitionCount)} definitions).`,
  );
}

/** 将后端返回的树结构解析为前端节点模型。 */
function parseServerTree(payload: unknown): SymbolTreeNode[] {
  if (!Array.isArray(payload)) {
    throw new Error("Invalid kotonebot/symbolTree response");
  }
  return payload.map((item) => parseTreeNode(item));
}

/** 递归解析单个树节点。 */
function parseTreeNode(value: unknown): SymbolTreeNode {
  if (typeof value !== "object" || value === null) {
    throw new Error("Invalid tree node payload");
  }
  const node = value as Record<string, unknown>;
  const kind = node.kind;
  if (kind === "group") {
    const label = node.label;
    const children = node.children;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid group.label");
    }
    if (!Array.isArray(children)) {
      throw new Error("Invalid group.children");
    }
    return {
      kind: "group",
      label,
      children: children.map((item) => parseTreeNode(item)),
    };
  }
  if (kind === "symbol") {
    const label = node.label;
    const fullName = node.fullName;
    const displayName = node.displayName;
    const children = node.children;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid symbol.label");
    }
    if (typeof fullName !== "string" || fullName.trim() === "") {
      throw new Error("Invalid symbol.fullName");
    }
    if (displayName !== null && typeof displayName !== "string") {
      throw new Error("Invalid symbol.displayName");
    }
    if (!Array.isArray(children)) {
      throw new Error("Invalid symbol.children");
    }
    return {
      kind: "symbol",
      label,
      fullName,
      displayName,
      children: children.map((item) => {
        const child = parseTreeNode(item);
        if (child.kind !== "variant") {
          throw new Error("symbol.children must be variant nodes");
        }
        return child;
      }),
    };
  }
  if (kind === "variant") {
    const label = node.label;
    const children = node.children;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid variant.label");
    }
    if (!Array.isArray(children)) {
      throw new Error("Invalid variant.children");
    }
    return {
      kind: "variant",
      label,
      children: children.map((item) => {
        const child = parseTreeNode(item);
        if (child.kind !== "file") {
          throw new Error("variant.children must be file nodes");
        }
        return child;
      }),
    };
  }
  if (kind === "file") {
    const label = node.label;
    const metaPath = node.metaPath;
    const imagePath = node.imagePath;
    const definitionId = node.definitionId;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid file.label");
    }
    if (typeof metaPath !== "string" || metaPath.trim() === "") {
      throw new Error("Invalid file.metaPath");
    }
    if (typeof imagePath !== "string" || imagePath.trim() === "") {
      throw new Error("Invalid file.imagePath");
    }
    if (typeof definitionId !== "string" || definitionId.trim() === "") {
      throw new Error("Invalid file.definitionId");
    }
    return {
      kind: "file",
      label,
      metaPath,
      imagePath,
      definitionId,
    };
  }
  throw new Error(`Unsupported node kind: ${String(kind)}`);
}

class SymbolTreeProvider implements vscode.TreeDataProvider<SymbolTreeNode> {
  /** 用于触发树视图刷新。 */
  constructor(private readonly client: LanguageClient) {}

  /** 树数据变更事件发射器。 */
  private readonly changeEmitter = new vscode.EventEmitter<SymbolTreeNode | undefined | null | void>();
  /** 当前缓存的根节点列表。 */
  private cachedRootNodes: SymbolTreeNode[] = [];
  /** 树数据变更事件。 */
  readonly onDidChangeTreeData = this.changeEmitter.event;

  /** 从服务端拉取已构建好的符号树。 */
  async refresh(): Promise<void> {
    const response = await this.client.sendRequest<unknown>(SYMBOL_TREE_METHOD, {});
    this.cachedRootNodes = parseServerTree(response);
    this.changeEmitter.fire();
  }

  /** 返回给定节点的直接子节点。 */
  getChildren(element?: SymbolTreeNode): Thenable<SymbolTreeNode[]> {
    if (!element) {
      return Promise.resolve(this.cachedRootNodes);
    }
    if (element.kind === "group") {
      return Promise.resolve(element.children);
    }
    if (element.kind === "symbol") {
      return Promise.resolve(element.children);
    }
    if (element.kind === "variant") {
      return Promise.resolve(element.children);
    }
    return Promise.resolve([]);
  }

  /** 将树节点映射为 VS Code TreeItem。 */
  getTreeItem(element: SymbolTreeNode): vscode.TreeItem {
    if (element.kind === "group") {
      const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Collapsed);
      item.iconPath = new vscode.ThemeIcon("symbol-namespace");
      return item;
    }
    if (element.kind === "symbol") {
      const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Collapsed);
      item.tooltip = element.fullName;
      item.description = element.displayName ?? undefined;
      item.iconPath = new vscode.ThemeIcon("symbol-class");
      item.contextValue = "kotonebot.symbol";
      return item;
    }
    if (element.kind === "variant") {
      if (element.children.length === 1) {
        const only = element.children[0];
        const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.None);
        item.iconPath = new vscode.ThemeIcon("symbol-enum-member");
        item.command = {
          command: SYMBOL_TREE_OPEN_SYMBOL_COMMAND,
          title: "Open Symbol In Editor",
          arguments: [{ metaPath: only.metaPath, imagePath: only.imagePath, definitionId: only.definitionId }],
        };
        return item;
      }
      const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.Collapsed);
      item.iconPath = new vscode.ThemeIcon("symbol-enum-member");
      return item;
    }
    const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.None);
    item.tooltip = element.metaPath;
    item.iconPath = new vscode.ThemeIcon("symbol-file");
    item.command = {
      command: SYMBOL_TREE_OPEN_SYMBOL_COMMAND,
      title: "Open Symbol In Editor",
      arguments: [{ metaPath: element.metaPath, imagePath: element.imagePath, definitionId: element.definitionId }],
    };
    return item;
  }
}

/** 注册符号树视图、命令与自动刷新监听。 */
export function registerSymbolTree(context: vscode.ExtensionContext, client: LanguageClient): void {
  const provider = new SymbolTreeProvider(client);
  context.subscriptions.push(vscode.window.createTreeView(SYMBOL_TREE_VIEW_ID, { treeDataProvider: provider }));

  context.subscriptions.push(
    vscode.commands.registerCommand(SYMBOL_TREE_REFRESH_COMMAND, async () => {
      await provider.refresh();
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(SYMBOL_TREE_RENAME_COMMAND, async (node: SymbolTreeNode | undefined) => {
      if (node === undefined || !isSymbolNode(node)) {
        throw new Error("kotonebot.symbolTree.rename requires a symbol tree node");
      }
      await renameSymbolByNode(client, provider, node);
    }),
  );

  const watcher = vscode.workspace.createFileSystemWatcher(META_PATTERN);
  context.subscriptions.push(watcher);
  context.subscriptions.push(watcher.onDidCreate(async () => provider.refresh()));
  context.subscriptions.push(watcher.onDidDelete(async () => provider.refresh()));
  context.subscriptions.push(watcher.onDidChange(async () => provider.refresh()));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async () => provider.refresh()));

  provider.refresh().catch((err: unknown) => {
    void vscode.window.showErrorMessage(`Kotonebot symbol tree refresh failed: ${String(err)}`);
  });
}
