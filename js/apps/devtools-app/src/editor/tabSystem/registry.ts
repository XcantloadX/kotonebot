import type React from "react";
import type { ITab, TabKindDefinition } from "./types";

const registry = new Map<string, TabKindDefinition>();

export function registerTabKind(kind: string, def: TabKindDefinition): void {
  if (registry.has(kind)) {
    throw new Error(`Tab kind "${kind}" is already registered`);
  }
  registry.set(kind, def);
}

export function getTabKind(kind: string): TabKindDefinition | undefined {
  return registry.get(kind);
}

export function getTabComponent(kind: string): React.ComponentType<{ tab: ITab }> | null {
  return registry.get(kind)?.component ?? null;
}
