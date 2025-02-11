from typing import Callable, ParamSpec, Generic, TypeVar

P = ParamSpec('P')
R = TypeVar('R')
class LogCallable(Generic[P, R]):
    def __init__(self, func: Callable[P, R]):
        self.func = func
        self.log = None

    def use(self, *, log: str):
        self.log = log
        return self

    def __reset(self):
        self.log = None

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
        if self.log is not None:
            print(self.log)
        ret = self.func(*args, **kwargs)
        self.__reset()
        return ret

def log(func: Callable[P, None]):
    return LogCallable(func)

@log
def add(a: int, b: int):
    print(a + b)

# with log
add.use(log='adding 1 and 2')(1, 2)

# without log
add(1, 2)



P = ParamSpec("P")
R = TypeVar("R")

def wrap_with_id(fn: Callable[P, R]):
    def wrapper(id: str, *args: P.args, **kwargs: P.kwargs) -> R:
        return fn(*args, **kwargs)

    return wrapper


@wrap_with_id
def func(x: int, y: int) -> str:
    ...

func