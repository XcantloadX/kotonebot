import { fetchJson } from "./client";

export interface ServerCommandSpec {
  id: string;
  title: string;
  args_schema: Record<string, string>;
}

export async function getServerCommands(): Promise<ServerCommandSpec[]> {
  return fetchJson<ServerCommandSpec[]>("/api/server/commands");
}

export async function executeServerCommand<T>(command: string, args: Record<string, unknown>): Promise<T> {
  return fetchJson<T>("/api/server/execute_command", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command, args }),
  });
}
