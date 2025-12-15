from dataclasses import dataclass


class EditorMetadata:
    """
    Prefab Devtool 编辑器元数据类
    
    此类用于声明自定义 Prefab 的编辑器元数据，包括ID、名称、
    描述、自定义字段等。只需要在你的 Prefab 类下声明一个
    继承自此类的嵌套类（名称随意），Devtool 会自动扫描并识别
    出你的自定义 Prefab，并按照元数据展示。
    """
    id: str
    name: str
    description: str
    export_slice: bool
    """
    是否导出切片
    
    若为 True，将会自动裁剪选中范围的图像为切片数据并保存。
    """

@dataclass
class EditorData:
    prefabs_module: str | None = None

@dataclass
class PyProjectData:
    editor: EditorData | None = None