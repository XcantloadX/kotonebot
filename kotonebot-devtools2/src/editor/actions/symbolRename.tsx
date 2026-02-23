import React from "react";
import { executeServerCommand } from "../../api/serverCommands";
import { readText } from "../../api/fs";
import { messageBox } from "../../ui/messageBox";
import { toaster } from "../../ui/toaster";
import { useAppStore } from "../state";
import { useSymbolIndexStore } from "../symbolIndexStore";
import { SERVER_COMMAND_ID } from "../commands/serverIds";

interface RenameSymbolTarget {
  symbolKey: string;
  metaPath: string;
  imagePath: string;
  definitionId: string;
  variant: string | null;
  type: string;
  oldName: string;
  newName: string;
}

interface RenameSymbolPrecheckResult {
  sourceMetaPath: string;
  sourceDefinitionId: string;
  oldName: string;
  newName: string;
  targets: RenameSymbolTarget[];
  affectedMetaCount: number;
  affectedDefinitionCount: number;
}

interface RenameSymbolExecuteResult extends RenameSymbolPrecheckResult {
  updatedIndexVersion: number;
  updatedContentHash: string;
}

function normalizePath(path: string): string {
  return path.split("\\").join("/").toLowerCase();
}

function buildRenameConfirmContent(precheck: RenameSymbolPrecheckResult): React.ReactNode {
  const affectedMetaPaths = Array.from(new Set(precheck.targets.map((item) => item.metaPath))).sort();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 900 }}>
      <div style={{ fontWeight: 600 }}>
        Rename {precheck.oldName} -&gt; {precheck.newName}
      </div>
      <div style={{ fontSize: 12, color: "#5c7080" }}>
        Affected definitions: {precheck.affectedDefinitionCount} | Affected files: {precheck.affectedMetaCount}
      </div>
      <div
        style={{
          maxHeight: 420,
          overflowY: "auto",
          border: "1px solid #d8e1e8",
          borderRadius: 4,
          padding: "10px",
          background: "#f8fbff",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {affectedMetaPaths.map((metaPath) => (
          <div
            key={metaPath}
            style={{
              fontFamily: "Consolas, 'Courier New', monospace",
              fontSize: 12,
              color: "#106ba3",
              background: "#ffffff",
              border: "1px solid #d8e1e8",
              borderRadius: 3,
              padding: "6px 8px",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {metaPath}
          </div>
        ))}
      </div>
    </div>
  );
}

async function saveDirtyAffectedOpenDocuments(affectedMetaPathSet: Set<string>): Promise<void> {
  const current = useAppStore.getState();
  const previousActiveId = current.activeDocumentId;
  const affectedDocIds = Object.values(current.documents)
    .filter((doc) => {
      if (!doc.meta) {
        throw new Error(`Document meta is not loaded: ${doc.id}`);
      }
      return affectedMetaPathSet.has(normalizePath(doc.meta.path));
    })
    .map((doc) => doc.id);

  for (const docId of affectedDocIds) {
    const loopState = useAppStore.getState();
    const doc = loopState.documents[docId];
    if (!doc) {
      throw new Error(`Document not found: ${docId}`);
    }
    if (!doc.meta) {
      throw new Error(`Document meta is not loaded: ${docId}`);
    }
    if (!doc.dirty) {
      continue;
    }
    loopState.setActiveDocument(docId);
    await useAppStore.getState().saveActiveDocument();
  }
  if (previousActiveId) {
    useAppStore.getState().setActiveDocument(previousActiveId);
  }
}

async function reloadAffectedOpenDocuments(affectedMetaPathSet: Set<string>): Promise<void> {
  const app = useAppStore.getState();
  for (const doc of Object.values(app.documents)) {
    if (!doc.meta) {
      throw new Error(`Document meta is not loaded: ${doc.id}`);
    }
    if (!affectedMetaPathSet.has(normalizePath(doc.meta.path))) {
      continue;
    }
    const content = await readText(doc.meta.path);
    const data = JSON.parse(content);
    if (data.version !== 2) {
      throw new Error(`Unsupported meta version: ${data.version}`);
    }
    useAppStore.getState().setActiveMeta(doc.id, data);
  }
}

export async function renameSymbolNameForActiveDefinition(definitionId: string, newNameInput: string): Promise<boolean> {
  const state = useAppStore.getState();
  const activeId = state.activeDocumentId;
  if (!activeId) {
    throw new Error("No active document");
  }
  const doc = state.documents[activeId];
  if (!doc || !doc.meta) {
    throw new Error("Active document has no meta");
  }
  const definition = doc.meta.data.definitions[definitionId];
  if (!definition) {
    throw new Error(`Definition not found: ${definitionId}`);
  }
  const oldName = definition.name ?? "";
  const newName = newNameInput.trim();
  if (newName === "") {
    throw new Error("Name cannot be empty");
  }
  if (newName === oldName) {
    return false;
  }

  const precheck = await executeServerCommand<RenameSymbolPrecheckResult>(SERVER_COMMAND_ID.SYMBOL_RENAME_PRECHECK, {
    metaPath: doc.meta.path,
    definitionId,
    newName,
  });
  const confirmed = await messageBox.confirm_cancel({
    title: "Confirm Symbol Rename",
    content: buildRenameConfirmContent(precheck),
    confirmText: "Rename",
    cancelText: "Cancel",
    confirmIntent: "primary",
    cancelIntent: "none",
  });
  if (!confirmed) {
    return false;
  }

  const affectedMetaPathSet = new Set(precheck.targets.map((item) => normalizePath(item.metaPath)));
  await saveDirtyAffectedOpenDocuments(affectedMetaPathSet);
  const result = await executeServerCommand<RenameSymbolExecuteResult>(SERVER_COMMAND_ID.SYMBOL_RENAME_EXECUTE, {
    metaPath: doc.meta.path,
    definitionId,
    newName,
  });
  await reloadAffectedOpenDocuments(affectedMetaPathSet);
  await useSymbolIndexStore.getState().refetch();
  toaster.show({
    message: `Renamed '${result.oldName}' to '${result.newName}' in ${result.affectedDefinitionCount} definition(s)`,
    intent: "success" as any,
  });
  return true;
}
