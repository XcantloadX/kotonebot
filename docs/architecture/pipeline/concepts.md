# Pipeline 概念、定义与术语

本文档是 [Pipeline 设计规范](index.md) 的一部分，定义核心模型、概念与术语。
调度语义、四层架构与构图规则见 [架构设计](design.md)，框架内置节点见 [内置节点体系](builtins.md)，被拒绝的设计与理由见 [为什么？（被拒绝的设计）](why.md#rejected-designs)。

使用说明见 [Pipeline 教程](../../tutorials/pipeline.md)。

---

## 1. 定位与设计哲学 {#positioning}

### 1.1 是什么

Pipeline 面向视觉驱动自动化（类似 MaaFramework 的 pipeline），**不是**传统事件驱动状态机，也**不是**线性数据处理链。

准确模型：

```text
有向候选图 + 条件命中 + 节点副作用
```

| 概念 | 含义 |
|------|------|
| NodeFactory | `@node` 产生的工厂，调用后创建 `Node` 实例 |
| Node | 可匹配、命中后执行 action 的原子步骤 |
| Fragment | 构图期片段，暴露 entry/exit，展开为纯 Node 图 |
| Pipeline | 一次具体任务流程，负责校验和执行 |
| Runner | 执行循环（由 `Pipeline._run` 实现），驱动 current 沿 next 推进 |
| entry / exit | Pipeline 的入口与完成点 |
| next | 有序候选列表，**唯一**基础控制流 |
| bool | 候选是否命中并接管流程 |
| `>>` | `.next` 的结构化写法，带硬约束检查 |

### 1.2 设计哲学

```text
最小惊讶原则：让 Python 使用者觉得自然，而不是在写 Python DSL
完整 Python 函数 / 闭包是默认写法
Python 是图语义的唯一真源
next 是唯一的基础控制流
节点只表达"本候选是否命中"
调度器负责推进 current
不引入第二套配置语言
```

`next` 声明相对方法内 `goto` 的优势在于，它**同时**表达：

- 从哪个阶段开始找
- 可以尝试哪些后继
- 检查优先级
- 命中之后控制权自然移到哪里

### 1.3 命名说明

讨论中曾考虑 `Workflow`、`TaskGraph`、`Scenario`、`Flow` 等名称。定稿对外与框架核心对象统一使用 **Pipeline**，与 MaaFramework 领域习惯对齐；其语义并非严格线性 pipeline，而是有序候选图。

---

## 2. 节点 {#node}

### 2.1 基本协议

节点只有一个基本协议：返回 `bool`。

```python
@node
def some_node() -> bool:
    ...
```

| 返回值 | 含义 |
|--------|------|
| `True` | 当前候选命中并成功接管流程；识别已成立，且 action（若有）已执行 |
| `False` | 当前候选不适用；调度器立即尝试同级下一个 |

节点**不返回** `NodeResult`、`DONE`、`MISS`、`SKIP`、`JUMP`、`FAIL` 等额外状态（为什么，见 [为什么？（被拒绝的设计）](why.md#no-noderesult)）。

### 2.2 bool 的语义：识别 + 动作合在一起

返回值只表达"本节点是否成功接管当前流程"：

```python
@node
def start_button() -> bool:
    if not game.screen.exists("start_button"):
        return False
    game.device.tap("start_button")
    return True
```

也可以只做识别：

```python
@node
def home() -> bool:
    return game.screen.exists("home")
```

### 2.3 节点种类

以下节点都遵循同一个 `-> bool` 协议，**不进入不同调度分支**：

- 自定义 Python 函数节点（`@node`）
- builtins 自带节点（`ocr` / `template_match` / `dummy` 等，见 [内置节点体系](builtins.md)）
- 通过 `Node(callback=...)` 显式构造的节点

调度器只关心 `target() -> bool`。

### 2.4 节点元数据

节点可携带展示与定位元数据：

```python
@node(id="home", label="主页")
def home() -> bool:
    ...
```

| 字段 | 用途 |
|------|------|
| `id` | 稳定身份：编辑器定位、trace、断点、回放 |
| `label` | 面向用户的展示名称 |

若不显式指定 `id`，默认使用 `模块名.函数qualname`。

这些元数据仅供展示与定位，不参与调度；图冻结只保护 `next` 结构，
`label` / `kind` 等在冻结后仍可修改（例如 `resolve_labels()` 会运行时改写 `label`）。

---

## 3. 配置改变行为 {#config-behavior}

### 3.1 节点内部判断

```python
@node
def fast_route() -> bool:
    return config.use_fast_route and screen.exists("fast_route")
```

配置未启用时，`fast_route` 返回 `False`，调度器自然继续尝试下一个候选。

### 3.2 配置决定拓扑

```python
def Daily(config: DailyConfig) -> Pipeline:
    ...
    if config.fast_mode:
        home >> [fast_route]
    else:
        home >> [normal_route]
    return Pipeline(entry=home, exit=done)
```
