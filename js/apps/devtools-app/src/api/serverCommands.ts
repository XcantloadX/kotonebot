import { client, unwrap } from "./client";
import type { components } from "./schema";

/** 服务端命令规范。 */
export type ServerCommandSpec = components["schemas"]["ServerCommandSpec"];

export async function getServerCommands(): Promise<ServerCommandSpec[]> {
  return unwrap(client.GET("/api/server/commands"));
}

export async function executeServerCommand<T>(command: string, args: Record<string, unknown>): Promise<T> {
  const result = await unwrap(client.POST("/api/server/execute_command", { body: { command, args } }));
  // server 命令为动态分发，单个端点返回多种结果形状，由调用方按命令 ID 断言
  return result as unknown as T;
}
