import cv2
import uuid
from pathlib import Path
from typing import List, Dict, Tuple
from kotonebot.devtools.errors import InvalidImageError

from .core import ResourceNode, ClassNode

# --- 字符串处理 ---
def to_camel_case(s: str) -> str:
    """使用简单黑名单把不可出现在变量名的字符当作分隔符，生成 PascalCase。

    实现策略（简单黑名单）：
    - 将 `string.punctuation`（标点）和空白字符视为分隔符，但保留下划线 `_`，因为下划线可以出现在变量名中。
    - 连续的分隔符视为单个分隔符。
    - 如果原始字符串中没有任何分隔符，则返回原样（保持 Unicode 字符如 CJK、emoji 的大小写/形式）。
    """
    import string as _string

    # 构造黑名单：标点 + 空白（包含下划线 `_`，因为我们把下划线也视为常见的分隔符）
    blacklist = set(_string.punctuation) | set(_string.whitespace)

    # 检查是否存在任意分隔符字符
    if not any((ch in blacklist) for ch in s):
        # 如果没有分隔符：
        # - 若字符串包含大写字母（可能已是驼峰/混合大小写），则保留原样；
        # - 否则将首字母大写以兼容先前的期望（'hello' -> 'Hello'）
        if any(ch.isupper() for ch in s):
            return s
        return s.capitalize()

    # 按黑名单分割：手工扫描以支持任意 Unicode 字符
    parts = []
    cur = []
    for ch in s:
        if ch in blacklist:
            if cur:
                parts.append(''.join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append(''.join(cur))

    def cap(p: str) -> str:
        return p[0].upper() + p[1:] if p else ''

    return ''.join(cap(p) for p in parts)

def unify_path(path: str) -> str:
    return path.replace('\\', '/')

# --- 树构建逻辑 ---
def build_class_tree(resources: List[ResourceNode]) -> List[ClassNode]:
    """
    将扁平的资源列表转换为树状 ClassNode 结构。
    依赖 resource.metadata['class_path'] (List[str])
    """
    root_map: Dict[str, ClassNode] = {}
    
    # 辅助：获取或创建节点
    node_registry: Dict[str, ClassNode] = {} # full_path -> ClassNode

    def get_node(path_parts: List[str]) -> ClassNode:
        key = ".".join(path_parts)
        if key in node_registry:
            return node_registry[key]
        
        name = path_parts[-1]
        node = ClassNode(name=name)
        node_registry[key] = node
        
        # 如果是顶层节点
        if len(path_parts) == 1:
            root_map[name] = node
        else:
            # 挂载到父节点
            parent = get_node(path_parts[:-1])
            # 避免重复添加
            if node not in parent.children:
                parent.children.append(node)
        
        return node

    for res in resources:
        class_path = res.metadata.get('class_path', [])
        if not class_path:
            continue # 或者是挂在默认根节点
        
        # 获取该资源所属的类节点
        parent_node = get_node(class_path)
        parent_node.attributes.append(res)

    return list(root_map.values())

# --- 图片处理工具 ---
class ImageProcessor:
    @staticmethod
    def save_crop(source_path: str, rect: Tuple[float, float, float, float], output_dir: str, prefix: str) -> str:
        """
        裁剪图片并保存。
        rect: (x1, y1, x2, y2)
        Returns: 保存后的绝对路径
        """
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        img = cv2.imread(source_path)
        if img is None:
            raise InvalidImageError(f"Could not read image: {source_path}")

        x1, y1, x2, y2 = map(int, rect)
        # 边界检查
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        clip = img[y1:y2, x1:x2]
        filename = f"{prefix}_{uuid.uuid4().hex[:8]}.png"
        out_path = output_dir_path / filename

        cv2.imwrite(str(out_path), clip)
        return str(out_path.resolve())

    @staticmethod
    def save_crop_to_path(source_path: str, rect: Tuple[float, float, float, float], output_dir: str, filename: str) -> str:
        """裁剪图片并使用固定文件名保存。

        主要用于 Meta V2 ImageProp 导出的切片命名：<definitionId>_<propKey>.png。
        """
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        img = cv2.imread(source_path)
        if img is None:
            raise InvalidImageError(f"Could not read image: {source_path}")

        x1, y1, x2, y2 = map(int, rect)
        h, w = img.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        clip = img[y1:y2, x1:x2]
        out_path = output_dir_path / filename
        cv2.imwrite(str(out_path), clip)
        return str(out_path.resolve())

    @staticmethod
    def copy_image(source_path: str, output_dir: str, new_name: str | None = None) -> str:
        """复制图片并返回绝对路径"""
        import shutil
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)

        if new_name is None:
            new_name = Path(source_path).name

        dst_path = output_dir_path / new_name
        shutil.copy(source_path, str(dst_path))
        return str(dst_path.resolve())