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
            info = detect_and_validate_meta_schema(data)
            # 支持 simple 与 v2 两种格式
            return info.format in ("simple", "v2")
        except (json.JSONDecodeError, OSError, MetaValidationError):
            return False

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        """
        解析 V2 格式的 meta。
        Context 需要包含: 'output_img_dir' (图片输出目录)
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        schema_info = detect_and_validate_meta_schema(data)
        output_dir = context.get('output_img_dir', 'tmp')
        png_file = file_path.replace('.json', '')

        if schema_info.format == "simple":
            definition = data.get("definition")
            if not isinstance(definition, dict):
                raise MetaValidationError("Simple meta missing 'definition' object")
            return self._parse_simple_definition(definition, png_file, output_dir, context)

        if schema_info.format == "v2":
            return self._parse_v2_schema(data, png_file, output_dir, context)

        raise MetaValidationError(f"KotoneV1Parser cannot parse meta format: {schema_info.format}")

    def _parse_v2_schema(self, data: Dict[str, Any], png_file: str, output_dir: str, context: Dict[str, Any]) -> List[ResourceNode]:
        resources: List[ResourceNode] = []
        definitions = data.get('definitions', {})
        
        for def_id, definition in definitions.items():
            def_type = definition['type']
            name = definition.get('name')
            
            if not name:
                continue
                
            name_parts = name.split('.')
            class_path = [to_camel_case(p) for p in name_parts[:-1]]
            attr_name = name_parts[-1]
            display_name = definition.get('displayName', attr_name)
            desc = definition.get('description', '')
            
            metadata = {
                'class_path': class_path,
                'origin_file': os.path.abspath(png_file),
                'display_name': display_name,
                'description': desc
            }
            
            props = definition.get('props', {})
            
            if def_type == 'template':
                target_prop = None
                target_key = None

                for k, v in props.items():
                    if isinstance(v, dict) and v.get('kind') == 'image':
                        target_prop = v
                        target_key = k
                        break

                if not target_prop:
                    for k, v in props.items():
                        if isinstance(v, dict) and v.get('kind') == 'rect':
                            target_prop = v
                            target_key = k
                            break

                if target_prop:
                    rect = (target_prop['x1'], target_prop['y1'], target_prop['x2'], target_prop['y2'])
                    final_name = f'{def_id}_{target_key}.png'
                    metadata['abs_path'] = ImageProcessor.save_crop_to_path(png_file, rect, output_dir, final_name)

                    node = ResourceNode(
                        name=attr_name,
                        type='template',
                        value=ImageAsset(path=metadata['abs_path'], rect=rect),
                        docstring=self._build_docstring(display_name, desc, class_path, metadata['abs_path'], png_file),
                        metadata=metadata
                    )
                    resources.append(node)

            elif def_type == 'prefab':
                prefab_id = definition.get('prefab_id')

                prefab_props = {}
                for k, v in props.items():
                    if isinstance(v, dict) and v.get('kind') == 'image':
                        rect = (v['x1'], v['y1'], v['x2'], v['y2'])
                        final_name = f'{def_id}_{k}.png'
                        path = ImageProcessor.save_crop_to_path(png_file, rect, output_dir, final_name)
                        prefab_props[k] = ImageAsset(path=path, rect=rect)
                    elif isinstance(v, dict) and v.get('kind') == 'rect':
                        # keep rect as dict for now; generator can decide how to emit
                        prefab_props[k] = v
                    elif isinstance(v, dict) and v.get('kind') == 'point':
                        prefab_props[k] = v
                    else:
                        prefab_props[k] = v

                primary_image = prefab_props.get('templateImage') or prefab_props.get('image')
                if not isinstance(primary_image, ImageAsset):
                    for vv in prefab_props.values():
                        if isinstance(vv, ImageAsset):
                            primary_image = vv
                            break

                node = ResourceNode(
                    name=attr_name,
                    type='prefab',
                    value=PrefabData(
                        image=primary_image,
                        prefab_id=prefab_id,
                        props=prefab_props
                    ),
                    docstring=self._build_docstring(display_name, desc, class_path, None, png_file),
                    metadata=metadata
                )
                resources.append(node)

            elif def_type == 'hint-box':
                # 寻找 rect 或 image 类型的 props 来生成 BoxData
                target_prop = None
                for k, v in props.items():
                    if isinstance(v, dict) and v.get('kind') in ('rect', 'image'):
                        target_prop = v
                        break

                if target_prop:
                    rect = (target_prop['x1'], target_prop['y1'], target_prop['x2'], target_prop['y2'])
                    node = ResourceNode(
                        name=attr_name,
                        type='hint-box',
                        value=BoxData(x1=rect[0], y1=rect[1], x2=rect[2], y2=rect[3]),
                        docstring=self._build_docstring(display_name, desc, class_path, None, png_file),
                        metadata=metadata
                    )
                    resources.append(node)

            elif def_type == 'hint-point':
                # 解析 point
                target_prop = None
                for k, v in props.items():
                    if isinstance(v, dict) and v.get('kind') == 'point':
                        target_prop = v
                        break

                if target_prop:
                    pt = (target_prop['x'], target_prop['y'])
                    node = ResourceNode(
                        name=attr_name,
                        type='hint-point',
                        value=PointData(x=pt[0], y=pt[1]),
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
            'isSimple': True,
            'display_name': display_name,
            'description': desc,
        }

        if def_type == "template":
            node = ResourceNode(
                name=attr_name,
                type='template',
                value=ImageAsset(path=metadata['abs_path'], rect=None),
                docstring=self._build_docstring(display_name, desc, class_path, metadata['abs_path'], png_file),
                metadata=metadata,
            )
        else:  # prefab
            prefab_id_ref = definition.get('prefab_id')
            if not isinstance(prefab_id_ref, str) or not prefab_id_ref.strip():
                raise MetaValidationError(f"Prefab definition missing prefab_id in simple meta for {png_file}")

            node = ResourceNode(
                name=attr_name,
                type='prefab',
                value=PrefabData(
                    image=ImageAsset(path=metadata['abs_path'], rect=None),
                    prefab_id=prefab_id_ref,
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
            value=ImageAsset(path=final_path, rect=None),
            docstring=doc,
            metadata=metadata
        )]


