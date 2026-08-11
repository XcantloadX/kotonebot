import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { InputGroup, Spinner } from "@blueprintjs/core";
import { useShortcutScope } from "../shortcuts/shortcutManager";
import i18n from "../i18n";

/** Quick Pick 列表项定义。 */
export interface QuickPickItem<TValue> {
  /** 列表项唯一 ID。 */
  id: string;
  /** 主标题文本。 */
  label: string;
  /** 次级描述文本。 */
  description?: string;
  /** 额外明细文本（通常展示路径或上下文）。 */
  detail?: string;
  /** 参与过滤的补充搜索文本。 */
  searchText?: string;
  /** 是否禁用该项。 */
  disabled?: boolean;
  /** 选中该项后返回给调用方的值。 */
  value: TValue;
}

/** Quick Pick 打开参数。 */
export interface QuickPickOptions<TValue> {
  /** 面板标题。 */
  title?: string;
  /** 输入框占位提示。 */
  placeholder?: string;
  /** 初始查询文本。 */
  initialQuery?: string;
  /** 无结果时展示文案。 */
  emptyText?: string;
  /** 静态候选项列表（与 getItems 二选一或混用）。 */
  items?: QuickPickItem<TValue>[];
  /** 动态获取候选项函数，会在查询变化时调用。 */
  getItems?: (query: string) => QuickPickItem<TValue>[] | Promise<QuickPickItem<TValue>[]>;
  /** 是否允许 Esc 关闭。 */
  canEscapeKeyClose?: boolean;
  /** 是否允许点击面板外关闭。 */
  canOutsideClickClose?: boolean;
  /** 首次打开时希望默认高亮的列表项 ID。 */
  initialSelectedItemId?: string;
  /** 将输入框原始查询转换为高亮匹配词（用于 ">"、 "#" 等带前缀的搜索模式）。 */
  highlightQuery?: (query: string) => string;
}

/** 面向字符串列表的快捷选择参数。 */
interface QuickPickSelectOptions {
  /** 面板标题。 */
  title?: string;
  /** 输入框占位提示。 */
  placeholder?: string;
  /** 可选字符串列表。 */
  options: string[];
  /** 默认高亮项。 */
  defaultValue?: string;
  /** 无结果时展示文案。 */
  emptyText?: string;
}

/** Quick Pick 队列中的待处理请求。 */
interface PendingQuickPickRequest {
  /** 打开参数。 */
  options: QuickPickOptions<any>;
  /** 关闭时回传结果。 */
  resolve: (value: any | null) => void;
}

/** Quick Pick 对外 API。 */
export interface QuickPickApi {
  /** 通用选择入口。 */
  show: <TValue>(options: QuickPickOptions<TValue>) => Promise<TValue | null>;
  /** 字符串列表快捷选择入口。 */
  select: (options: QuickPickSelectOptions) => Promise<string | null>;
}

const QuickPickContext = createContext<QuickPickApi | null>(null);
let globalQuickPickApi: QuickPickApi | null = null;

/** 设置全局 Quick Pick API（由 Provider 生命周期维护）。 */
export function setGlobalQuickPick(api: QuickPickApi | null): void {
  globalQuickPickApi = api;
}

/** 读取全局 Quick Pick API。 */
export function getGlobalQuickPick(): QuickPickApi | null {
  return globalQuickPickApi;
}

/** 读取全局 Quick Pick API；未初始化时抛错。 */
export function getGlobalQuickPickOrThrow(): QuickPickApi {
  const api = getGlobalQuickPick();
  if (!api) {
    throw new Error("QuickPick API is not initialized");
  }
  return api;
}

export const quickPick: QuickPickApi = {
  show: (options) => getGlobalQuickPickOrThrow().show(options),
  select: (options) => getGlobalQuickPickOrThrow().select(options),
};

/** 在组件内读取 Quick Pick API。 */
export const useQuickPick = (): QuickPickApi => {
  const value = useContext(QuickPickContext);
  if (!value) {
    throw new Error("useQuickPick must be used within QuickPickProvider");
  }
  return value;
};

/** 将文本中命中查询关键字的片段加粗并高亮，其余部分保持原样（类似 VSCode 的匹配高亮）。 */
const HighlightedText: React.FC<{ text: string; query: string }> = ({ text, query }) => {
  const parts = useMemo(() => {
    const q = query.trim().toLowerCase();
    const segments: { text: string; match: boolean }[] = [];
    if (q.length === 0) {
      return [{ text, match: false }];
    }
    const lower = text.toLowerCase();
    let index = 0;
    // 逐个寻找命中区间，重叠时并入同一段，保证不遗漏也不重复。
    while (index < text.length) {
      const found = lower.indexOf(q, index);
      if (found < 0) {
        if (index < text.length) {
          segments.push({ text: text.slice(index), match: false });
        }
        break;
      }
      if (found > index) {
        segments.push({ text: text.slice(index, found), match: false });
      }
      segments.push({ text: text.slice(found, found + q.length), match: true });
      index = found + q.length;
    }
    return segments;
  }, [text, query]);

  return (
    <>
      {parts.map((part, i) =>
        part.match ? (
          <span key={i} style={{ fontWeight: 700, background: "#ffe58f", borderRadius: 2 }}>
            {part.text}
          </span>
        ) : (
          <span key={i}>{part.text}</span>
        )
      )}
    </>
  );
};

/** Quick Pick 全局 Provider，负责队列、键盘交互与弹层渲染。 */
export const QuickPickProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [queue, setQueue] = useState<PendingQuickPickRequest[]>([]);
  // 仅展示队列头部请求，其余请求按 FIFO 等待。
  const current = queue[0] ?? null;
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<QuickPickItem<any>[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const panelRef = useRef<HTMLDivElement>(null);

  useShortcutScope("palette", !!current);

  /** 完成当前请求并出队。 */
  const settleCurrent = useCallback((value: any | null) => {
    setQueue((prev) => {
      const [head, ...rest] = prev;
      if (!head) {
        throw new Error("No pending quick pick request");
      }
      head.resolve(value);
      return rest;
    });
  }, []);

  const closeCurrent = useCallback(() => {
    settleCurrent(null);
  }, [settleCurrent]);

  /** 入队一个新的 Quick Pick 请求。 */
  const show = useCallback(<TValue,>(options: QuickPickOptions<TValue>): Promise<TValue | null> => {
    return new Promise<TValue | null>((resolve) => {
      setQueue((prev) => [
        ...prev,
        {
          options,
          resolve: (value) => resolve((value ?? null) as TValue | null),
        },
      ]);
    });
  }, []);

  /** 基于字符串数组构建常用选择器。 */
  const select = useCallback(async (options: QuickPickSelectOptions): Promise<string | null> => {
    if (options.options.length === 0) {
      throw new Error("select requires at least one option");
    }
    if (options.defaultValue !== undefined && !options.options.includes(options.defaultValue)) {
      throw new Error("defaultValue must be one of options");
    }
    const result = await show<string>({
      title: options.title,
      placeholder: options.placeholder,
      initialQuery: "",
      emptyText: options.emptyText ?? i18n.t('quickPick.noMatch'),
      items: options.options.map((it) => ({
        id: it,
        label: it,
        searchText: it,
        value: it,
      })),
      initialSelectedItemId: options.defaultValue,
    });
    return result;
  }, [show]);

  const api = useMemo<QuickPickApi>(() => ({
    show,
    select,
  }), [select, show]);

  useEffect(() => {
    setGlobalQuickPick(api);
    return () => {
      setGlobalQuickPick(null);
    };
  }, [api]);

  useEffect(() => {
    if (!current) {
      setQuery("");
      setItems([]);
      setLoading(false);
      setSelectedIndex(0);
      return;
    }
    setQuery(current.options.initialQuery ?? "");
    setSelectedIndex(0);
  }, [current]);

  useEffect(() => {
    if (!current) {
      return;
    }
    let cancelled = false;
    const loadItems = async () => {
      const { getItems, items: staticItems } = current.options;
      if (!getItems) {
        const list = staticItems ?? [];
        const q = query.trim().toLowerCase();
        const filtered = q.length === 0
          ? list
          : list.filter((item) => {
            const haystack = `${item.label} ${item.description ?? ""} ${item.detail ?? ""} ${item.searchText ?? ""}`.toLowerCase();
            return haystack.includes(q);
          });
        if (!cancelled) {
          setItems(filtered);
          setLoading(false);
          const initialSelectedId = current.options.initialSelectedItemId;
          if (initialSelectedId) {
            const idx = filtered.findIndex((item) => item.id === initialSelectedId);
            if (idx >= 0) {
              setSelectedIndex(idx);
              return;
            }
          }
          setSelectedIndex((prev) => (filtered.length === 0 ? 0 : Math.min(prev, filtered.length - 1)));
        }
        return;
      }
      // 异步模式用于按查询动态计算候选项。
      setLoading(true);
      try {
        const loaded = await Promise.resolve(getItems(query));
        if (!cancelled) {
          setItems(loaded);
          setLoading(false);
          const initialSelectedId = current.options.initialSelectedItemId;
          if (initialSelectedId) {
            const idx = loaded.findIndex((item) => item.id === initialSelectedId);
            if (idx >= 0) {
              setSelectedIndex(idx);
              return;
            }
          }
          setSelectedIndex((prev) => (loaded.length === 0 ? 0 : Math.min(prev, loaded.length - 1)));
        }
      } catch (e) {
        if (cancelled) {
          return;
        }
        setItems([]);
        setLoading(false);
      }
    };
    void loadItems();
    return () => {
      cancelled = true;
    };
  }, [current, query]);

  useEffect(() => {
    if (!current) {
      return;
    }
    if (items.length === 0) {
      return;
    }
    const el = document.getElementById(`kb-quick-pick-row-${selectedIndex}`);
    el?.scrollIntoView({ block: "nearest" });
  }, [current, items.length, selectedIndex]);

  useEffect(() => {
    if (!current) {
      return;
    }
    if (current.options.canOutsideClickClose === false) {
      return;
    }
    const onMouseDown = (e: MouseEvent) => {
      const target = e.target as Node;
      const isInside = panelRef.current?.contains(target) ?? false;
      if (!isInside) {
        closeCurrent();
      }
    };
    window.addEventListener("mousedown", onMouseDown);
    return () => {
      window.removeEventListener("mousedown", onMouseDown);
    };
  }, [closeCurrent, current]);

  /** 确认当前高亮项并返回结果。 */
  const confirmSelection = useCallback(() => {
    const picked = items[selectedIndex];
    if (!picked || picked.disabled) {
      return;
    }
    settleCurrent(picked.value);
  }, [items, selectedIndex, settleCurrent]);

  // 高亮用匹配词：允许调用方对原始查询做前缀剥离，避免 ">"、"#" 等前缀破坏匹配。
  const highlightTerm = current?.options.highlightQuery
    ? current.options.highlightQuery(query)
    : query;

  return (
    <QuickPickContext.Provider value={api}>
      {children}
      {current ? (
        <div
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 3000,
            pointerEvents: "none",
          }}
        >
          <div
            ref={panelRef}
            style={{
              position: "absolute",
              left: "50%",
              top: "12vh",
              width: "min(820px, calc(100vw - 24px))",
              transform: "translateX(-50%)",
              background: "#ffffff",
              border: "1px solid #b7c6d2",
              borderRadius: 6,
              boxShadow: "0 18px 48px rgba(16, 22, 26, 0.28)",
              pointerEvents: "auto",
            }}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div style={{ padding: 10, borderBottom: "1px solid #d8e1e8" }}>
              {current.options.title ? (
                <div style={{ fontSize: 12, fontWeight: 600, color: "#5c7080", marginBottom: 6 }}>{current.options.title}</div>
              ) : null}
              <InputGroup
                autoFocus
                leftIcon="search"
                value={query}
                placeholder={current.options.placeholder ?? i18n.t('quickPick.typeToFilter')}
                onChange={(e) => setQuery((e.target as HTMLInputElement).value)}
                onKeyDown={(e) => {
                  // 键盘优先：在面板内完成导航与确认，避免焦点跳出。
                  const currentLength = items.length;
                  if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setSelectedIndex((v) => (currentLength === 0 ? 0 : (v + 1) % currentLength));
                    return;
                  }
                  if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setSelectedIndex((v) => (currentLength === 0 ? 0 : (v - 1 + currentLength) % currentLength));
                    return;
                  }
                  if (e.key === "Home") {
                    e.preventDefault();
                    setSelectedIndex(0);
                    return;
                  }
                  if (e.key === "End") {
                    e.preventDefault();
                    setSelectedIndex(Math.max(0, currentLength - 1));
                    return;
                  }
                  if (e.key === "Enter" || e.key === "Tab") {
                    e.preventDefault();
                    confirmSelection();
                    return;
                  }
                  if (e.key === "Escape") {
                    if (current.options.canEscapeKeyClose === false) {
                      return;
                    }
                    e.preventDefault();
                    closeCurrent();
                  }
                }}
              />
            </div>
            <div style={{ maxHeight: 420, overflowY: "auto" }}>
              {loading ? (
                <div style={{ display: "flex", alignItems: "center", gap: 8, padding: 12, color: "#5c7080" }}>
                  <Spinner size={16} />
                  {i18n.t('quickPick.loading')}
                </div>
              ) : null}
              {!loading && items.length === 0 ? (
                <div style={{ padding: 12, color: "#5c7080" }}>{current.options.emptyText ?? i18n.t('quickPick.noMatch')}</div>
              ) : null}
              {!loading
                ? items.map((item, index) => {
                  const isSelected = index === selectedIndex;
                  return (
                    <div
                      id={`kb-quick-pick-row-${index}`}
                      key={item.id}
                      style={{
                        padding: "8px 10px",
                        borderTop: "1px solid #eef2f5",
                        background: isSelected ? "#ebf1f5" : "#ffffff",
                        cursor: item.disabled ? "not-allowed" : "pointer",
                        opacity: item.disabled ? 0.5 : 1,
                      }}
                      onMouseEnter={() => setSelectedIndex(index)}
                      onClick={() => {
                        if (item.disabled) {
                          return;
                        }
                        settleCurrent(item.value);
                      }}
                    >
                      <div style={{ fontSize: 13, color: "#182026" }}>
                        <HighlightedText text={item.label} query={highlightTerm} />
                      </div>
                      {item.description ? (
                        <div style={{ fontSize: 12, color: "#5c7080", marginTop: 2 }}>
                          <HighlightedText text={item.description} query={highlightTerm} />
                        </div>
                      ) : null}
                      {item.detail ? (
                        <div style={{ fontSize: 11, color: "#8a9ba8", marginTop: 2 }}>
                          <HighlightedText text={item.detail} query={highlightTerm} />
                        </div>
                      ) : null}
                    </div>
                  );
                })
                : null}
            </div>
          </div>
        </div>
      ) : null}
    </QuickPickContext.Provider>
  );
};
