from typing import Callable, Sequence


class KotonebotError(Exception):
    pass

class KotonebotWarning(Warning):
    pass

class MissingDependencyError(KotonebotError, ImportError):
    def __init__(self, e: ImportError, group_name: str) -> None:
        self.original_error = e
        super().__init__(f'Cannot import module "{e.name}". Did you forget to run "pip install kotonebot[{group_name}]"?')

class UserFriendlyError(KotonebotError):
    def __init__(
        self,
        message: str,
        actions: list[tuple[int, str, Callable[[], None]]] = [],
        *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.message = message
        self.actions = actions or []

    @property
    def action_buttons(self) -> list[tuple[int, str]]:
        """
        以 (id: int, btn_text: str) 的形式返回所有按钮定义。
        """
        return [(id, text) for id, text, _ in self.actions]
    
    def invoke(self, action_id: int):
        """
        执行指定 ID 的 action。
        """
        for id, _, func in self.actions:
            if id == action_id:
                func()
                break
        else:
            raise ValueError(f'Action with id {action_id} not found.')

class UnrecoverableError(KotonebotError):
    pass

class GameUpdateNeededError(UnrecoverableError):
    def __init__(self):
        super().__init__(
            'Game update required. '
            'Please go to Play Store and update the game manually.'
        )

class ResourceFileMissingError(KotonebotError):
    def __init__(self, file_path: str, description: str):
        self.file_path = file_path
        self.description = description
        super().__init__(f'Resource file ({description}) "{file_path}" is missing.')

class TaskNotFoundError(KotonebotError):
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f'Task "{task_id}" not found.')

class UnscalableResolutionError(KotonebotError):
    def __init__(self, target_resolution: Sequence[int], screen_size: Sequence[int]):
        self.target_resolution = target_resolution
        self.screen_size = screen_size
        super().__init__(f'Cannot scale to target resolution {target_resolution}. '
                         f'Screen size: {screen_size}')

class ContextNotInitializedError(KotonebotError):
    def __init__(self, msg: str = 'Context not initialized'):
        super().__init__(msg)

class StopCurrentTask(KotonebotError):
    pass

class CapabilityNotSupportedError(KotonebotError):
    def __init__(self, capability_name: str):
        self.capability_name = capability_name
        super().__init__(f'Capability "{capability_name}" is not supported by the current device implementation.')

class DeviceAlreadyStartedError(KotonebotError):
    def __init__(self):
        super().__init__('Device lifecycle is already started.')


class DeviceThreadMismatchError(KotonebotError):
    def __init__(self, action: str, owner_thread: str, current_thread: str):
        self.action = action
        self.owner_thread = owner_thread
        self.current_thread = current_thread
        super().__init__(
            f'Device lifecycle {action} must be called from the owner thread. '
            f'owner={owner_thread}, current={current_thread}.'
        )


class MissingResourceVariant(KotonebotError):
    """当请求的资源变体不存在时抛出。"""

    def __init__(self, variant_name: str, resource_class: str):
        self.variant_name = variant_name
        self.resource_class = resource_class
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Unsupported resource variant: {self.variant_name} for {self.resource_class}"

    def __repr__(self) -> str:
        return f"MissingResourceVariant(variant_name={self.variant_name!r}, resource_class={self.resource_class!r})"
