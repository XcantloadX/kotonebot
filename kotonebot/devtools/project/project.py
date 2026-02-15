from pathlib import Path

try:
    from tomllib import loads as toml_loader  # py>=3.11 # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    from tomli import loads as toml_loader  # py<3.11

from kotonebot.devtools.project.schema import PyProjectData


PYPROJECT_PATH = './pyproject.toml'

class Project:
    def __init__(self, *, conf_path: str = PYPROJECT_PATH) -> None:
        conf_file = Path(conf_path).resolve()
        self.conf_path: str = str(conf_file)
        self.pyproject_root: Path = conf_file.parent
        self.conf: PyProjectData

        self.load()
    
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

        if self.conf.variant is not None:
            names: list[str] | None = None
            if self.conf.variant.names is not None:
                seen: set[str] = set()
                deduped: list[str] = []
                for item in self.conf.variant.names:
                    if not isinstance(item, str):
                        raise ValueError("variant.names must contain only strings")
                    value = item.strip()
                    if value == "":
                        raise ValueError("variant.names cannot contain empty string")
                    if value in seen:
                        raise ValueError(f"variant.names contains duplicated value: {value}")
                    seen.add(value)
                    deduped.append(value)
                names = deduped
                self.conf.variant.names = names

            if self.conf.variant.base is not None:
                base = self.conf.variant.base.strip()
                if base == "":
                    raise ValueError("variant.base cannot be empty")
                self.conf.variant.base = base
                if names is None:
                    raise ValueError("variant.base requires variant.names")
                if base not in names:
                    raise ValueError(f"variant.base '{base}' is not declared in variant.names")

            if self.conf.variant.path_pattern is not None:
                raw_path_pattern = self.conf.variant.path_pattern.strip()
                if raw_path_pattern == "":
                    raise ValueError("variant.path_pattern cannot be empty")
                if raw_path_pattern == "nest" or raw_path_pattern == "flat":
                    self.conf.variant.path_pattern = raw_path_pattern
                elif raw_path_pattern.startswith("pattern:"):
                    template = raw_path_pattern[len("pattern:"):].strip()
                    if template == "":
                        raise ValueError("variant.path_pattern 'pattern:' template cannot be empty")
                    self.conf.variant.path_pattern = f"pattern: {template}"
                else:
                    raise ValueError("variant.path_pattern must be 'nest', 'flat', or 'pattern: <template>'")


if __name__ == '__main__':
    project = Project()
    print(project.conf)
