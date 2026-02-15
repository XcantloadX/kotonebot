# Devtools Meta Formats

本文档说明 `kotonebot/devtools` 相关的 meta JSON 格式，包括旧格式与当前格式。

## 1. 文件命名

meta 文件与图片同名，后缀为 `.png.json`，例如：

- 图片：`button.png`
- meta：`button.png.json`

## 2. 格式总览

当前历史上存在 3 种格式：

1. Legacy Simple（旧版简单格式）
2. Legacy Complex（旧版复杂格式）
3. Meta V2（当前新格式）

其中 **当前推荐并持续演进的是 Meta V2**。

## 3. Legacy Simple

顶层结构特征：

- `isSimple: true`
- `definition: object`
- 顶层不能包含 `definitions` / `annotations`

示例：

```json
{
  "isSimple": true,
  "definition": {
    "type": "template",
    "name": "ui.button",
    "displayName": "Button",
    "description": "Main button"
  }
}
```

## 4. Legacy Complex

顶层结构特征：

- `isSimple` 缺省或为 `false`
- 必须包含 `definitions: object`
- 必须包含 `annotations: array`
- 顶层不能包含 `definition`

示例：

```json
{
  "definitions": {
    "def-1": {
      "name": "ui.button",
      "type": "template",
      "annotationId": "annot-1"
    }
  },
  "annotations": [
    {
      "id": "annot-1",
      "type": "rect",
      "data": { "x1": 10, "y1": 20, "x2": 100, "y2": 200 }
    }
  ]
}
```

## 5. Meta V2（推荐）

顶层结构特征：

- `version` 必须为 `2`
- 必须包含 `definitions: object`
- 不允许 `annotations`

`definitions` 下每个 definition 常见字段：

- `type: string`
- `name?: string`
- `displayName?: string`
- `description?: string`
- `prefab_id?: string`
- `props: object`

示例：

```json
{
  "version": 2,
  "definitions": {
    "loginButton": {
      "type": "template",
      "name": "ui.login.button",
      "displayName": "Login Button",
      "description": "button in login panel",
      "props": {
        "templateImage": { "kind": "image", "x1": 100, "y1": 200, "x2": 220, "y2": 260 }
      }
    }
  }
}
```

## 6. 当前模块支持状态

### 6.1 `devtools/indexing`

- 使用共享入口解析 Meta V2。
- 面向 symbol index / diagnostics。
- 不做旧格式兼容。

### 6.2 `devtools/resgen`

- 历史上支持 Legacy Simple / Legacy Complex / V2。
- 当前主路径建议使用 V2。
- 旧格式仅用于存量兼容与迁移阶段。

## 7. 结论

新增或重构资源时，请统一使用 **Meta V2**，避免继续引入 legacy 格式。
