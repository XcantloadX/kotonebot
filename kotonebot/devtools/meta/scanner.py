from pathlib import Path

from pydantic import BaseModel

from kotonebot.devtools.errors import NotFoundError


class DocRef(BaseModel):
    image_path: str
    """PNG 图片文件的相对路径，POSIX 风格，主键。"""
    abs_image_path: Path
    """PNG 图片文件的绝对路径。"""
    json_path: str | None = None
    """对应的 .png.json 元数据文件的相对路径，_None_ 表示裸 PNG。"""
    abs_json_path: Path | None = None
    """对应的 .png.json 元数据文件的绝对路径，_None_ 表示裸 PNG。"""
    mtime_ns: int
    """PNG 文件的修改时间，单位为纳秒。"""
    size: int
    """PNG 文件的大小，单位为字节。"""


def scan_docs(resource_root: Path) -> list[DocRef]:
    """递归扫描指定文件夹下的所有文档（PNG + 对应 JSON）。

    :param resource_root: 资源文件根目录。
    :raises ValueError: 资源文件根目录不存在时。
    :return: 文档基本信息。不包含文件内容。
    """
    if not resource_root.exists() or not resource_root.is_dir():
        raise NotFoundError(f"Resource root does not exist or is not a directory: {resource_root}")

    json_png_stems: set[Path] = set()
    for json_abs in resource_root.rglob("*.png.json"):
        png_stem = json_abs.with_suffix("")
        json_png_stems.add(png_stem)

    entries: list[DocRef] = []
    for png_abs in sorted(resource_root.rglob("*.png")):
        stat = png_abs.stat()
        json_abs = png_abs.with_suffix(".png.json")
        if png_abs in json_png_stems:
            entries.append(DocRef(
                image_path=png_abs.as_posix(),
                abs_image_path=png_abs,
                json_path=json_abs.as_posix(),
                abs_json_path=json_abs,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
            ))
        else:
            entries.append(DocRef(
                image_path=png_abs.as_posix(),
                abs_image_path=png_abs,
                mtime_ns=stat.st_mtime_ns,
                size=stat.st_size,
            ))
    return entries
