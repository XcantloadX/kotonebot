import { editorCommandRegistry, paletteCommandIds } from "./registry";
import type { EditorCommandArgsMap, EditorCommandContext, EditorCommandDefinition, EditorCommandId, NoArgCommandId } from "./types";

/** 判断命令在当前上下文是否具备所需 UI 能力。 */
export function isCommandAvailable<K extends EditorCommandId>(id: K, ctx: EditorCommandContext): boolean {
  const requiredUi = editorCommandRegistry[id].requiredUi;
  if (!requiredUi || requiredUi.length === 0) {
    return true;
  }
  return requiredUi.every((key) => !!ctx.ui[key]);
}

/** 判断命令在当前状态与参数下是否可执行。 */
export function isCommandEnabled<K extends EditorCommandId>(id: K, args: EditorCommandArgsMap[K]): boolean {
  const command = editorCommandRegistry[id];
  if (!command.when) {
    return true;
  }
  return command.when(args);
}

/** 执行命令，内部会先做可用性和启用态检查。 */
export async function executeCommand<K extends EditorCommandId>(
  id: K,
  ctx: EditorCommandContext,
  args: EditorCommandArgsMap[K],
): Promise<void> {
  if (!isCommandAvailable(id, ctx)) {
    console.warn(`Command "${id}" is not available: missing required UI handlers`);
    return;
  }
  if (!isCommandEnabled(id, args)) {
    return;
  }
  await editorCommandRegistry[id].run(ctx, args);
}

/** 返回当前上下文可展示在命令面板中的命令定义。 */
export function getPaletteCommands(ctx: EditorCommandContext): Array<EditorCommandDefinition<NoArgCommandId>> {
  return paletteCommandIds
    .map((id) => editorCommandRegistry[id])
    .filter((command) => isCommandAvailable(command.id, ctx)) as Array<EditorCommandDefinition<NoArgCommandId>>;
}
