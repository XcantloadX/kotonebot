import { LanguageClient } from "vscode-languageclient/node";

/** 文档重命名预检返回的单条文件计划。 */
export interface RenameFileItem {
  /** 文件类型。 */
  kind: "image" | "meta";
  /** 所属变体名称。 */
  variant: string;
  /** 源文件绝对路径。 */
  sourcePath: string;
  /** 目标文件绝对路径。 */
  targetPath: string;
}

/** 文档重命名预检结果。 */
export interface RenameDocumentPrecheckResult {
  /** 是否存在冲突。 */
  hasConflicts: boolean;
  /** 冲突详情。 */
  conflicts: string[];
  /** 计划执行的文件重命名列表。 */
  fileRenames: RenameFileItem[];
}

/** 符号重命名受影响目标。 */
export interface RenameSymbolTarget {
  /** 唯一符号键。 */
  symbolKey: string;
  /** 所在 meta 文件路径。 */
  metaPath: string;
  /** 所在图片文件路径。 */
  imagePath: string;
  /** definition 标识。 */
  definitionId: string;
  /** 变体名；base 为 null。 */
  variant: string | null;
  /** definition 类型。 */
  type: string;
  /** 原符号名。 */
  oldName: string;
  /** 目标符号名。 */
  newName: string;
}

/** 符号重命名预检结果。 */
export interface RenameSymbolPrecheckResult {
  /** 触发重命名的源 meta。 */
  sourceMetaPath: string;
  /** 触发重命名的源 definition。 */
  sourceDefinitionId: string;
  /** 原符号名。 */
  oldName: string;
  /** 目标符号名。 */
  newName: string;
  /** 受影响目标列表。 */
  targets: RenameSymbolTarget[];
  /** 受影响 meta 文件数。 */
  affectedMetaCount: number;
  /** 受影响 definition 数。 */
  affectedDefinitionCount: number;
}

/** 符号重命名执行结果。 */
export interface RenameSymbolExecuteResult extends RenameSymbolPrecheckResult {
  /** 执行后的索引版本。 */
  updatedIndexVersion: number;
  /** 执行后的索引哈希。 */
  updatedContentHash: string;
}

/** 服务端命令与参数/返回值的类型映射。 */
export interface ServerCommandMap {
  /** 全量重建 meta 索引。 */
  "server.meta.refetch": {
    /** 命令参数。 */
    args: Record<string, never>;
    /** 命令返回值。 */
    result: unknown;
  };
  /** 更新单个 meta 文件索引。 */
  "server.meta.updateFile": {
    /** 命令参数。 */
    args: { metaPath: string };
    /** 命令返回值。 */
    result: unknown;
  };
  /** 文档改名预检。 */
  "server.document.rename.precheck": {
    /** 命令参数。 */
    args: { sourceImagePath: string; targetImagePath: string };
    /** 命令返回值。 */
    result: RenameDocumentPrecheckResult;
  };
  /** 文档改名执行。 */
  "server.document.rename.execute": {
    /** 命令参数。 */
    args: { sourceImagePath: string; targetImagePath: string };
    /** 命令返回值。 */
    result: unknown;
  };
  /** 符号重命名预检。 */
  "server.symbol.rename.precheck": {
    /** 命令参数。 */
    args: { metaPath: string; definitionId: string; newName: string };
    /** 命令返回值。 */
    result: RenameSymbolPrecheckResult;
  };
  /** 符号重命名执行。 */
  "server.symbol.rename.execute": {
    /** 命令参数。 */
    args: { metaPath: string; definitionId: string; newName: string };
    /** 命令返回值。 */
    result: RenameSymbolExecuteResult;
  };
}

/** 通过 LSP `workspace/executeCommand` 调用服务端命令。 */
export async function executeServerCommand<C extends keyof ServerCommandMap>(
  client: LanguageClient,
  command: C,
  args: ServerCommandMap[C]["args"],
): Promise<ServerCommandMap[C]["result"]> {
  return client.sendRequest("workspace/executeCommand", { command, arguments: [args] });
}
