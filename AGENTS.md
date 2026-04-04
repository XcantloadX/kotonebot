# KotoneBot Development Guide

## Frontend (kotonebot-devtools2)

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
2. **combo 冲突**：同一作用域内相同 combo 会抛出错误
3. **when 函数**：使用 `() => condition` 而非 `condition`，确保响应式更新
4. **输入框兼容**：默认在输入框内不触发，需要时设置 `allowInInput: true`
