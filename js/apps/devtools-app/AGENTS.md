# KotoneBot DevTools Frontend 开发指南

## 代码风格

### 错误提示

- 用户可见的错误/警告/成功提示必须使用 `toaster.show()`（从 `../../ui/toaster` 导入），禁止使用内联 `div` 展示错误信息。
- 仅在对话框内部状态管理或开发调试时可例外。

### 注释

使用 **JSDoc** 风格，中文撰写：

```ts
/** 简要描述功能。
 *
 * @param param1 - 参数说明
 * @param param2 - 参数说明
 * @returns 返回值说明
 */
function func(param1: string, param2: number): boolean { ... }
```

#### 覆盖范围

| 元素 | 必须 | 格式 |
|------|------|------|
| 模块/文件 | 是 | 文件顶部 `/** ... */` 或行注释 |
| 组件 | 是 | JSDoc，中文 |
| 公开函数/方法 | 是 | JSDoc，中文 |
| 私有方法/辅助函数 | 推荐 | JSDoc 或行注释 |
| Props 接口 / 类型定义 | 推荐 | 字段后注释 |

#### 行内注释

- 使用 `//`，中文
- **只写「为什么」不写「做了什么」**

---

### 快捷键系统

项目使用自定义的快捷键管理系统 (`src/shortcuts/shortcutManager.tsx`)，基于 React Context 实现。

#### 基本使用

1. **确保组件在 ShortcutProvider 内**

应用根组件已包裹 `ShortcutProvider`，所有子组件都可以使用快捷键功能。

```tsx
// App.tsx
<ShortcutProvider>
  <EditorApp />
</ShortcutProvider>
```

2. **注册单条快捷键：`useShortcut`**

```tsx
import { useShortcut } from "../shortcuts/shortcutManager";

useShortcut({
  id: "unique-shortcut-id",        // 唯一标识，用于冲突检测
  combo: "mod+s",                   // 快捷键组合
  scope: "editor",                  // 作用域
  onKeyDown: (event) => {           // 按下时触发
    // 处理逻辑
  },
  when: () => someCondition,        // 可选：运行时启用条件
  allowInInput: false,              // 可选：是否允许在输入框内触发
  allowRepeat: false,               // 可选：是否允许长按重复触发
});
```

3. **批量注册快捷键：`useShortcuts`**

```tsx
import { useShortcuts } from "../shortcuts/shortcutManager";

useShortcuts([
  { id: "shortcut-1", combo: "a", scope: "editor", onKeyDown: () => {} },
  { id: "shortcut-2", combo: "b", scope: "editor", onKeyDown: () => {} },
]);
```

4. **激活/停用作用域：`useShortcutScope`**

```tsx
import { useShortcutScope } from "../shortcuts/shortcutManager";

// 当 modalOpen 为 true 时激活 "modal" 作用域
useShortcutScope("modal", modalOpen);
```

#### 作用域与优先级

系统预设的作用域按优先级从低到高：

| 作用域 | 优先级 | 用途 |
|--------|--------|------|
| `global` | 0 | 全局快捷键，始终可用 |
| `editor` | 10 | 编辑器主界面 |
| `menu` | 20 | 菜单打开时 |
| `palette` | 30 | 命令面板/QuickPick |
| `modal` | 40 | 弹窗/对话框 |

高优先级作用域激活后，会屏蔽低优先级作用域的同名快捷键。

#### 快捷键组合格式

- 单键：`a`、`1`、`escape`、`space`、`up`、`down`、`enter`
- 修饰键：`ctrl`、`shift`、`alt`、`meta`（Mac 的 Command）
- 跨平台：`mod`（Mac 为 `meta`，Windows/Linux 为 `ctrl`）
- 组合：`mod+s`、`ctrl+shift+z`、`alt+enter`

#### 常见模式

**带快捷键角标的按钮**

对话框中如果按钮存在明确快捷键（例如 Enter / Esc），优先使用 `ShortcutButton` 显示角标，避免在业务组件里重复手写样式。

```tsx
import { ShortcutButton } from "../ui/components/ShortcutButton";

<ShortcutButton
  intent="primary"
  onClick={handleConfirm}
  shortcutText="Enter"
>
  {t("dialog.confirm")}
</ShortcutButton>
```

**对话框内快捷键**

```tsx
const MyDialog: React.FC<{ isOpen: boolean }> = ({ isOpen }) => {
  const [hasData, setHasData] = useState(false);

  useShortcut({
    id: "dialog-confirm",
    combo: "enter",
    scope: "modal",
    when: () => isOpen && hasData,  // 仅在对话框打开且有数据时响应
    onKeyDown: () => {
      handleConfirm();
    },
  });

  return <Dialog isOpen={isOpen}>...</Dialog>;
};
```

**条件性快捷键**

```tsx
useShortcut({
  id: "delete-selected",
  combo: "delete",
  scope: "editor",
  when: () => hasSelection,  // 仅在有选中项时响应
  onKeyDown: () => deleteSelection(),
});
```

#### 注意事项

1. **id 必须唯一**：重复的 id 会抛出错误
2. **combo 冲突**：`editor` / `menu` / `palette` 仍保持严格冲突校验；`modal` 允许多个可见弹窗共存，由后注册的绑定在运行时优先生效
3. **when 函数**：使用 `() => condition` 而非 `condition`，确保响应式更新
4. **输入框兼容**：默认在输入框内不触发，需要时设置 `allowInInput: true`

---

### Action / Command / Top Menu / Right Menu 四层架构

#### 总体数据流

```
Right Menu / Top Menu
  → executeCommand(COMMAND_ID.*, context, args)
    → Command Registry（查定义 + 评估 when/requiredUi）
      → run() → editorActions.xxx.yyy()
        → Zustand stores / Server RPC
```

#### Action

**位置**：`src/editor/actions/index.ts` + 同目录子文件（`close.ts`、`definition.ts`、`image.ts` 等）

最底层的具体实现，以命名空间对象导出：

```typescript
editorActions = {
  image, document, variant, navigation, definition, symbol
}
```

每个成员是纯异步函数，直接操作 Zustand store 或调用服务端 RPC。

#### Command

**位置**：`src/editor/commands/`

| 文件 | 职责 |
|------|------|
| `ids.ts` | `COMMAND_ID` 常量表 |
| `types.ts` | `EditorCommandArgsMap`（参数类型）、`EditorCommandDefinition`（结构）、`EditorCommandUiHandlers`（需 UI 提供的回调） |
| `registry.ts` | `editorCommandRegistry`（注册表）+ `paletteCommandIds`（命令面板列表） |
| `executor.ts` | `executeCommand()` |
| `status.ts` | `useCommandStatuses()` hook，供 UI 查询启用态 |

命令定义结构：
```typescript
{
  id: COMMAND_ID.FILE_SAVE,
  title: t('menuItem.save'),
  keywords: ["save"],
  showInPalette: true,
  when: () => canSaveActiveDocument(),   // 启用态判断（可选）
  requiredUi: ["openImageDialog"],        // 需要 UI 回调时填写（可选）
  run: async (ctx, args) => { await editorActions.document.save(); }
}
```

#### Top Menu

**位置**：`src/ui/TopMenuBar.tsx`

三个菜单（`file` / `edit` / `variant`）全部硬编码在 `menuDefinitions` 这一 `useMemo` 对象中。菜单项的 `disabled` 通过 `useCommandStatuses()` 从对应 command 的 `when()` 派生，`onClick` 调用 `executeCommand()`。键盘快捷键通过 `useShortcut()` 单独注册。

#### Right Menu

**位置**（三处独立，不共享）：
- `src/editor/konva/StageView.tsx`：画布右键（点击 shape / 点击空白各一套）
- `src/ui/HierarchyPanel.tsx`：层级面板右键
- `src/ui/TabBar.tsx`：Tab 标签右键

每处用 `useState<{x, y, ...} | null>` 管理菜单状态，菜单项直接内联 JSX，`onClick` 调用 `executeCommand()`。

---

#### 新增功能完整步骤

1. **Action**：在 `src/editor/actions/` 对应子文件实现函数，并在 `index.ts` 的 `editorActions` 中挂载。
2. **Command ID**：在 `ids.ts` 的 `COMMAND_ID` 对象加一行。
3. **参数类型**：在 `types.ts` 的 `EditorCommandArgsMap` 加一行（无参数填 `undefined`）。
4. **命令定义**：在 `registry.ts` 的 `commands` 对象加一项（含 `title`、`when`、`run`）；若需命令面板入口，同时加入 `paletteCommandIds`。
5. **翻译**：在 `src/i18n/locales/zh-CN.json` 和 `en.json` 加对应 key。
6. **Top Menu**（如需）：在 `TopMenuBar.tsx` 的 `statusEntries` 加条目、在 `menuDefinitions` 对应菜单数组加菜单项、用 `useShortcut()` 注册快捷键。
7. **Right Menu**（如需）：在 `HierarchyPanel.tsx` / `StageView.tsx` 的右键菜单 JSX 加 `<MenuItem>`，`onClick` 调用 `executeCommand()`。

#### 修改已有项

| 修改内容 | 需动的文件 |
|----------|-----------|
| 改命令显示名称 | `registry.ts` 的 `title` + i18n JSON |
| 改启用/禁用逻辑 | `registry.ts` 的 `when()` 及 `selectors.ts` |
| 改执行逻辑 | `registry.ts` 的 `run()` 或 actions 子文件 |
| 改菜单项文字 | i18n JSON + `TopMenuBar.tsx` 中的 `text` 字段 |
| 改菜单项位置 | `TopMenuBar.tsx` 中 `menuDefinitions` 数组顺序 |

#### 删除功能

1. `ids.ts`：删除 `COMMAND_ID` 条目
2. `types.ts`：删除 `EditorCommandArgsMap` 对应行
3. `registry.ts`：删除命令定义，以及 `paletteCommandIds` 中的引用
4. `TopMenuBar.tsx`：删除 `statusEntries` 条目、`menuDefinitions` 菜单项、`useShortcut` 注册
5. `HierarchyPanel.tsx` / `StageView.tsx` / `TabBar.tsx`：删除对应 `<MenuItem>`
6. i18n JSON：删除对应 key
7. `actions/`：删除 action 实现及 `index.ts` 挂载
