export interface OpenMetaDocumentPayload {
  metaPath: string;
  imagePath?: string;
}

export interface HostOpenMetaDocumentPayload {
  metaPath: string;
}

export interface OpenSymbolPayload {
  metaPath: string;
  imagePath: string;
  definitionId: string;
}

export interface JumpToSymbolPayload {
  metaPath: string;
  imagePath: string;
  definitionId: string;
}

export interface RunEditorCommandPayload {
  command: "undo" | "redo" | "save";
}

export interface EditorDocumentStatePayload {
  metaPath: string;
  content: string;
  dirty: boolean;
}

export interface BridgeReadyPayload {
  capabilities: string[];
}

export interface BridgeErrorPayload {
  type: string;
  message: string;
}
