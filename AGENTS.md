# KotoneBot Development Guide

## 维护本文件（必读）

**每次对项目做出改动后**，必须检查本 `AGENTS.md` 是否仍与代码库一致。若出现以下情况，应同步更新本文档：

- 新增/删除/移动模块或目录
- 架构、数据流、API 契约发生变化
- 配置格式有调整
- 开发/测试/构建命令变更
- 代码规范或质量检查流程变更

不要把 AGENTS.md 当作一次性文档；它是 Agent 与开发者协作的**活文档**。

---

## 通用 Style

### 通用原则

* 在改动或重构时，不可以删除原来用户的注释。除非相关代码已经被移除。如果代码逻辑变动，则需要一并修改注释内容

### 注释规范

#### Docstring 格式（Python）

使用 **reStructuredText (RST)** 格式，中文撰写：

```python
def func(param1: str, param2: int) -> bool:
    """简要描述功能。

    :param param1: 参数说明
    :param param2: 参数说明
    :returns: 返回值说明
    :raises SomeError: 异常说明
    """
```

##### 覆盖范围

| 元素 | 必须 | 格式 |
|------|------|------|
| 模块 | 是 | 文件顶部一行中文描述 |
| 类 | 是 | 类定义下方，中文 |
| 公开方法 | 是 | RST，中文 |
| 私有方法 | 推荐 | 一行 `#` 注释或 docstring |
| 属性（dataclass / pydantic field） | 是 | 字段后的注释 |

#### Docstring 格式（TypeScript / React）

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

##### 覆盖范围

| 元素 | 必须 | 格式 |
|------|------|------|
| 模块/文件 | 是 | 文件顶部 `/** ... */` 或行注释 |
| 组件 | 是 | JSDoc，中文 |
| 公开函数/方法 | 是 | JSDoc，中文 |
| 私有方法/辅助函数 | 推荐 | JSDoc 或行注释 |
| Props 接口 / 类型定义 | 是 | 字段后注释 |

#### 代码行内注释

- 复杂逻辑段上方加 `#`（Python）或 `//`（TypeScript）注释说明意图
- **禁止写「这段代码做了什么」这类显而易见的注释，而应写「为什么要这样做」**
- 所有注释使用中文

---

## 通用规范

### 路径管理集中化

- **严格禁止**在代码中散落路径字符串字面量（包括文件系统路径与 API 路径）。
- 如果某个路径是项目内约定俗成的固定路径，例如 `./logs`、`./conf` 等，必须在某处专用管理路径的模块内提供常量与拼接函数。如果不存在这样的模块，先询问用户关于在哪里创建的意见。
- 对于约定好的固定路径，**绝对禁止**任何形式的裸露字符串插值。

### 兼容性

- 如果本次更改涉及配置、数据、公共 API 等兼容性问题，**总是显式询问**用户为兼容性更新还是破坏性更新。
- 如果本次更改仅涉及内部 API、方法、类等**更名**，**总是不需要兼容性**（除非用户提出）。并且必须一次性完成所有调用方的重命名。
- 如果需要移除某功能或 API，**严格禁止在任何位置留下"XXX已移除""XXX现已被XXX代替"等无意义说明。此项必须绝对执行！**

### 类型

- 对于 Python 与 TypeScript，必须严格执行类型标注。**除非极其困难，否则不得使用 any、unknown！**
- **除非极其困难，否则不得使用 `//ts-igore`、`# type: ignore` 等任意类型忽略！**
- 本次更改的代码中，若涉及 any、unknown 或任意类型 ignore，必须向用户报告。
- 对于 TS，**尽量避免**过长的 inline 类型。
- 对于 PySide/PyQt（本项目中不涉及），类型忽略规则不适用。

### 降级处理

- 任何时候，除非用户显式要求，否则**严格禁止**任何形式的 fallback。
- **绝对不允许**任何形式的"简化处理"或"placeholder 代码"。如果是因为用户要求模糊导致，总是停下来询问用户，直到得出明确清晰的实现为止才开始编写代码。
- 总是遵循 fail fast 原则。

### 杂项

- 除非用户要求，否则**禁止私自**格式化代码。

---

## Python 代码规范

### 禁止裸露 dict / tuple

- **绝对禁止**在代码中使用裸露的 `dict`（包括任意字面量 `{...}` 作为数据容器）。
- **绝对禁止**使用超过两个元素的裸露 `tuple`（两个元素的 `tuple` 仅限用于类似 `(x, y)` 坐标等明确场景）。
- **一律使用 Pydantic `BaseModel`**，包括函数参数、返回值、内部中间数据结构。

### import 规则

- 除非是重依赖懒加载、平台可选依赖、循环导入等场景，否则**严格禁止**在非文件顶部导入模块。
- 除非用户明确要求这是可选依赖，否则**严格禁止** try import except print("依赖未安装")。
- **import 库总是不考虑 try except 与 fallback**，除非这是平台兼容或 Python 兼容相关代码。

### 日志与异常处理

- raise 异常时，**尽可能避免** RuntimeError/Exception，而是定义足够语义化的异常。如果项目内还没有成体系的异常系统，总是先询问用户意见。
- 捕获异常后，**绝对需要**日志输出，哪怕这是预期中可被处理的情况。
- 在编写代码的过程中，**总是**有意识的输出可辅助调试与排查问题的日志。不要一条日志都没有，也不要过于 verbose。

### HTTP 交互

- **绝对禁止**任何裸露 fetch/XHR/axios，而是使用项目内已有的请求体系。如果没有这样的体系，总是先询问用户是否建立。
- 在定义 API 请求与响应格式时，**总是**遵循项目内已有的体系。如果没有这样的体系，总是先询问用户是否建立。

### 杂项

- **任何时候都绝对禁止**使用 `from __future__ import annotations`。
- 除非 atrr name 真的是动态的，否则**严格禁止**使用 `getattr` 与 `setattr`。
- 返回 `Pipeline` / `Fragment` 的**工厂函数**（即「定义流程」的函数）使用**大驼峰命名**（如 `Daily`、`ClosePopup`），与类名一致；`@node` 节点回调保持小写（如 `buy`、`finish`）。

---

## 代码质量

每次代码修改完成后，必须运行以下检查并确保全部通过：

| 范围 | 命令 | 说明 |
|------|------|------|
| Python lint | `uv run ruff check .` | ruff 规则检查 |
| Python tests | `uv run python -m unittest discover` | 全部单测 |
| JS/TS build | `cd js/apps/devtools-app && npm run build` | 类型检查 + 构建 |

---

## Commit 规范

采用 Angular Commit Convention，message 用中文，scope 示例：

| Scope | 说明 |
|-------|------|
| **core** | `kotonebot/` 核心运行时库 |
| **devtools** | `kotonebot/devtools/` + `js/apps/devtools-app/` |
| **devtools:backend** | `kotonebot/devtools/` Python 代码 |
| **devtools:frontend** | `js/apps/devtools-app/` |
| **devtools:conversion** | `kotonebot/devtools/conversion/` Single→Multi 转换模块 |
| **ext** | `js/apps/vscode-ext/` |
| **docs** | `docs/`、`AGENTS.md`、`README.md` |
| **deps** | 依赖升级 |
| **ci** | `.github/workflows/`、构建配置 |

## Changelog 规范

`CHANGELOG.md` 是写给**下游使用用户**看的，记录用户在升级后可直接察觉的行为变化。

- **面向用户**：只记录用户可察觉的变化（功能、行为、配置格式、破坏性变更）。**禁止**写入内部实现细节，例如内部 API 更名、代码结构重构、内部模块调整等。
- **条目格式**：`[类型] 描述`，类型为 `feat`（新功能）、`fix`（修复）、`refactor`（用户可见行为变化的重构）、`chore` 等，描述使用中文。
- **分组**：按模块分组，依次为 `Devtool:` / `Devtools:`、`Library:`、`Framework:` 等，组内条目编号。
- **破坏性变更**：在条目内标注 `**BREAKING**`，必要时另起段落说明迁移方式。
- **版本号**：已有未发布版本条目时追加到该版本；新版本条目加在文件顶部。
- **提交**：changelog 更新与对应代码改动在同一个 commit 中提交。

## 专用 Style
- 对于 OpenCV Image，Python 类型标注为 cv2.typing.MatLike 而不是 np.ndarray