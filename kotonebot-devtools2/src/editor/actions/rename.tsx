import { Intent } from '@blueprintjs/core';
import { executeRenameDocument, precheckRenameDocument } from "../../api/fs";
import { toaster } from "../../ui/toaster";
import { messageBox } from "../../ui/messageBox";
import { useSymbolIndexStore } from "../symbolIndexStore";
import { useAppStore } from "../state";
import i18n from "../../i18n";

export async function promptAndRenameActiveDocument(): Promise<void> {
  const current = useAppStore.getState();
  const activeId = current.activeDocumentId;
  if (!activeId) {
    throw new Error("No active document");
  }
  const activeDoc = current.documents[activeId];
  if (!activeDoc) {
    throw new Error(`Document not found: ${activeId}`);
  }
  if (!activeDoc.meta) {
    throw new Error(`Document meta is not loaded: ${activeId}`);
  }

  const input = await messageBox.prompt({
    title: i18n.t('document.rename'),
    content: `${i18n.t('document.currentPath')}:\n${activeId}`,
    defaultValue: activeId,
    placeholder: i18n.t('document.enterNewPath'),
    confirmText: i18n.t('variant.rename'),
  });
  if (input === null) {
    return;
  }
  const nextPath = input.trim();
  if (nextPath === "") {
    throw new Error("New path cannot be empty");
  }
  if (nextPath === activeId) {
    return;
  }
  if (current.documents[nextPath]) {
    throw new Error(`Document already opened: ${nextPath}`);
  }

  await current.saveActiveDocument();

  const precheck = await precheckRenameDocument(activeId, nextPath);
  if (precheck.hasConflicts) {
    await messageBox.ok({
      title: i18n.t('document.renameBlocked'),
      content: precheck.conflicts.join("\n"),
    });
    return;
  }
  if (precheck.fileRenames.length === 0) {
    throw new Error("No files to rename");
  }

  const confirmed = await messageBox.confirm_cancel({
    title: i18n.t('document.confirmRenamePreview'),
    content: (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 900 }}>
        <div style={{ fontWeight: 600 }}>
          {i18n.t('document.plannedRenames')} ({precheck.fileRenames.length})
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
            gap: 10,
          }}
        >
          {precheck.fileRenames.map((item, idx) => (
            <div
              key={`${item.kind}-${item.variant}-${item.sourcePath}-${idx}`}
              style={{
                border: "1px solid #d8e1e8",
                borderRadius: 4,
                background: "#ffffff",
                padding: "8px 10px",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ fontSize: 12, color: "#5c7080" }}>
                {item.variant} · {item.kind}
              </div>
              <div
                style={{
                  fontFamily: "Consolas, 'Courier New', monospace",
                  fontSize: 12,
                  color: "#106ba3",
                  background: "#f2f8ff",
                  border: "1px solid #d8e1e8",
                  borderRadius: 3,
                  padding: "6px 8px",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {item.sourcePath}
              </div>
              <div style={{ color: "#f29d49", fontSize: 13, fontWeight: 600 }}>-&gt;</div>
              <div
                style={{
                  fontFamily: "Consolas, 'Courier New', monospace",
                  fontSize: 12,
                  color: "#0a6640",
                  background: "#edf8f3",
                  border: "1px solid #cce8dc",
                  borderRadius: 3,
                  padding: "6px 8px",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {item.targetPath}
              </div>
            </div>
          ))}
        </div>
      </div>
    ),
    confirmText: i18n.t('variant.rename'),
    cancelText: i18n.t('dialog.cancel'),
    confirmIntent: "primary",
    cancelIntent: "none",
  });
  if (!confirmed) {
    return;
  }

  const beforeSaveState = useAppStore.getState();
  const previousActiveId = beforeSaveState.activeDocumentId;
  const affectedSourceImages = new Set(precheck.documents.map((item) => item.sourceImagePath));
  for (const sourceImagePath of affectedSourceImages) {
    const loopState = useAppStore.getState();
    const targetDoc = loopState.documents[sourceImagePath];
    if (!targetDoc) {
      continue;
    }
    if (!targetDoc.meta) {
      throw new Error(`Document meta is not loaded: ${sourceImagePath}`);
    }
    if (targetDoc.dirty) {
      loopState.setActiveDocument(sourceImagePath);
      await useAppStore.getState().saveActiveDocument();
    }
  }
  if (previousActiveId) {
    useAppStore.getState().setActiveDocument(previousActiveId);
  }

  const result = await executeRenameDocument(activeId, nextPath);
  const stateAfterExecute = useAppStore.getState();
  const openedRenames = result.documents
    .filter((item) => !!stateAfterExecute.documents[item.sourceImagePath])
    .map((item) => ({ oldId: item.sourceImagePath, newId: item.targetImagePath }));
  if (openedRenames.length > 0) {
    useAppStore.getState().renameDocuments(openedRenames);
  }
  await useSymbolIndexStore.getState().refetch();
  toaster.show({ message: i18n.t('document.renamedCount', { count: result.renamedDocumentCount }), intent: Intent.SUCCESS });
}
