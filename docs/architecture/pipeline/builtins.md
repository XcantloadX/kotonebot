# Pipeline 内置节点体系

本文档是 [Pipeline 设计规范](index.md) 的一部分，描述框架内置节点与命中后动作。
核心概念与术语见 [概念、定义与术语](concepts.md)，架构与调度语义见 [架构设计](design.md)。

使用说明见 [Pipeline 教程](../../tutorials/pipeline.md)。

---

## 1. API {#api}

| API | 说明 |
|-----|------|
| `ocr` | 文本识别工厂；返回 `Node` |
| `template_match` | 模板匹配工厂；返回 `Node` |
| `prefab` | Prefab 类工厂；返回 `Node` |
| `dummy` | 恒 `True` 占位节点 |
| `click_first` | 点击第一个匹配结果中心的 action |
| `sleep(seconds)` | 睡眠指定秒数的 action 工厂 |
| `resolve_labels()` | 自动为调用者局部作用域的 Node 变量设置 label 为其变量名 |
| `AfterMatch[T]` | 匹配结果包装，提供 `.matches` / `.first` / `.hit` |

## 2. 命中后动作 {#actions}

所有命中后动作通过 `actions=` 参数在构造时配置：

```python
ocr("领取", actions=[click_first])
ocr("关闭", actions=[lambda ctx: device.click(ctx.first)])
template_match("x.png", actions=[click_first, sleep(1.0)])
```

action 回调签名：`Callable[[AfterMatch[T]], Any]`。

控制流只有 `next` / `>>`。Actions 是节点内副作用。
