import * as vscode from "vscode";
import { imageToMetaPath } from "../../shared/metaPaths";
import { BridgeSessionManager } from "./bridgeSessionManager";
import { EditorDocumentProvider } from "./editorDocumentProvider";
import { EditorCommandHandler, OpenSymbolPayload } from "./editorCommandHandler";

const VIEW_TYPE = "kotonebot.metaEditor";

const COMMAND_EDITOR_OPEN = "kotonebot.editor.open";
const COMMAND_EDITOR_OPEN_SYMBOL = "kotonebot.editor.openSymbol";
const COMMAND_META_OPEN_EDITOR = "kotonebot.meta.openEditor";
const COMMAND_META_OPEN_TEXT = "kotonebot.meta.openText";
const COMMAND_META_UNDO = "kotonebot.meta.undo";
const COMMAND_META_REDO = "kotonebot.meta.redo";
const COMMAND_META_SAVE = "kotonebot.meta.save";
const COMMAND_META_OPEN_FROM_IMAGE = "kotonebot.meta.openFromImage";

export function registerEditorPanel(
  context: vscode.ExtensionContext,
  getEditorUrl: () => string,
): void {
  const sessionManager = new BridgeSessionManager();
  const commandHandler = new EditorCommandHandler(sessionManager);
  const provider = new EditorDocumentProvider(getEditorUrl, sessionManager, commandHandler);

  context.subscriptions.push(sessionManager);
  context.subscriptions.push(
    vscode.window.registerCustomEditorProvider(VIEW_TYPE, provider, {
      webviewOptions: {
        retainContextWhenHidden: true,
      },
      supportsMultipleEditorsPerDocument: false,
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_EDITOR_OPEN, async (arg: unknown) => {
      const uri = commandHandler.getMetaUriFromCommandArg(arg);
      await commandHandler.openMetaInEditor(uri);
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_EDITOR_OPEN_SYMBOL, async (payload: OpenSymbolPayload) => {
      if (typeof payload !== "object" || payload === null) {
        throw new Error("openSymbol payload is required");
      }
      if (typeof payload.metaPath !== "string" || payload.metaPath.trim() === "") {
        throw new Error("openSymbol payload.metaPath is required");
      }
      if (typeof payload.imagePath !== "string" || payload.imagePath.trim() === "") {
        throw new Error("openSymbol payload.imagePath is required");
      }
      if (typeof payload.definitionId !== "string" || payload.definitionId.trim() === "") {
        throw new Error("openSymbol payload.definitionId is required");
      }
      await commandHandler.openSymbol(payload);
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_OPEN_EDITOR, async (arg: unknown) => {
      const uri = commandHandler.getMetaUriFromCommandArg(arg);
      await commandHandler.openMetaInEditor(uri);
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_OPEN_TEXT, async (arg: unknown) => {
      const uri = commandHandler.getMetaUriFromCommandArg(arg);
      await commandHandler.openMetaInText(uri);
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_UNDO, async (arg: unknown) => {
      const uri = commandHandler.getMetaUriFromCommandArg(arg);
      await commandHandler.runEditorCommand(uri, "undo");
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_REDO, async (arg: unknown) => {
      const uri = commandHandler.getMetaUriFromCommandArg(arg);
      await commandHandler.runEditorCommand(uri, "redo");
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_SAVE, async (arg: unknown) => {
      const uri = commandHandler.getMetaUriFromCommandArg(arg);
      await commandHandler.runEditorCommand(uri, "save");
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_OPEN_FROM_IMAGE, async (arg: unknown) => {
      const imageUri = commandHandler.getImageUriFromCommandArg(arg);
      const metaUri = vscode.Uri.file(imageToMetaPath(imageUri.fsPath));
      await commandHandler.ensureMetaDocumentExists(metaUri);
      await commandHandler.openMetaInEditor(metaUri);
    }),
  );
}
