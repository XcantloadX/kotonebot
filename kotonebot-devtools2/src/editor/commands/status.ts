import { useMemo } from "react";
import { useAppStore } from "../state";
import { selectActiveDocumentId } from "./selectors";
import { editorCommandRegistry } from "./registry";
import type { EditorCommandArgsMap, EditorCommandContext, EditorCommandId } from "./types";

/** 命令状态结果。 */
export interface CommandStatus {
  /** 当前上下文是否具备执行该命令的 UI 能力。 */
  available: boolean;
  /** 当前命令是否可执行（已包含 available 判定结果）。 */
  enabled: boolean;
}

/** 命令状态查询项。 */
export type CommandStatusEntry<K extends EditorCommandId> = {
  /** 目标命令 ID。 */
  id: K;
  /** 对应命令参数。 */
  args: EditorCommandArgsMap[K];
};

/** 内部可用性判定。 */
function isAvailable<K extends EditorCommandId>(id: K, ctx: EditorCommandContext): boolean {
  const requiredUi = editorCommandRegistry[id].requiredUi;
  if (!requiredUi || requiredUi.length === 0) {
    return true;
  }
  return requiredUi.every((key) => !!ctx.ui[key]);
}

/** 内部启用态判定。 */
function isEnabled<K extends EditorCommandId>(id: K, args: EditorCommandArgsMap[K]): boolean {
  const when = editorCommandRegistry[id].when;
  if (!when) {
    return true;
  }
  return when(args);
}

/** 获取单个命令的当前可用性与启用态。 */
export function getCommandStatus<K extends EditorCommandId>(
  id: K,
  ctx: EditorCommandContext,
  args: EditorCommandArgsMap[K],
): CommandStatus {
  const available = isAvailable(id, ctx);
  return {
    available,
    enabled: available && isEnabled(id, args),
  };
}

/** 批量获取命令状态。 */
export function getCommandStatuses<const E extends readonly CommandStatusEntry<EditorCommandId>[]>(
  entries: E,
  ctx: EditorCommandContext,
): Record<E[number]["id"], CommandStatus> {
  const result: Partial<Record<EditorCommandId, CommandStatus>> = {};
  for (const entry of entries) {
    result[entry.id] = getCommandStatus(entry.id, ctx, entry.args as never);
  }
  return result as Record<E[number]["id"], CommandStatus>;
}

/** 响应式批量命令状态接口，供 UI 统一读取。 */
export function useCommandStatuses<const E extends readonly CommandStatusEntry<EditorCommandId>[]>(
  entries: E,
  ctx: EditorCommandContext,
): Record<E[number]["id"], CommandStatus> {
  const { activeDocId, documents } = useAppStore((state) => ({
    activeDocId: selectActiveDocumentId(state),
    documents: state.documents,
  }));

  return useMemo(
    () => getCommandStatuses(entries, ctx),
    [activeDocId, documents, entries, ctx],
  );
}
