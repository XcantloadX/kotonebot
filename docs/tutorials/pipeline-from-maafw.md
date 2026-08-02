# Pipeline：从 MaaFramework 到 Kbot

> 🤖**本文由 AI 编写，已经过人工检查。**

> **面向读者**：已经熟悉 MaaFramework（下文简称 **Maa**）的 Pipeline JSON 协议，想用 kotonebot pipeline（下文简称 **Kbot**）编写或迁移自动化流程的开发者。
>
> **本文目标**：把 Maa 的心智模型逐项映射到 Kbot Pipeline，并用渐进式例子从入门讲到高级。你不需要先读设计文档，但遇到疑问时可以回查：
>
> - [Pipeline 概念、定义与术语](../architecture/pipeline/concepts.md)
> - [Pipeline 架构设计](../architecture/pipeline/design.md)
> - [内置节点体系](../architecture/pipeline/builtins.md)
> - [被拒绝的设计与理由](../architecture/pipeline/why.md)

---

## 0. 先建立心智模型

### 0.1 最核心的一句话

> **Maa 的节点是「JSON 对象 + 框架解析」，Kbot 的节点是「Python 函数 + 你写的代码」。**

Maa 把识别、动作、时序、状态、错误全部做成**声明式字段**（`recognition`、`action`、`pre_delay`、`anchor`、`on_error`……），框架负责解释这些字段。
Kbot 把这些**全部交还给 Python**：识别是你调用的函数，动作是你写的代码，时序是你调用的 `sleep`，状态是你的变量。框架只保留最小的调度内核。

因此对 Maa 用户而言，Kbot Pipeline 只有两个概念必须先接受，其余都是常识：

1. **节点只返回 `bool`**，没有 `DONE / RETRY / JUMP`。
2. **控制流只有 `next`**，没有隐式的 jump-back。

这两个选择的原因和代价，见 [被拒绝的设计与理由](../architecture/pipeline/why.md)。

### 0.2 概念对照表

| Maa                                                     | Kbot                                          | 说明                                                          |
| ------------------------------------------------------- | --------------------------------------------- | ------------------------------------------------------------- |
| 节点（JSON Object）                                     | `@node` 装饰的函数工厂 + `factory()` 调用 | 工厂返回`Node` 实例                                         |
| `recognition` + `action` 字段                       | 节点回调（`() -> bool`）                    | Kbot 并不关心你的回调里做了什么识别或动作，这完全由你自己决定 |
| 返回成功进入`next`                                    | 回调返回`True`                              | 二者相同，命中并接管流程                                      |
| 识别失败重试下一轮                                      | 回调返回`False`                             | 二者相同，立即尝试同级下一个候选                              |
| `next`（有序候选）                                    | `>>` / `.next`                           | 二者相同，顺序即检查优先级，第一个命中即停                    |
| 上一个节点的`timeout`                                 | `pipeline.run(timeout=...)`                 | 轮询等待直到命中                                              |
| `rate_limit`                                          | `run(interval=...)`                         | 最小轮次间隔                                                  |
| `on_error`（超时/动作失败）                           | `run()` 返回 `False` 或 Python 异常       | Kbot 没有声明式 on_error                                      |
| `[JumpBack]` / `is_sub` / `interrupt`             | **显式回边**（`a >> b >> a`）         | Kbot 没有 JumpBack，所有循环都是图上的显式边                  |
| `anchor`                                              | 闭包变量保存`Rect`                          | 上次命中的位置存在局部变量里                                  |
| `hit_count` / `enabled` / `max_hit` / `inverse` | 闭包状态 + Python 条件构图                    | 动态控制写在你自己的代码里                                    |
| `Context`（全局状态）                                 | 闭包捕获的 dataclass                          | Kbot 没有上下文的概念，你可以用任意方式实现                   |
| `Custom` 识别 / 动作                                  | `@node` 任意 Python 函数                    | 默认写法，不是特例                                            |
| 子任务`run_task`                                      | 节点内调用`pipeline.try_run(...)`           | 嵌套子流程                                                    |
| 节点全局命名空间                                        | Python 函数 +`Fragment`                     | 复用通过函数组合，每次调用独立实例                            |
| `DirectHit`                                           | `dummy` / 恒 `True` 回调                  | 不做识别，直接命中                                            |
| ROI /`box` / `target`                               | 识别结果的`.rect` 字段                      | 识别即返回坐标对象                                            |
| PipelineChecker（加载期校验）                           | `Pipeline(...)` 构造期强校验 + 图冻结       | 详见 §3.2                                                    |

### 0.3 同一个流程的两种写法

先看全貌。这是一个「日常任务」流程：进入日常页，若已在则循环点「领取」，点「关闭」结束；否则点「日常」进入后再重试。

**Maa（JSON）：**

```JSON
{
    "DailyStart": {
        "next": [
            "DailyIsAtDailyTasks",
            "DailyEnterTasks"
        ]
    },
    "DailyEnterTasks": {
        "recognition": "OCR",
        "expected": ["日常"],
        "action": "Click"
    },
    "DailyIsAtDailyTasks": {
        "recognition": "OCR",
        "expected": ["日常任务"],
        "action": "DoNothing",
        "next": [
            "DailyClickClaim",
            "DailyClickClose"
        ]
    },
    "DailyClickClaim": {
        "recognition": "OCR",
        "expected": ["领取"],
        "action": "Click",
        "next": ["DailyIsAtDailyTasks"]   // 显式回边，代替 [JumpBack]
    },
    "DailyClickClose": {
        "recognition": "OCR",
        "expected": ["关闭"],
        "action": "Click"
    }
}
```

**Kbot（Python）：**

```python
from kotonebot.pipeline import Pipeline, dummy, ocr, click_first

def Daily() -> Pipeline:
    start = dummy()                                   # 恒命中入口 ≈ DirectHit
    is_at_daily_tasks = ocr("日常任务")                # 识别不动作 ≈ DoNothing
    click_claim = ocr("领取", actions=[click_first])  # 识别 + 点击 ≈ OCR + Click
    click_close = ocr("关闭", actions=[click_first])
    enter_tasks = ocr("日常", actions=[click_first])

    start >> [
        is_at_daily_tasks >> [
            click_claim >> is_at_daily_tasks,          # 显式回边：循环点「领取」
            click_close,
        ],
        enter_tasks >> start,                          # 显式回边：进不去就重试
    ]
    return Pipeline(entry=start, exit=click_close)

# 运行
Daily().run(timeout=120)
```

对照要点：

- `>>` 列表 = Maa 的 `next` 列表，顺序即优先级。
- 命中后点击用 `actions=[click_first]`，不是 `.act()`，也不是 `>>`。
- 循环全部是**显式回边**，Maa 的 `[JumpBack]` 语义用 `click_claim >> is_at_daily_tasks` 表达。
- `Pipeline(entry=..., exit=...)` 对应 Maa 的「指定 entry 的 post_task」；`exit` 是任务完成点。

下面从最小例子开始逐步展开。

---

## 1. 入门

### 1.1 最小 Pipeline

Maa 最小任务：一个 `DoNothing` 节点，`next` 为空即结束。

```json
{
    "Start": {
        "action": "DoNothing",
        "next": []
    }
}
```

Kbot 等价写法：

```python
from kotonebot.pipeline import Pipeline, dummy

def Main() -> Pipeline:
    start = dummy()  # dummy：恒命中的占位节点
    return Pipeline(entry=start, exit=start)

# 运行
Main().run()
```

上面把流程包进 `Main()` 工厂函数，是为了命名清晰、便于复用。**函数包装不是必须的**——直接连边、构造 `Pipeline`、`.run()`（见 §1.2 的写法）也是一样。

几个必须知道的事实：

- `@node` **总是返回 `NodeFactory`**，必须调用工厂才得到 `Node`。`dummy()` 内部也是这么做的。
- `Pipeline` 是**图容器**，不是节点：没有 `.next`，没有 `>>`，只负责校验、冻结、运行。
- `exit` 必须是**叶子**（`next` 为空），并且从 `entry` **可达**。不满足在构造期直接抛 `PipelineGraphError`。

> **命名约定**：返回 `Pipeline` / `Fragment` 的工厂函数（即「定义流程」的函数）使用**大驼峰命名**，和类名一致（如 `Daily`、`DoShopping`、`ClosePopup`）；而 `@node` 节点回调保持小写（如 `buy`、`finish`）。这样一眼就能区分「流程定义」与「节点」。

### 1.2 节点 = 识别 + 动作

Maa 用两个字段描述一个节点：`recognition` 决定「认不认得出」，`action` 决定「认出来后做什么」。

```json
{
    "EnterStore": {
        "recognition": "OCR",
        "expected": ["商店"],
        "action": "Click"
    }
}
```

Kbot 把这两件事合并在**一个回调**里，回调返回 `bool`：

```python
from kotonebot.pipeline import Pipeline, ocr, click_first

enter = ocr("商店", actions=[click_first])
pipeline = Pipeline(entry=enter, exit=enter)
pipeline.run()
```

`ocr("商店", actions=[click_first])` 是一个**内置节点工厂**，等价于你手写：

```python
from kotonebot import device, ocr as _ocr
from kotonebot.pipeline import Pipeline, node

@node
def enter() -> bool:
    result = _ocr.find("商店")      # 识别
    if result is None:
        return False                # 未命中
    device.click(result.rect)       # 动作
    return True                     # 命中并接管

enter_node = enter()                # @node 返回工厂，必须调用
pipeline = Pipeline(entry=enter_node, exit=enter_node)
```

**`bool` 的语义**（这是 Kbot 唯一的节点协议）：

| 返回值    | 含义                                             |
| --------- | ------------------------------------------------ |
| `True`  | 本候选命中，动作（若有）已执行，接管流程         |
| `False` | 本候选不适用，调度器**立即**尝试同级下一个 |

### 1.3 `next`：候选与优先级

Maa：

```json
{
    "Home": {
        "recognition": "OCR",
        "expected": ["首页"],
        "next": ["OpenShop", "OpenMall"]
    }
}
```

Kbot：

```python
home = ocr("首页")
open_shop = ocr("商店", actions=[click_first])
open_mall = ocr("商场", actions=[click_first])

home >> [open_shop, open_mall]
```

调度语义与 Maa 完全一致：

- 依次检查 `home.next` 中的候选：先试 `open_shop`，再试 `open_mall`。
- **第一个返回 `True` 的候选胜出**，成为新的当前节点，本轮扫描停止。
- 返回 `False` 立即试下一个；**全部未命中**则进入等待（见 §1.4）。

Kbot 的 Node 也支持类似 Maa 的列表 `next` 写法：

```python
home = ocr("首页")
open_shop = ocr("商店", actions=[click_first])
open_mall = ocr("商场", actions=[click_first])
home.next = [open_shop, open_mall]
```

`.next` 是 `>>` 的底层实现。**正常情况下，你应该使用 `>>` 而不是 `.next`**，因为 `>>` 会额外多做合法检查（例如禁止候选重复等）。

### 1.4 运行、轮询与超时

Maa 中「识别超时」由**上一个节点**的 `timeout` 决定（`next` 列表识别超过该时长进 `on_error`），轮询节流由 `rate_limit` 控制。

Kbot 没有 per-node 的 timeout，统一由 `Pipeline.run` 管理：

```python
pipeline.run(timeout=0)      # 单轮扫描，不阻塞；本轮全未命中立即返回 False
pipeline.run(timeout=None)   # 无限等待，直到命中或 cancel
pipeline.run(timeout=30.0)   # 30 秒内轮询；超时返回 False
pipeline.run(interval=0.5)   # 每轮迭代结束后至少等待 0.5s（≈ rate_limit）
pipeline.run(cancel=lambda: should_we_stop_now())  # 取消回调
```

超时 / 取消只在**全部候选未命中**的轮次中评估——只要流程持续推进，超时不会生效。

`timeout` 与 `interval` 必须非负，否则抛 `ValueError`。

### 1.5 内置节点体系（builtins）

为避免简单逻辑也要写函数定义的冗余，Kbot 自带一组封装好的**内置节点工厂**（builtins）。它们与手写 `@node` 的语义完全一致：命中返回 `True` 并接管流程，未命中返回 `False` 让位。

builtins 由三类组成：**识别节点工厂**（返回 `Node`）、**命中后动作**（传给 `actions=` 的回调）与构图期辅助工具。

| 节点工厂                | 识别方式                | 对应 Maa recognition |
| ----------------------- | ----------------------- | -------------------- |
| `ocr(text)`           | OCR 文本识别            | `OCR`              |
| `template_match(img)` | 模板匹配                | `TemplateMatch`    |
| `prefab(Cls)`         | Prefab 查询（见 §3.1） | 自定义               |
| `dummy()`             | 恒命中占位              | `DirectHit`        |

#### 1.5.1 `ocr`：文本识别

`ocr(matches, *, roi=None, actions=None)`。`matches` 可以是**单个字符串**或**字符串列表**，二者命中语义不同：

- **单个字符串**：精确查找该文本，找到即命中；`AfterMatch.first` 是第一个命中结果。
- **字符串列表**：**任一**文本出现即命中（≈ Maa 的多个 `expected`）；此时 `AfterMatch.matches` 里是所有命中的结果，而不是只保留第一个。

```python
enter_store = ocr("商店", actions=[click_first])           # 单个文本
any_badge = ocr(["礼包", "红点"], actions=[click_first])   # 任一出现即命中
title = ocr("标题", roi=Rect(0, 0, 100, 50))                # 限定识别区域
```

`roi=Rect(x, y, w, h)` 限定识别区域，对应 Maa 的 `roi` 字段（§4 速查表有对应项）。限定区域既能提升识别速度，也能避免把页面别处出现的同名文本误认成目标。

#### 1.5.2 `template_match`：模板匹配

`template_match(template, *, roi=None, actions=None)`。`template` 可以传：

- **图像路径字符串**，如 `"battle_button.png"`；
- **`Image` / `ImageSlice` 对象**；`ImageSlice` 额外支持 `slice_rect`，只取整张图里的某一块作为模板；
- **`MatLike`**（cv2 的 `Mat` / `np.ndarray`）。

传入**模板列表**时，会按序逐个尝试，返回**第一个匹配到**的模板（≈ Maa 的多模板）。内置工厂使用默认匹配阈值（0.8）；需要细粒度控制阈值、区域、是否匹配颜色等参数时，用 §3.1 的 `TemplateMatchPrefab`。

```python
from kotonebot.pipeline import template_match, click_first

battle_btn = template_match("battle_button.png", actions=[click_first])
```

对应 Maa：

```json
{
    "EnterBattle": {
        "recognition": "TemplateMatch",
        "template": "battle_button.png",
        "action": "Click"
    }
}
```

#### 1.5.3 `prefab`：Prefab 查询

`prefab(prefab_cls, actions=None)`。`prefab_cls` 可以是一个 **Prefab 类**（§3.1 定义的 `OcrPrefab` / `TemplateMatchPrefab` 子类）、一个 **`BoundPrefab`**（通过 `Cls.q(...)` 绑定查询参数得到），或**多个的列表**（按序尝试，返回首个命中）：

```python
enter = prefab(BattleButton, actions=[click_first])          # Prefab 类
enter_special = prefab(BattleButton.q(threshold=0.9))        # 绑定查询参数
enter_any = prefab(AnyButton, actions=[click_first])         # 组合识别（AnyOf）
```

Prefab 是「识别算法 + 参数 + 结果类型」三位一体的封装，能覆盖内置工厂表达不了的自定义识别（Yolo、颜色检测等），详见 §3.1。

#### 1.5.4 `dummy`：恒命中占位

`dummy(actions=None)` 不做任何识别，恒返回 `True`。它有两个典型用途：

- 作为流程**入口**：`start = dummy()` 让流程无条件启动（§0.3 的 `Daily`、§1.1 的 `Main` 都是这么用的）；
- 作为需要**无条件执行某段动作**的节点，例如 `dummy(actions=[sleep(0.5)])`。

#### 1.5.5 命中后动作

所有节点工厂都接受 `actions=` 参数，传入命中后要执行的回调。内置动作：

| 动作                                   | 说明                     |
| -------------------------------------- | ------------------------ |
| `click_first`                        | 点击第一个匹配结果的中心 |
| `sleep(seconds)`                     | 命中后睡眠指定秒数       |
| 自定义`(ctx: AfterMatch[T]) -> None` | 任意函数                 |

`actions` 是**节点内副作用**，不是控制流；`AfterMatch`、自定义 action 与 `sleep` 的完整机制见 §1.6。

#### 1.5.6 辅助：`resolve_labels()`

`resolve_labels()` 遍历**调用者局部作用域**，把所有 `Node` 变量的 `label` 自动设为**变量名**，让 devtools 里的 trace / 断点显示可读名称（与 §3.3 的 `id` / `label` 元数据配套）。在工厂函数里连完图、构造 `Pipeline` 前调用一次即可：

```python
def Daily() -> Pipeline:
    start = dummy()
    claim = ocr("领取", actions=[click_first])
    done = ocr("已完成")
    start >> [claim, done]
    resolve_labels()           # 自动把 start / claim / done 设为 label
    return Pipeline(entry=start, exit=done)
```

相比逐个手写 `@node(id=..., label=...)`，`resolve_labels()` 省去样板，代价是依赖变量名；二者可混用，显式传入的 `id` / `label` 优先。

#### 1.5.7 命中后动作（`actions=`）

Maa 的动作是字段（`Click` / `Swipe` / `LongPress` / `InputText`……）。在内置节点体系内，Kbot 统一为 `actions=` 参数：识别命中后**按序执行**一组回调，每个回调拿到匹配结果包装。

```python
from kotonebot.pipeline import ocr, click_first, sleep as after_sleep

ocr("领取", actions=[click_first, after_sleep(0.5)])
```

`AfterMatch[T]` 是匹配结果包装：

| 属性         | 含义                           |
| ------------ | ------------------------------ |
| `.matches` | 所有命中结果列表               |
| `.first`   | 第一个命中结果（无则`None`） |
| `.hit`     | 是否有至少一个命中             |

自定义 action 就是一个函数：

```python
from kotonebot.pipeline import AfterMatch
from kotonebot.backend.ocr import OcrResult

def click_all(ctx: AfterMatch[OcrResult]) -> None:
    """点击所有命中项。"""
    for m in ctx.matches:
        device.click(m.rect)

ocr(["礼包A", "礼包B"], actions=[click_all])
```

要点：**actions 不是控制流**。控制流只有 `next` / `>>`。`actions=` 只负责节点内部的副作用。

---

## 2. 进阶

真实流程绕不开四件事：自定义逻辑、状态、循环、复用。这一节逐一讲。

### 2.1 自定义识别 / 动作（对应 Maa 的 `Custom`）

Maa 的 `Custom` 需要注册回调并传参数。Kbot 里自定义识别/动作就是**默认写法**——任何无参返回 `bool` 的函数都可以是节点：

```python
from dataclasses import dataclass
from kotonebot import device, ocr as _ocr, image as _image
from kotonebot.pipeline import Pipeline, node

@node
def boss_appears() -> bool:
    """只识别，不动作。"""
    return _ocr.find("BOSS") is not None

@node
def use_skill() -> bool:
    """识别到才动作。"""
    btn = _image.find("skill.png")
    if btn is None:
        return False
    device.click(btn.rect)
    return True

def current_hp() -> float:
    """（示意）你自己的逻辑，从游戏数据里读当前血量。"""
    return game_state.hp_ratio

@node
def wait_for_ready() -> bool:
    """纯逻辑节点：Maa 里很难表达，Python 里随手写。"""
    return current_hp() > 0.3
```

规则：回调**必须无参调用**，返回类型标注（若存在）必须是 `bool`，否则在定义期抛 `TypeError`。运行时若返回非 `bool` 会 fail fast。

> **命名提醒**：`kotonebot.pipeline.ocr` 是节点工厂；`kotonebot.ocr`（顶层导出）是后端 OCR 引擎实现。示例里用 `_ocr` 区分后者。

### 2.2 状态：用闭包代替 Context

Maa 的 `hit_count`、`anchor`、`enabled` 都是 `Context` 里由框架维护的全局状态。Kbot **没有通用 ctx**（为什么见 [设计文档 §5](../architecture/pipeline/why.md#no-ctx)），状态放在闭包捕获的局部对象上即可。

**计数（≈ Maa 的 `hit_count` + `max_hit`）：**

```python
from dataclasses import dataclass
from kotonebot import device, ocr as _ocr
from kotonebot.pipeline import Pipeline, node, dummy
from kotonebot.primitives import Rect

@dataclass
class ShopState:
    purchase_count: int = 0
    coin_pos: Rect | None = None

def DoShopping(max_purchases: int = 10) -> Pipeline:
    state = ShopState()

    @node
    def buy() -> bool:
        if state.purchase_count >= max_purchases:
            return False # 达到上限 → 让位给下一个候选
        r = _ocr.find("购买")
        if r is None:
            return False
        device.click(r.rect)
        state.purchase_count += 1
        return True

    @node
    def finish() -> bool:
        return _ocr.find("离开") is not None

    start = dummy()
    buy_node = buy()
    finish_node = finish()
    start >> buy_node
    buy_node >> [buy_node, finish_node] # 自环：继续买，或离开
    return Pipeline(entry=start, exit=finish_node)
```

如果你不想为此专门声明一个 dataclass，也可以用**局部变量 + `nonlocal`**：

```python
def DoShopping(max_purchases: int = 10) -> Pipeline:
    count = 0 # 普通局部变量

    @node
    def buy() -> bool:
        nonlocal count # 改写外层局部变量
        if count >= max_purchases:
            return False
		# ...

    @node
    def finish() -> bool:
        return _ocr.find("离开") is not None

	# ...
```

或者你也可以用 dict 储存状态数据，避免丑陋的 `nonlocal`。

重点是你可以用任何你喜欢的方式，只要这种方式是合法的 Python 代码即可！

**锚点（≈ Maa 的 `anchor` 字段）：**

Maa 用 `anchor` 把某个节点的识别框存下来，供后续节点的 `target` 引用。Kbot 直接存 `Rect`：

```python
def FooPipeline() -> Pipeline:
    state = ShopState()          # 复用上面的状态类，state 在工厂内

    @node
    def locate_coins() -> bool:
        r = _ocr.find("金币")
        if r is None:
            return False
        state.coin_pos = r.rect                  # ≈ set anchor "CoinPos"
        return True

    @node
    def click_coins() -> bool:
        if state.coin_pos is None:
            return False
        device.click(state.coin_pos)             # ≈ target "[Anchor]CoinPos"
        return True

    locate = locate_coins()
    click = click_coins()
    locate >> click
    return Pipeline(entry=locate, exit=click)
```

**为什么这样可以？** 节点函数与 `state` 在同一作用域，读写直接、类型完整，没有任何间接层——这就是 Kbot「Python 是唯一语义真源」的体现。

### 2.3 循环：显式回边代替 `[JumpBack]`

Maa 的 `[JumpBack]` 是栈式语义：某节点 `next` 为空时「弹栈返回」。Kbot 认为这种**隐式控制流**不可分析，所有循环必须画在图上。

「反复点领取，直到出现已完成」：

**Maa（示意）：**

```json
{
    "Enter": {
        "next": [{ "name": "ClickClaim", "jump_back": true }, "CheckDone"]
    },
    "ClickClaim": {
        "recognition": "OCR",
        "expected": ["领取"],
        "action": "Click"
    },
    "CheckDone": {
        "recognition": "OCR",
        "expected": ["已完成"],
        "action": "DoNothing"
    }
}
```

**Kbot：**

```python
def Daily() -> Pipeline:
    enter = dummy()
    click_claim = ocr("领取", actions=[click_first])
    check_done = ocr("已完成")

    enter >> [
      click_claim >> enter,   # 显式回边，等价于 [JumpBack]
      check_done
    ]
    return Pipeline(entry=enter, exit=check_done)
```

行为完全一致：进入后优先试 `click_claim`，命中则点「领取」并跳回 `enter` 继续循环；点完了 `check_done` 命中则结束。

> 注意：`exit` 必须从 `entry` 可达。上面 `enter >> [click_claim, check_done]` 里的 `check_done` 就是为满足可达性而显式画上的边。

### 2.4 复用组合：Fragment 代替子任务

Maa 里复用一个流程片段 = 把一组节点放进全局命名空间，别的节点 `next` 直接引用。缺点是没有隔离，也没有「组合子」。

Kbot 用 `Fragment`：**只暴露入口和出口的构图片段**，连接时展开为纯 `Node` 图，不进入运行时。

```python
from kotonebot.pipeline import Fragment, ocr, click_first, dummy

def ClosePopup(title: str) -> Fragment:
    """「关弹窗」子流程：识别标题 → 点确认。"""
    detect = ocr(title, actions=[click_first])
    confirm = ocr("确认", actions=[click_first])
    detect >> confirm
    return Fragment(entry=detect, exit=confirm)

def Main() -> Pipeline:
    start = dummy()
    done = dummy()
    start >> ClosePopup("公告") >> ClosePopup("活动") >> done
    return Pipeline(entry=start, exit=done)
```

`Fragment` 只是对「一组含入口和出口的节点」的封装。本质上，你也可以用一个普通函数返回 `(entry, exit)` 元组，再由调用方手动解构并连线：

```python
from kotonebot.pipeline import Node, dummy, ocr, click_first

def popup(title: str, confirm_text: str):
    """返回（入口, 出口）两个节点。"""
    detect = ocr(title, actions=[click_first])
    confirm = ocr(confirm_text, actions=[click_first])
    detect >> confirm
    return detect, confirm

# 调用方手动解构 + 连线
start = dummy()
done = dummy()
detect1, confirm1 = popup("公告", "确认")
detect2, confirm2 = popup("活动", "确认")
start >> detect1 >> confirm1 >> detect2 >> confirm2 >> done
```

这样完全可行，但每个子流程都要自己约定「返回元组 + 手动解构」的规矩。
为了方便，Kbot 专门设计了 `Fragment` 类用于简化并规范节点复用。`start >> ClosePopup("公告") >> ClosePopup("活动") >> done` 等价于把两个 Fragment 的内部节点全部串联进图：

```python
start >> detect1 >> confirm1 >> detect2 >> confirm2 >> done
```

Fragment 在 `>>` 连接时被展开为内部 Node 图，只保留 `entry` 与 `exit` 作为对外接口；运行时不存在 Fragment。

要点：

- `start >> fragment >> next` 等价于把 fragment 内部节点全部串联进图。
- **每次调用函数都创建全新实例**，互不共享冻结状态，可以放心复用。
- Fragment 只是构图期语法糖，运行时只有纯 `Node` 图。

> **【陷阱：不要复用同一个 Fragment 实例】**
>
> `frag = ClosePopup("公告")` 之后再把同一个 `frag` 作为 `>>` 源连到两处，会**静默覆盖**上一次连接（Fragment 的 `>>` 不执行 once-only 检查，直接改写 `exit` 的 `next`）：
>
> ```python
> frag = ClosePopup("公告")
> start >> frag >> next1     # frag 的 exit 指向 next1
> start2 >> frag >> next2    # ❌ 静默覆盖：frag 的 exit 改指向 next2
> ```
>
> 若同一批 Node 被接入两个 Pipeline，还会触发所有权校验。复用请**重新调用工厂函数**（每次 `ClosePopup(...)` 都是全新实例）。

### 2.5 条件与动态构图

Maa 用 `enabled`、`inverse`、`And` / `Or` 等字段做条件。Kbot 用 Python 条件构图，更直接。

**分支（多候选 = Or）：**

```python
home >> [open_shop, open_mall]   # 等同 Maa 的 next 列表按序试
```

**多条件同时成立（≈ Maa 的 `And`）：**

```python
@node
def confirm_dialog() -> bool:
    return _ocr.find("确认") is not None and _image.find("icon.png") is not None
```

**配置决定拓扑（≈ Maa 的 `enabled` 动态开关 / `override_pipeline`）：**

```python
def Daily(config: DailyConfig) -> Pipeline:
    home = ocr("首页")
    claim = ocr("领取", actions=[click_first])
    done = dummy()

    if config.skip_shopping:
        home >> claim >> done
    else:
        shop = ocr("商店", actions=[click_first])
        home >> [claim, shop]
        shop >> done
    return Pipeline(entry=home, exit=done)
```

**嵌套子流程（≈ Maa 的 `Context.run_task`）：** 节点内部可以同步运行另一个 `Pipeline`，用 `try_run`：

```python
close_popup_pipeline = ...   # 另一个独立的 Pipeline 实例

@node
def dismiss_popup() -> bool:
    return close_popup_pipeline.try_run(timeout=3.0)
```

`try_run` 默认单轮扫描（`timeout=0`）；这里给了 3 秒，等价于 Maa 的「等待子任务最多 3 秒」。

---

## 3. 高级

### 3.1 Prefab：把识别封装成可复用类型

§1.5 的 `template_match` 与 §1.2 的 `ocr` 是**内置节点工厂**，适合大多数场景。Maa 把「识别算法 + 参数」做成字段，Kbot 则更进一步，把「识别算法 + 参数 + 结果类型」封装成一个 **Prefab 类**，可以携带查询参数、谓词、编辑器元数据：

```python
from kotonebot.core import TemplateMatchPrefab, GameObject, OcrPrefab, AnyOf
from kotonebot.primitives import ImageSlice, Rect
from kotonebot.pipeline import prefab, click_first

class BattleButton(TemplateMatchPrefab[GameObject]):
    template = ImageSlice(file_path="battle.png", lazy_load=True,
                          slice_rect=Rect(0, 0, 10, 10))
    threshold = 0.8

class BossLabel(OcrPrefab[GameObject]):
    pattern = "BOSS"

# 组合识别：任意一个命中（≈ Maa 的 Or / 多模板）
AnyButton = AnyOf[BattleButton, BossLabel]

enter = prefab(BattleButton, actions=[click_first])
enter_any = prefab(AnyButton, actions=[click_first])
```

也可以在普通 `@node` 里直接用 Prefab 的查询能力（`find` / `find_all` / `wait` / `try_click` 等），它们与节点协议天然互补。

### 3.2 错误处理与图安全

**Maa 的 `on_error` 在 Kbot 里没有声明式等价物**，需要你主动选择：

- **未命中 / 不适用**：回调返回 `False`，调度器自动试下一个候选。
- **超时**：`pipeline.run()` 返回 `False`，自己处理：

```python
if not pipeline.run(timeout=10):
    logger.warning("每日任务 10 秒内未完成")
    recover()            # 手动兜底，等价于手动接管 on_error
```

- **真错误**：直接抛异常，fail fast。`run()` 不会吞异常：

```python
try:
    pipeline.run(timeout=60)
except UserFriendlyError as e:
    logger.error(f"任务失败：{e.message}")
```

**构图期强校验**（对应 Maa 的 PipelineChecker）：

| 校验                         | 触发条件                                                                  |
| ---------------------------- | ------------------------------------------------------------------------- |
| `PipelineGraphError`       | entry 不是`Node`；exit 不是叶子；exit 从 entry 不可达；非 exit 叶子存在 |
| `PipelineGraphFrozenError` | 图冻结（`Pipeline(...)` 成功后）仍尝试修改 `next` / `>>`            |
| `NodeAlreadyWiredError`    | 节点已经作为`>>` 源连接过，再次 `>>`                                  |
| `TypeError`                | 节点回调签名非法 / 返回非`bool`                                         |
| 所有权隔离                   | 一个`Node` 不能同时属于两个 `Pipeline`                                |

图一旦构造成功即**冻结**，运行期结构不可变——这是「图是控制流真源」的保障。

### 3.3 集成到完整 Bot

Pipeline 是「一次任务的流程描述」，实际运行由 Bot 调度。把 Pipeline 包进 `@task`，交给 `KotoneBot` 运行：

```python
from kotonebot import device
from kotonebot.backend.context import task
from kotonebot.core.bot import KotoneBot
from kotonebot.pipeline import Pipeline, dummy, ocr, click_first

def Daily() -> Pipeline:
    start = dummy()
    claim = ocr("领取", actions=[click_first])
    done = ocr("已完成")
    start >> [claim, done]
    claim >> start
    return Pipeline(entry=start, exit=done)

@task("每日任务", description="自动领取每日奖励")
def do_daily() -> None:
    Daily().run(timeout=120)

if __name__ == "__main__":
    # device_factory 返回你的设备实现（Windows / Android / macOS）
    bot = KotoneBot(device_factory=lambda: create_device())
    bot.run([do_daily.task])
```

关于调试：`@node` 支持 `id` / `label` 元数据（默认 `模块名.函数名`），用 `resolve_labels()` 可自动把节点 `label` 设为变量名，配合 devtools 做 trace 与断点。

---

## 4. 迁移速查表

| 你要做的事      | Maa                                  | Kbot                                     |
| --------------- | ------------------------------------ | ---------------------------------------- |
| 声明入口        | `tasker.post_task("Start")`        | `Pipeline(entry=start_node, exit=...)` |
| 纯识别          | `"recognition": "OCR"`             | `ocr("文本")`                          |
| 识别 + 点击     | `"action": "Click"`                | `ocr("文本", actions=[click_first])`   |
| 模板匹配        | `"recognition": "TemplateMatch"`   | `template_match("x.png")`              |
| 直接命中        | `"action": "DirectHit"`            | `dummy()` 或返回 `True` 的回调       |
| 有序候选        | `"next": ["A", "B"]`               | `a_node >> [b_node, c_node]`           |
| 识别区域        | `"roi": [x, y, w, h]`              | `ocr(..., roi=Rect(x, y, w, h))`       |
| 点击坐标来源    | `"target"` / `[Anchor]X`         | 识别结果`.rect` / 闭包里的 `Rect`    |
| 等待轮询        | 上一节点`timeout` + `rate_limit` | `run(timeout=..., interval=...)`       |
| 超时失败处理    | `on_error`                         | `run()` 返回 `False`；或捕获异常     |
| 循环            | `[JumpBack]` / `is_sub`          | 显式回边`a >> b >> a`                  |
| 子流程          | `Context.run_task`                 | 节点内`sub_pipeline.try_run(...)`      |
| 计数 / 上限     | `hit_count` / `max_hit`          | 闭包计数                                 |
| 引用上次位置    | `anchor`                           | 闭包保存`Rect`                         |
| 动态开关        | `enabled` / `override_pipeline`  | Python`if` 构图                        |
| 组合复用        | 全局命名空间引用                     | `Fragment(entry, exit)` + 函数调用     |
| 多条件识别      | `And` / `Or`                     | 自写回调；多候选；`AnyOf`              |
| 自定义识别/动作 | `Custom` + 注册回调                | 任何`() -> bool` 的 `@node`          |

---

## 5. 常见陷阱

1. **忘了调用工厂**：`@node` 返回 `NodeFactory`，`start >> start` 是错的，要 `node = start()`。
2. **重复 `>>`**：一个节点只能作为 `>>` 源连接一次；需要覆盖用 `node.next = [...]`。
3. **`exit` 不是叶子**：`exit` 必须 `next == []`，否则 `PipelineGraphError`。
4. **`exit` 不可达**：记得把通向 `exit` 的边显式画出来（见 §2.3 的注意）。
5. **图冻结后改结构**：`Pipeline(...)` 成功后任何 `>>` / `.next=` 都会抛 `PipelineGraphFrozenError`；先组图再构造 `Pipeline`。
6. **返回了非 `bool`**：运行时立刻 `TypeError`。
7. **一个节点塞进两个 Pipeline**：所有权隔离，会抛 `PipelineGraphError`；需要复用就再调用一次工厂。
8. **两个 `ocr` 分不清**：`kotonebot.pipeline.ocr` 是节点工厂，`kotonebot.ocr` 是后端 OCR；命名冲突时用 `as` 改名。
9. **习惯性想写 `on_error`**：没有。用「返回 `False` 让位」或「异常 + try/except」代替。
10. **想用 `goto` / `jump`**：被明确禁止（[为什么？](../architecture/pipeline/why.md#no-jump)）。所有跳转都是显式 `next` 边。

---

> 更完整的设计原理与取舍，见 [Pipeline 设计规范](../architecture/pipeline/index.md) 与 [为什么？（被拒绝的设计）](../architecture/pipeline/why.md)。
