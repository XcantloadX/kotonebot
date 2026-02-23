import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";

const SYMBOL_TREE_METHOD = "kotonebot/symbolTree";
const SYMBOL_TREE_VIEW_ID = "kotonebot.symbolsView";
const SYMBOL_TREE_OPEN_FILE_COMMAND = "kotonebot.symbolTree.openFile";
const SYMBOL_TREE_REFRESH_COMMAND = "kotonebot.symbolTree.refresh";
const META_PATTERN = "**/*.png.json";

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
}

/** 将后端返回的树结构解析为前端节点模型。 */
function parseServerTree(payload: unknown): SymbolTreeNode[] {
  if (!Array.isArray(payload)) {
    throw new Error("Invalid kotonebot/symbolTree response");
  }
  return payload.map((item) => parseTreeNode(item));
}

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
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid file.label");
    }
    if (typeof metaPath !== "string" || metaPath.trim() === "") {
      throw new Error("Invalid file.metaPath");
    }
    return {
      kind: "file",
      label,
      metaPath,
    };
  }
  throw new Error(`Unsupported node kind: ${String(kind)}`);
}

class SymbolTreeProvider implements vscode.TreeDataProvider<SymbolTreeNode> {
  /** 用于触发树视图刷新。 */
  constructor(private readonly client: LanguageClient) {}

  private readonly changeEmitter = new vscode.EventEmitter<SymbolTreeNode | undefined | null | void>();
  private cachedRootNodes: SymbolTreeNode[] = [];
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
      return item;
    }
    if (element.kind === "variant") {
      if (element.children.length === 1) {
        const only = element.children[0];
        const item = new vscode.TreeItem(element.label, vscode.TreeItemCollapsibleState.None);
        item.iconPath = new vscode.ThemeIcon("symbol-enum-member");
        item.command = {
          command: SYMBOL_TREE_OPEN_FILE_COMMAND,
          title: "Open File",
          arguments: [only.metaPath],
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
      command: SYMBOL_TREE_OPEN_FILE_COMMAND,
      title: "Open File",
      arguments: [element.metaPath],
    };
    return item;
  }
}

/** 注册符号树视图、命令与自动刷新监听。 */
export function registerSymbolTree(context: vscode.ExtensionContext, client: LanguageClient): void {
  const provider = new SymbolTreeProvider(client);
  context.subscriptions.push(vscode.window.createTreeView(SYMBOL_TREE_VIEW_ID, { treeDataProvider: provider }));

  context.subscriptions.push(
    vscode.commands.registerCommand(SYMBOL_TREE_OPEN_FILE_COMMAND, async (metaPath: string) => {
      if (typeof metaPath !== "string" || metaPath.trim() === "") {
        throw new Error("metaPath is required");
      }
      const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(metaPath));
      await vscode.window.showTextDocument(doc, { preview: false });
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand(SYMBOL_TREE_REFRESH_COMMAND, async () => {
      await provider.refresh();
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
