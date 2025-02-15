from typing import Protocol

from cv2.typing import MatLike

class PushkitProtocol(Protocol):
    def push(
        self,
        title: str,
        message: str,
        *,
        images: list[str | MatLike] | None = None,
    ) -> None:
        ...
