import os
import json
import uuid
from typing import List, Dict, Any
from .core import SchemaParser, ResourceNode, ImageAsset, BoxData, PointData, PrefabData
from .utils import to_camel_case, ImageProcessor
from .validation import MetaValidationError, detect_and_validate_meta_schema

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
        # 使用统一的 schema 检测逻辑：只有在结构被认为是合法的
        # simple/complex meta 时才返回 True。
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            detect_and_validate_meta_schema(data)
            return True
        except (json.JSONDecodeError, OSError, MetaValidationError):
            return False

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        """
        解析 V1 Schema。
        Context 需要包含: 'output_img_dir' (图片输出目录)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        schema_info = detect_and_validate_meta_schema(data)

        output_dir = context.get('output_img_dir', 'tmp')
        png_file = file_path.replace('.json', '')
        resources: List[ResourceNode] = []

        # --- 简单 schema: 单一 definition + isSimple: true ---
        if schema_info.format == "simple":
            definition = data["definition"]
            return self._parse_simple_definition(definition, png_file, output_dir, context)

        # --- 复杂 schema: 原有 definitions + annotations ---
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


    def _parse_simple_definition(
        self,
        definition: Dict[str, Any],
        png_file: str,
        output_dir: str,
        context: Dict[str, Any],
    ) -> List[ResourceNode]:
        """Parse a single-definition simple meta file.

        当前仅支持 `type == "template"` 与 `type == "prefab"` 的简单资源：
        - 不依赖 annotations；
        - 直接复制整张图片作为模板或 prefab 图像来源。

        针对简单格式：
        - `name` 与 `displayName` 均可为空或缺省；
        - 当为空时，按照原有简单格式（BasicSpriteParser）的逻辑自动推导：
          * name: 由文件名转换得到的 CamelCase 属性名；
          * displayName: 使用原始文件名（含扩展名）。

        其他类型在缺少 annotations 的情况下暂不支持，会抛出 MetaValidationError，
        以避免产生语义不明确的结果。
        """
        def_type = definition.get("type")
        if def_type not in ("template", "prefab"):
            raise MetaValidationError(
                f"Simple meta currently only supports type 'template' or 'prefab', got '{def_type}'."
            )

        # --- 基于文件路径的默认推导（复用 BasicSpriteParser 逻辑） ---
        root_scan_path = context.get('root_scan_path', '')
        file_name = os.path.basename(png_file)
        name_no_ext = file_name.replace('.png', '')
        try:
            rel_dir = os.path.dirname(os.path.relpath(png_file, root_scan_path)) if root_scan_path else ''
        except ValueError:
            # os.path.relpath 可能在 root_scan_path 非法时抛错，此时退回空相对目录
            rel_dir = ''

        path_class_path = [
            to_camel_case(p)
            for p in rel_dir.split(os.sep)
            if p and p != '.'
        ]
        path_attr_name = to_camel_case(name_no_ext)
        path_display_name = file_name

        # --- 处理 name（可选） ---
        raw_name = definition.get("name")
        if isinstance(raw_name, str) and raw_name.strip():
            name_parts = raw_name.split('.')
            class_path = [to_camel_case(p) for p in name_parts[:-1]]
            attr_name = name_parts[-1]
        else:
            class_path = path_class_path
            attr_name = path_attr_name

        # --- 处理 displayName（可选） ---
        raw_display_name = definition.get('displayName')
        if isinstance(raw_display_name, str) and raw_display_name.strip():
            display_name = raw_display_name
        else:
            # 没有显式 displayName 时，沿用简单格式原有行为：使用文件名
            display_name = path_display_name

        desc = definition.get('description', '')

        # 复制整张图片作为资源
        img_uuid = str(uuid.uuid4())
        new_name = f"{img_uuid}.png"
        final_path = ImageProcessor.copy_image(png_file, output_dir, new_name)

        metadata = {
            'class_path': class_path,
            'origin_file': os.path.abspath(png_file),
            'abs_path': os.path.abspath(final_path),
            'display_name': display_name,
            'description': desc,
        }

        if def_type == "template":
            node = ResourceNode(
                name=attr_name,
                type='template',
                value=ImageAsset(path=metadata['abs_path']),
                docstring=self._build_docstring(display_name, desc, class_path, metadata['abs_path'], png_file),
                metadata=metadata,
            )
        else:  # prefab
            prefab_def = definition.get("prefab") or {}
            class_name_ref = prefab_def.get("className")
            if not isinstance(class_name_ref, str) or not class_name_ref.strip():
                raise MetaValidationError("Prefab definition missing className")

            node = ResourceNode(
                name=attr_name,
                type='prefab',
                value=PrefabData(
                    image=ImageAsset(path=metadata['abs_path'], rect=None),
                    class_name=class_name_ref,
                ),
                docstring=self._build_docstring(display_name, desc, class_path, metadata['abs_path'], png_file),
                metadata=metadata,
            )

        return [node]


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