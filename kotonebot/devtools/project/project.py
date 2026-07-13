from pathlib import Path

try:
    from tomllib import loads as toml_loader  # py>=3.11 # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from tomli import loads as toml_loader  # py<3.11

from kotonebot.devtools.errors import ValidationError
from kotonebot.devtools.project.schema import PyProjectData


PYPROJECT_PATH = './pyproject.toml'

class Project:
    def __init__(self, *, conf_path: str = PYPROJECT_PATH) -> None:
        conf_file = Path(conf_path).resolve()
        self.conf_path: str = str(conf_file)
        self.pyproject_root: Path = conf_file.parent
        self.conf: PyProjectData

        self.load()
    
    @property
    def allowed_roots(self) -> list[Path]:
        """
        返回允许访问的根目录列表。

        用于 Devtool 访问文件系统时的安全检查，确保只能访问项目相关的目录。
        """
        resource_root = Path(self.conf.editor.resource_path).resolve() if self.conf.editor and self.conf.editor.resource_path else self.pyproject_root
        return [resource_root, self.pyproject_root / ".kotonebot"]
    
    def load(self) -> None:
        """
        载入项目的配置文件。
        
        :raises FileNotFoundError: 如果配置文件不存在。
        :raises toml.TomlDecodeError: 如果配置文件格式无效。
        """
        conf_dict = toml_loader(Path(self.conf_path).read_text(encoding='utf-8'))

        tool_conf = conf_dict.get('tool', {}).get('kotonebot', {})
        if tool_conf:
            self.conf = PyProjectData.model_validate(tool_conf)
        else:
            self.conf = PyProjectData()
        
        if self.conf.editor and self.conf.editor.resource_path is not None:
            resource_path = Path(self.conf.editor.resource_path).absolute()
            if not resource_path.exists():
                raise FileNotFoundError(
                    f'resource_path does not exist: {resource_path}. '
                    'Please set [tool.kotonebot.editor.resource_path] to a valid path in pyproject.toml.'
                )
            self.conf.editor.resource_path = str(resource_path)
        if self.conf.editor and self.conf.editor.r_file is not None:
            r_file = self.conf.editor.r_file.strip()
            if r_file == "":
                raise ValidationError("editor.r_file cannot be empty")
            resolved_r_file = Path(r_file)
            if not resolved_r_file.is_absolute():
                resolved_r_file = (self.pyproject_root / resolved_r_file).resolve()
            else:
                resolved_r_file = resolved_r_file.resolve()
            if not resolved_r_file.exists():
                raise FileNotFoundError(
                    f'editor.r_file does not exist: {resolved_r_file}. '
                    'Please set [tool.kotonebot.editor.r_file] to a valid file path in pyproject.toml.'
                )
            if not resolved_r_file.is_file():
                raise ValidationError(f"editor.r_file must be a file path: {resolved_r_file}")
            self.conf.editor.r_file = str(resolved_r_file)

        if self.conf.variant is not None:
            variants = self.conf.variant.variants
            if variants is None:
                raise ValidationError("variant.variants must be configured in pyproject.toml")
            seen: set[str] = set()
            deduped: list[str] = []
            for item in variants:
                if not isinstance(item, str):
                    raise ValidationError("variant.variants must contain only strings")
                value = item.strip()
                if value == "":
                    raise ValidationError("variant.variants cannot contain empty string")
                if value in seen:
                    raise ValidationError(f"variant.variants contains duplicated value: {value}")
                seen.add(value)
                deduped.append(value)
            if len(deduped) == 0:
                raise ValidationError("variant.variants cannot be empty")
            self.conf.variant.variants = deduped

            if self.conf.variant.base is None:
                raise ValidationError("variant.base must be configured in pyproject.toml")
            base = self.conf.variant.base.strip()
            if base == "":
                raise ValidationError("variant.base cannot be empty")
            if base in deduped:
                raise ValidationError("variant.base must not be included in variant.variants")
            self.conf.variant.base = base

            if self.conf.variant.path_pattern is not None:
                raw_path_pattern = self.conf.variant.path_pattern.strip()
                if raw_path_pattern == "":
                    raise ValidationError("variant.path_pattern cannot be empty")
                if raw_path_pattern == "nest" or raw_path_pattern == "flat":
                    self.conf.variant.path_pattern = raw_path_pattern
                elif raw_path_pattern.startswith("pattern:"):
                    template = raw_path_pattern[len("pattern:"):].strip()
                    if template == "":
                        raise ValidationError("variant.path_pattern 'pattern:' template cannot be empty")
                    self.conf.variant.path_pattern = f"pattern: {template}"
                else:
                    raise ValidationError("variant.path_pattern must be 'nest', 'flat', or 'pattern: <template>'")


if __name__ == '__main__':
    project = Project()
    print(project.conf)
