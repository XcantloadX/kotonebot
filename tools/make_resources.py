# 此脚本用于扫描图片资源并自动生成 Python 脚本

from genericpath import isfile
import os
import shutil
import uuid
import jinja2
from typing import Any, TypeGuard, Literal, Union, cast
from dataclasses import dataclass
from dataclasses_json import dataclass_json, DataClassJsonMixin

import cv2
from cv2.typing import MatLike

PATH = '.\\res\\sprites'

SpriteType = Literal['basic', 'metadata']

@dataclass
class Sprite(DataClassJsonMixin):
    """表示一个精灵图像资源及其元数据。"""
    
    type: SpriteType
    uuid: str
    """编译后的 UUID。作为图片名称。"""
    name: str
    """在 R.py 的类中出现的属性名称"""
    display_name: str
    """在调试中显示的名称"""
    class_path: list[str]
    """
    在 R.py 的类中出现的路径。
    例如 ['Common', 'Button'] 会变为 Common.Button。
    不包括属性名。
    """
    rel_path: str
    """相对于项目根目录的路径。用于调试信息的显示"""
    abs_path: str
    """sprite 图片的绝对路径"""
    origin_file: str
    """原始图片的绝对路径"""

@dataclass
class RectPoints(DataClassJsonMixin):
    """表示一个矩形的两个对角点坐标"""
    x1: float
    y1: float
    x2: float
    y2: float

@dataclass
class Point(DataClassJsonMixin):
    """表示一个二维坐标点"""
    x: float
    y: float

@dataclass
class Annotation(DataClassJsonMixin):
    """图像标注数据"""
    id: str
    type: Literal['rect']
    data: RectPoints
    tip: Union[str, None]

@dataclass
class Definition(DataClassJsonMixin):
    """资源定义基类"""
    name: str
    """在 R.py 的类中出现的属性名称"""
    displayName: str
    """在调试器与调试输出中的名称"""
    type: Literal['template', 'ocr', 'color', 'hint-box']
    """标注类型"""
    annotationId: str
    """标注 ID"""

class TemplateDefinition(Definition):
    """模板匹配类型的资源定义"""
    useHintRect: bool
    """
    是否将这个模板的矩形范围作为运行时执行模板寻找函数时的提示范围。
    
    若为 true，则运行时会先在这个范围内寻找，如果没找到，再在整张截图中寻找。
    """

@dataclass
class SpriteMetadata(DataClassJsonMixin):
    """Sprite 元数据，包含标注和定义信息"""
    annotations: list[Annotation]
    definitions: dict[str, Definition]

@dataclass
class OutputClass(DataClassJsonMixin):
    """输出类定义"""
    type: Literal['class']
    name: str
    attributes: 'list[OutputClass | ImageAttribute]'

@dataclass
class ImageAttribute(DataClassJsonMixin):
    """图像属性定义"""
    type: Literal['image']
    name: str
    docstring: str
    value: str


def to_camel_case(s: str) -> str:
    return ''.join(word.capitalize() for word in s.split('_'))

def to_camel_cases(arr: list[str]) -> list[str]:
    return [to_camel_case(s) for s in arr]

def escape(s: str) -> str:
    return s.replace('\\', '\\\\')

def unify_path(path: str) -> str:
    return path.replace('/', '\\')

def scan_png_files(path: str) -> list[str]:
    """扫描所有 PNG 文件"""
    png_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.png'):
                file_path = os.path.join(root, file)
                png_files.append(file_path)
    return png_files

def load_and_copy_meta_data_sprite(root_path: str, png_file: str) -> list[Sprite]:
    """加载 metadata 类型的 sprite"""
    json_path = png_file + '.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        metadata = SpriteMetadata.from_json(f.read())  # 使用 dataclass-json 的解析方法
    # 裁剪并保存图片
    clips: dict[str, str] = {} # id -> 文件路径
    image = cv2.imread(png_file)
    for annotation in metadata.annotations:
        if annotation.type == 'rect':
            rect = annotation.data
            x1, y1, x2, y2 = rect.x1, rect.y1, rect.x2, rect.y2
            clip = image[int(y1):int(y2), int(x1):int(x2)]
            # 保存图片
            if not os.path.exists('tmp'):
                os.makedirs('tmp')
            path = os.path.join('tmp', f'{annotation.id}.png')
            cv2.imwrite(path, clip)
            clips[annotation.id] = path
    # 关联 Definition，创建 Sprite
    sprites: list[Sprite] = []
    for definition in metadata.definitions.values():
        if definition.type != 'template':
            continue
        sprites.append(Sprite(
            type='metadata',
            uuid=definition.annotationId,
            name=to_camel_case(definition.name.split('.')[-1]),
            display_name=definition.displayName,
            class_path=to_camel_cases(definition.name.split('.')[:-1]),
            rel_path=png_file,
            abs_path=os.path.abspath(clips[definition.annotationId]),
            origin_file=os.path.abspath(png_file),
        ))
    return sprites

def load_basic_sprite(root_path: str, png_file: str) -> Sprite:
    """加载 basic 类型的 sprite"""
    file_name = os.path.basename(png_file)
    class_path = os.path.relpath(os.path.dirname(png_file), root_path).split(os.sep)
    class_path = [to_camel_case(c) for c in class_path]
    return Sprite(
        type='basic',
        uuid=str(uuid.uuid4()),
        name=to_camel_case(file_name.replace('.png', '')),
        display_name=file_name,
        class_path=class_path,
        rel_path=png_file,
        abs_path=os.path.abspath(png_file),
        origin_file=os.path.abspath(png_file)
    )

def load_sprites(root_path: str, png_files: list[str]) -> list[Sprite]:
    """"""
    sprites = []
    for file in png_files:
        # 判断类型
        json_path = file + '.json'
        if os.path.exists(json_path):
            sprites.extend(load_and_copy_meta_data_sprite(root_path, file))
        else:
            # continue
            sprites.append(load_basic_sprite(root_path, file))
    return sprites

def make_classes(sprites: list[Sprite], output_path: str) -> list[OutputClass]:
    """根据 Sprite 数据生成 R.py 中的类信息。"""
    # 按照 class_path 对 sprites 进行分组
    class_map: dict[str, OutputClass] = {}
    
    # 创建或获取指定路径的类
    def get_or_create_class(path: list[str]) -> Union[OutputClass, None]:
        if not path:
            return None
        
        class_key = '.'.join(path)
        if class_key in class_map:
            return class_map[class_key]
        
        new_class = OutputClass(
            type='class',
            name=path[-1],
            attributes=[]
        )
        class_map[class_key] = new_class
        return new_class
    
    # 处理每个 sprite
    for sprite in sprites:
        # 获取当前 sprite 的完整路径
        class_path = sprite.class_path
        
        # 创建或获取所有父类
        current_class = None
        for i in range(len(class_path)):
            path = class_path[:i + 1]
            cls = get_or_create_class(path)
            if not cls:
                continue
            
            # 如果这个类还没有被添加到父类的属性中，添加它
            if i > 0:
                parent = get_or_create_class(path[:-1])
                if parent and not any(isinstance(attr, OutputClass) and attr.name == cls.name for attr in parent.attributes):
                    parent.attributes.append(cls)
            
            current_class = cls
        
        # 将 sprite 添加为最后一级类的属性
        if current_class:
            # 创建图片属性
            docstring = (
                f"名称：{sprite.display_name}\\n\n"
                f"路径：{escape(sprite.rel_path)}\\n\n"
                f"模块：`{'.'.join(sprite.class_path)}`\\n\n"
                f'<img src="vscode-file://vscode-app/{escape(sprite.abs_path)}" title="{sprite.display_name}" />\\n\n'
            )
            if sprite.type == 'metadata':
                docstring += (
                    f"原始文件：\\n\n"
                    f"<img src='vscode-file://vscode-app/{escape(sprite.origin_file)}' title='原始文件' width='80%' />"
                )
            img_attr = ImageAttribute(
                type='image',
                name=sprite.name,
                docstring=docstring,
                value=f'image(res_path(r"{output_path}\\{sprite.uuid}.png"))'
            )
            current_class.attributes.append(img_attr)
    
    # 返回顶层类列表
    return [cls for (path, cls) in class_map.items() if path.find('.') == -1]

def copy_sprites(sprites: list[Sprite], output_folder: str) -> list[Sprite]:
    """复制 sprites 图片到目标路径，并输出 R.py"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    for sprite in sprites:
        src_img_path = sprite.abs_path
        img_name = sprite.uuid + '.png'
        dst_img_path = os.path.join(output_folder, img_name)
        shutil.copy(src_img_path, dst_img_path)
        sprite.abs_path = os.path.abspath(dst_img_path)
    return sprites

def indent(text: str, indent: int = 4) -> str:
    """调整文本的缩进"""
    lines = text.split('\n')
    return '\n'.join(' ' * indent + line for line in lines)

if __name__ == '__main__':
    if os.path.exists('res\\sprites_compiled'):
        shutil.rmtree('res\\sprites_compiled')
    path = PATH + '\\jp'
    files = scan_png_files(path)
    sprites = load_sprites(path, files)
    sprites = copy_sprites(sprites, 'res\\sprites_compiled')
    classes = make_classes(sprites, 'res\\sprites_compiled')
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('./tools'))
    env.filters['indent'] = indent
    
    template = env.get_template('R.jinja2')
    with open('./kotonebot/tasks/R.py', 'w', encoding='utf-8') as f:
        f.write(template.render(data=classes))