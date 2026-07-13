from pathlib import Path
from typing import TYPE_CHECKING

from kotonebot.devtools.errors import PathSafetyError

if TYPE_CHECKING:
    from kotonebot.devtools.project.project import Project


def unify_path(path: str | Path) -> str:
    """归一化为绝对 POSIX 小写字符串，用于比较、哈希、去重。"""
    return str(Path(path).resolve()).replace("\\", "/").lower()


def to_rel(path: str | Path, root: Path) -> str:
    """绝对路径 → 相对于 root 的 POSIX 字符串。
    如果不在 root 下，回退为绝对 POSIX 路径。"""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def from_rel(rel_path: str | Path, root: Path) -> Path:
    """相对路径 → 绝对 Path 对象。"""
    p = Path(rel_path)
    if p.is_absolute():
        return p.resolve()
    return (root / p).resolve()


def get_safe_path(path_str: str, project: "Project") -> Path:
    """
    Validate that a path is within one of the project's allowed root directories.
    
    Args:
        path_str: The path to validate (can be relative or absolute)
        project: The Project instance providing allowed roots
        
    Returns:
        The resolved absolute path
        
    Raises:
        ValueError: If the path is not within any allowed root
    """
    allowed_roots = project.allowed_roots
    if not allowed_roots:
        raise PathSafetyError("No allowed roots configured for project")

    p = Path(path_str)
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = from_rel(p, project.pyproject_root)

    for root in allowed_roots:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
        except OSError:
            continue

    roots_str = ", ".join(str(r) for r in allowed_roots)
    raise PathSafetyError(f"Invalid path: '{path_str}' is not within allowed roots: {roots_str}")
