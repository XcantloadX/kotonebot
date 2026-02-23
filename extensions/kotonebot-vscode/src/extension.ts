import * as vscode from "vscode";
import { createLanguageClient } from "./client";
import { registerCommands } from "./commands";

let clientStopped: Promise<void> | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const client = createLanguageClient(context);
  context.subscriptions.push({
    dispose: () => {
      clientStopped = client.stop();
    },
  });
  await client.start();
  registerCommands(context, client);
}

export async function deactivate(): Promise<void> {
  if (clientStopped) {
    await clientStopped;
  }
}
