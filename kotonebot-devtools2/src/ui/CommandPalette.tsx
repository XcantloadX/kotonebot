import React, { useEffect, useMemo, useState } from "react";
import { Classes, Dialog, InputGroup } from "@blueprintjs/core";
import { SymbolLite } from "../model/symbolIndex";
import { useSymbolIndexStore } from "../editor/symbolIndexStore";
import { useAppStore } from "../editor/state";
import { jumpToSymbol } from "../editor/actions/navigation";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

type RankedSymbol = {
  symbol: SymbolLite;
  score: number;
};

function splitQueryTokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/[\s._\-]+/g)
    .map((token) => token.trim())
    .filter((token) => token.length > 0);
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function renderHighlightedText(text: string, tokens: string[]): React.ReactNode {
  const normalizedTokens = tokens.filter((token) => token.length > 0);
  if (normalizedTokens.length === 0 || text.length === 0) {
    return text;
  }
  const pattern = normalizedTokens
    .map((token) => escapeRegExp(token))
    .sort((a, b) => b.length - a.length)
    .join("|");
  if (pattern.length === 0) {
    return text;
  }
  const regex = new RegExp(`(${pattern})`, "ig");
  const parts = text.split(regex);
  return (
    <>
      {parts.map((part, idx) => {
        if (part.length === 0) {
          return null;
        }
        const isMatch = normalizedTokens.some((token) => part.toLowerCase() === token.toLowerCase());
        if (isMatch) {
          return (
            <strong key={idx} style={{ background: "#fff3bf", fontWeight: 700 }}>
              {part}
            </strong>
          );
        }
        return <React.Fragment key={idx}>{part}</React.Fragment>;
      })}
    </>
  );
}

function buildResultTitle(symbol: SymbolLite): string {
  const main = (symbol.name || symbol.definitionId).trim();
  const displayName = (symbol.displayName || "").trim();
  if (displayName.length === 0) {
    return main;
  }
  return `${main} ${displayName}`;
}

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

/**
 * 命令面板组件，目前只有搜索符号的功能。
 * 通过 Ctrl + Shift + P 打开，输入 # 加上关键词搜索符号，使用上下键选择，回车确认。
 * 搜索结果会根据匹配度、最近使用情况和是否在当前文档中进行排序。
 */
export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
}) => {
  const { activeDocumentId } = useAppStore();
  const { symbols, recentSymbolKeys } = useSymbolIndexStore();
  const [query, setQuery] = useState("#");
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    if (isOpen) {
      setQuery("#");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const recentOrder = useMemo(() => {
    const map = new Map<string, number>();
    for (let i = 0; i < recentSymbolKeys.length; i += 1) {
      map.set(recentSymbolKeys[i], i);
    }
    return map;
  }, [recentSymbolKeys]);

  const queryTokens = useMemo(() => {
    if (!query.startsWith("#")) {
      return [];
    }
    const raw = query.slice(1).trim();
    if (raw.length === 0) {
      return [];
    }
    return splitQueryTokens(raw);
  }, [query]);

  const ranked = useMemo((): RankedSymbol[] => {
    if (!query.startsWith("#")) {
      return [];
    }
    const raw = query.slice(1).trim();
    if (raw.length === 0) {
      return [];
    }
    return symbols
      .map((symbol) => ({
        symbol,
        score: rankSymbol(symbol, raw, queryTokens, activeDocumentId, recentOrder),
      }))
      .filter((it) => it.score >= 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 100);
  }, [query, symbols, activeDocumentId, recentOrder, queryTokens]);

  useEffect(() => {
    if (selectedIndex >= ranked.length) {
      setSelectedIndex(0);
    }
  }, [ranked, selectedIndex]);

  useEffect(() => {
    if (ranked.length === 0) {
      return;
    }
    const selected = document.getElementById(`command-palette-row-${selectedIndex}`);
    selected?.scrollIntoView({ block: "nearest" });
  }, [selectedIndex, ranked.length]);

  const handleConfirm = async (symbol: SymbolLite | undefined) => {
    if (!symbol) {
      return;
    }
    await jumpToSymbol(symbol);
    onClose();
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Command Palette" style={{ width: 720 }}>
      <div className={Classes.DIALOG_BODY}>
        <InputGroup
          autoFocus
          leftIcon="search"
          value={query}
          onChange={(e) => setQuery((e.target as HTMLInputElement).value)}
          placeholder="#search symbol"
          onKeyDown={async (e) => {
            const step = 10;
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setSelectedIndex((v) => (ranked.length === 0 ? 0 : (v + 1) % ranked.length));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setSelectedIndex((v) => (ranked.length === 0 ? 0 : (v - 1 + ranked.length) % ranked.length));
            } else if (e.key === "Home") {
              e.preventDefault();
              setSelectedIndex(0);
            } else if (e.key === "End") {
              e.preventDefault();
              setSelectedIndex(Math.max(0, ranked.length - 1));
            } else if (e.key === "PageDown") {
              e.preventDefault();
              setSelectedIndex((v) => Math.min(Math.max(0, ranked.length - 1), v + step));
            } else if (e.key === "PageUp") {
              e.preventDefault();
              setSelectedIndex((v) => Math.max(0, v - step));
            } else if (e.key === "Enter") {
              e.preventDefault();
              await handleConfirm(ranked[selectedIndex]?.symbol);
            } else if (e.key === "Tab") {
              e.preventDefault();
              await handleConfirm(ranked[selectedIndex]?.symbol);
            } else if (e.key === "Escape") {
              e.preventDefault();
              onClose();
            }
          }}
        />
        <div style={{ marginTop: 10, border: "1px solid #d8e1e8", borderRadius: 4, maxHeight: 360, overflowY: "auto" }}>
          {query.startsWith("#") ? null : (
            <div style={{ padding: 12, color: "#5c7080" }}>Type # to search symbols</div>
          )}
          {query.startsWith("#") && ranked.length === 0 ? (
            <div style={{ padding: 12, color: "#5c7080" }}>No symbol match</div>
          ) : null}
          {ranked.map((item, idx) => {
            const symbol = item.symbol;
            const mainLabel = (symbol.name || symbol.definitionId).trim();
            const displayLabel = (symbol.displayName || "").trim();
            const label = buildResultTitle(symbol);
            const subtitle = [symbol.type, symbol.prefabId || "-", symbol.imagePath.split(/[\\/]/).pop() || symbol.imagePath].join(" | ");
            const isSelected = idx === selectedIndex;
            return (
              <div
                id={`command-palette-row-${idx}`}
                key={symbol.symbolKey}
                style={{
                  padding: "8px 10px",
                  borderBottom: "1px solid #eef2f5",
                  background: isSelected ? "#ebf1f5" : "#ffffff",
                  cursor: "pointer",
                }}
                onMouseEnter={() => setSelectedIndex(idx)}
                onClick={() => void handleConfirm(symbol)}
              >
                <div style={{ fontSize: 13, color: "#182026" }} aria-label={label}>
                  {renderHighlightedText(mainLabel, queryTokens)}
                  {displayLabel.length > 0 ? (
                    <>
                      {" "}
                      <span style={{ color: "#8a9ba8" }}>{renderHighlightedText(displayLabel, queryTokens)}</span>
                    </>
                  ) : null}
                </div>
                <div style={{ fontSize: 12, color: "#5c7080", marginTop: 2 }}>{renderHighlightedText(subtitle, queryTokens)}</div>
              </div>
            );
          })}
        </div>
      </div>
    </Dialog>
  );
};
