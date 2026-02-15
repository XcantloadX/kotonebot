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

        if self.conf.resource_variants is not None:
            seen: set[str] = set()
            deduped: list[str] = []
            for item in self.conf.resource_variants:
                if not isinstance(item, str):
                    raise ValueError("resource_variants must contain only strings")
                value = item.strip()
                if value == "":
                    raise ValueError("resource_variants cannot contain empty string")
                if value in seen:
                    raise ValueError(f"resource_variants contains duplicated value: {value}")
                seen.add(value)
                deduped.append(value)
            self.conf.resource_variants = deduped


if __name__ == '__main__':
    project = Project()
    print(project.conf)
