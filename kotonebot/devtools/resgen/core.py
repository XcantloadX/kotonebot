import contextlib
from dataclasses import dataclass, field
from typing import List, Any, Protocol, Dict, Optional, Union, Tuple

# --- 工具类: CodeWriter ---
class CodeWriter:
    def __init__(self):
        self._lines = []
        self._indent_level = 0
        self._indent_str = "    "

    def write(self, text: str):
        """写入一行代码，自动处理缩进"""
        self._lines.append((self._indent_str * self._indent_level) + text)

    def write_empty_line(self):
        self._lines.append("")

    @contextlib.contextmanager
    def indent(self):
        """缩进上下文管理器"""
        self._indent_level += 1
        yield
        self._indent_level -= 1

    def get_content(self) -> str:
        return "\n".join(self._lines)

# --- 中间表示 (IR) 数据结构 ---


@dataclass
class ImageAsset:
    """代表图片资源的结构化数据"""
    path: str
    rect: Optional[Tuple[int, int, int, int]] = None  # (x1, y1, x2, y2)


@dataclass
class BoxData:
    """代表矩形区域的结构化数据"""
    x1: int
    y1: int
    x2: int
    y2: int
    resolution: Tuple[int, int] = (720, 1280)


@dataclass
class PointData:
    """代表点的结构化数据"""
    x: int
    y: int


@dataclass
class ResourceNode:
    """资源的最小单元 (Sprite, HintBox 等)。value 存放 IR 对象，而不是代码字符串。"""
    name: str
    type: str  # 'template', 'hint-box', 'hint-point'
    value: Union[ImageAsset, BoxData, PointData, Any]
    docstring: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict) # 原始数据备份，用于扩展

@dataclass
class ClassNode:
    """表示一个生成的类节点"""
    name: str
    children: List['ClassNode'] = field(default_factory=list)
    attributes: List[ResourceNode] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        return not self.children and not self.attributes

# --- 接口定义 ---

class SchemaParser(Protocol):
    """解析器协议"""
    def can_parse(self, file_path: str) -> bool:
        """判断该解析器是否能处理此文件"""
        ...

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        """解析文件并返回资源列表。Context 可包含输出目录等配置"""
        ...