import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";
import { SYMBOL_TREE_METHOD, SYMBOL_TREE_OPEN_SYMBOL_COMMAND } from "./constants";
import { parseServerTree } from "./parser";
import { SymbolTreeNode } from "./types";

/** 符号树刷新能力抽象。 */
export interface SymbolTreeRefresher {
  refresh(): Promise<void>;
}

/** 符号树数据提供器。 */
export class SymbolTreeProvider implements vscode.TreeDataProvider<SymbolTreeNode>, SymbolTreeRefresher {
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
