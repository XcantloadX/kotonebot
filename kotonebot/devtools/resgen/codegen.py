import os
from typing import Any, List

from .core import CodeWriter, ClassNode, ResourceNode, ImageAsset, BoxData, PointData, PrefabData
from .utils import unify_path

class StandardGenerator:
    """标准 Python 生成器基类"""
    
    def __init__(self, production: bool = False, ide_type: str | None = None):
        self.writer = CodeWriter()
        self.production = production
        self.ide_type = ide_type

    def generate(self, root_nodes: List[ClassNode]) -> str:
        self.render_header()
        self.writer.write_empty_line()
        for node in root_nodes:
            self.render_class(node)
        return self.writer.get_content()

    def render_header(self):
        """可被重写：文件头"""
        w = self.writer
        if not self.production:
            w.write("#######           图片资源文件         #######")
            w.write("#######     此文件为自动生成，请勿编辑    #######")
            w.write("####### AUTO GENERATED. DO NOT EDIT. #######")
        w.write("from kotonebot.backend.core import Image, HintBox, HintPoint")

    def render_class(self, node: ClassNode):
        """递归渲染类"""
        w = self.writer
        w.write(f"class {node.name}:")
        with w.indent():
            if node.is_empty():
                w.write("pass")
                return

            # 1. 渲染属性
            for attr in node.attributes:
                self.render_attribute(attr)
                w.write_empty_line()

            # 2. 渲染子类
            for child in node.children:
                self.render_class(child)
                w.write_empty_line()

    def render_attribute(self, attr: ResourceNode):
        """渲染单个属性。根据 attr.value 的 IR 类型生成对应的代码字符串。"""
        val = attr.value
        code_str = ""

        if isinstance(val, ImageAsset):
            # 使用相对名作为资源引用（保留原来的 sprite_path 风格）
            rel = os.path.basename(val.path)
            code_str = f'Image(path=sprite_path("{rel}"))'
        elif isinstance(val, BoxData):
            code_str = (f'HintBox(x1={val.x1}, y1={val.y1}, x2={val.x2}, y2={val.y2}, '
                        f'source_resolution=({val.resolution[0]}, {val.resolution[1]}))')
        elif isinstance(val, PointData):
            code_str = f'HintPoint(x={val.x}, y={val.y})'
        else:
            # fallback: str 转换
            code_str = str(val)

        self.writer.write(f"{attr.name} = {code_str}")
        if not self.production:
            self.render_docstring(attr)

    def render_docstring(self, attr: ResourceNode):
        """渲染 Docstring，包含图片标签生成逻辑"""
        w = self.writer
        base_doc = attr.docstring
        
        # 构造 HTML 图片标签
        img_tags = ""
        # 1. 当前资源图片
        if 'abs_path' in attr.metadata:
            img_tags += self._make_img_tag(attr.metadata['abs_path'], attr.metadata.get('display_name', 'Img')) + '\\n'
        elif 'preview_path' in attr.metadata:
             img_tags += self._make_img_tag(attr.metadata['preview_path'], "Preview") + '\\n'
        
        # 2. 原始大图 (可选)
        if 'origin_file' in attr.metadata:
             img_tags += "\nOriginal:\n" + self._make_img_tag(attr.metadata['origin_file'], "Original", height="200")

        full_doc = f"{base_doc}\n\n{img_tags}"
        
        # 写入
        w.write('"""')
        for line in full_doc.split('\n'):
            w.write(line)
        w.write('"""')

    def _make_img_tag(self, path: str, title: str, height: str = "") -> str:
        path = unify_path(path)
        # 简单的 IDE 适配逻辑
        if self.ide_type == 'vscode':
            # VSCode 需要转义
            path = path.replace('\\', '\\\\')
            return f'<img src="vscode-file://vscode-app/{path}" title="{title}" height="{height}" />'
        elif self.ide_type == 'pycharm':
            return f'.. image:: http://localhost:6532/image?path={path}'
        else:
            return f'<img src="file:///{path}" title="{title}" height="{height}" />'
        

class EntityGenerator(StandardGenerator):
    """
    KotoneBot 实体代码生成器。
    
    输出规范:
    1. Template (图片) -> 生成继承自 TemplateMatchPrefab 的嵌套类。
    2. HintBox/Point -> 生成类的静态属性实例。
    """

    def render_header(self):
        w = self.writer
        w.write("#######           实体资源文件         #######")
        w.write("#######    此文件为自动生成，请勿编辑     #######")
        w.write("####### AUTO GENERATED. DO NOT EDIT. #######")
        w.write_empty_line()
        w.write("from kotonebot.core import TemplateMatchPrefab")
        w.write("from kotonebot.primitives import Image, Rect")
        w.write("from kotonebot.backend.core import HintBox, HintPoint")
        w.write_empty_line()

    def render_attribute(self, attr: ResourceNode):
        """
        核心分发逻辑：
        根据 ResourceNode 携带的 value 类型，决定生成策略。
        """
        data = attr.value

        if isinstance(data, ImageAsset):
            self._render_prefab_class(attr, data)
        elif isinstance(data, PrefabData):
            self._render_custom_prefab_class(attr, data)
        elif isinstance(data, (BoxData, PointData)):
            self._render_primitive_assignment(attr, data)
        else:
            # 兜底：如果 value 是未知类型或纯字符串，回退到默认赋值
            super().render_attribute(attr)

    def _render_custom_prefab_class(self, node: ResourceNode, data: PrefabData):
        """
        渲染自定义基类的 Prefab 嵌套类
        """
        w = self.writer
        class_name = node.name
        base_class = data.class_name
        
        # 1. 类定义
        w.write(f"class {class_name}({base_class}):")
        
        with w.indent():
            # 2. Docstring
            if not self.production:
                self.render_docstring(node)
            
            # 3. template 属性 (Image)
            clean_path = unify_path(data.image.path)
            w.write(f'template = Image(file_path="{clean_path}")')
            
            # 4. display_name 属性
            display_name = node.metadata.get('display_name', node.name)
            w.write(f'display_name = "{display_name}"')
            
            # 5. _orig_rect 属性
            if data.image.rect:
                x1, y1, x2, y2 = data.image.rect
                w.write(f"_orig_rect = Rect(x={x1}, y={y1}, w={x2-x1}, h={y2-y1})")
            else:
                w.write("_orig_rect = None")

    def _render_prefab_class(self, node: ResourceNode, data: ImageAsset):
        """
        渲染 TemplateMatchPrefab 嵌套类
        """
        w = self.writer
        class_name = node.name
        
        # 1. 类定义
        w.write(f"class {class_name}(TemplateMatchPrefab):")
        
        with w.indent():
            # 2. Docstring
            if not self.production:
                self.render_docstring(node)
            
            # 3. template 属性 (Image)
            # 确保路径分隔符统一，避免 Windows 反斜杠问题
            clean_path = unify_path(data.path)
            w.write(f'template = Image(file_path="{clean_path}")')
            
            # 4. display_name 属性
            # 优先从 metadata 取，如果没有则用变量名
            display_name = node.metadata.get('display_name', node.name)
            w.write(f'display_name = "{display_name}"')
            
            # 5. _orig_rect 属性 (用于调试或记录原始位置)
            if data.rect:
                x1, y1, x2, y2 = data.rect
                w.write(f"_orig_rect = Rect(x={x1}, y={y1}, w={x2-x1}, h={y2-y1})")
            else:
                w.write("_orig_rect = None")

    def _render_primitive_assignment(self, node: ResourceNode, data: Any):
        """
        渲染 HintBox 或 HintPoint 的赋值语句
        Example: MyBox = HintBox(x1=1, y1=2...)
        """
        # 1. 生成 Docstring (如果是非生产模式)
        if not self.production:
            # 对于属性赋值，docstring 通常写在上方，或者不写
            # Python 标准是将 docstring 写在赋值语句下方，但这在类属性中不太常见
            # 这里我们选择不为 HintBox 生成复杂的 docstring，或者作为注释生成
            pass 

        # 2. 构造构造函数字符串
        constructor_str = ""
        
        if isinstance(data, BoxData):
            constructor_str = (
                f"HintBox("
                f"x1={data.x1}, y1={data.y1}, "
                f"x2={data.x2}, y2={data.y2}, "
                f"source_resolution={data.resolution})"
            )
            
        elif isinstance(data, PointData):
            constructor_str = f"HintPoint(x={data.x}, y={data.y})"

        # 3. 写入代码
        self.writer.write(f"{node.name} = {constructor_str}")

    def render_docstring(self, attr: ResourceNode):
        """
        重写文档渲染逻辑，支持 markdown 图片预览
        """
        w = self.writer
        lines = []
        
        # 基础描述
        if attr.docstring:
            lines.extend(attr.docstring.split('\n'))
            
        # 图片预览 (仅当它是 ImageAsset 且有绝对路径用于 IDE 预览时)
        # 注意：这里的 abs_path 需要 Parser 在 metadata 里额外塞进去，
        # 因为 ImageAsset.path 可能已经是相对路径了。
        if self.ide_type and isinstance(attr.value, ImageAsset):
            preview_path = attr.metadata.get('origin_file') or attr.metadata.get('abs_path')
            if preview_path:
                lines.append("")
                lines.append(self._make_img_tag(preview_path, "Preview"))

        if not lines:
            return

        w.write('"""')
        for line in lines:
            w.write(line)
        w.write('"""')