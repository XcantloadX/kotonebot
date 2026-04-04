import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ValidateShortcutCombo } from "./shortcutCombo";

type ShortcutPhase = "keydown" | "keyup";

/**
 * 单条快捷键绑定定义。
 */
export interface ShortcutBinding {
  /** 唯一标识，用于注册冲突检测与卸载。 */
  id: string;
  /** 快捷键组合，例如 `mod+s`、`shift+escape`、`v`。 */
  combo: string;
  /** 快捷键所属作用域。 */
  scope: string;
  /** `keydown` 触发处理。 */
  onKeyDown?: (event: KeyboardEvent) => void;
  /** `keyup` 触发处理。 */
  onKeyUp?: (event: KeyboardEvent) => void;
  /** 运行时启用条件，不满足时忽略该快捷键。 */
  when?: () => boolean;
  /** 是否允许在输入态（input/textarea/select/contentEditable）触发。 */
  allowInInput?: boolean;
  /** 是否允许按键重复触发（长按）。 */
  allowRepeat?: boolean;
  /** 是否阻止浏览器默认行为，默认 `true`。 */
  preventDefault?: boolean;
  /** 是否阻止事件继续冒泡，默认 `false`。 */
  stopPropagation?: boolean;
}

interface ParsedCombo {
  key: string;
  ctrl: boolean;
  meta: boolean;
  shift: boolean;
  alt: boolean;
}

interface RegisteredShortcut {
  binding: ShortcutBinding;
  order: number;
  parsed: ParsedCombo;
}

interface ShortcutManagerContextValue {
  registerShortcut: (binding: ShortcutBinding) => () => void;
  setScopeActive: (scope: string, active: boolean) => void;
}

const ShortcutManagerContext = createContext<ShortcutManagerContextValue | null>(null);

type ValidatedBinding<T extends ShortcutBinding> = Omit<T, "combo"> & {
  combo: ValidateShortcutCombo<T["combo"]>;
};

const DEFAULT_SCOPE_PRIORITIES: Record<string, number> = {
  global: 0,
  editor: 10,
  menu: 20,
  palette: 30,
  modal: 40,
};

const macLikePlatform = /Mac|iPhone|iPad|iPod/i.test(navigator.platform);

function getScopePriority(scope: string): number {
  if (scope in DEFAULT_SCOPE_PRIORITIES) {
    return DEFAULT_SCOPE_PRIORITIES[scope];
  }
  throw new Error(`Unknown shortcut scope '${scope}'`);
}

function normalizeEventKey(event: KeyboardEvent): string {
  if (event.key === " ") {
    return "space";
  }
  const lower = event.key.toLowerCase();
  if (lower === "esc") {
    return "escape";
  }
  if (lower === "arrowup") {
    return "up";
  }
  if (lower === "arrowdown") {
    return "down";
  }
  if (lower === "arrowleft") {
    return "left";
  }
  if (lower === "arrowright") {
    return "right";
  }
  return lower;
}

function parseShortcutCombo(combo: string): ParsedCombo {
  const tokens = combo
    .split("+")
    .map((token) => token.trim().toLowerCase())
    .filter((token) => token.length > 0);
  if (tokens.length === 0) {
    throw new Error("Shortcut combo cannot be empty");
  }

  let ctrl = false;
  let meta = false;
  let shift = false;
  let alt = false;
  let key: string | null = null;

  for (const token of tokens) {
    if (token === "ctrl" || token === "control") {
      ctrl = true;
      continue;
    }
    if (token === "meta" || token === "cmd" || token === "command") {
      meta = true;
      continue;
    }
    if (token === "shift") {
      shift = true;
      continue;
    }
    if (token === "alt" || token === "option") {
      alt = true;
      continue;
    }
    if (token === "mod") {
      if (macLikePlatform) {
        meta = true;
      } else {
        ctrl = true;
      }
      continue;
    }
    if (key !== null) {
      throw new Error(`Shortcut combo '${combo}' has more than one key`);
    }
    key = token;
  }

  if (!key) {
    throw new Error(`Shortcut combo '${combo}' must include a key`);
  }

  if (key === "spacebar") {
    key = "space";
  }
  if (key === "esc") {
    key = "escape";
  }
  if (key === "arrowup") {
    key = "up";
  }
  if (key === "arrowdown") {
    key = "down";
  }
  if (key === "arrowleft") {
    key = "left";
  }
  if (key === "arrowright") {
    key = "right";
  }

  return { key, ctrl, meta, shift, alt };
}

function eventComposesText(event: KeyboardEvent): boolean {
  const target = event.target as HTMLElement | null;
  const tag = target?.tagName;
  return !!target && (target.isContentEditable || tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT");
}

function matchCombo(event: KeyboardEvent, combo: ParsedCombo): boolean {
  if (normalizeEventKey(event) !== combo.key) {
    return false;
  }
  if (event.ctrlKey !== combo.ctrl) {
    return false;
  }
  if (event.metaKey !== combo.meta) {
    return false;
  }
  if (event.shiftKey !== combo.shift) {
    return false;
  }
  if (event.altKey !== combo.alt) {
    return false;
  }
  return true;
}

function toConflictKey(scope: string, phase: ShortcutPhase, parsed: ParsedCombo): string {
  return `${scope}:${phase}:${parsed.ctrl ? "1" : "0"}${parsed.meta ? "1" : "0"}${parsed.shift ? "1" : "0"}${parsed.alt ? "1" : "0"}:${parsed.key}`;
}

/**
 * 全局快捷键提供者。
 * 仅注册一套 `window` 键盘监听，并在内部完成作用域、优先级与冲突处理。
 */
export const ShortcutProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const bindingsRef = useRef<Map<string, RegisteredShortcut>>(new Map());
  const activeScopesRef = useRef<Set<string>>(new Set());
  const [scopeVersion, setScopeVersion] = useState(0);
  const orderRef = useRef(0);

  const setScopeActive = useCallback((scope: string, active: boolean) => {
    getScopePriority(scope);
    const before = activeScopesRef.current.has(scope);
    if (active && !before) {
      activeScopesRef.current.add(scope);
      setScopeVersion((v) => v + 1);
      return;
    }
    if (!active && before) {
      activeScopesRef.current.delete(scope);
      setScopeVersion((v) => v + 1);
    }
  }, []);

  const registerShortcut = useCallback((binding: ShortcutBinding) => {
    if (!binding.onKeyDown && !binding.onKeyUp) {
      throw new Error(`Shortcut '${binding.id}' must register at least one handler`);
    }
    if (bindingsRef.current.has(binding.id)) {
      throw new Error(`Duplicate shortcut id '${binding.id}'`);
    }

    getScopePriority(binding.scope);
    const parsed = parseShortcutCombo(binding.combo);

    const phases: ShortcutPhase[] = [];
    if (binding.onKeyDown) {
      phases.push("keydown");
    }
    if (binding.onKeyUp) {
      phases.push("keyup");
    }

    for (const phase of phases) {
      const conflictKey = toConflictKey(binding.scope, phase, parsed);
      const allowModalCoexistence = binding.scope === "modal";
      for (const registered of bindingsRef.current.values()) {
        if (registered.binding.id === binding.id) {
          continue;
        }
        const otherPhaseList: ShortcutPhase[] = [];
        if (registered.binding.onKeyDown) {
          otherPhaseList.push("keydown");
        }
        if (registered.binding.onKeyUp) {
          otherPhaseList.push("keyup");
        }
        if (!otherPhaseList.includes(phase)) {
          continue;
        }
        const otherConflictKey = toConflictKey(registered.binding.scope, phase, registered.parsed);
        if (otherConflictKey === conflictKey && !allowModalCoexistence) {
          throw new Error(
            `Shortcut conflict in scope '${binding.scope}' for combo '${binding.combo}' (${phase}): '${binding.id}' and '${registered.binding.id}'`,
          );
        }
      }
    }

    bindingsRef.current.set(binding.id, {
      binding,
      parsed,
      order: orderRef.current,
    });
    orderRef.current += 1;

    return () => {
      bindingsRef.current.delete(binding.id);
    };
  }, []);

  const dispatch = useCallback(
    (phase: ShortcutPhase, event: KeyboardEvent) => {
      const typing = eventComposesText(event);
      const activePriorities = Array.from(activeScopesRef.current).map((scope) => getScopePriority(scope));
      const minPriority = activePriorities.length > 0 ? Math.max(...activePriorities) : -Infinity;

      const candidates = Array.from(bindingsRef.current.values()).filter((registered) => {
        const { binding } = registered;
        if (phase === "keydown" && !binding.onKeyDown) {
          return false;
        }
        if (phase === "keyup" && !binding.onKeyUp) {
          return false;
        }
        if (binding.scope !== "global" && !activeScopesRef.current.has(binding.scope)) {
          return false;
        }
        const scopePriority = getScopePriority(binding.scope);
        if (scopePriority < minPriority) {
          return false;
        }
        if (typing && !binding.allowInInput) {
          return false;
        }
        if (phase === "keydown" && event.repeat && !binding.allowRepeat) {
          return false;
        }
        if (!matchCombo(event, registered.parsed)) {
          return false;
        }
        if (binding.when && !binding.when()) {
          return false;
        }
        return true;
      });

      if (candidates.length === 0) {
        return;
      }

      candidates.sort((a, b) => {
        const byScope = getScopePriority(b.binding.scope) - getScopePriority(a.binding.scope);
        if (byScope !== 0) {
          return byScope;
        }
        return b.order - a.order;
      });

      const chosen = candidates[0].binding;
      if (chosen.preventDefault !== false) {
        event.preventDefault();
      }
      if (chosen.stopPropagation) {
        event.stopPropagation();
      }
      if (phase === "keydown") {
        chosen.onKeyDown?.(event);
      } else {
        chosen.onKeyUp?.(event);
      }
    },
    [scopeVersion],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      dispatch("keydown", event);
    };
    const onKeyUp = (event: KeyboardEvent) => {
      dispatch("keyup", event);
    };
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("keyup", onKeyUp);
    };
  }, [dispatch]);

  const value = useMemo<ShortcutManagerContextValue>(
    () => ({
      registerShortcut,
      setScopeActive,
    }),
    [registerShortcut, setScopeActive],
  );

  return <ShortcutManagerContext.Provider value={value}>{children}</ShortcutManagerContext.Provider>;
};

/**
 * 注册单条快捷键。
 * 组件卸载时会自动注销。
 */
export function useShortcut<const T extends ShortcutBinding>(binding: T & ValidatedBinding<T>): void {
  const context = useContext(ShortcutManagerContext);
  if (!context) {
    throw new Error("useShortcut must be used inside ShortcutProvider");
  }

  const bindingRef = useRef(binding);
  bindingRef.current = binding;
  const registrationKey = [
    binding.id,
    binding.scope,
    binding.combo,
    binding.allowInInput ? "1" : "0",
    binding.allowRepeat ? "1" : "0",
    binding.preventDefault === false ? "0" : "1",
    binding.stopPropagation ? "1" : "0",
    binding.onKeyDown ? "1" : "0",
    binding.onKeyUp ? "1" : "0",
    binding.when ? "1" : "0",
  ].join("|");

  useEffect(() => {
    const unregister = context.registerShortcut({
      ...bindingRef.current,
      onKeyDown: bindingRef.current.onKeyDown
        ? (event) => {
            const current = bindingRef.current;
            if (current.onKeyDown) {
              current.onKeyDown(event);
            }
          }
        : undefined,
      onKeyUp: bindingRef.current.onKeyUp
        ? (event) => {
            const current = bindingRef.current;
            if (current.onKeyUp) {
              current.onKeyUp(event);
            }
          }
        : undefined,
      when: bindingRef.current.when
        ? () => {
            const current = bindingRef.current;
            if (!current.when) {
              throw new Error(`Shortcut '${current.id}' lost its 'when' function`);
            }
            return current.when();
          }
        : undefined,
    });
    return unregister;
  }, [context, registrationKey]);
}

/**
 * 批量注册快捷键。
 * 适合动态快捷键场景（例如根据 schema 生成的快捷键列表）。
 */
export function useShortcuts<const B extends readonly ShortcutBinding[]>(
  bindings: B & { [K in keyof B]: B[K] extends ShortcutBinding ? ValidatedBinding<B[K]> : never },
): void {
  const context = useContext(ShortcutManagerContext);
  if (!context) {
    throw new Error("useShortcuts must be used inside ShortcutProvider");
  }

  const bindingsRef = useRef(bindings);
  bindingsRef.current = bindings;

  const signature = bindings
    .map((binding) => [
      binding.id,
      binding.scope,
      binding.combo,
      binding.allowInInput ? "1" : "0",
      binding.allowRepeat ? "1" : "0",
      binding.preventDefault === false ? "0" : "1",
      binding.stopPropagation ? "1" : "0",
      binding.onKeyDown ? "1" : "0",
      binding.onKeyUp ? "1" : "0",
      binding.when ? "1" : "0",
    ].join("|"))
    .join(";");

  useEffect(() => {
    const cleanups: Array<() => void> = [];
    for (const binding of bindingsRef.current) {
      const unregister = context.registerShortcut({
        ...binding,
        onKeyDown: binding.onKeyDown
          ? (event) => {
              const current = bindingsRef.current.find((it) => it.id === binding.id);
              if (!current) {
                throw new Error(`Shortcut '${binding.id}' is missing`);
              }
              current.onKeyDown?.(event);
            }
          : undefined,
        onKeyUp: binding.onKeyUp
          ? (event) => {
              const current = bindingsRef.current.find((it) => it.id === binding.id);
              if (!current) {
                throw new Error(`Shortcut '${binding.id}' is missing`);
              }
              current.onKeyUp?.(event);
            }
          : undefined,
        when: binding.when
          ? () => {
              const current = bindingsRef.current.find((it) => it.id === binding.id);
              if (!current || !current.when) {
                throw new Error(`Shortcut '${binding.id}' is missing 'when'`);
              }
              return current.when();
            }
          : undefined,
      });
      cleanups.push(unregister);
    }
    return () => {
      for (const cleanup of cleanups) {
        cleanup();
      }
    };
  }, [context, signature]);
}

/**
 * 设置作用域激活状态。
 * 高优先级作用域激活后会屏蔽低优先级作用域快捷键。
 */
export function useShortcutScope(scope: string, active: boolean): void {
  const context = useContext(ShortcutManagerContext);
  if (!context) {
    throw new Error("useShortcutScope must be used inside ShortcutProvider");
  }

  useEffect(() => {
    context.setScopeActive(scope, active);
    return () => {
      context.setScopeActive(scope, false);
    };
  }, [active, context, scope]);
}
