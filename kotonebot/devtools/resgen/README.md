# resgen 模块说明

`kotonebot.devtools.resgen` 是 KotoneBot 的资源代码生成模块，用于将图片资源（PNG）及其元信息（meta JSON）转换为可直接在代码中引用的 Python 类与属性。

该模块的典型任务流程：

1. **扫描资源文件**：遍历某个根目录下的 `.png` 与 `.png.json` 文件。
2. **解析资源**：使用一组 `SchemaParser`（如 `KotoneV1Parser`、`BasicSpriteParser`）将文件解析成中间表示 `ResourceNode` 列表。
3. **构建类树**：将扁平的 `ResourceNode` 列表通过 `build_class_tree` 组织成树状的 `ClassNode` 结构（类似 `Ui.Buttons.Submit`）。
4. **代码生成**：使用 `StandardGenerator` 或 `EntityGenerator` 将 `ClassNode` 树渲染为最终 Python 代码文件（通常是资源索引 `R.py` 或实体 prefab 代码）。

后续二次开发主要就是：
- 新增/修改解析器（支持新的 meta 格式或资源类型）；
- 调整代码生成器（生成不同风格的 Python 代码或目标模块）；
- 扩展 meta JSON 结构与校验逻辑。

---

## 模块结构总览

### 顶层导出（`kotonebot.devtools.resgen`）

`kotonebot.devtools.__init__` 通过 `from .resgen import ...` 导出了一组核心 Symbol，方便外部直接使用：

- `CodeWriter`：简单的代码缩进/写入工具。
- `ResourceNode` / `ClassNode`：中间表示（IR）结构。
- `SchemaParser`：解析器协议接口。
- `StandardGenerator` / `EntityGenerator`：代码生成器。
- `ParserRegistry` / `KotoneV1Parser` / `BasicSpriteParser`：解析器注册表与内置解析器。
- `to_camel_case` / `unify_path` / `build_class_tree` / `ImageProcessor`：工具函数与图片处理工具。

核心源码位于：

- `core.py`：IR 数据结构与 `SchemaParser` 协议。
- `parsers.py`：`ParserRegistry`、`KotoneV1Parser`、`BasicSpriteParser`。
- `codegen.py`：`StandardGenerator`、`EntityGenerator` 以及代码渲染逻辑。
- `utils.py`：`to_camel_case`、`unify_path`、`build_class_tree`、`ImageProcessor`。
- `validation.py`：meta JSON 格式的检测与校验逻辑。

---

## 中间表示（IR）与核心类

### `CodeWriter`

位于 `core.py`，负责生成 Python 源码时的缩进管理与逐行写入：

- `write(text: str)`：写入一行代码（自动加缩进）。
- `write_empty_line()`：写入空行。
- `indent()`：上下文管理器，进入时缩进 +1，退出时缩进 -1。
- `get_content() -> str`：返回最终拼接好的源码字符串。

代码生成器不会直接拼字符串，而是通过 `CodeWriter` 来保证缩进正确、结构清晰。

### IR 数据结构

都定义在 `core.py`：

- `ImageAsset`：图片资源信息。
  - `path: str`：图片路径（通常为输出目录中的 PNG）。
  - `rect: Optional[Tuple[int, int, int, int]]`：裁剪矩形 `(x1, y1, x2, y2)`，可选。

- `PrefabData`：自定义 Prefab 资源信息。
  - `image: ImageAsset`：底层图片资源。
  - `class_name: str`：Prefab 的基类名（字符串形式）。

- `BoxData`：矩形区域数据（用于 HintBox）。
  - `x1, y1, x2, y2: int`：矩形坐标。
  - `resolution: Tuple[int, int] = (720, 1280)`：原图分辨率。

- `PointData`：点数据（用于 HintPoint）。
  - `x, y: int`：点坐标。

- `ResourceNode`：**资源的最小单元**，是解析器的输出、生成器的输入。字段：
  - `name: str`：Python 属性名或类名（如 `Button`、`DialogArea`）。
  - `type: str`：资源类型：`"template"` / `"hint-box"` / `"hint-point"` / `"prefab"` 等。
  - `value: Union[ImageAsset, BoxData, PointData, PrefabData, Any]`：资源 IR 对象。
  - `docstring: str`：资源的文档说明（后续会被生成到代码中）。
  - `metadata: Dict[str, Any]`：原始元数据（如 `class_path`、原始文件路径等），用于扩展与调试。

- `ClassNode`：表示一个生成的 Python 类节点，是 `build_class_tree` 的输出。
  - `name: str`：类名。
  - `children: List[ClassNode]`：子类列表，用于构建层级结构（如 `Ui.Buttons.Submit`）。
  - `attributes: List[ResourceNode]`：类中的属性列表。
  - `is_empty()`：是否没有子类与属性。

### `SchemaParser` 协议

定义在 `core.py`，是所有解析器的接口约定：

```python
class SchemaParser(Protocol):
    def can_parse(self, file_path: str) -> bool: ...
    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]: ...
```

- `can_parse`：判断当前解析器是否能处理给定路径。
- `parse`：真正解析文件，返回 `ResourceNode` 列表；`context` 中可以放输出目录、根扫描路径等配置信息。

要支持新格式，只需实现一个满足该协议的类，再注册到 `ParserRegistry` 即可。

---

## 解析层：`parsers.py`

### `ParserRegistry`

简单的解析器注册表：

- `register(parser: SchemaParser)`：注册一个解析器，按注册顺序参与匹配。
- `parse_file(file_path: str, context: Dict[str, Any]) -> List[ResourceNode]`：
  - 依次调用已注册解析器的 `can_parse`，找到第一个返回 `True` 的解析器，并调用其 `parse`；
  - 如果没有解析器匹配，返回空列表。

### `KotoneV1Parser`

负责解析带有 meta JSON 的 `*.png.json` 文件，详见下文“meta JSON 格式”。

接口：

- `can_parse(file_path: str) -> bool`
  - 要求扩展名为 `.png.json`；
  - 打开 JSON，调用 `detect_and_validate_meta_schema` 检测/校验；
  - 若 JSON 结构合法，返回 `True`，否则返回 `False`。

- `parse(file_path: str, context: Dict[str, Any]) -> List[ResourceNode]`
  - `file_path` 必须是 `xxx.png.json`；
  - `context` 至少应包含：
    - `output_img_dir`: 图片输出目录（裁剪/复制后的图片会写到这里）；
    - `root_scan_path`: 可选，用于单定义模式下推导 `class_path`。
  - 加载 JSON，调用 `detect_and_validate_meta_schema` 得到 `MetaSchemaInfo`：
    - `format == "single"`：走简单格式解析 `_parse_single_definition`；

#### 单定义格式解析（`format == "single"`）

由 `_parse_single_definition` 完成，专门处理：

- 顶层只有一个 `definition` 对象；
- `isSimple` 必须为 `true`；
- 不允许出现 `definitions` 与 `annotations`。

目前单定义格式仅支持：

- `type == "template"`
- `type == "prefab"`

并且：

- **不依赖任何 `annotations`**，直接把整张 PNG 当作模板/Prefab 图像；
- 针对 `name` 和 `displayName` 都做了“可选”与“自动推导”处理：
  - 若 `definition.name` 为空或缺省，则：
    - 根据 PNG 相对 `root_scan_path` 的目录结构推导 `class_path`；
    - 使用文件名（不含扩展名）做 `attr_name`，并通过 `to_camel_case` 转成 CamelCase；
  - 若 `definition.displayName` 为空或缺省，则使用原始文件名（含扩展名）作为显示名。

复制图片时：

- 使用 `uuid4` 生成随机文件名 `{uuid}.png`；
- 通过 `ImageProcessor.copy_image` 复制到 `output_img_dir`；
- 在 `metadata` 中记录 `origin_file` 与 `abs_path`。

对于 `prefab`：

- 要求 `definition.prefab.className` 为非空字符串，否则抛出 `MetaValidationError`。

### `BasicSpriteParser`

面向 **没有任何 JSON meta 文件** 的简单 PNG：

- `can_parse(file_path)`：
  - 扩展名为 `.png`；
  - 同名 JSON（`file_path + '.json'`）不存在。

- `parse(file_path, context)`：
  - 从 `context` 读取：
    - `output_img_dir`：输出目录；
    - `root_scan_path`：用于构建相对路径与 `class_path`；
  - 将源 PNG 复制到输出目录，文件名改为 `{uuid}.png`；
  - 计算：
    - `class_path`：根据 `os.path.relpath(file_path, root_scan_path)` 的目录部分拆分并 `to_camel_case`；
    - `attr_name`：文件名（去 `.png`）的 CamelCase 形式；
    - `display_name`：原始文件名。
  - 返回一个 `ResourceNode`：
    - `type = "template"`
    - `value = ImageAsset(path=final_path)`
    - `metadata` 包含：`class_path`、`origin_file`、`abs_path`、`display_name`。

---

## 工具层：`utils.py`

### `to_camel_case(s: str) -> str`

- 将包含分隔符的字符串转换为 PascalCase / CamelCase：
  - 分隔符集合为：所有标点和空白字符（含下划线 `_`）；
  - 连续分隔符视为一个；
  - 没有分隔符时：
    - 若原字符串中含大写字母，则原样返回；
    - 否则仅首字母大写（`"hello" -> "Hello"`）。
- 适用于文件名、目录名到类名/属性名的转换，支持 Unicode 字符（如 CJK）。

### `unify_path(path: str) -> str`

- 简单将 `\\` 替换为 `/`，用于统一路径分隔符，避免在生成代码或 IDE 显示时出现 Windows 反斜杠问题。

### `build_class_tree(resources: List[ResourceNode]) -> List[ClassNode]`

- 输入：带有 `metadata['class_path']` 的 `ResourceNode` 列表；
- 逻辑：
  - 按 `class_path`（如 `['Ui', 'Buttons']`）构建分层的 `ClassNode` 树：
    - 顶层节点收集在 `root_map` 中；
    - 通过 `node_registry` 缓存已创建节点；
    - 将每个 `ResourceNode` 挂到其 `class_path` 对应的 `ClassNode.attributes`。
- 输出：顶层 `ClassNode` 列表，供生成器递归遍历。

### `ImageProcessor`

对依赖 OpenCV（`cv2`）的图片操作进行了封装：

- `save_crop(source_path, rect, output_dir, prefix) -> str`：
  - 从原图读取并按 `(x1, y1, x2, y2)` 裁剪；
  - 自动保护边界（不超过图像尺寸，坐标下限为 0）；
  - 文件名形如 `{prefix}_{8位uuid}.png`；
  - 返回裁剪后图片的**绝对路径**。

- `copy_image(source_path, output_dir, new_name=None) -> str`：
  - 使用 `shutil.copy` 复制文件到输出目录；
  - 若 `new_name` 为 `None`，则保留原文件名；
  - 返回复制后文件的**绝对路径**。

---

## 代码生成层：`codegen.py`

### `StandardGenerator`

生成“资源索引类”风格的 Python 代码，主要输出：

- 文件头部：
  - 开发模式（`production=False`）下会输出多行警告注释：
    - `此文件为自动生成，请勿编辑` 等；
  - 无论何种模式，都会导入：
    - `from kotonebot.backend.core import Image, HintBox, HintPoint`。

- 类与属性：
  - 对每个 `ClassNode` 生成一个 `class Xxx:`；
  - 若类没有子类和属性，写入 `pass`；
  - 否则依次生成属性与子类定义。

#### `render_attribute`

根据 `ResourceNode.value` 的 IR 类型生成具体赋值代码：

- `ImageAsset`：
  - 使用裁剪图（或复制图）的文件名作为 sprite 路径：
    - `rel = os.path.basename(val.path)`
    - 输出：`Image(path=sprite_path("{rel}"))`
    - 注意：这里依赖外部存在 `sprite_path` 函数（通常在 R.py 所在上下文定义）。

- `BoxData`：
  - 输出：`HintBox(x1=..., y1=..., x2=..., y2=..., source_resolution=(w, h))`。

- `PointData`：
  - 输出：`HintPoint(x=..., y=...)`。

- 其他类型：
  - 退化为 `str(value)`。

若为开发模式（`production=False`），还会跟一个三引号 `docstring`，用 `render_docstring` 生成。

#### `render_docstring`

开发模式下，为每个资源属性生成带图片的文档字符串：

- 基本文本来自 `ResourceNode.docstring`（通常是名称、描述、模块等信息）；
- 再根据 `metadata` 补充图片标签：
  - 若存在 `metadata['abs_path']` 或 `metadata['preview_path']`，使用 `_make_img_tag` 生成 `<img>` 标签；
  - 若存在原始大图 `metadata['origin_file']`，再附加一段 `Original:` 图片；
- 通过 `_make_img_tag` 适配不同 IDE：
  - VSCode：`vscode-file://vscode-app/...`；
  - PyCharm：`http://localhost:6532/image?path=...`；
  - 默认：`file:///...`。

### `EntityGenerator`

生成“实体 Prefab 代码”，与 `StandardGenerator` 的区别：

- 头部导入不同：
  - `from kotonebot.core import TemplateMatchPrefab`
  - `from kotonebot.primitives import Image, Rect`
  - `from kotonebot.backend.core import HintBox, HintPoint`

- `render_attribute` 根据不同类型分发：
  - `ImageAsset`：调用 `_render_prefab_class`，生成继承自 `TemplateMatchPrefab` 的嵌套类；
  - `PrefabData`：调用 `_render_custom_prefab_class`，生成继承自自定义 `base_class` 的嵌套类；
  - `BoxData` / `PointData`：调用 `_render_primitive_assignment`，生成 `HintBox(...)` / `HintPoint(...)` 赋值；
  - 其他类型：回退到父类 `StandardGenerator.render_attribute`。

#### `_render_prefab_class`

针对简单 `ImageAsset` 的 prefab：

- 生成类似：

  ```python
  class Button(TemplateMatchPrefab):
      """docstring..."""
      template = Image(file_path="/abs/path/to/crop.png")
      display_name = "按钮"
      _orig_rect = Rect(x=..., y=..., w=..., h=...)
  ```

- `template` 路径通过 `unify_path` 统一分隔符；
- 若有 `rect`，会计算出 `Rect`；否则 `_orig_rect = None`。

#### `_render_custom_prefab_class`

针对 `PrefabData`（`class_name` 为自定义基类）：

- 类似 `_render_prefab_class`，但类签名为：

  ```python
  class SomeName(SomeBaseClass):
      ...
  ```

#### `_render_primitive_assignment`

- 对于 `BoxData` / `PointData`，生成简单赋值语句：

  ```python
  DialogArea = HintBox(...)
  TouchPoint = HintPoint(...)
  ```

- 当前不为这些赋值生成复杂 docstring。

---

## meta JSON 格式规范

meta JSON 的检测/校验逻辑集中在 `validation.py` 的 `detect_and_validate_meta_schema` 中，核心规则：

- **单定义格式（single）**：
  - 顶层必须有：`isSimple: true`；
  - 顶层必须有：`definition`（对象）；
  - 顶层不能有：`definitions` 或 `annotations`；


若结构不能满足条件，会抛出 `MetaValidationError`。

### 单定义格式（single meta）

顶层结构：

```jsonc
{
  "isSimple": true,
  "definition": {
    "name": "ui.button",        // 可选
    "type": "template",        // 必须，支持 "template" / "prefab"
    "displayName": "按钮",      // 可选
    "description": "测试按钮",  // 可选
    "prefab": {                  // 仅当 type == "prefab" 时使用
      "className": "MyPrefabBase"
    }
  }
}
```

- `name`：
  - 若存在且非空：
    - 以 `.` 分割：前部转 CamelCase 得到 `class_path`，最后一段作为属性名（不做 CamelCase 强制）；
  - 若缺省或为空：
    - 使用文件系统信息推导：
      - `class_path`：由 `os.path.relpath(png_file, root_scan_path)` 的目录部分拆分并 `to_camel_case`；
      - `attr_name`：由文件名（无扩展名）经 `to_camel_case` 得到。

- `displayName`：
  - 若存在且非空：直接使用；
  - 否则回退为原始文件名（含 `.png`）。

- `type`：
  - `"template"`：生成 `ResourceNode(type="template", value=ImageAsset(...))`；
  - `"prefab"`：需要 `definition.prefab.className` 为非空字符串，否则抛出 `MetaValidationError`。

- 不涉及 `annotations`，图片直接整体复制：
  - 输出路径：`output_img_dir/{uuid}.png`。

**简单模板示例（template）：**

```json
{
  "isSimple": true,
  "definition": {
    "name": "ui.button",
    "type": "template",
    "displayName": "按钮",
    "description": "主按钮"
  }
}
```

**简单 Prefab 示例：**

```json
{
  "isSimple": true,
  "definition": {
    "name": "ui.dialog.okButton",
    "type": "prefab",
    "displayName": "确定按钮",
    "description": "弹窗上的确定按钮",
    "prefab": {
      "className": "MyOkButtonPrefab"
    }
  }
}
```



---

## 典型使用流程示例

下面是一个近似于 `tests/devtools/test_resgen_integration.py` 的完整流程示例，展示如何从 PNG / meta JSON 生成 Python 代码字符串。

```python
from kotonebot.devtools.resgen import (
    ParserRegistry,
    KotoneV1Parser,
    BasicSpriteParser,
    build_class_tree,
    StandardGenerator,
)

root_scan_path = "/path/to/assets"
output_img_dir = "/path/to/generated/images"

# 1. 构建解析器注册表
registry = ParserRegistry()
registry.register(KotoneV1Parser())   # 优先解析带 .png.json 的复杂/简单 meta
registry.register(BasicSpriteParser())  # 再解析普通 PNG

# 2. 遍历资源目录
all_resources = []
for dirpath, _, filenames in os.walk(root_scan_path):
    for name in filenames:
        full_path = os.path.join(dirpath, name)
        context = {
            "output_img_dir": output_img_dir,
            "root_scan_path": root_scan_path,
        }
        resources = registry.parse_file(full_path, context)
        all_resources.extend(resources)

# 3. 构建类树
root_nodes = build_class_tree(all_resources)

# 4. 生成代码
# 开发模式（带 docstring + 图片标签，方便调试）
gen = StandardGenerator(production=False, ide_type="vscode")
code_str = gen.generate(root_nodes)

# 把生成代码写入某个 R.py 文件
with open("R.py", "w", encoding="utf-8") as f:
    f.write(code_str)
```

如果需要生成实体 Prefab 代码，则将 `StandardGenerator` 换成 `EntityGenerator` 即可：

```python
from kotonebot.devtools.resgen import EntityGenerator

gen = EntityGenerator(production=False, ide_type="vscode")
code_str = gen.generate(root_nodes)
```

---

## 如何二次开发 / 扩展

### 1. 新增自定义解析器

场景：需要支持新的 meta 格式（例如其他工具导出的 JSON），可以：

1. 在 `parsers.py` 中新增一个类，实现 `SchemaParser` 协议：

   ```python
   from .core import SchemaParser, ResourceNode, ImageAsset

   class MyCustomParser(SchemaParser):
       def can_parse(self, file_path: str) -> bool:
           # 根据文件扩展名或者内容判断
           return file_path.endswith(".my.json")

       def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
           # 解析 JSON -> 构造 ResourceNode 列表
           ...
   ```

2. 在使用端，将该解析器注册进 `ParserRegistry`：

   ```python
   registry = ParserRegistry()
   registry.register(MyCustomParser())
   registry.register(KotoneV1Parser())
   registry.register(BasicSpriteParser())
   ```

3. 保持约定：为每个 `ResourceNode.metadata` 至少填充：
   - `class_path: List[str]`
   - `origin_file: str`（绝对路径）
   - `abs_path: str`（图片绝对路径）
   - `display_name: str`

### 2. 扩展/修改 meta JSON 结构

- 若只是 **在现有单定义格式中新增可选字段**：
  - 可以直接在解析器的 `definition` / `annotation` 处理逻辑中读这些字段，并写入 `ResourceNode.metadata`；
  - 若这些字段需要强约束（必填、类型限制），可以在 `validation.detect_and_validate_meta_schema` 中补充检查逻辑（或编写新的验证函数）。

- 若需要 **引入第三种 schema 类型**：
  - 可以在 `validation.py` 中：
    - 扩展 `MetaFormat` 与 `MetaSchemaInfo`；
    - 在 `detect_and_validate_meta_schema` 中加入新的分支；
  - 然后在 `KotoneV1Parser.parse` 中，根据返回的 `format` 值选择不同解析分支。

### 3. 定制代码生成结果

- 若只是希望调整变量命名、docstring 风格等：
  - 可以继承 `StandardGenerator` / `EntityGenerator`，重写：
    - `render_header`：控制头部导入与注释；
    - `render_class`：控制类声明与嵌套结构（一般无需修改）；
    - `render_attribute`：控制属性渲染策略；
    - `render_docstring`：控制文档字符串与图片标签样式。

- 若需要输出到其他语言/模板（例如 TypeScript）：
  - 仍然可以重用 `ResourceNode` / `ClassNode` 与 `build_class_tree`；
  - 编写一个新的 Generator，内部也可以使用 `CodeWriter` 或任意模板引擎。

### 4. IDE 集成与图片预览

- `StandardGenerator` 和 `EntityGenerator` 都支持通过 `ide_type` 参数生成不同格式的图片标签：
  - `ide_type='vscode'`：
    - 使用 `vscode-file://vscode-app/...`；
  - `ide_type='pycharm'`：
    - 使用本地 HTTP 服务器形式 `http://localhost:6532/image?path=...`；
  - 其他 / `None`：
    - 使用 `file:///...`。

- 解析器需要在 `ResourceNode.metadata` 中填充：
  - 对普通模板：`abs_path`、`origin_file`；
  - 对 HintBox：`preview_path`、`origin_file`；

生成器会基于这些字段自动为 docstring 添加 `<img>` 标签。

---

## 小结

- `resgen` 将“**图片 + meta JSON**”统一转化为 `ResourceNode` / `ClassNode`，再通过 Generator 生成最终 Python 代码；
- meta JSON 支持 **单定义格式**：
  - 单定义格式适合单一资源（整体图片）快速配置；
- 模块内部通过清晰的 IR、解析器协议与生成器分层，便于扩展新的 meta 格式和代码生成目标。
