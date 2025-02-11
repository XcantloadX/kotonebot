class UnrecoverableError(Exception):
    pass

class ResourceFileMissingError(Exception):
    def __init__(self, file_path: str, description: str):
        self.file_path = file_path
        self.description = description
        super().__init__(f'Resource file ({description}) "{file_path}" is missing.')

class KotonebotWarning(Warning):
    pass