import type { SymbolLite } from "../../model/symbolIndex";
import { quickPick } from "../../ui/quickPick";
import { COMMAND_ID, executeCommand, getPaletteCommands, getCommandStatus } from "../commands";
import type { EditorCommandContext, EditorCommandDefinition, NoArgCommandId } from "../commands";
import { useAppStore } from "../state";
import { selectActiveDocumentId } from "../commands/selectors";
import { getGlobalCommandContext } from "../EditorDialogsContext";
import { useSymbolIndexStore } from "../symbolIndexStore";
import i18n from "../../i18n";
import { listWorkspaceImages } from "../../api/fs";
import { openImageWithMeta } from "./image";

/** 命令面板中“命令项”返回值。 */
interface CommandPaletteCommandValue {
  /** 结果类型标识。 */
  kind: "command";
  /** 被选中的命令定义。 */
  command: EditorCommandDefinition<NoArgCommandId>;
}

/** 命令面板中“符号项”返回值。 */
interface CommandPaletteSymbolValue {
  /** 结果类型标识。 */
  kind: "symbol";
  /** 被选中的符号。 */
  symbol: SymbolLite;
}

/** 命令面板中"文档项"返回值。 */
interface CommandPaletteDocumentValue {
  /** 结果类型标识。 */
  kind: "document";
  /** 被选中的图片文件绝对路径。 */
  imagePath: string;
}

/** 命令面板的统一返回值。 */
type CommandPaletteValue =
  | CommandPaletteCommandValue
  | CommandPaletteSymbolValue
  | CommandPaletteDocumentValue;

/** 将输入文本切分为可用于匹配的 token。 */
function splitQueryTokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[\s._\-]+/g)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}

/** 生成符号结果主标题。 */
function buildResultTitle(symbol: SymbolLite): string {
  const main = (symbol.name || symbol.definitionId).trim();
  const displayName = (symbol.displayName || "").trim();
  if (displayName.length === 0) {
    return main;
  }
  return `${main} ${displayName}`;
}

/** 计算符号匹配分数。 */
function rankSymbol(symbol: SymbolLite, query: string, tokens: string[], activeDocumentId: string | null, recentOrder: Map<string, number>): number {
  const label = buildResultTitle(symbol).toLowerCase();
  const full = query.toLowerCase();
  const haystack = symbol.searchText.toLowerCase();

  let score = 0;
  if (label === full || symbol.definitionId.toLowerCase() === full) {
    score += 1000;
  } else if (label.startsWith(full)) {
    score += 800;
  } else if (tokens.every((token) => haystack.includes(token))) {
    score += 500;
  } else if (haystack.includes(full)) {
    score += 300;
  } else {
    return -1;
  }

  if (activeDocumentId && symbol.imagePath === activeDocumentId) {
    score += 80;
  }
  const recentIndex = recentOrder.get(symbol.symbolKey);
  if (recentIndex !== undefined) {
    score += Math.max(0, 50 - recentIndex);
  }
  return score;
}

/** 计算命令匹配分数。 */
function rankCommand(command: EditorCommandDefinition<NoArgCommandId>, query: string, tokens: string[]): number {
  if (query.trim() === "") {
    return 100;
  }
  const full = query.toLowerCase();
  const title = command.title.toLowerCase();
  const keywords = (command.keywords ?? []).join(" ").toLowerCase();
  const haystack = `${title} ${keywords}`.trim();

  if (title === full) {
    return 1000;
  }
  if (title.startsWith(full)) {
    return 800;
  }
  if (tokens.length > 0 && tokens.every((token) => haystack.includes(token))) {
    return 500;
  }
  if (haystack.includes(full)) {
    return 300;
  }
  return -1;
}

/** 计算文档匹配分数。 */
function rankDocument(imagePath: string, query: string, tokens: string[]): number {
  if (query.trim() === "") {
    return 100;
  }
  const filename = (imagePath.split("/").pop() ?? "").toLowerCase();
  const full = query.toLowerCase();
  const haystack = imagePath.toLowerCase();

  if (filename === full) {
    return 1000;
  }
  if (filename.startsWith(full)) {
    return 800;
  }
  if (tokens.length > 0 && tokens.every((token) => haystack.includes(token))) {
    return 500;
  }
  if (haystack.includes(full)) {
    return 300;
  }
  return -1;
}

/** 打开命令面板并执行用户最终选中的命令或符号跳转。 */
export async function openCommandPalette(): Promise<void> {
  const commandContext = getGlobalCommandContext();
  const selected = await quickPick.show<CommandPaletteValue>({
    title: i18n.t('commandPalette.title'),
    placeholder: i18n.t('commandPalette.placeholder'),
    emptyText: i18n.t('commandPalette.empty'),
    canOutsideClickClose: true,
    canEscapeKeyClose: true,
    getItems: async (query) => {
      const activeDocumentId = selectActiveDocumentId(useAppStore.getState());
      const { symbols, recentSymbolKeys } = useSymbolIndexStore.getState();

      // ">" 前缀：命令搜索。
      if (query.startsWith(">")) {
        const raw = query.slice(1);
        const queryTokens = splitQueryTokens(raw);
        return getPaletteCommands(commandContext)
          .map((command) => ({
            command,
            score: rankCommand(command, raw, queryTokens),
          }))
          .filter((item) => item.score >= 0)
          .sort((a, b) => b.score - a.score)
          .map((item) => {
            const status = getCommandStatus(item.command.id, commandContext, undefined);
            return {
              id: item.command.id,
              label: item.command.title,
              description: item.command.id,
              searchText: `${item.command.title} ${(item.command.keywords ?? []).join(" ")}`.trim(),
              disabled: !status.enabled,
              value: { kind: "command", command: item.command } as const,
            };
          });
      }

      // "#" 前缀：符号搜索。
      if (query.startsWith("#")) {
        const raw = query.slice(1).trim();
        if (raw.length === 0) {
          return [];
        }
        const queryTokens = splitQueryTokens(raw);
        const recentOrder = new Map<string, number>();
        for (let i = 0; i < recentSymbolKeys.length; i += 1) {
          recentOrder.set(recentSymbolKeys[i], i);
        }
        return symbols
          .map((symbol) => ({
            symbol,
            score: rankSymbol(symbol, raw, queryTokens, activeDocumentId, recentOrder),
          }))
          .filter((item) => item.score >= 0)
          .sort((a, b) => b.score - a.score)
          .slice(0, 100)
          .map((item) => {
            const symbol = item.symbol;
            const subtitle = [symbol.type, symbol.prefabId || "-", symbol.imagePath.split("/").pop() || symbol.imagePath].join(" | ");
            return {
              id: symbol.symbolKey,
              label: buildResultTitle(symbol),
              description: subtitle,
              detail: symbol.metaPath,
              searchText: symbol.searchText,
              value: { kind: "symbol", symbol } as const,
            };
          });
      }

      // 无前缀：workspace 文档搜索。
      const queryTokens = splitQueryTokens(query);
      const imagePaths = await listWorkspaceImages();
      return imagePaths
        .map((imagePath) => ({
          imagePath,
          score: rankDocument(imagePath, query, queryTokens),
        }))
        .filter((item) => item.score >= 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 100)
        .map((item) => {
          const filename = item.imagePath.split("/").pop() ?? item.imagePath;
          return {
            id: item.imagePath,
            label: filename,
            description: item.imagePath,
            searchText: item.imagePath,
            value: { kind: "document", imagePath: item.imagePath } as const,
          };
        });
    },
  });

  if (!selected) {
    return;
  }
  if (selected.kind === "document") {
    await openImageWithMeta(selected.imagePath);
    return;
  }
  if (selected.kind === "symbol") {
    await executeCommand(COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL, commandContext, { symbol: selected.symbol });
    return;
  }
  await executeCommand(selected.command.id, commandContext, undefined);
}
