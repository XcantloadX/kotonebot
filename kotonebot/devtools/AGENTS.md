# KotoneBot DevTools Backend 开发指南

## 代码风格

### import

- import 语句始终放在文件开头（标准库→第三方→本地），除非是以下场景之一：可选依赖、重型依赖懒加载、其他合理场景（需在注释中说明原因）。

### Pydantic

- 所有结构化数据传输对象（配置、请求/响应体、跨模块参数）必须使用 `pydantic.BaseModel` 定义类型，禁止使用裸露的 `dict` 传递。
- 例外情况：仅在函数内部临时组装、绝不跨函数传递的局部数据可以使用 `dict`。
- Pydantic 模型统一放在对应模块的 `types.py` 中（如 `kotonebot/devtools/ai/types.py`），若仅在该模块内部使用也可内联定义。
- 在决定类型定义位置前必须检索是否已经存在统一的合理的 type 存放位置，如有则存放在相应位置。

### HTTP 路由返回类型

- **所有 JSON 路由必须在装饰器中声明 `response_model=ResponseModel[X]`**，其中 `X` 为实际的 data 模型；函数返回类型注解为 `-> JSONResponse`（路由通过 `ok_response()` 返回 `JSONResponse`，FastAPI 对 Response 返回值不做校验，因此 `response_model` 仅用于生成 OpenAPI schema——供前端 `openapi-typescript` 生成客户端类型——不影响运行时输出）。不要用 `-> ResponseModel[X]` 作为返回注解，否则与实际的 `JSONResponse` 返回不匹配会触发类型检查器报错。
- 无 data 的路由 `response_model=ResponseModel[None]`。
- 响应模型优先复用服务层/索引层已有的模型；仅在需要新增 HTTP 专用形状时定义在 `transports/http/models.py`。
- 修改路由签名或响应模型后，需重新生成前端类型：`cd js/apps/devtools-app && npm run gen:api:full`。

### 注释

#### Docstring 格式

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

#### 覆盖范围

| 元素 | 必须 | 格式 |
|------|------|------|
| 模块 | 是 | 文件顶部一行中文描述 |
| 类 | 是 | 类定义下方，中文 |
| 公开方法 | 是 | RST，中文 |
| 私有方法 | 推荐 | 一行 `#` 注释或 docstring |
| 属性（dataclass / pydantic field） | 推荐 | 字段后的注释 |

#### 代码行内注释

- 复杂逻辑段上方加 `#` 注释说明意图
- **禁止写「这段代码做了什么」这类显而易见的注释，而应写「为什么要这样做」**
- 中文注释

### 路径约定

- **相对路径的根**：所有 API 返回或接收的相对路径均以 `pyproject_root`（`pyproject.toml` 所在目录）为根。
- **`resource_root`（`project_root`）**：图片/文档的实际存放目录，通常是 `pyproject_root` 的子目录（如 `resources/`），通过 `[tool.kotonebot.editor.resource_path]` 配置。该路径仅在内部构建目录树（如 `get_folder_tree`）或前端文件对话框导航时使用。
- **路径解析**：使用 `get_safe_path()` 将相对路径转为绝对路径时，内部调用 `from_rel()` 将其拼接到 `pyproject_root` 上。所有 API 端点应统一使用 `get_safe_path()`，不要对相对路径使用其他根（除非有明确理由并注释说明）。
- 前端与后端之间的所有相对路径均以 `/` 分隔的 POSIX 格式传递。
