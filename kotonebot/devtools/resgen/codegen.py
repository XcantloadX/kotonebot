import os
from typing import Any, Callable, Protocol

from .core import CodeWriter, ClassNode, ResourceNode, ImageAsset, BoxData, RectData, PointData, PrefabData
from .utils import to_camel_case, unify_path


class MissingResourceVariant(Exception):
    """当请求的资源变体不存在时抛出。"""

    def __init__(self, variant_name: str, resource_class: str):
        self.variant_name = variant_name
        self.resource_class = resource_class
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Unsupported resource variant: {self.variant_name} for {self.resource_class}"

    def __repr__(self) -> str:
        return f"MissingResourceVariant(variant_name={self.variant_name!r}, resource_class={self.resource_class!r})"


class RenderContext:
    """渲染时传递给自定义资源渲染器的辅助对象。"""

    def __init__(self, generator: "StandardGenerator", attr: ResourceNode):
        self.generator = generator
        self.attr = attr

    @property
    def writer(self) -> CodeWriter:
        return self.generator.writer

    def write(self, text: str) -> None:
        self.writer.write(text)

    def write_empty_line(self) -> None:
        self.writer.write_empty_line()

    def path_expr(self, original_path: str, default_expr: str) -> str:
        return self.generator._transform_path(original_path, default_expr)


class PathPolicy(Protocol):
    """生成图片引用的路径表达式策略。"""

    def transform_path(
        self,
        original_path: str,
        default_expr: str,
        *,
        generator: "StandardGenerator",
    ) -> str:
        ...


class DocstringPolicy(Protocol):
    """文档字符串渲染策略。
    
    如果策略处理了输出，返回 True 以跳过默认的文档字符串渲染。
    """

    def render_docstring(self, attr: ResourceNode, *, generator: "StandardGenerator") -> bool:
        ...


class ResourceRenderer(Protocol):
    """资源节点的自定义属性渲染器。"""

    id: str
    render_docstring: bool

    def match(self, attr: ResourceNode, *, generator: "StandardGenerator") -> bool:
        ...

    def render(self, context: RenderContext) -> None:
        ...


class RendererRegistry:
    """自定义资源渲染器的注册表。
    
    渲染器按注册顺序的逆序进行匹配，这样后注册的渲染器可以覆盖先注册的，
    而不需要替换所有默认渲染器。
    """

    def __init__(self):
        self._renderers: list[ResourceRenderer] = []
        self._renderer_indexes: dict[str, int] = {}

    def register(self, renderer: ResourceRenderer, *, replace: bool = False) -> None:
        renderer_id = renderer.id
        if renderer_id in self._renderer_indexes:
            if not replace:
                raise ValueError(f"Renderer '{renderer_id}' already registered")
            index = self._renderer_indexes[renderer_id]
            self._renderers[index] = renderer
            return
        self._renderer_indexes[renderer_id] = len(self._renderers)
        self._renderers.append(renderer)

    def resolve(self, attr: ResourceNode, *, generator: "StandardGenerator") -> ResourceRenderer | None:
        for renderer in reversed(self._renderers):
            if renderer.match(attr, generator=generator):
                return renderer
        return None

class StandardGenerator:
    """标准 Python 生成器基类"""
    
    def __init__(self, production: bool = False, ide_type: str | None = None,
                 path_transformer: Callable[[str], str] | None = None,
                 renderer_registry: RendererRegistry | None = None,
                 path_policy: PathPolicy | None = None,
                 docstring_policy: DocstringPolicy | None = None):
        self.writer = CodeWriter()
        self.production = production
        self.ide_type = ide_type
        self.path_transformer = path_transformer
        self.renderer_registry = renderer_registry or RendererRegistry()
        self.path_policy = path_policy
        self.docstring_policy = docstring_policy

    def register_renderer(self, renderer: ResourceRenderer, *, replace: bool = False) -> None:
        self.renderer_registry.register(renderer, replace=replace)

    def _render_with_custom_renderer(self, attr: ResourceNode) -> bool:
        renderer = self.renderer_registry.resolve(attr, generator=self)
        if renderer is None:
            return False

        renderer.render(RenderContext(generator=self, attr=attr))
        if not self.production and getattr(renderer, "render_docstring", True):
            self.render_docstring(attr)
        return True

    def _transform_path(self, original_path: str, default_expr: str) -> str:
        """返回图片路径的代码表达式。
        
        如果提供了 `path_transformer`，则使用原始路径调用它，
        并将其返回值原样作为要生成的表达式。否则回退到 `default_expr`。
        """
        if self.path_policy:
            return self.path_policy.transform_path(
                original_path,
                default_expr,
                generator=self,
            )
        if self.path_transformer:
            return self.path_transformer(original_path)
        return default_expr

    def generate(self, root_nodes: list[ClassNode]) -> str:
        self.render_header()
        self.writer.write_empty_line()
        for node in root_nodes:
            self.render_class(node, class_path=node.name)
        return self.writer.get_content()

    def render_header(self):
        """可被重写：文件头"""
        w = self.writer
        if not self.production:
            w.write("#######           图片资源文件         #######")
            w.write("#######     此文件为自动生成，请勿编辑    #######")
            w.write("####### AUTO GENERATED. DO NOT EDIT. #######")
        w.write("from kotonebot.backend.core import Image, HintBox, HintPoint")
        w.write("from kotonebot.primitives import ImageSlice, Rect")

    def render_class(self, node: ClassNode, class_path: str = ""):
        """递归渲染类"""
        w = self.writer
        w.write(f"class {node.name}:")
        with w.indent():
            if node.is_empty():
                w.write("pass")
                return

            # 1. 渲染属性
            for attr in node.attributes:
                self.render_attribute(attr, class_path=class_path)
                w.write_empty_line()

            # 2. 渲染子类
            for child in node.children:
                child_path = f"{class_path}.{child.name}" if class_path else child.name
                self.render_class(child, class_path=child_path)
                w.write_empty_line()

    def render_attribute(self, attr: ResourceNode, class_path: str = ""):
        """渲染单个属性。根据 attr.value 的 IR 类型生成对应的代码字符串。"""
        if self._render_with_custom_renderer(attr):
            return

        val = attr.value
        code_str = ""

        if isinstance(val, ImageAsset):
            rect_expr: str
            if val.rect is not None:
                x1, y1, x2, y2 = val.rect
                width = x2 - x1
                height = y2 - y1
                rect_expr = f"Rect(x={x1}, y={y1}, w={width}, h={height})"
            else:
                rect_expr = "None"
            # 使用相对名作为资源引用（保留原来的 sprite_path 风格）
            rel = os.path.basename(val.path)
            display_name = attr.metadata.get('display_name', attr.name)
            default = f'sprite_path("{rel}")'
            path_expr = self._transform_path(val.path, default)
            code_str = f'ImageSlice(file_path={path_expr}, name="{display_name}", slice_rect={rect_expr})'
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
        if self.docstring_policy and self.docstring_policy.render_docstring(attr, generator=self):
            return

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

    def __init__(
        self,
        production: bool = False,
        ide_type: str | None = None,
        path_transformer: Callable[[str], str] | None = None,
        renderer_registry: RendererRegistry | None = None,
        path_policy: PathPolicy | None = None,
        docstring_policy: DocstringPolicy | None = None,
        default_variant: str = "",
    ):
        super().__init__(
            production=production,
            ide_type=ide_type,
            path_transformer=path_transformer,
            renderer_registry=renderer_registry,
            path_policy=path_policy,
            docstring_policy=docstring_policy,
        )
        if not isinstance(default_variant, str):
            raise ValueError("default_variant must be str")
        self.default_variant = default_variant

    def render_header(self):
        w = self.writer
        w.write("#######           实体资源文件         #######")
        w.write("#######    此文件为自动生成，请勿编辑     #######")
        w.write("####### AUTO GENERATED. DO NOT EDIT. #######")
        w.write_empty_line()
        w.write("from contextvars import ContextVar")
        w.write("from kotonebot.core import TemplateMatchPrefab")
        w.write("from kotonebot.primitives import Image, ImageSlice, Point, Rect")
        w.write("from kotonebot.backend.core import HintBox, HintPoint")
        w.write("from kotonebot.errors import MissingResourceVariant")
        w.write_empty_line()
        w.write(f"current_variant = ContextVar('current_variant', default={self.default_variant!r})")
        w.write_empty_line()
        w.write("class classproperty:")
        with w.indent():
            w.write("def __init__(self, func):")
            with w.indent():
                w.write("self._func = func")
            w.write("def __get__(self, _, owner):")
            with w.indent():
                w.write("return self._func(owner)")
        w.write_empty_line()

    def render_attribute(self, attr: ResourceNode, class_path: str = ""):
        """
        核心分发逻辑：
        根据 ResourceNode 携带的 value 类型，决定生成策略。
        """
        if self._render_with_custom_renderer(attr):
            return

        data = attr.value

        if isinstance(data, ImageAsset):
            self._render_prefab_class(attr, data, class_path=class_path)
        elif isinstance(data, PrefabData):
            self._render_custom_prefab_class(attr, data, class_path=class_path)
        elif isinstance(data, (BoxData, PointData)):
            self._render_primitive_assignment(attr, data)
        else:
            # 兜底：如果 value 是未知类型或纯字符串，回退到默认赋值
            super().render_attribute(attr)

    def _render_custom_prefab_class(self, node: ResourceNode, data: PrefabData, class_path: str = ""):
        """
        渲染自定义基类的 Prefab 嵌套类
        """
        w = self.writer
        class_name = node.name
        full_class_path = f"{class_path}.{class_name}" if class_path else class_name
        resource_class_repr = f"<class '{full_class_path}'>"
        if not getattr(data, 'prefab_id', None):
            raise ValueError(f"PrefabData missing prefab_id for node {node.name}")
        base_class = data.prefab_id

        # 1. 类定义
        w.write(f"class {class_name}({base_class}):")
        
        with w.indent():
            # 2. Docstring
            if not self.production:
                self.render_docstring(node)

            # display_name 属性（用于 Image.name 参数）
            display_name = node.metadata.get('display_name', node.name)

            if data.variant_props is not None:
                variant_display_names = node.metadata.get("variant_display_names") or {}
                variant_keys = sorted(data.variant_props.keys())
                dispatch_fields: set[str] = {"display_name", "template"}
                for variant in variant_keys:
                    inner_class_name = self._variant_inner_class_name(variant)
                    props = data.variant_props[variant]
                    self._validate_prefab_props(
                        prefab_id=data.prefab_id,
                        props=props,
                        node_name=node.name,
                        variant_name=variant,
                    )
                    dispatch_fields.update(props.keys())
                    w.write(f"class {inner_class_name}:")
                    with w.indent():
                        variant_display_name = variant_display_names.get(variant, display_name)
                        self._render_prefab_prop_assignments(
                            props=props,
                            display_name=variant_display_name,
                        )
                        w.write(f'display_name = "{variant_display_name}"')
                        if "template" not in props:
                            primary_image = props.get("templateImage") or props.get("image")
                            if not isinstance(primary_image, ImageAsset):
                                for value in props.values():
                                    if isinstance(value, ImageAsset):
                                        primary_image = value
                                        break
                            if isinstance(primary_image, ImageAsset):
                                template_expr = self._image_asset_expr(primary_image, variant_display_name)
                                w.write(f"template = {template_expr}")
                    w.write_empty_line()

                inner_class_names = [self._variant_inner_class_name(v) for v in variant_keys]
                type_union = " | ".join(f"type[{name}]" for name in inner_class_names)
                w.write(f"_variant_classes: dict[str, {type_union}] = {{")
                with w.indent():
                    for variant in variant_keys:
                        inner_class_name = self._variant_inner_class_name(variant)
                        w.write(f"'{variant}': {inner_class_name},")
                w.write("}")
                w.write_empty_line()
                w.write("@classmethod")
                w.write("def _get_variant_class(cls):")
                with w.indent():
                    w.write("variant = current_variant.get()")
                    w.write("target = cls._variant_classes.get(variant)")
                    w.write("if target is None:")
                    with w.indent():
                        w.write(f"raise MissingResourceVariant(variant, {resource_class_repr!r})")
                    w.write("return target")
                w.write_empty_line()

                for field in sorted(dispatch_fields):
                    w.write("@classproperty")
                    w.write(f"def {field}(cls):")
                    with w.indent():
                        w.write("target = cls._get_variant_class()")
                        w.write(f"return target.{field}")
                    w.write_empty_line()
                return

            # 3. If PrefabData has an image, expose it as `template` for convenience
            #    so simple prefab definitions that only provide an image still
            #    produce a usable `template` attribute on the generated class.
            # Only expose `template` automatically for prefabs that originated
            # from a single meta file (isSimple == True). Multi prefabs may
            # define images via props and should not implicitly expose `template`.
            if data.image is not None and node.metadata.get('isSimple'):
                rect_expr: str
                if data.image.rect is not None:
                    x1, y1, x2, y2 = data.image.rect
                    ix1, iy1, ix2, iy2 = map(int, (x1, y1, x2, y2))
                    rect_width = ix2 - ix1
                    rect_height = iy2 - iy1
                    rect_expr = f"Rect(x={ix1}, y={iy1}, w={rect_width}, h={rect_height})"
                else:
                    rect_expr = "None"

                clean_path = unify_path(data.image.path)
                default = f'"{clean_path}"'
                path_expr = self._transform_path(clean_path, default)
                w.write(f'template = ImageSlice(file_path={path_expr}, name="{display_name}", slice_rect={rect_expr})')
                w.write_empty_line()
            
            self._validate_prefab_props(
                prefab_id=data.prefab_id,
                props=data.props,
                node_name=node.name,
                variant_name=None,
            )

            # 4. V2 Props
            self._render_prefab_prop_assignments(
                props=data.props,
                display_name=display_name,
            )
            
            # 5. display_name 属性
            display_name = node.metadata.get('display_name', node.name)
            w.write(f'display_name = "{display_name}"')

    def _image_asset_expr(self, value: ImageAsset, display_name: str) -> str:
        rect_expr: str
        if value.rect is not None:
            x1, y1, x2, y2 = value.rect
            ix1, iy1, ix2, iy2 = map(int, (x1, y1, x2, y2))
            rect_width = ix2 - ix1
            rect_height = iy2 - iy1
            rect_expr = f"Rect(x={ix1}, y={iy1}, w={rect_width}, h={rect_height})"
        else:
            rect_expr = "None"
        clean_path = unify_path(value.path)
        default = f'"{clean_path}"'
        path_expr = self._transform_path(clean_path, default)
        return f'ImageSlice(file_path={path_expr}, name="{display_name}", slice_rect={rect_expr})'

    def _render_prefab_prop_assignments(self, *, props: dict[str, Any], display_name: str) -> None:
        for key, value in props.items():
            if isinstance(value, ImageAsset):
                self.writer.write(f"{key} = {self._image_asset_expr(value, display_name)}")
                continue
            if isinstance(value, RectData):
                width = int(value.x2) - int(value.x1)
                height = int(value.y2) - int(value.y1)
                self.writer.write(
                    f"{key} = Rect(x={int(value.x1)}, y={int(value.y1)}, w={width}, h={height})"
                )
                continue
            if isinstance(value, PointData):
                self.writer.write(
                    f"{key} = Point(x={value.x}, y={value.y})"
                )
                continue
            if isinstance(value, (int, float, str, bool)):
                self.writer.write(f"{key} = {repr(value)}")
                continue
            if value is None:
                self.writer.write(f"{key} = None")
                continue
            if isinstance(value, dict):
                self.writer.write(f"{key} = {repr(value)}")
                continue
            if isinstance(value, list):
                self.writer.write(f"{key} = {repr(value)}")
                continue
            raise ValueError(f"Unsupported prefab prop value type for '{key}': {type(value).__name__}")

    def _validate_prefab_props(
        self,
        *,
        prefab_id: str,
        props: dict[str, Any],
        node_name: str,
        variant_name: str | None,
    ) -> None:
        if prefab_id != "TemplateMatchPrefab":
            return
        allowed_fields = {
            "template",
            "templateImage",
            "image",
            "region",
            "threshold",
            "colored",
            "fixed",
        }
        context = f"{node_name}[{variant_name}]" if variant_name is not None else node_name
        for key, value in props.items():
            if key not in allowed_fields:
                raise ValueError(f"Unsupported field '{key}' for TemplateMatchPrefab in '{context}'")
            if key in {"template", "templateImage", "image"} and not isinstance(value, ImageAsset):
                raise ValueError(
                    f"Field '{key}' for TemplateMatchPrefab must be ImageAsset in '{context}'"
                )
            if key == "region" and value is not None and not isinstance(value, RectData):
                raise ValueError(
                    f"Field 'region' for TemplateMatchPrefab must be RectData or None in '{context}'"
                )
            if key == "threshold" and not isinstance(value, (int, float)):
                raise ValueError(
                    f"Field 'threshold' for TemplateMatchPrefab must be int|float in '{context}'"
                )
            if key in {"colored", "fixed"} and not isinstance(value, bool):
                raise ValueError(
                    f"Field '{key}' for TemplateMatchPrefab must be bool in '{context}'"
                )

    def _variant_inner_class_name(self, variant: str) -> str:
        if variant == "":
            return "Base"
        return to_camel_case(variant)

    def _render_prefab_class(self, node: ResourceNode, data: ImageAsset, class_path: str = ""):
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
            rect_expr: str
            if data.rect is not None:
                x1, y1, x2, y2 = data.rect
                ix1, iy1, ix2, iy2 = map(int, (x1, y1, x2, y2))
                rect_width = ix2 - ix1
                rect_height = iy2 - iy1
                rect_expr = f"Rect(x={ix1}, y={iy1}, w={rect_width}, h={rect_height})"
            else:
                rect_expr = "None"
            display_name = node.metadata.get('display_name', node.name)
            default = f'"{clean_path}"'
            path_expr = self._transform_path(clean_path, default)
            w.write(f'template = ImageSlice(file_path={path_expr}, name="{display_name}", slice_rect={rect_expr})')
            
            # 4. display_name 属性
            # 优先从 metadata 取，如果没有则用变量名
            w.write(f'display_name = "{display_name}"')

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
