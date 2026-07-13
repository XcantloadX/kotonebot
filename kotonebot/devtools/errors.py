class DevtoolsError(Exception):
    code: str = "DEVTOOLS_ERROR"
    status_code: int = 400

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class NotFoundError(DevtoolsError):
    code = "NOT_FOUND"
    status_code = 404


class ValidationError(DevtoolsError):
    code = "VALIDATION_ERROR"
    status_code = 422


class VariantNotDeclaredError(DevtoolsError):
    code = "VARIANT_NOT_DECLARED"
    status_code = 400


class InvalidImageError(DevtoolsError):
    code = "INVALID_IMAGE"
    status_code = 400


class PathSafetyError(DevtoolsError):
    code = "PATH_UNSAFE"
    status_code = 403


class CommandError(DevtoolsError):
    code = "COMMAND_ERROR"
    status_code = 400
