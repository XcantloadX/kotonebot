import os
from typing import List

from .core import CodeWriter, ClassNode, ResourceNode, ImageAsset, BoxData, PointData
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