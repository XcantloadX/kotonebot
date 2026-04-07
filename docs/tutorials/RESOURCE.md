# 资源生成自定义

本教程从一个最小可用流程开始，逐步讲清楚 `resgen` 的 API、工具化入口，以及如何做下游自定义扩展。

## 1. 你会得到什么

完成本教程后，你将能够：

- 从 `PNG` 与 `PNG.json` 元信息生成资源代码。
- 理解 `Parser -> IR -> Generator` 的主流程。
- 使用 `generate_resources` 走一体化流程。
- 使用 `RendererRegistry`、`PathPolicy`、`DocstringPolicy` 定制输出。

## 2. 核心概念

`resgen` 的核心对象：

- `SchemaParser`：把输入文件解析成 `ResourceNode`。
- `ParserRegistry`：按文件类型分发给可用解析器。
- `ResourceNode`：单个资源节点（模板、框、点、prefab）。
- `ClassNode`：类树节点。
- `build_class_tree`：把扁平资源组织成类树。
- `StandardGenerator` / `EntityGenerator`：把类树渲染成 Python 代码。
- `generate_resources`：扫描、解析、生成的一站式入口。

## 3. 最小流程：手动串联 API

这个版本最适合理解 pipeline。

```python
import os

from kotonebot.devtools.resgen import (
    ParserRegistry,
    KotoneV1Parser,
    BasicSpriteParser,
    build_class_tree,
    StandardGenerator,
)

root_scan_path = "./assets/resources"
output_img_dir = "./tmp"

registry = ParserRegistry()
registry.register(KotoneV1Parser())
registry.register(BasicSpriteParser())

all_resources = []
for dirpath, _, filenames in os.walk(root_scan_path):
    for name in filenames:
        file_path = os.path.join(dirpath, name)
        context = {
            "output_img_dir": output_img_dir,
            "root_scan_path": root_scan_path,
        }
        parsed = registry.parse_file(file_path, context)
        if parsed:
            all_resources.extend(parsed)

root_nodes = build_class_tree(all_resources)

generator = StandardGenerator(production=True)
code = generator.generate(root_nodes)

with open("R.py", "w", encoding="utf-8") as f:
    f.write(code)
```

## 4. 工具化流程：使用 runner

日常项目推荐使用 `generate_resources`，它会处理扫描、上下文加载、诊断与输出写入。

```python
from kotonebot.devtools.resgen import StandardGenerator, generate_resources

result = generate_resources(
    output_code_file="./src/tasks/res/R.py",
    generator_factory=lambda default_variant: StandardGenerator(
        production=True,
        ide_type="vscode",
    ),
    conf_path="./pyproject.toml",
    output_img_dir="./tmp",
)

print(result.model_dump())
```

### 参数说明（常用）

- `output_code_file`：目标 Python 文件路径。
- `generator_factory`：接收 `default_variant`，返回一个生成器实例。
- `conf_path`：项目配置文件（用于加载 resgen 配置）。
- `output_img_dir`：中间图像输出目录。
- `include_base_variant`：是否包含基础 variant。
- `show_diagnostics`：是否显示诊断信息。
- `ignore_error`：是否在错误时继续。

## 5. 生成实体 prefab：使用 EntityGenerator

当你希望输出 `TemplateMatchPrefab` 风格类时，使用 `EntityGenerator`。

```python
from kotonebot.devtools.resgen import EntityGenerator, generate_resources

generate_resources(
    output_code_file="./src/tasks/res/entities.py",
    generator_factory=lambda default_variant: EntityGenerator(
        production=True,
        ide_type="vscode",
        default_variant=default_variant,
    ),
    conf_path="./pyproject.toml",
    output_img_dir="./tmp",
)
```

## 6. 由浅入深的扩展示例

下面从最小改动开始，逐步扩展。

### 6.1 仅改路径表达式（PathPolicy）

```python
from kotonebot.devtools.resgen import StandardGenerator

class AssetRefPathPolicy:
    def transform_path(self, original_path: str, default_expr: str, *, generator: StandardGenerator) -> str:
        _ = default_expr
        path = original_path.replace("\\", "/")
        return f'asset_ref("{path}")'

gen = StandardGenerator(
    production=True,
    path_policy=AssetRefPathPolicy(),
)
```

### 6.2 仅改 docstring 输出（DocstringPolicy）

```python
from kotonebot.devtools.resgen import ResourceNode, StandardGenerator

class CompactDocPolicy:
    def render_docstring(self, attr: ResourceNode, *, generator: StandardGenerator) -> bool:
        if not attr.docstring:
            return True
        generator.writer.write('"""')
        generator.writer.write(attr.docstring)
        generator.writer.write('"""')
        return True

gen = StandardGenerator(
    production=False,
    docstring_policy=CompactDocPolicy(),
)
```

### 6.3 覆盖某类资源渲染（RendererRegistry）

```python
from kotonebot.devtools.resgen import (
    RenderContext,
    RendererRegistry,
    ResourceNode,
    StandardGenerator,
)

class UnknownRenderer:
    id = "custom-unknown"
    render_docstring = False

    def match(self, attr: ResourceNode, *, generator: StandardGenerator) -> bool:
        return attr.type == "unknown"

    def render(self, context: RenderContext) -> None:
        context.write(f"{context.attr.name} = custom_expr()")

registry = RendererRegistry()
registry.register(UnknownRenderer())

gen = StandardGenerator(
    production=True,
    renderer_registry=registry,
)
```

## 7. 选择建议

- 只想改路径：优先 `PathPolicy`。
- 只想改文档样式：优先 `DocstringPolicy`。
- 只想替换某类资源输出：用 `RendererRegistry` 注册 renderer。
- 想完全重写输出结构：继承 `StandardGenerator` / `EntityGenerator`。

## 8. 常见问题

### 为什么要区分 Renderer 和 Policy？

- `Renderer` 负责“生成什么结构”。
- `Policy` 负责“生成时遵循什么规则”。

### 自定义 renderer 会影响所有资源吗？

不会。仅对 `match` 命中的资源生效。

### 可以同时使用 `path_transformer` 和 `path_policy` 吗？

可以，但当 `path_policy` 存在时会优先使用它。