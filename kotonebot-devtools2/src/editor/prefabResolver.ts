/**
 * 为 Variant 渲染解析 base prefab 定义，统一查找顺序：
 * 1）已打开文档的内存状态（包含未保存改动）；
 * 2）symbol index 快照；
 * 3）磁盘上的 meta 文件。
 */
import { readText } from "../api/fs";
import { DefinitionModel } from "../model/metaV2";
import { SymbolLite } from "../model/symbolIndex";
import { DocumentState } from "./state";

interface ResolveBasePrefabOptions {
  names: string[];
  documents: Record<string, DocumentState>;
  symbols: SymbolLite[];
}

export interface ResolveBasePrefabResult {
  byName: Record<string, DefinitionModel>;
  missingNames: string[];
}

export async function resolveBasePrefabsByName(options: ResolveBasePrefabOptions): Promise<ResolveBasePrefabResult> {
  const requested = Array.from(new Set(options.names));
  if (requested.length === 0) {
    return { byName: {}, missingNames: [] };
  }

  const byName: Record<string, DefinitionModel> = {};
  for (const doc of Object.values(options.documents)) {
    if (!doc.meta) {
      continue;
    }
    for (const definition of Object.values(doc.meta.data.definitions)) {
      if (definition.type !== "prefab" || !!definition.variant || !definition.name) {
        continue;
      }
      if (byName[definition.name]) {
        continue;
      }
      byName[definition.name] = definition;
    }
  }

  const loadedMetaCache: Record<string, any> = {};
  const missingNames: string[] = [];
  for (const name of requested) {
    if (byName[name]) {
      continue;
    }

    const baseSymbol = options.symbols.find((symbol) => symbol.type === "prefab" && symbol.name === name && symbol.variant === null);
    if (!baseSymbol) {
      missingNames.push(name);
      continue;
    }

    if (!loadedMetaCache[baseSymbol.metaPath]) {
      const text = await readText(baseSymbol.metaPath);
      loadedMetaCache[baseSymbol.metaPath] = JSON.parse(text);
    }
    const baseMeta = loadedMetaCache[baseSymbol.metaPath];
    if (!baseMeta || baseMeta.version !== 3 || !baseMeta.definitions) {
      missingNames.push(name);
      continue;
    }

    const baseDefinition = baseMeta.definitions[baseSymbol.definitionId];
    if (!baseDefinition || baseDefinition.type !== "prefab") {
      missingNames.push(name);
      continue;
    }
    byName[name] = baseDefinition as DefinitionModel;
  }

  return { byName, missingNames };
}
