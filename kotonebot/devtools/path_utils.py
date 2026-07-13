from pathlib import Path
from typing import TYPE_CHECKING

from kotonebot.devtools.errors import PathSafetyError

if TYPE_CHECKING:
    from kotonebot.devtools.project.project import Project


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

    for root in allowed_roots:
        if not p.is_absolute():
            candidate = root / p
        else:
            candidate = p

        try:
            resolved = candidate.resolve()
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue
        except OSError:
            continue

    roots_str = ", ".join(str(r) for r in allowed_roots)
    raise PathSafetyError(f"Invalid path: '{path_str}' is not within allowed roots: {roots_str}")
