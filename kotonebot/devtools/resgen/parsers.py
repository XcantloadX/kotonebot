import os
import json
import uuid
from typing import List, Dict, Any
from .core import SchemaParser, ResourceNode, ImageAsset, BoxData, PointData, PrefabData
from .utils import to_camel_case, ImageProcessor

class ParserRegistry:
    def __init__(self):
        self._parsers: List[SchemaParser] = []

    def register(self, parser: SchemaParser):
        self._parsers.append(parser)

    def parse_file(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser.parse(file_path, context)
        return []


class KotoneV1Parser(SchemaParser):
    def can_parse(self, file_path: str) -> bool:
        if not file_path.endswith('.png.json'):
            return False
        # 简单检查内容特征
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return "definitions" in data and "annotations" in data
        except:  # noqa: E722
            return False

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        """
        解析 V1 Schema。
        Context 需要包含: 'output_img_dir' (图片输出目录)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        output_dir = context.get('output_img_dir', 'tmp')
        png_file = file_path.replace('.json', '')
        resources = []
        
        # 建立 id -> annotation 的映射
        annotations = {a['id']: a for a in data.get('annotations', [])}
        
        for def_id, definition in data.get('definitions', {}).items():
            name_parts = definition['name'].split('.')
            class_path = [to_camel_case(p) for p in name_parts[:-1]]
            attr_name = name_parts[-1]
            display_name = definition.get('displayName', attr_name)
            desc = definition.get('description', '')
            def_type = definition['type']
            annot_id = definition.get('annotationId')
            
            # 基础 metadata
            metadata = {
                'class_path': class_path,
                'origin_file': os.path.abspath(png_file),
                'display_name': display_name,
                'description': desc
            }

            if def_id not in annotations and def_type != 'template':
                 # template 类型的 def_id 本身可能不是 annotation id，这里沿用原逻辑
                 # 但实际上原逻辑 template 的 uuid 也就是 annotationId
                 pass

            annotation = annotations.get(annot_id)

            if def_type == 'template':
                # 模板匹配：需要裁剪出模板图
                if annotation and annotation['type'] == 'rect':
                    rect_data = annotation['data']
                    rect = (rect_data['x1'], rect_data['y1'], rect_data['x2'], rect_data['y2'])
                    
                    # 裁剪并保存
                    img_uuid = annot_id
                    save_path = ImageProcessor.save_crop(png_file, rect, output_dir, f"tmpl_{attr_name}")
                    
                    # 重新命名为 uuid.png 以符合 R.py 的引用习惯
                    final_name = f"{img_uuid}.png"
                    final_path = os.path.join(output_dir, final_name)
                    if os.path.exists(save_path) and save_path != final_path:
                         os.rename(save_path, final_path)
                    
                    metadata['abs_path'] = os.path.abspath(final_path)

                    node = ResourceNode(
                        name=attr_name,
                        type='template',
                        value=ImageAsset(path=metadata['abs_path'], rect=rect),
                        docstring=self._build_docstring(display_name, desc, class_path, metadata['abs_path'], png_file),
                        metadata=metadata
                    )
                    resources.append(node)

            elif def_type == 'prefab':
                prefab_def = definition.get('prefab')
                if not prefab_def or not prefab_def.get('className'):
                    raise ValueError(f"Prefab definition {def_id} missing className")
                
                class_name_ref = prefab_def['className']

                if annotation and annotation['type'] == 'rect':
                    rect_data = annotation['data']
                    rect = (rect_data['x1'], rect_data['y1'], rect_data['x2'], rect_data['y2'])
                    
                    # 裁剪并保存
                    img_uuid = annot_id
                    save_path = ImageProcessor.save_crop(png_file, rect, output_dir, f"tmpl_{attr_name}")
                    
                    final_name = f"{img_uuid}.png"
                    final_path = os.path.join(output_dir, final_name)
                    if os.path.exists(save_path) and save_path != final_path:
                         os.rename(save_path, final_path)
                    
                    metadata['abs_path'] = os.path.abspath(final_path)

                    node = ResourceNode(
                        name=attr_name,
                        type='prefab',
                        value=PrefabData(
                            image=ImageAsset(path=metadata['abs_path'], rect=rect),
                            class_name=class_name_ref
                        ),
                        docstring=self._build_docstring(display_name, desc, class_path, metadata['abs_path'], png_file),
                        metadata=metadata
                    )
                    resources.append(node)

            elif def_type == 'hint-box':
                if annotation and annotation['type'] == 'rect':
                    d = annotation['data']
                    # HintBox 需要生成裁剪图用于文档预览，但运行时使用坐标
                    crop_path = ImageProcessor.save_crop(png_file, (d['x1'], d['y1'], d['x2'], d['y2']), os.path.join(output_dir, 'preview'), f"hb_{attr_name}")
                    metadata['preview_path'] = crop_path
                    
                    # HACK: 硬编码分辨率 720x1280，实际应从 content 读取
                    node = ResourceNode(
                        name=attr_name,
                        type='hint-box',
                        value=BoxData(x1=int(d['x1']), y1=int(d['y1']), x2=int(d['x2']), y2=int(d['y2'])),
                        docstring=self._build_docstring(display_name, desc, class_path, crop_path, png_file),
                        metadata=metadata
                    )
                    resources.append(node)

            elif def_type == 'hint-point':
                if annotation and annotation['type'] == 'point':
                    d = annotation['data']
                    node = ResourceNode(
                        name=attr_name,
                        type='hint-point',
                        value=PointData(x=int(d['x']), y=int(d['y'])),
                        docstring=self._build_docstring(display_name, desc, class_path, None, png_file),
                        metadata=metadata
                    )
                    resources.append(node)

        return resources

    def _build_docstring(self, name, desc, path_list, img_path, origin_path):
        lines = [
            f"名称：{name}\\n",
            f"描述：{desc}\\n",
            f"模块：`{'.'.join(path_list)}`\\n"
        ]
        # 注意：这里我们只存放纯文本信息，图片标签的生成留给 Generator
        # 但为了方便，我们把图片路径存入 metadata，Generator 读取 metadata 生成 <img> 标签
        return "\n".join(lines)


# --- 2. Basic Sprite Parser (无 Json 的普通图片) ---

class BasicSpriteParser(SchemaParser):
    def can_parse(self, file_path: str) -> bool:
        # 只有是 png 且没有对应的 json 文件时
        if not file_path.endswith('.png'):
            return False
        if os.path.exists(file_path + '.json'):
            return False
        return True

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        output_dir = context.get('output_img_dir', 'tmp')
        root_scan_path = context.get('root_scan_path', '')
        
        file_name = os.path.basename(file_path)
        name_no_ext = file_name.replace('.png', '')
        
        # 计算 class path: 相对路径文件夹转 CamelCase
        rel_dir = os.path.dirname(os.path.relpath(file_path, root_scan_path))
        class_path = [to_camel_case(p) for p in rel_dir.split(os.sep) if p and p != '.']
        
        # 复制图片
        img_uuid = str(uuid.uuid4())
        new_name = f"{img_uuid}.png"
        final_path = ImageProcessor.copy_image(file_path, output_dir, new_name)
        
        attr_name = to_camel_case(name_no_ext)
        display_name = file_name
        
        metadata = {
            'class_path': class_path,
            'origin_file': os.path.abspath(file_path),
            'abs_path': final_path,
            'display_name': display_name
        }

        doc = f"名称：{display_name}\\n\n模块：`{'.'.join(class_path)}`\\n"

        return [ResourceNode(
            name=attr_name,
            type='template',
            value=ImageAsset(path=final_path),
            docstring=doc,
            metadata=metadata
        )]