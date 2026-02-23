import * as vscode from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from "vscode-languageclient/node";

/** Devtools HTTP 服务连接配置。 */
export interface DevtoolsHttpConfig {
  /** Devtools 服务监听主机。 */
  host: string;
  /** Devtools 服务监听端口。 */
  port: number;
}

/** 读取并校验 Devtools 服务配置。 */
export function getDevtoolsServerConfig(): DevtoolsHttpConfig {
  const host = vscode.workspace.getConfiguration("kotonebot").get<string>("devtoolsServerHost") || "127.0.0.1";
  const port = vscode.workspace.getConfiguration("kotonebot").get<number>("devtoolsServerPort", 1178);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid kotonebot.devtoolsServerPort: ${port}`);
  }
  return { host, port };
}

/** 计算编辑器页面基础 URL。 */
export function getEditorBaseUrl(server: DevtoolsHttpConfig): string {
  const value = vscode.workspace.getConfiguration("kotonebot").get<string>("editorBaseUrl") || "";
  const trimmed = value.trim();
  if (trimmed === "") {
    return `http://${server.host}:${server.port}/`;
  }
  return trimmed.endsWith("/") ? trimmed : `${trimmed}/`;
}

/** 创建 Kotonebot Devtools 语言客户端实例。 */
export function createLanguageClient(context: vscode.ExtensionContext): LanguageClient {
  const lspCommand = vscode.workspace.getConfiguration("kotonebot").get<string>("lspCommand") || "kbot";
  const server = getDevtoolsServerConfig();
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const args = ["devtools-host", "--host", server.host, "--port", String(server.port)];
  if (workspaceFolder) {
    args.push("--workspace", workspaceFolder);
  }
  const serverOptions: ServerOptions = {
    command: lspCommand,
    args,
    transport: TransportKind.stdio,
  };
  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", pattern: "**/*.png.json" }],
  };
  return new LanguageClient("kotonebot-devtools", "Kotonebot Devtools", serverOptions, clientOptions);
}
