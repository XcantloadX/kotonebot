# 为什么？

本文档是 [Pipeline 设计规范](index.md) 的一部分，集中收录设计过程中**被拒绝（摒弃）的方案与理由**，回答「为什么不采用 X」这类问题。

设计正文只保留结论与正向设计；「为什么」的讨论统一引向本文。核心概念与术语见 [概念、定义与术语](concepts.md)，架构与调度语义见 [架构设计](design.md)，使用说明见 [Pipeline 教程](../../tutorials/pipeline.md)。

---

## 被拒绝的设计总览 {#rejected-designs}

被拒绝的设计及理由见下表，每一项的详细表述见对应小节：

| 拒绝项 | 原因 | 详细 |
|--------|------|------|
| `NodeResult` / `DONE` / `MISS` / `JUMP` | 与 Maa 式候选匹配冲突 | [§1](#no-noderesult) |
| 任意 `JUMP` 到图外节点 | 破坏静态图作为控制流真源 | [§2](#no-jump) |
| 通用 `ctx` / `PipelineContext` 作为主 API | 闭包 / 局部状态已足够 | [§3](#no-ctx) |
| `Flow` / `PipelineCall` 等运行时复合类型 | 由 Fragment 构图期展开替代 | [§4](#no-runtime-fragment) |
| jump-back 隐式语义 | 所有循环必须显式 | [§5](#no-jump-back) |
| `@node.entry` / `@node.exit` | 图角色与节点行为耦合 | [§6](#no-entry-exit) |
| 第二份 JSON / YAML 可运行 pipeline 定义 | 退回 Maa 配置路线 | [§7](#no-config) |
| `.act()` 方法 | 统一为 `actions=` 构造参数 | [§8](#no-act) |
| class + `wire()` 辅路径 | 函数工厂 + Fragment 已覆盖全部场景 | [§9](#no-class-wire) |
| `Pipeline.next` / `Pipeline >>` | Pipeline 是图容器，不是图元素 | [§10](#pipeline-not-node) |
| 预声明 `Node()` 再绑定实现 | 双重命名，IDE / 阅读不友好 | [§11](#no-predeclare) |
| 事务式 `commit` / `rollback` | 普通 Python 装配 + 失败丢弃即可 | [§12](#no-commit) |

## 1. 为什么节点只返回 bool，不用 NodeResult {#no-noderesult}

相关正文见 [概念、定义与术语 §2.1](concepts.md#node)。

中间方案曾提出 `DONE / RETRY / SKIP / JUMP / FAIL`，对 Maa 式候选扫描是错误抽象：

- `RETRY` / `MISS` 会阻塞在当前候选上，破坏"同级候选按序检查"
- `JUMP` 绕开静态边，图不再是控制流真源
- `SKIP` / `FAIL` 把本可由 `False`、Runner 超时或显式错误后继表达的事复杂化

定稿只保留：

```python
True   # 命中，已执行 action
False  # 未命中；立即继续检查同级下一个候选
```

## 2. 为什么禁止任意跳转 {#no-jump}

相关正文见 [架构设计 §2](design.md#scheduling)。

节点函数内部**不提供** `goto()`、`jump()` 或返回目标节点，控制流必须显式声明在图上的 `next` 关系中。

任意 `JUMP` 到图外节点会破坏静态图作为控制流真源：跳转目标不在图上，图不再是完整、可分析、可 trace 的控制流表述。

## 3. 为什么没有通用 ctx / PipelineContext {#no-ctx}

相关正文见 [架构设计 §8.1](design.md#state)。

Pipeline 不引入通用 `PipelineContext`，状态放在闭包捕获的局部对象上即可：

- 局部对象与节点函数处于同一作用域，读写直接、类型完整，无需额外的间接层
- 不需要为一次任务实例管理 ctx 的生命周期、所有权与并发访问
- 符合「完整 Python 函数 / 闭包是默认写法」「让 Python 始终作为唯一语义真源」的定位

状态写法的具体示例见 [架构设计 §8.1](design.md#state)。

## 4. 为什么不把 Fragment 做成运行时类型 {#no-runtime-fragment}

相关正文见 [架构设计 §3](design.md#fragment-design)。

Fragment 被设计为纯粹的构图期概念，原因：

- **简化 Runner**：Runner 只需要处理单一类型（Node），无需在运行时分支判断 Node vs Pipeline vs Fragment
- **消除 jump-back**：旧的子 Pipeline 模型引入了隐式 jump-back 语义（空 `Pipeline.next` 时返回父节点），Fragment 展开后所有连接都是显式的
- **图分析更简单**：展开后的纯 Node 图没有复合节点，可达性分析、可视化、trace 都只需要处理一种类型

## 5. 为什么拒绝 jump-back 隐式语义 {#no-jump-back}

相关正文见 [架构设计 §1.4](design.md#four-layer-model)。

旧子 Pipeline 模型与「Pipeline 伪装成 Node」的模型都有"`next` 为空时返回父节点"的隐式行为。问题：

- **控制流不可见**：图上没有显式标注返回边，trace、可视化与可达性分析都会漏掉这条隐式路径
- **心智负担**：读者必须知道"空 `next` 隐含返回"才能理解运行行为，违背最小惊讶原则
- **与显式原则冲突**：设计哲学要求所有后继显式声明，隐式跳转制造不可见的控制流

新设计中所有循环与转移都通过显式 `next` 边表达。

## 6. 为什么拒绝 @node.entry / @node.exit {#no-entry-exit}

曾考虑在 `@node` 装饰器上提供 `entry` / `exit` 参数，让节点自述图角色。问题：

- **职责耦合**：图角色（入口 / 出口）是构图期的拓扑信息，与节点自身行为无关
- **阻碍复用**：同一节点在不同图或同一图的不同位置可能扮演不同角色，写死在装饰器上无法复用
- **角色本应属于容器**：入口 / 出口由 Fragment / Pipeline 的构造参数显式声明即可

因此节点不感知自己的图角色，图角色由容器在构图期声明。

## 7. 为什么拒绝第二份 JSON / YAML 定义 {#no-config}

曾考虑允许用第二份 JSON / YAML 声明可运行的 pipeline。问题：

- **双重语义真源**：同一流程存在 Python 与配置文件两套表述，必须手动保持一致，容易漂移
- **表达力不足**：视觉条件、状态判断、复杂动作无法在配置语言中完整表达，最终仍需回退到 Python
- **违背定位**：与「不引入第二套 DSL」「让 Python 始终作为唯一语义真源」冲突

Python 本身即配置语言，声明式配置路线退回 Maa 配置。

## 8. 为什么拒绝 .act() 方法 {#no-act}

曾考虑让节点提供 `.act()` 方法在命中后执行动作。问题：

- **副作用位置分散**：动作逻辑写在节点内部，识别与动作分离，阅读时需要跳转
- **无法声明式组合**：动作（点击、睡眠、日志等）难以像数据一样列出并复用
- **`actions=` 更优**：`actions=` 构造参数把命中后动作作为节点数据显式声明，便于检查与复用

因此统一为 `actions=` 构造参数。

## 9. 为什么拒绝 class + wire() 辅路径 {#no-class-wire}

曾考虑提供 class 风格配合 `wire()` 方法显式装配的辅助路径。问题：

- **双写范式**：同一构图逻辑存在函数与 class 两种写法，读者、编辑器与工具都要处理两套形态
- **无新增能力**：复用、组合、参数化全部场景已被函数工厂 + Fragment 覆盖
- **维护翻倍**：API 面、文档、测试都要双轨维护

因此只保留函数工厂 + Fragment 一条路径。

## 10. 为什么 Pipeline 不再伪装成 Node {#pipeline-not-node}

相关正文见 [架构设计 §6](design.md#pipeline-design)。

旧设计中 `Pipeline` 继承 `_GraphElement`，拥有 `.next` 和 `>>`，可以作为复合节点出现在其他 Pipeline 的 `next` 中。这引入了：

- **jump-back 语义**：`Pipeline.next` 为空时隐含"返回父节点"
- **两层冻结**：内部节点冻结 vs 外部 `Pipeline.next` 解耦
- **运行时复合类型**：Runner 需要同时处理 `Node` 和 `Pipeline`

新设计中：

- `Pipeline` 不再是图元素，而是图容器
- `Fragment` 承担了构图期组合的职责
- Runner 只处理纯 `Node` 图
- 所有后继关系都是显式的，没有隐式语义

## 11. 为什么拒绝预声明 Node() 再绑定实现 {#no-predeclare}

曾考虑先 `Node()` 创建占位实例，后续再绑定回调实现。问题：

- **双重命名**：同一节点既要给占位实例命名，又要给回调函数命名，IDE 与阅读都不友好
- **绑定顺序脆弱**：先使用占位节点、再绑定实现，容易遗漏或顺序错误
- **`@node` 一步到位**：工厂一次调用即可创建完整节点，无需两阶段

因此拒绝预声明再绑定的写法。

## 12. 为什么拒绝事务式 commit / rollback {#no-commit}

曾考虑在构图期提供事务式提交 / 回滚（装配失败可回滚到上次成功状态）。问题：

- **复杂化构图期**：需要维护装配历史与回滚栈，收益有限
- **普通 Python 天然可丢弃**：装配失败直接抛异常丢弃本次构造，函数重跑即重建
- **fail fast 原则**：装配错误应尽早暴露，而不是回滚重来

因此构图期只使用普通 Python 装配，失败即丢弃。
