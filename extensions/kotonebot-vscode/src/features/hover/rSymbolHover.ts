import * as vscode from "vscode";
import { DevtoolsHttpConfig } from "../../lsp/client";
import {
  fetchHoverPreviewImage,
  fetchMetaIndexSnapshot,
  fetchProjectBaseVariant,
  SymbolLite,
  SymbolSnapshotLite,
} from "../../shared/kotonebotApi";

const R_CHAIN_PATTERN = /R(?:\.[A-Za-z_][A-Za-z0-9_]*)+/g;
const R_TOKEN_CHARS = new Set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.");

function extractRChainAtPosition(text: string, position: vscode.Position): {
  chainText: string;
  symbolName: string;
  range: vscode.Range;
} | null {
  const lineText = text.split(/\r?\n/)[position.line];
  if (lineText === undefined || lineText.length === 0) {
    return null;
  }
  let cursor = position.character;
  if (cursor === lineText.length) {
    cursor -= 1;
  }
  if (cursor < 0 || cursor >= lineText.length) {
    return null;
  }
  if (!R_TOKEN_CHARS.has(lineText[cursor])) {
    return null;
  }
  let start = cursor;
  while (start > 0 && R_TOKEN_CHARS.has(lineText[start - 1])) {
    start -= 1;
  }
  let end = cursor + 1;
  while (end < lineText.length && R_TOKEN_CHARS.has(lineText[end])) {
    end += 1;
  }
  const token = lineText.slice(start, end);
  for (const match of token.matchAll(R_CHAIN_PATTERN)) {
    const relativeStart = match.index;
    if (relativeStart === undefined) {
      throw new Error("Regex match index is undefined");
    }
    const chainText = match[0];
    const absoluteStart = start + relativeStart;
    const absoluteEnd = absoluteStart + chainText.length;
    if (absoluteStart <= cursor && cursor < absoluteEnd) {
      return {
        chainText,
        symbolName: chainText.slice(2),
        range: new vscode.Range(position.line, absoluteStart, position.line, absoluteEnd),
      };
    }
  }
  return null;
}

function sortSymbolsForVariant(symbols: SymbolLite[]): SymbolLite[] {
  return symbols.slice().sort((a, b) => {
    const aBase = a.variant === null ? 0 : 1;
    const bBase = b.variant === null ? 0 : 1;
    if (aBase !== bBase) {
      return aBase - bBase;
    }
    const aVariant = a.variant ?? "";
    const bVariant = b.variant ?? "";
    if (aVariant !== bVariant) {
      return aVariant.localeCompare(bVariant);
    }
    if (a.metaPath !== b.metaPath) {
      return a.metaPath.localeCompare(b.metaPath);
    }
    return a.definitionId.localeCompare(b.definitionId);
  });
}

function resolveSymbolsFromChain(
  symbols: SymbolLite[],
  symbolName: string,
): { resolvedName: string; symbols: SymbolLite[] } | null {
  const parts = symbolName.split(".").filter((part) => part !== "");
  while (parts.length > 0) {
    const candidate = parts.join(".");
    const matched = sortSymbolsForVariant(symbols.filter((item) => item.name === candidate));
    if (matched.length > 0) {
      return { resolvedName: candidate, symbols: matched };
    }
    parts.pop();
  }
  return null;
}

function escapeMarkdownInline(value: string): string {
  return value.replace(/([\\`*_[\]()#+\-.!|])/g, "\\$1").replace(/\n/g, " ");
}

function commandLinkForOpenSymbol(symbol: SymbolLite): string {
  const arg = encodeURIComponent(
    JSON.stringify([
      {
        metaPath: symbol.metaPath,
        imagePath: symbol.imagePath,
        definitionId: symbol.definitionId,
      },
    ]),
  );
  return `command:kotonebot.editor.openSymbol?${arg}`;
}

class RSymbolHoverProvider implements vscode.HoverProvider {
  private indexCache: SymbolSnapshotLite | null = null;
  private indexCacheTimeMs = 0;
  private baseVariantNameCache: string | null = null;
  private baseVariantNameCacheTimeMs = 0;
  private readonly previewCache = new Map<string, string>();

  constructor(private readonly server: DevtoolsHttpConfig) {}

  async provideHover(document: vscode.TextDocument, position: vscode.Position): Promise<vscode.Hover | null> {
    const chain = extractRChainAtPosition(document.getText(), position);
    if (chain === null) {
      return null;
    }
    const snapshot = await this.getIndexSnapshot();
    const resolved = resolveSymbolsFromChain(snapshot.symbols, chain.symbolName);
    if (resolved === null) {
      return null;
    }
    const symbolStartCharacter = chain.range.start.character + 2;
    const symbolEndCharacter = symbolStartCharacter + resolved.resolvedName.length;
    const lastDotOffset = resolved.resolvedName.lastIndexOf(".");
    const lastSegmentStartCharacter =
      lastDotOffset < 0 ? symbolStartCharacter : symbolStartCharacter + lastDotOffset + 1;
    const isOnTerminalSegment = position.character >= lastSegmentStartCharacter && position.character < symbolEndCharacter;
    if (!isOnTerminalSegment) {
      return null;
    }
    const primarySymbol = resolved.symbols[0];
    if (primarySymbol === undefined) {
      throw new Error("resolved symbols is empty");
    }
    const hoverRange = new vscode.Range(
      chain.range.start.line,
      chain.range.start.character,
      chain.range.end.line,
      chain.range.start.character + 2 + resolved.resolvedName.length,
    );
    const lines: string[] = [];
    const imageDataUri = await this.getPreviewDataUri(primarySymbol);
    const description = primarySymbol.description;
    const trimmedDescription = description === null ? "" : description.trim();
    lines.push(`![preview](${imageDataUri})`);
    lines.push("");
    lines.push(`- name: \`${resolved.resolvedName}\``);
    if (trimmedDescription === "") {
      lines.push("- description:");
    } else {
      lines.push(`- description: \`${escapeMarkdownInline(trimmedDescription)}\``);
    }
    const baseVariantName = await this.getBaseVariantName();
    const variantLinks = resolved.symbols.map((symbol) => {
      const label = escapeMarkdownInline(symbol.variant ?? baseVariantName);
      return `[${label}](${commandLinkForOpenSymbol(symbol)})`;
    });
    lines.push(`- variant: ${variantLinks.join(" | ")}`);

    const markdown = new vscode.MarkdownString(lines.join("\n"), true);
    markdown.isTrusted = { enabledCommands: ["kotonebot.editor.openSymbol"] };
    return new vscode.Hover(markdown, hoverRange);
  }

  private async getIndexSnapshot(): Promise<SymbolSnapshotLite> {
    const now = Date.now();
    if (this.indexCache !== null && now - this.indexCacheTimeMs < 1500) {
      return this.indexCache;
    }
    const snapshot = await fetchMetaIndexSnapshot(this.server);
    this.indexCache = snapshot;
    this.indexCacheTimeMs = now;
    return snapshot;
  }

  private async getBaseVariantName(): Promise<string> {
    const now = Date.now();
    if (this.baseVariantNameCache !== null && now - this.baseVariantNameCacheTimeMs < 5000) {
      return this.baseVariantNameCache;
    }
    const baseVariant = await fetchProjectBaseVariant(this.server);
    this.baseVariantNameCache = baseVariant;
    this.baseVariantNameCacheTimeMs = now;
    return baseVariant;
  }

  private async getPreviewDataUri(symbol: SymbolLite): Promise<string> {
    const key = `${symbol.imagePath}|${JSON.stringify(symbol.primaryGeometry)}|original`;
    const cached = this.previewCache.get(key);
    if (cached !== undefined) {
      return cached;
    }
    const imageBytes = await fetchHoverPreviewImage(this.server, symbol.imagePath, symbol.primaryGeometry);
    const dataUri = `data:image/png;base64,${imageBytes.toString("base64")}`;
    this.previewCache.set(key, dataUri);
    return dataUri;
  }
}

export function registerRSymbolHover(context: vscode.ExtensionContext, server: DevtoolsHttpConfig): void {
  const provider = new RSymbolHoverProvider(server);
  context.subscriptions.push(
    vscode.languages.registerHoverProvider(
      [{ scheme: "file", language: "python" }],
      provider,
    ),
  );
}
