# Pipeline 设计规范

本文档是 Pipeline 的正式设计规范，定义核心模型、调度语义、API 形态与构图规则。整体分为三个部分：

| 文档 | 内容 |
|------|------|
| [概念、定义与术语](concepts.md) | 定位与设计哲学、节点协议、术语表、配置如何改变行为 |
| [架构设计](design.md) | 四层架构模型、调度语义、Fragment / Runner / `>>` / 图冻结等设计细节 |
| [内置节点体系](builtins.md) | 框架内置节点 API 与命中后动作（actions） |
| [为什么？（被拒绝的设计）](why.md) | 集中收录被拒绝的设计与理由，正文以链接引用 |

## 阅读顺序建议 {#reading-order}

- **初学者**：从 [概念、定义与术语](concepts.md) 开始，理解「有向候选图 + 条件命中 + 节点副作用」的模型，再阅读 [架构设计](design.md) 掌握调度语义。
- **需要快速上手**：直接阅读 [Pipeline 教程](../../tutorials/pipeline.md)，在设计规范中遇到疑问时再回到本部分查阅。
- **需要了解可用节点**：查阅 [内置节点体系](builtins.md)。
- **想了解设计取舍**：查阅 [为什么？（被拒绝的设计）](why.md)，了解被拒绝的方案与理由。

## 核心模型速览 {#core-model}

```text
有向候选图 + 条件命中 + 节点副作用
```

- **Node** 是调度基本单元，只返回 `bool`：命中并接管，或未命中。
- **next** 是唯一基础控制流，顺序即检查优先级。
- **Fragment** 是构图期可复用片段，展开为纯 Node 图。
- **Pipeline** 是图容器，负责校验、冻结与运行。
- **`>>`** 是 `.next` 的结构化写法，带硬约束检查。

## 关键设计决策 {#key-decisions}

- 节点只返回 `bool`，不引入 `DONE` / `RETRY` / `JUMP` 等额外状态（见 [概念、定义与术语 §2](concepts.md#node)）。
- 控制流声明在图的 `next` 关系中，禁止任意跳转（见 [架构设计 §2](design.md#scheduling)）。
- Fragment 是纯粹的构图期概念，Runner 只处理纯 Node 图（见 [架构设计 §3](design.md#fragment-design)）。
- Pipeline 是图容器而非图元素，没有 `.next` 与 `>>`（见 [架构设计 §6](design.md#pipeline-design)）。
- 被拒绝的设计与理由集中见 [为什么？（被拒绝的设计）](why.md#rejected-designs)。

使用说明见 [Pipeline 教程](../../tutorials/pipeline.md)。
