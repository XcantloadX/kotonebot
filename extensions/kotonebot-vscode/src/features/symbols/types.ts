/** 符号树节点联合类型。 */
export type SymbolTreeNode = GroupNode | SymbolNode | VariantNode | FileNode;

/** 命名空间分组节点，对应 name 点分路径中的中间层。 */
export interface GroupNode {
  /** 节点类型标记。 */
  kind: "group";
  /** 当前分组段名。 */
  label: string;
  /** 子节点列表。 */
  children: SymbolTreeNode[];
}

/** 业务符号节点，同一个完整 name 在树中只保留一份。 */
export interface SymbolNode {
  /** 节点类型标记。 */
  kind: "symbol";
  /** 显示名称（name 最后一段）。 */
  label: string;
  /** 完整符号名（点分形式）。 */
  fullName: string;
  /** 人类可读名称。 */
  displayName: string | null;
  /** variant 子节点列表。 */
  children: VariantNode[];
}

/** 变体节点，承载同一符号在不同 variant 下的文件入口。 */
export interface VariantNode {
  /** 节点类型标记。 */
  kind: "variant";
  /** 变体名。 */
  label: string;
  /** 文件叶子节点列表。 */
  children: FileNode[];
}

/** 文件叶子节点，点击后仅打开文件。 */
export interface FileNode {
  /** 节点类型标记。 */
  kind: "file";
  /** 展示名称（meta 文件名）。 */
  label: string;
  /** meta 文件绝对路径。 */
  metaPath: string;
  /** image 文件绝对路径。 */
  imagePath: string;
  /** definition 标识。 */
  definitionId: string;
}

/** Python 重命名预演结果。 */
export interface PythonRenamePreview {
  /** 预演得到的工作区编辑；无需改动时为 null。 */
  edit: import("vscode").WorkspaceEdit | null;
  /** 将被修改的 Python 文件列表。 */
  pythonFiles: string[];
}
