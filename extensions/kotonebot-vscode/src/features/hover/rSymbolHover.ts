import * as http from "node:http";
import * as https from "node:https";
import * as vscode from "vscode";
import { DevtoolsHttpConfig } from "../../lsp/client";

interface ApiEnvelope<T> {
  success: boolean;
  message: string | null;
  data: T | null;
}

interface SymbolLite {
  symbolKey: string;
  definitionId: string;
  type: string;
  name: string;
  displayName: string | null;
  description: string | null;
  prefabId: string | null;
  variant: string | null;
  metaPath: string;
  imagePath: string;
  primaryGeometry: Record<string, unknown> | null;
  searchText: string;
}

interface SymbolSnapshotLite {
  indexVersion: number;
  contentHash: string;
  symbols: SymbolLite[];
}

interface ProjectRootData {
  variant: {
    base: string;
  } | null;
}

const R_CHAIN_PATTERN = /R(?:\.[A-Za-z_][A-Za-z0-9_]*)+/g;
const R_TOKEN_CHARS = new Set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.");

function requestBuffer(url: string): Promise<Buffer> {
  const parsed = new URL(url);
  const sender = parsed.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const req = sender.request(
      parsed,
      {
        method: "GET",
        timeout: 8000,
      },
      (res) => {
        const status = res.statusCode;
        if (status === undefined || status < 200 || status >= 300) {
          reject(new Error(`Request failed with status ${String(status)}: ${url}`));
          res.resume();
          return;
        }
        const chunks: Buffer[] = [];
        res.on("data", (chunk: Buffer) => {
          chunks.push(chunk);
        });
        res.on("end", () => {
          resolve(Buffer.concat(chunks));
        });
      },
    );
    req.on("timeout", () => {
      req.destroy(new Error(`Request timeout: ${url}`));
    });
    req.on("error", (err: Error) => {
      reject(err);
    });
    req.end();
  });
}

async function requestJson<T>(url: string): Promise<T> {
  const content = await requestBuffer(url);
  const parsed = JSON.parse(content.toString("utf-8")) as T;
  return parsed;
}

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

function previewUrl(server: DevtoolsHttpConfig, symbol: SymbolLite): string {
  const params = new URLSearchParams();
  params.set("path", symbol.imagePath);
  const geometry = symbol.primaryGeometry;
  if (geometry !== null) {
    const kind = geometry.kind;
    if (kind === "image" || kind === "rect") {
      for (const key of ["x1", "y1", "x2", "y2"]) {
        const value = geometry[key];
        if (value === undefined || value === null) {
          throw new Error(`primaryGeometry missing ${key}`);
        }
        params.set(key, String(value));
      }
    }
  }
  return `http://${server.host}:${String(server.port)}/api/image/hover_preview?${params.toString()}`;
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
    const url = `http://${this.server.host}:${String(this.server.port)}/api/meta/index`;
    const envelope = await requestJson<ApiEnvelope<SymbolSnapshotLite>>(url);
    if (envelope.success !== true) {
      throw new Error(`meta index request failed: ${String(envelope.message)}`);
    }
    if (envelope.data === null) {
      throw new Error("meta index response data is null");
    }
    this.indexCache = envelope.data;
    this.indexCacheTimeMs = now;
    return envelope.data;
  }

  private async getBaseVariantName(): Promise<string> {
    const now = Date.now();
    if (this.baseVariantNameCache !== null && now - this.baseVariantNameCacheTimeMs < 5000) {
      return this.baseVariantNameCache;
    }
    const url = `http://${this.server.host}:${String(this.server.port)}/api/project/root`;
    const envelope = await requestJson<ApiEnvelope<ProjectRootData>>(url);
    if (envelope.success !== true) {
      throw new Error(`project root request failed: ${String(envelope.message)}`);
    }
    if (envelope.data === null) {
      throw new Error("project root response data is null");
    }
    if (envelope.data.variant === null) {
      throw new Error("project root response variant is null");
    }
    if (typeof envelope.data.variant.base !== "string" || envelope.data.variant.base.trim() === "") {
      throw new Error("project root response variant.base is invalid");
    }
    this.baseVariantNameCache = envelope.data.variant.base;
    this.baseVariantNameCacheTimeMs = now;
    return envelope.data.variant.base;
  }

  private async getPreviewDataUri(symbol: SymbolLite): Promise<string> {
    const key = `${symbol.imagePath}|${JSON.stringify(symbol.primaryGeometry)}|original`;
    const cached = this.previewCache.get(key);
    if (cached !== undefined) {
      return cached;
    }
    const url = previewUrl(this.server, symbol);
    const imageBytes = await requestBuffer(url);
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
