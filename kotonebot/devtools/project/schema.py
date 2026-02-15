from typing import Any
from pydantic import BaseModel, Field

class EditorMetadata:
    """
    ## Prefab 元数据类
    
    此类用于声明自定义 Prefab 的编辑器元数据，包括ID、名称、
    描述、自定义字段等。只需要在你的 Prefab 类下声明一个
    继承自此类的嵌套类（名称随意），Devtool 会自动扫描并识别
    出你的自定义 Prefab，并按照元数据展示。

    ### 例
    ```python
    class MyButtonPrefab(Prefab):
        # 实际属性
        type: Literal['primary' | 'secondary'] = 'primary'
        region: Rect | None = None
        match_text: str = ''

        # 编辑器元数据
        class Editor(EditorMetadata):
            id = 'my_button'
            name = '按钮'
            description = '一个自定义按钮 Prefab'
            props = {
                'type': ChoiceProp(label='按钮类型', description='按钮的样式类型', default_value='primary', choices=[('主按钮', 'primary'), ('次按钮', 'secondary')]),
                'region': RectProp(label='按钮区域', description='按钮在屏幕上的位置区域', default_value=None),
                'match_text': StrProp(label='匹配文本', description='按钮上的文本内容', default_value=''),
            }

    ```
    """
    id: str
    name: str
    description: str | None = None
    primary_prop: str | None = None
    shortcut: str | None = None
    """
    用于切换到此工具的快捷键，可以为单按键。
    """
    icon: str | None = None
    """展示在编辑器上的 icon 名称。"""
    """
    主属性 key（例如 rect / anchor / image）。
    """
    props: 'dict[str, EditorProp]' = {}
    """
    此 Prefab 的属性，格式为 dict[属性键名, EditorProp]。
    """


class EditorProp(BaseModel):
    kind: str
    label: str
    description: str | None = None
    default_value: Any = None


class RectProp(EditorProp):
    kind: str = 'rect'


class PointProp(EditorProp):
    kind: str = 'point'


class ImageProp(EditorProp):
    kind: str = 'image'

class BoolProp(EditorProp):
    kind: str = 'bool'


class FloatProp(EditorProp):
    kind: str = 'float'
    min: float | None = None
    max: float | None = None


class IntProp(EditorProp):
    kind: str = 'int'


class StrProp(EditorProp):
    kind: str = 'str'


class ChoiceProp(EditorProp):
    kind: str = 'choice'
    choices: list[tuple[str, Any]] = Field(...)

class EditorData(BaseModel):
    prefabs_module: str | None = None
    resource_path: str | None = None


class VariantData(BaseModel):
    names: list[str] | None = None
    base: str | None = None
    path_pattern: str | None = None


class PyProjectData(BaseModel):
    editor: EditorData | None = None
    variant: VariantData | None = None
