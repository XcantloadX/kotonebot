import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, cast

from pydantic import BaseModel, Field
from kotonebot.devtools.errors import ValidationError
from kotonebot.devtools.meta import (
    Diagnostic,
    MetaMultiModel,
    ResolvedPrefabVariants,
    build_variant_projection_for_resgen,
    parse_meta_file,
)
from kotonebot.devtools.path_utils import unify_path
from .core import SchemaParser, ResourceNode, ImageAsset, BoxData, RectData, PointData, PrefabData
from .utils import to_camel_case, ImageProcessor
from .validation import MetaValidationError, detect_and_validate_meta_schema

_CTX_VARIANT_GROUP_BY_BASE_KEY = "_variant_group_by_base_key"
_CTX_VARIANT_SKIP_KEYS = "_variant_skip_keys"
_CTX_VARIANT_INCLUDE_BASE = "resgen_include_base_variant"
_CTX_VARIANT_BASE = "_variant_base"


class ResgenProjectContext(BaseModel):
    parser_context: dict[str, Any]
    default_variant: str
    diagnostics: list[Diagnostic] = Field(default_factory=list)





def _meta_to_image_path(meta_path: str) -> str:
    path = Path(meta_path)
    if path.name.endswith(".png.json"):
        return path.with_suffix("").as_posix()
    return meta_path.replace(".json", "")


def build_variant_context(
    meta_files: list[str],
    resource_variants: list[str],
    base_variant: str,
) -> tuple[dict[str, Any], list[Diagnostic]]:
    projection = build_variant_projection_for_resgen(
        meta_files=meta_files,
        resource_variants=resource_variants,
        base_variant=base_variant,
    )

    return (
        {
            "resource_variants": resource_variants,
            _CTX_VARIANT_GROUP_BY_BASE_KEY: projection.variant_group_by_base_key,
            _CTX_VARIANT_SKIP_KEYS: projection.variant_skip_keys,
            _CTX_VARIANT_INCLUDE_BASE: True,
            _CTX_VARIANT_BASE: base_variant,
        },
        projection.diagnostics,
    )


def _load_project(conf_path: str):
    from kotonebot.devtools.project.project import Project
    return Project(conf_path=conf_path)


def _require_resource_path(project: Any) -> str:
    editor_conf = project.conf.editor
    if editor_conf is None or editor_conf.resource_path is None:
        raise ValidationError("editor.resource_path must be configured in pyproject.toml")
    return editor_conf.resource_path


def _build_project_context(
    *,
    project: Any,
    meta_files: list[str],
    include_base_variant: bool,
) -> ResgenProjectContext:
    variant_conf = project.conf.variant
    if variant_conf is None:
        return ResgenProjectContext(parser_context={}, default_variant="", diagnostics=[])
    if variant_conf.variants is None:
        raise ValidationError("variant.variants must be configured in pyproject.toml")
    if variant_conf.base is None:
        raise ValidationError("variant.base must be configured in pyproject.toml")

    parser_context, diagnostics = build_variant_context(meta_files, variant_conf.variants, variant_conf.base)
    parser_context[_CTX_VARIANT_INCLUDE_BASE] = include_base_variant

    default_variant = variant_conf.base

    return ResgenProjectContext(
        parser_context=parser_context,
        default_variant=default_variant,
        diagnostics=diagnostics,
    )


def load_resgen_project_context(
    *,
    meta_files: list[str] | None = None,
    conf_path: str = "./pyproject.toml",
    include_base_variant: bool = True,
) -> ResgenProjectContext:
    project = _load_project(conf_path)
    resolved_meta_files = meta_files
    if resolved_meta_files is None:
        if project.conf.variant is not None:
            from kotonebot.devtools.meta import scan_meta_files
            resource_path = _require_resource_path(project)
            resolved_meta_files = [entry.meta_path for entry in scan_meta_files(Path(resource_path))]
        else:
            resolved_meta_files = []
    return _build_project_context(
        project=project,
        meta_files=resolved_meta_files,
        include_base_variant=include_base_variant,
    )


def load_resgen_runtime_context(
    *,
    conf_path: str = "./pyproject.toml",
    include_base_variant: bool = True,
    output_img_dir: str | None = None,
    root_scan_path: str | None = None,
    meta_files: list[str] | None = None,
) -> ResgenProjectContext:
    project = _load_project(conf_path)
    resolved_root_scan_path = root_scan_path or _require_resource_path(project)
    resolved_output_img_dir = output_img_dir or "tmp"

    resolved_meta_files = meta_files
    if resolved_meta_files is None:
        if project.conf.variant is not None:
            from kotonebot.devtools.meta import scan_meta_files
            resolved_meta_files = [entry.meta_path for entry in scan_meta_files(Path(resolved_root_scan_path))]
        else:
            resolved_meta_files = []

    project_context = _build_project_context(
        project=project,
        meta_files=resolved_meta_files,
        include_base_variant=include_base_variant,
    )
    runtime_context = {
        "output_img_dir": resolved_output_img_dir,
        "root_scan_path": resolved_root_scan_path,
        **project_context.parser_context,
    }
    return ResgenProjectContext(
        parser_context=runtime_context,
        default_variant=project_context.default_variant,
        diagnostics=project_context.diagnostics,
    )


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
        # single/multi meta 时才返回 True。
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            info = detect_and_validate_meta_schema(data)
            if info.format == "multi":
                parse_meta_file(Path(file_path))
            # 支持 single 与 multi 两种格式
            return info.format in ("single", "multi")
        except (json.JSONDecodeError, OSError, MetaValidationError):
            return False
        except ValueError:
            return False

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        """解析多定义 meta（multi）。Context 需要包含: 'output_img_dir'。"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        schema_info = detect_and_validate_meta_schema(data)
        output_dir = context.get('output_img_dir', 'tmp')
        png_file = file_path.replace('.json', '')

        if schema_info.format == "single":
            definition = data.get("definition")
            if not isinstance(definition, dict):
                raise MetaValidationError("Simple meta missing 'definition' object")
            return self._parse_single_definition(definition, png_file, output_dir, context)

        if schema_info.format == "multi":
            multi_data = parse_meta_file(Path(file_path))
            return self._parse_multi_schema(multi_data, file_path, png_file, output_dir, context)

        raise MetaValidationError(f"KotoneV1Parser cannot parse meta format: {schema_info.format}")

    def _parse_multi_schema(self, data: MetaMultiModel, meta_path: str, png_file: str, output_dir: str, context: Dict[str, Any]) -> List[ResourceNode]:
        resources: List[ResourceNode] = []
        definitions = data.definitions
        normalized_meta_path = unify_path(meta_path)
        resource_variants = context.get("resource_variants")
        if resource_variants is not None and not isinstance(resource_variants, list):
            raise ValidationError("resource_variants must be a list[str]")
        include_base_variant = context.get(_CTX_VARIANT_INCLUDE_BASE, True)
        if not isinstance(include_base_variant, bool):
            raise ValidationError(f"{_CTX_VARIANT_INCLUDE_BASE} must be bool")

        raw_variant_group_by_base_key = context.get(_CTX_VARIANT_GROUP_BY_BASE_KEY)
        raw_skipped_variant_keys = context.get(_CTX_VARIANT_SKIP_KEYS)
        raw_base_variant = context.get(_CTX_VARIANT_BASE)
        variant_group_by_base_key: dict[tuple[str, str], ResolvedPrefabVariants]
        skipped_variant_keys: set[tuple[str, str]]
        if raw_variant_group_by_base_key is None or raw_skipped_variant_keys is None:
            if resource_variants is not None:
                if not isinstance(raw_base_variant, str):
                    raise ValidationError(f"{_CTX_VARIANT_BASE} must be str")
                projection = build_variant_projection_for_resgen(
                    meta_files=[meta_path],
                    resource_variants=resource_variants,
                    base_variant=raw_base_variant,
                )
                error_messages = [
                    diag.message
                    for diag in projection.diagnostics
                    if diag.severity == "error"
                ]
                if error_messages:
                    raise ValidationError("; ".join(error_messages))
                variant_group_by_base_key = projection.variant_group_by_base_key
                skipped_variant_keys = projection.variant_skip_keys
            else:
                variant_group_by_base_key = {}
                skipped_variant_keys = set()
        else:
            if not isinstance(raw_variant_group_by_base_key, dict):
                raise ValidationError(f"{_CTX_VARIANT_GROUP_BY_BASE_KEY} must be dict")
            if not isinstance(raw_skipped_variant_keys, set):
                raise ValidationError(f"{_CTX_VARIANT_SKIP_KEYS} must be set")
            variant_group_by_base_key = cast(
                dict[tuple[str, str], ResolvedPrefabVariants],
                raw_variant_group_by_base_key,
            )
            skipped_variant_keys = cast(set[tuple[str, str]], raw_skipped_variant_keys)

        def build_prefab_props(
            definition_id: str,
            props: dict[str, Any],
            *,
            source_png_file: str | None = None,
            file_prefix: str | None = None,
        ) -> dict[str, Any]:
            prefab_props: dict[str, Any] = {}
            crop_source = source_png_file or png_file
            for k, v in props.items():
                if isinstance(v, dict) and v.get('kind') == 'image':
                    rect = (int(v['x1']), int(v['y1']), int(v['x2']), int(v['y2']))
                    image_name_prefix = file_prefix or definition_id
                    final_name = f'{image_name_prefix}_{k}.png'
                    path = ImageProcessor.save_crop_to_path(crop_source, rect, output_dir, final_name)
                    prefab_props[k] = ImageAsset(path=path, rect=rect)
                elif isinstance(v, dict) and v.get('kind') in ('rect', 'point'):
                    if v['kind'] == 'rect':
                        prefab_props[k] = RectData(
                            x1=int(v['x1']),
                            y1=int(v['y1']),
                            x2=int(v['x2']),
                            y2=int(v['y2']),
                        )
                    else:
                        prefab_props[k] = PointData(
                            x=int(v['x']),
                            y=int(v['y']),
                        )
                else:
                    prefab_props[k] = v
            return prefab_props
        
        for def_id, definition in definitions.items():
            if (normalized_meta_path, def_id) in skipped_variant_keys:
                continue
            def_type = definition.type
            name = definition.name
            
            if not name or not def_type:
                continue
                
            name_parts = name.split('.')
            class_path = [to_camel_case(p) for p in name_parts[:-1]]
            attr_name = name_parts[-1]
            display_name = definition.display_name or attr_name
            desc = definition.description or ''
            
            metadata = {
                'class_path': class_path,
                'origin_file': str(Path(png_file).resolve()),
                'display_name': display_name,
                'description': desc
            }
            
            props = definition.props or {}
            
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
                    rect = (int(target_prop['x1']), int(target_prop['y1']), int(target_prop['x2']), int(target_prop['y2']))
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
                prefab_id = definition.prefab_id
                if prefab_id is None:
                    raise ValidationError(f"PrefabData missing prefab_id for node {name}")

                variant_group = variant_group_by_base_key.get((normalized_meta_path, def_id))
                variant_props: dict[str, dict[str, Any]] | None = None
                variant_display_names: dict[str, str] | None = None
                if variant_group is not None:
                    if resource_variants is None:
                        raise ValidationError("resource_variants is required when variant prefab exists")
                    if not isinstance(raw_base_variant, str):
                        raise ValidationError(f"{_CTX_VARIANT_BASE} must be str")
                    variant_props = {}
                    variant_display_names = {}
                    variant_keys = list(resource_variants)
                    if include_base_variant:
                        variant_keys = [raw_base_variant, *variant_keys]
                    base_policy = variant_group.base.definition.variant_policy or {}
                    ignore_error = context.get('ignore_error', False)
                    for variant in variant_keys:
                        merged_key = "" if variant == raw_base_variant else variant
                        if merged_key not in variant_group.merged:
                            # In multi format, exclude means this variant intentionally has no merged output.
                            if merged_key != "" and base_policy.get(variant) == "exclude":
                                continue
                            if ignore_error:
                                print(f'WARN: missing merged variant "{variant}" for prefab "{name}"')
                                # Skip missing variant and continue with next variant
                                continue
                            raise ValidationError(f"missing merged variant '{variant}' for prefab '{name}'")
                        merged_definition = variant_group.merged[merged_key]
                        variant_ref = variant_group.variants.get(merged_key)
                        source_meta_for_variant = variant_ref.meta_path if variant_ref is not None else variant_group.base.meta_path
                        source_png_for_variant = _meta_to_image_path(source_meta_for_variant)
                        variant_file_tag = variant
                        variant_props[variant] = build_prefab_props(
                            def_id,
                            merged_definition.props or {},
                            source_png_file=source_png_for_variant,
                            file_prefix=f"{def_id}_{variant_file_tag}",
                        )
                        variant_display_names[variant] = merged_definition.display_name or attr_name

                prefab_props = build_prefab_props(def_id, props)

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
                        props=prefab_props,
                        variant_props=variant_props,
                    ),
                    docstring=self._build_docstring(display_name, desc, class_path, None, png_file),
                    metadata={
                        **metadata,
                        "variant_display_names": variant_display_names,
                    }
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
                    rect = (int(target_prop['x1']), int(target_prop['y1']), int(target_prop['x2']), int(target_prop['y2']))
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
                    pt = (int(target_prop['x']), int(target_prop['y']))
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


    def _parse_single_definition(
        self,
        definition: Dict[str, Any],
        png_file: str,
        output_dir: str,
        context: Dict[str, Any],
    ) -> List[ResourceNode]:
        """Parse a single-definition meta file.

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
        png_path = Path(png_file)
        file_name = png_path.name
        name_no_ext = file_name.replace('.png', '')
        try:
            rel_dir = Path(png_file).parent.relative_to(root_scan_path).as_posix() if root_scan_path else ''
        except ValueError:
            rel_dir = ''

        path_class_path = [
            to_camel_case(p)
            for p in rel_dir.split('/')
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
            'origin_file': str(Path(png_file).resolve()),
            'abs_path': str(Path(final_path).resolve()),
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
                raise MetaValidationError(f"Prefab definition missing prefab_id in single meta for {png_file}")

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
        if Path(file_path + '.json').exists():
            return False
        return True

    def parse(self, file_path: str, context: Dict[str, Any]) -> List[ResourceNode]:
        output_dir = context.get('output_img_dir', 'tmp')
        root_scan_path = context.get('root_scan_path', '')
        
        p = Path(file_path)
        file_name = p.name
        name_no_ext = file_name.replace('.png', '')
        
        # 计算 class path: 相对路径文件夹转 CamelCase
        rel_dir = p.parent.relative_to(root_scan_path).as_posix()
        class_path = [to_camel_case(p) for p in rel_dir.split('/') if p and p != '.']
        
        # 复制图片
        img_uuid = str(uuid.uuid4())
        new_name = f"{img_uuid}.png"
        final_path = ImageProcessor.copy_image(file_path, output_dir, new_name)
        
        attr_name = to_camel_case(name_no_ext)
        display_name = file_name
        
        metadata = {
            'class_path': class_path,
            'origin_file': str(p.resolve()),
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


