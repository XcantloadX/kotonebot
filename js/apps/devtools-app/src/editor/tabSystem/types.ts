import type { EditorCommandContext } from "../commands/types";

/** 通用标签页接口。所有 tab 在 tab manager 眼中只通过此接口操作。 */
export interface ITab {
  /** 唯一标识，用于 dedup 和切换。 */
  id: string;
  /** 标签种类，对应注册表中的 TabKindDefinition。 */
  kind: string;
  /** 显示名称。 */
  label: string;
  /** 是否可关闭（默认 true）。 */
  closable?: boolean;
  /** 种类专属的附加数据。例如 document 的 { docId: string }。 */
  metadata?: Record<string, unknown>;
}

export interface TabKindDefinition {
  /** 该种类 tab 激活时渲染的组件。 */
  component: React.ComponentType<{ tab: ITab }>;
  /** 默认图标。 */
  icon?: React.ReactNode;
  /** 是否默认可关闭（单个 tab 可通过 ITab.closable 覆盖）。 */
  defaultClosable?: boolean;
  /** 完全接管关闭流程。返回 false 表示取消关闭（中止批量关闭）。 */
  onClose?: (tab: ITab, ctx: EditorCommandContext) => Promise<boolean>;
  /** 判断该 kind 的 tab 是否为脏状态（显示圆点标记）。 */
  isDirty?: (tab: ITab) => boolean;
  /** 右键菜单中追加的自定义项。 */
  contextMenuItems?: (tab: ITab, ctx: EditorCommandContext) => React.ReactNode[];
}
