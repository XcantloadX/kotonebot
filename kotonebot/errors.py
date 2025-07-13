class KotonebotError(Exception):
    pass

class KotonebotWarning(Warning):
    pass

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
    def __init__(self, target_resolution: tuple[int, int], screen_size: tuple[int, int]):
        self.target_resolution = target_resolution
        self.screen_size = screen_size
        super().__init__(f'Cannot scale to target resolution {target_resolution}. '
                         f'Screen size: {screen_size}')
        
class ContextNotInitializedError(KotonebotError):
    def __init__(self, msg: str = 'Context not initialized'):
        super().__init__(msg)