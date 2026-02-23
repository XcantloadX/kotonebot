from pathlib import Path

from pydantic import BaseModel


class MetaFileRef(BaseModel):
    meta_path: str
    """JSON 元数据文件的相对路径，使用 POSIX 风格路径表示。"""
    image_path: str
    """对应的图片文件的相对路径，使用 POSIX 风格路径表示。"""
    abs_meta_path: Path
    """JSON 元数据文件的绝对路径。"""
    mtime_ns: int
    """JSON 元数据文件的修改时间，单位为纳秒。"""
    size: int
    """JSON 元数据文件的大小，单位为字节。"""


def scan_meta_files(resource_root: Path) -> list[MetaFileRef]:
    """递归扫描指定文件夹下的所有元数据文件。

    :param resource_root: 资源文件根目录。
    :raises ValueError: 资源文件根目录不存在时。
    :return: 元数据文件基本信息。不包含文件内容。
    """
    if not resource_root.exists() or not resource_root.is_dir():
        raise ValueError(f"Resource root does not exist or is not a directory: {resource_root}")

    entries: list[MetaFileRef] = []
    for abs_meta_path in sorted(resource_root.rglob("*.png.json")):
        stat = abs_meta_path.stat()
        entries.append(
            MetaFileRef(
                meta_path=abs_meta_path.as_posix(),
                image_path=abs_meta_path.with_suffix("").as_posix(),
                abs_meta_path=abs_meta_path,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
            )
        )
    return entries
