import { normalizePath } from "../shared/normalizePath";

const DEFAULT_WORKSPACE_KEY = "default";

export function toWorkspaceKey(resourceRoot: string | null | undefined): string {
  const normalized = normalizePath(resourceRoot ?? "");
  if (normalized.length === 0) {
    return DEFAULT_WORKSPACE_KEY;
  }
  // djb2 hash to avoid exposing full local path in storage key.
  let hash = 5381;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = ((hash << 5) + hash) + normalized.charCodeAt(i);
    hash |= 0;
  }
  return `ws_${(hash >>> 0).toString(36)}`;
}
