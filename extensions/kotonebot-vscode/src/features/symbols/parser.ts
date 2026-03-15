import { SymbolTreeNode } from "./types";

/** 将后端返回的树结构解析为前端节点模型。 */
export function parseServerTree(payload: unknown): SymbolTreeNode[] {
  if (!Array.isArray(payload)) {
    throw new Error("Invalid kotonebot/symbolTree response");
  }
  return payload.map((item) => parseTreeNode(item));
}

/** 递归解析单个树节点。 */
function parseTreeNode(value: unknown): SymbolTreeNode {
  if (typeof value !== "object" || value === null) {
    throw new Error("Invalid tree node payload");
  }
  const node = value as Record<string, unknown>;
  const kind = node.kind;
  if (kind === "group") {
    const label = node.label;
    const children = node.children;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid group.label");
    }
    if (!Array.isArray(children)) {
      throw new Error("Invalid group.children");
    }
    return {
      kind: "group",
      label,
      children: children.map((item) => parseTreeNode(item)),
    };
  }
  if (kind === "symbol") {
    const label = node.label;
    const fullName = node.fullName;
    const displayName = node.displayName;
    const children = node.children;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid symbol.label");
    }
    if (typeof fullName !== "string" || fullName.trim() === "") {
      throw new Error("Invalid symbol.fullName");
    }
    if (displayName !== null && typeof displayName !== "string") {
      throw new Error("Invalid symbol.displayName");
    }
    if (!Array.isArray(children)) {
      throw new Error("Invalid symbol.children");
    }
    return {
      kind: "symbol",
      label,
      fullName,
      displayName,
      children: children.map((item) => {
        const child = parseTreeNode(item);
        if (child.kind !== "variant") {
          throw new Error("symbol.children must be variant nodes");
        }
        return child;
      }),
    };
  }
  if (kind === "variant") {
    const label = node.label;
    const children = node.children;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid variant.label");
    }
    if (!Array.isArray(children)) {
      throw new Error("Invalid variant.children");
    }
    return {
      kind: "variant",
      label,
      children: children.map((item) => {
        const child = parseTreeNode(item);
        if (child.kind !== "file") {
          throw new Error("variant.children must be file nodes");
        }
        return child;
      }),
    };
  }
  if (kind === "file") {
    const label = node.label;
    const metaPath = node.metaPath;
    const imagePath = node.imagePath;
    const definitionId = node.definitionId;
    if (typeof label !== "string" || label.trim() === "") {
      throw new Error("Invalid file.label");
    }
    if (typeof metaPath !== "string" || metaPath.trim() === "") {
      throw new Error("Invalid file.metaPath");
    }
    if (typeof imagePath !== "string" || imagePath.trim() === "") {
      throw new Error("Invalid file.imagePath");
    }
    if (typeof definitionId !== "string" || definitionId.trim() === "") {
      throw new Error("Invalid file.definitionId");
    }
    return {
      kind: "file",
      label,
      metaPath,
      imagePath,
      definitionId,
    };
  }
  throw new Error(`Unsupported node kind: ${String(kind)}`);
}
