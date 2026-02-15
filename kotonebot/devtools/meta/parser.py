import json
from pathlib import Path

from pydantic import ValidationError

from .models import MetaV2Model


def parse_meta_file(meta_path: str | Path) -> MetaV2Model:
    """读入并解析元数据文件，返回 `MetaV2Model` 实例。

    :param meta_path: 元数据文件的路径。
    :raises ValueError: 当元数据文件不存在或格式不正确时。
    :return: 解析后的 `MetaV2Model` 实例。
    """
    path = Path(meta_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        return MetaV2Model.model_validate(data)
    except ValidationError as exc:
        raise ValueError(str(exc)) from exc
