from typing import Any, Callable

TypeChecker = Callable[[Any], bool]

def match_types(
    args: tuple[Any, ...],
    kwargs: dict[str, Any] | None = None,
    *arg_types: type[Any],
    exact: bool = False,
    type_checkers: dict[type[Any], TypeChecker] | None = None,
    **kw_types: type[Any],
) -> bool:
    kwargs = kwargs or {}

    if exact:
        if len(args) != len(arg_types):
            return False
    else:
        if len(args) < len(arg_types):
            return False

    def _isinstance(value: Any, typ: type[Any]) -> bool:
        if type_checkers and typ in type_checkers:
            return type_checkers[typ](value)
        else:
            return isinstance(value, typ)

    if not all(_isinstance(arg, typ) for arg, typ in zip(args, arg_types)):
        return False

    return all(
        key in kwargs and _isinstance(kwargs[key], typ)
        for key, typ in kw_types.items()
    )