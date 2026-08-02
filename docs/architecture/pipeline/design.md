# Pipeline 架构设计

本文档是 [Pipeline 设计规范](index.md) 的一部分，描述四层架构、调度语义与构图规则。
核心概念与术语见 [概念、定义与术语](concepts.md)，框架内置节点见 [内置节点体系](builtins.md)，被拒绝的设计与理由见 [为什么？（被拒绝的设计）](why.md#rejected-designs)。

使用说明见 [Pipeline 教程](../../tutorials/pipeline.md)。

---

## 1. 四层架构模型 {#four-layer-model}

### 1.1 总览

```text
@node
  ↓
NodeFactory ──调用──> Node
                       │
普通函数组装多个 Node  │
  ↓                    │
Fragment(entry, exit) ─┘
  ↓ 构图期展开
纯 Node 图
  ↓
Pipeline(entry, exit)
  ↓ 校验、冻结、运行
Runner（Pipeline 内部执行循环）
```

### 1.2 NodeFactory（定义层）

`@node` 始终产生 `NodeFactory`。用户定义节点逻辑，但不直接得到可执行的 `Node`：

```python
@node
def home() -> bool:
    return game.screen.exists("home")
```

`home` 的类型是 `NodeFactory`。每次调用 `home()` 创建一个独立的 `Node` 实例。

职责：

- 保存节点函数引用与元数据（id、label）
- 每次调用创建全新的 `Node` 实例
- 验证函数签名是否正确（无参，返回 `bool`）

### 1.3 Node（实例层）

`Node` 是 Runner 调度的基本可执行单元。一个 `Node` 实例包含：

- **callback**：无参 `() -> bool` 函数
- **next**：有序后继列表（构图期写入，运行前冻结）
- **元数据**：id、label、kind

**核心约束：一个 `Node` 实例只有一个 `next` 列表。**

```python
check = my_factory()
home >> check       # 合法：check 首次作为候选
task >> check       # 合法：同一 Pipeline 内可共享 check 作为候选
```

约束细节：

- 一个 `Node` 作为 `>>` 源（左侧）只能连接一次；再次使用 `>>` 抛出 `NodeAlreadyWiredError`，需要覆盖时改用 `.next = [...]`（见 §5.5）
- 一个 `Node` 作为候选（右侧）可被多个父节点引用；但同一节点不能同时属于两个 Pipeline（所有权隔离，见 §5.2）
- 每次调用工厂都得到独立副本；需要复用时，多次调用工厂即可

### 1.4 Fragment（构图层）

`Fragment` 是只暴露 entry/exit 的构图片段：

```python
def LoginFlow() -> Fragment:
    page = ocr("登录")
    submit = submit_login()
    done = ocr("首页")

    page >> submit >> done
    return Fragment(entry=page, exit=done)
```

**Fragment 不是运行时类型。** 在构图期通过 `>>` 连接时，Fragment 展开为其内部的所有 Node，直接接入外层图的 `next` 关系中。

```python
start >> LoginFlow() >> finish
# 等价于：
start >> page >> submit >> done >> finish
```

设计理由：

- **零运行时开销**：Fragment 只在构图期存在，执行时只有纯 Node 图
- **类型安全**：Fragment 只暴露 entry/exit，内部节点对外不可见
- **简化 Runner**：Runner 只需处理 Node，无需处理复合类型
- **jump-back 消除**：没有隐式的子 Pipeline jump-back；所有后继显式声明

### 1.5 Pipeline（运行层）

`Pipeline` 不再伪装成 Node。它没有 `.next`，没有 `>>`，只负责：

1. **结构校验**：冻结前检查 entry/exit 合法性、可达性
2. **图冻结**：锁定所有 Node 的 next，防止运行时修改
3. **运行**：将冻结后的图交由内部执行循环（Runner）推进

```python
pipeline = Pipeline(entry=home, exit=done)
# pipeline.next          ← 不存在
# pipeline >> something  ← 不存在
pipeline.run(timeout=30.0)
```

### 1.6 Runner（执行循环）

Runner 不是独立类，而是 Pipeline 内部执行循环的统称，由 `Pipeline._run` 实现，
负责候选扫描、轮询、超时与取消。详情见 §4。

---

## 2. 调度语义 {#scheduling}

### 2.1 核心循环

Runner 的核心循环固定为：

```text
current = entry（先调用 entry；未命中则本次 run 未启动成功）

循环：
    在 current.next 中按顺序检查候选 n1、n2、n3、...

    1. 调用候选
    2. 返回 True：
       - 该候选已命中，且自身 action 已执行
       - 该候选成为新的 current
       - 停止本轮扫描
       - 开始检查新 current 的 next
    3. 返回 False：
       - 此候选不命中
       - 立即继续检查同级下一个候选
    4. 全部不命中：
       - 等待下一轮
       - 从 current.next 的第一个候选重新检查
       - 超时、取消由 Runner 统一处理
    
    本轮迭代结束（无论是否有候选命中），等待 interval 确保最小轮次间隔
```

### 2.2 关键约束

- 节点函数内部**不提供** `goto()`、`jump()` 或返回目标节点
- 控制流本身声明在图上的 `next` 关系中
- 节点是否被选择由自身的 recognition / predicate 决定
- 选中后执行 action，并自然成为新的 current
- `next` 顺序就是检查优先级
- **第一个命中即选中并停止本轮扫描**
- 候选返回 `False` 时**立即**检查下一个

### 2.3 与传统 FSM 的区别

| 传统 FSM | Pipeline |
|----------|----------|
| 节点返回 DONE / RETRY / JUMP | 节点只返回 `bool` |
| 节点内决定跳到哪里 | 图上的 `next` 决定可去哪里 |
| 边承载条件 | 条件属于目标节点自身 |
| 任意 JUMP | 禁止任意跳转 |
| MISS 阻塞当前候选 | `False` 立即试下一个 |
| 多个 DONE 都可能执行 | 第一个 True 即停止扫描 |

### 2.4 根 Pipeline 的启动与完成

```text
run() 开始：
    调用 entry
    entry 返回 False → 本次未成功启动
    entry 返回 True  → current = entry，进入主循环

命中 exit：
    整个任务正常结束

全部候选持续不命中：
    Runner 轮询等待，直到命中、超时或取消
```

---

## 3. Fragment 的设计理由 {#fragment-design}

为什么不把 Fragment 做成运行时类型（拒绝 `Flow` / `PipelineCall` 等运行时复合类型），见 [为什么？（被拒绝的设计） §4](why.md#no-runtime-fragment)。

### 3.1 复用组合

Fragment 通过普通 Python 函数组合：

```python
def ClosePopup(spec: PopupSpec) -> Fragment:
    detect = ocr(spec.text, actions=[click_first])
    confirm = ocr("确认", actions=[click_first])
    detect >> confirm
    return Fragment(entry=detect, exit=confirm)

# 复用
home >> ClosePopup(config.popup_a)
battle >> ClosePopup(config.popup_b)
```

每次调用 `ClosePopup()` 返回独立 Fragment，包含全新 Node 实例。

---

## 4. Runner 执行循环 {#runner}

> 本节中的 Runner 指 `Pipeline._run` 内部执行循环，并非独立类。

### 4.1 简化模型

Runner 只处理 `Node`，执行循环如下：

```text
current = entry（先调用 entry；未命中则本次 run 未启动成功）

主循环：
    current 是 exit，或（exit 为空且 current 无后继）→ 返回成功

    for candidate in current.next（按优先级顺序）:
        若 candidate 命中 → current = candidate; 继续下一轮
        未命中 → 立即尝试下一个候选

    全部候选未命中：
        current 无后继（非严格模式的自然结束）→ 返回成功
        单轮模式（timeout=0）→ 返回失败
        已到达 timeout 截止 → 返回失败
        cancel() 为真 → 返回失败
        否则等待 interval 后重扫

    每轮迭代（命中或全未命中）结束、且未提前返回时，等待 interval 确保最小轮次间隔
```

### 4.2 轮询 / 超时 / 取消

| 参数 | 语义 |
|------|------|
| `timeout=0` | 单轮扫描，不阻塞 |
| `timeout=None` | 无限等待直到完成或取消 |
| `timeout>0` | 在截止前轮询；截止时间从 `run()` 开始计算 |
| `interval` | 最小轮次间隔秒数；每轮迭代结束后至少等待此时间再开始下一轮 |
| `cancel` | 外部取消回调 |

`timeout` 与 `cancel` 只在「全部候选未命中」的轮次中评估；只要候选持续命中、
流程持续推进，超时不会生效。

`run_node(node)` 提供受控的单步节点执行（与 Runner 调用节点的语义一致），返回节点是否命中。

### 4.3 错误处理

| 场景 | 异常 |
|------|------|
| 节点返回非 `bool` | `TypeError` |
| `>>` 的非法 next 候选 | `TypeError`（仅 `>>` 路径校验类型） |
| 图已冻结仍修改 | `PipelineGraphFrozenError` |
| 图结构不合法 | `PipelineGraphError`（`ValueError` 子类） |
| `@node` 签名不合法 | 定义期 `TypeError` |

`.next = [...]` 是底层 setter，**不**校验候选类型；写入非法候选的错误
会在运行期扫描 `next` 时才暴露。

---

## 5. >> 运算符的约束规则 {#next-operator}

### 5.1 等价关系

`>>` 只是 `.next` 的结构化写法，**不引入新的调度语义**：

```python
source >> target
# 等价于 source.next = [target]

source >> [target_a, target_b]
# 等价于 source.next = [target_a, target_b]
```

Runner 最终看到的只有 `Node.next`。

等价关系仅指调度语义。`>>` 额外强制执行类型、重复项与 once-only 检查
（见 §5.2 / §5.5）；`.next = [...]` 是底层 setter，不做这些校验，
写入非法候选的错误会在运行期暴露。

### 5.2 硬约束

`>>` 在右侧元素上强制执行以下检查：

**所有权隔离**：不同图之间的 Node 不允许交叉连接。

```python
pipeline_a = Pipeline(entry=..., exit=...)
pipeline_b = Pipeline(entry=..., exit=...)
# 不可将 pipeline_a 的节点连接到 pipeline_b
```

### 5.3 嵌套与链式

```python
node1 >> [
    node2 >> node5 >> [
        node6,
        node7 >> node1,
    ],
    node3,
    node4,
]
```

连续 `>>` 表示连续连接：

```python
prepare >> open_task >> done
```

### 5.4 表达式结果

```text
head  = 整段表达式的入口
tails = 下一次链式连接要修改的末端
```

它们只是构图期间的临时信息，不进入 Runner。

### 5.5 覆盖语义

连接会立即修改源元素的 `next`。`Node` 作为 `>>` 源只允许连接一次（再次使用抛出 `NodeAlreadyWiredError`）；需要覆盖时通过 `.next` setter 完成：

```python
home >> [close_popup, start_task]
home.next = [recover]
assert home.next == [recover]
```

`Fragment` 作为 `>>` 源（`fragment >> target`）属于构图期语法糖，直接改写其
`exit` 的 `next`，不执行 once-only 检查；重复使用会静默覆盖上一次连接，
因此同一个 Fragment 实例不应作为多个目标的前驱复用。

---

## 6. Pipeline 的设计理由 {#pipeline-design}

Pipeline 不再伪装成 Node，而是作为图容器（为什么，见 [为什么？（被拒绝的设计） §10](why.md#pipeline-not-node)）。

### 6.1 Pipeline 的职责

```text
校验：R1 entry 已设置（所有模式）
      R2 exit 是叶子（exit.next == []；提供 exit 时所有模式执行）
      R3 exit 从 entry 可达（仅 strict 模式）
      R4 每个可达 Node 叶子必须是 exit（仅 strict 模式）

冻结：锁定所有 Node.next
运行：由内部执行循环（Runner）执行冻结后的图
```

`Pipeline` 接受 `strict: bool` 参数（默认 `True`）：

- **`strict=True`**（默认）：必须提供 `exit`，R1–R4 全部校验
- **`strict=False`**：`exit` 可为 `None`，R3 / R4 不校验；运行时节点无后继即自然结束；适用于无明确终点的流程

---

## 7. 图冻结 {#freezing}

### 7.1 冻结时机

`Pipeline(entry=..., exit=...)` 构造成功后，内部节点图立即冻结。

```text
装配中：
    可以设置 entry / exit / next
    可以使用 >>
    可以覆盖已有连接

装配完成后：
    内部 Node 的 next、entry、exit 冻结
    任何修改尝试抛出 PipelineGraphFrozenError
```

### 7.2 读取保护

读取 `next` 返回副本，不能通过 `home.next.append(...)` 绕过冻结。

### 7.3 实例隔离

每次调用工厂都得到独立节点和 `next`，不会共享冻结状态：

```python
p1 = Battle(game, config_a)
p2 = Battle(game, config_b)  # 完全独立的图
```

---

## 8. 状态 {#state}

### 8.1 无通用 ctx

Pipeline 不引入通用 `PipelineContext`（为什么，见 [为什么？（被拒绝的设计） §3](why.md#no-ctx)）。状态放在闭包捕获的局部对象上：

```python
@dataclass
class BattleState:
    enemy: Enemy | None = None
    rounds: int = 0

def Battle(game: Game, config: BattleConfig) -> Pipeline:
    state = BattleState()

    @node
    def detect_enemy() -> bool:
        enemy = game.ocr.read_enemy()
        if enemy is None:
            return False
        state.enemy = enemy
        return True

    @node
    def choose_strategy() -> bool:
        ...

    detect_enemy = detect_enemy()
    choose_strategy = choose_strategy()
    detect_enemy >> choose_strategy
    return Pipeline(entry=detect_enemy, exit=choose_strategy)
```

### 8.2 生命周期约束

```text
Pipeline 实例 = 一次任务实例
同一实例不应被并发运行
需要独立任务时，创建新的 Pipeline 实例
```

---

## 9. 一句话原则 {#principles}

```text
用 @node + 工厂调用创建可复用的节点定义
用 bool 节点表达"是否命中并接管"
用有序 next 表达"能去哪里、先试谁"
用第一个 True 停止扫描，False 立即试下一个
用全部 False + Runner 轮询表达等待
用 Fragment 表达可复用子流程（构图期展开）
用 Pipeline(entry, exit) 做图容器
用 >> 作为 next 的结构化写法
用 actions= 配置命中后动作
用普通 Python 做配置、复用与组合
让 Python 始终作为唯一语义真源
不要把框架写成第二套 DSL
```
