# i18n 国际化机制指南

## 概述

devtools2 前端项目使用 `react-i18next` 作为国际化方案，支持中文（zh-CN）和英文（en）两种语言。

## 目录结构

```
src/i18n/
├── index.ts           # i18next 初始化配置
├── localeStore.ts     # Zustand 语言状态管理
└── locales/
    ├── en.json        # 英文翻译
    └── zh-CN.json     # 中文翻译
```

## 核心机制

### 1. 初始化 (index.ts)

- 使用 `i18next-browser-languagedetector` 自动检测语言
- 优先级：localStorage > 浏览器语言 > 默认中文
- 语言设置保存在 `kb-devtools-language` localStorage key

### 2. 语言切换 (localeStore.ts)

- 提供 `useLocaleStore` Hook 管理语言状态
- `setLanguage(lang)` 切换语言并持久化

### 3. 使用方式

```typescript
// 组件中使用
import { useTranslation } from 'react-i18next';

const MyComponent = () => {
  const { t } = useTranslation();
  return <div>{t('key.path')}</div>;
};

// 非组件中使用 (如 actions)
import i18n from '../i18n';
i18n.t('key.path');
```

## 新增翻译文本流程

### Step 1: 在翻译文件中添加 key

编辑 `src/i18n/locales/zh-CN.json`（中文作为基础语言）:

```json
{
  "section": {
    "keyName": "中文文本"
  }
}
```

同时在 `en.json` 添加:

```json
{
  "section": {
    "keyName": "English Text"
  }
}
```

### Step 2: 在组件中使用翻译

```typescript
import { useTranslation } from 'react-i18next';

const MyComponent = () => {
  const { t } = useTranslation();
  return <button>{t('section.keyName')}</button>;
};
```

### Step 3: 支持变量插值

翻译文本中使用 `{{variable}}` 占位:

```json
{
  "greeting": "你好, {{name}}"
}
```

调用:

```typescript
t('greeting', { name: '张三' })  // 输出: 你好, 张三
```

## Key 命名规范

| 模块 | 前缀 | 示例 |
|------|------|------|
| 菜单 | `menu.` | `menu.file`, `menu.edit` |
| 菜单项 | `menuItem.` | `menuItem.save`, `menuItem.openImage` |
| 工具栏 | `toolbar.` | `toolbar.select` |
| 右键菜单 | `contextMenu.` | `contextMenu.copy`, `contextMenu.delete` |
| 状态消息 | `status.` | `status.saved`, `status.noActiveDocument` |
| 问题面板 | `problems.` | `problems.title`, `problems.error` |
| 对话框 | `dialog.` | `dialog.confirm`, `dialog.cancel` |
| 命令 | `commands.` | `commands.save`, `commands.openImage` |
| 错误 | `error.` | `error.saveFailed` |
| 变体 | `variant.` | `variant.selectVariant` |
| 快捷键提示 | `shortcut.` | `shortcut.ctrlS` |
| 占位符 | `placeholder.` | `placeholder.searchCommands` |

## 常见操作

### 1. 添加新语言

1. 在 `index.ts` 的 `SUPPORTED_LANGUAGES` 添加语言代码
2. 创建新的 `locales/xx.json` 文件
3. 复制 `en.json` 内容并翻译

### 2. 语言切换 UI

在 TopMenuBar 中已有语言切换下拉框示例:

```typescript
import { useLocaleStore, SUPPORTED_LANGUAGES } from '../i18n/localeStore';
import { HTMLSelect } from '@blueprintjs/core';

const { language, setLanguage } = useLocaleStore();

<HTMLSelect
  value={language}
  onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
  options={SUPPORTED_LANGUAGES.map((lang) => ({ 
    value: lang, 
    label: lang === 'zh-CN' ? '中文' : 'English' 
  }))}
/>
```

### 3. 在 Zustand Store 中使用翻译

由于 store 不是 React 组件，直接使用 `useTranslation` hook 不行，需要直接导入 i18n:

```typescript
import i18n from '../i18n';

// 在 store 的 action 中
toaster.show({ 
  message: i18n.t('error.saveFailed', { message: errorMsg }), 
  intent: 'danger' 
});
```

### 4. 翻译动态内容

对于需要运行时拼接的文本，使用命名空间或分组:

```json
{
  "variant": {
    "selectVariant": "选择变体",
    "copyTo": "复制到 {{target}}"
  }
}
```

## 注意事项

1. **始终先修改 zh-CN.json** - 中文是基础语言
2. **保持中英文 key 一致** - 确保两种语言都有相同的 key
3. **使用 TypeScript 类型安全** - 翻译 key 只是字符串，不支持自动补全
4. **避免硬编码** - 所有用户可见文本都应该使用翻译函数
5. **构建测试** - 修改后运行 `npm run build` 确保无错误

## 快速检查清单

- [ ] 新增文本是否已添加到 zh-CN.json
- [ ] 新增文本是否已添加到 en.json
- [ ] 组件/文件中是否正确使用 `t('key.path')`
- [ ] 是否需要处理变量插值
- [ ] 构建是否通过 (`npm run build`)
