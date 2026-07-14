import * as vscode from "vscode";

interface EditorDocumentStatePayload {
  metaPath: string;
  content: string;
  dirty: boolean;
}

function normalizeToDocumentEol(content: string, eol: vscode.EndOfLine): string {
  const normalized = content.replace(/\r\n/g, "\n");
  if (eol === vscode.EndOfLine.CRLF) {
    return normalized.replace(/\n/g, "\r\n");
  }
  return normalized;
}

export function defaultMetaContent(): Uint8Array {
  const payload = JSON.stringify({ version: 3, definitions: {} }, null, 2);
  return new TextEncoder().encode(payload);
}

export function parseEditorDocumentStatePayload(value: unknown): EditorDocumentStatePayload {
  if (typeof value !== "object" || value === null) {
    throw new Error("kotonebot.editor.documentState payload is required");
  }
  const payload = value as Partial<EditorDocumentStatePayload>;
  if (typeof payload.metaPath !== "string" || payload.metaPath.trim() === "") {
    throw new Error("kotonebot.editor.documentState payload.metaPath is required");
  }
  if (!payload.metaPath.toLowerCase().endsWith(".png.json")) {
    throw new Error(`kotonebot.editor.documentState payload.metaPath must end with .png.json: ${payload.metaPath}`);
  }
  if (typeof payload.content !== "string") {
    throw new Error("kotonebot.editor.documentState payload.content must be string");
  }
  if (typeof payload.dirty !== "boolean") {
    throw new Error("kotonebot.editor.documentState payload.dirty must be boolean");
  }
  return payload as EditorDocumentStatePayload;
}

export async function syncMetaTextDocument(payload: EditorDocumentStatePayload): Promise<void> {
  const uri = vscode.Uri.file(payload.metaPath);
  const doc = await vscode.workspace.openTextDocument(uri);
  const desiredContent = normalizeToDocumentEol(payload.content, doc.eol);
  if (doc.getText() !== desiredContent) {
    const end = doc.lineAt(doc.lineCount - 1).range.end;
    const edit = new vscode.WorkspaceEdit();
    edit.replace(uri, new vscode.Range(0, 0, end.line, end.character), desiredContent);
    const applied = await vscode.workspace.applyEdit(edit);
    if (!applied) {
      throw new Error(`Failed to apply text sync edit: ${payload.metaPath}`);
    }
  }
  const latest = vscode.workspace.textDocuments.find((item) => item.uri.toString() === uri.toString());
  if (!latest) {
    throw new Error(`Text document not found after sync: ${payload.metaPath}`);
  }
  if (!payload.dirty && latest.isDirty) {
    await latest.save();
  }
}
