import time
import logging
from dataclasses import dataclass
from typing import Any, Callable, Literal

from dataclasses import dataclass

from kotonebot.backend.ocr import StringMatchFunction
from kotonebot.primitives import Rect, is_rect

from .core import Image

logger = logging.getLogger(__name__)

@dataclass
class ClickParams:
    finish: bool = False
    log: str | None = None

class ClickCenter:
    def __init__(self, sd: 'SimpleDispatcher', target: Image | str | StringMatchFunction | Literal['center'], *, params: ClickParams = ClickParams()):
        self.target = target
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device
        if self.params.log:
            self.sd.logger.info(self.params.log)
        device.click_center()
        if self.params.finish:
            self.sd.finished = True

class ClickImage:
    def __init__(self, sd: 'SimpleDispatcher', image: Image, *, params: ClickParams = ClickParams()):
        self.image = image
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device, image
        if image.find(self.image):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            device.click()
            if self.params.finish:
                self.sd.finished = True

class ClickImageAny:
    def __init__(self, sd: 'SimpleDispatcher', images: list[Image], params: ClickParams = ClickParams()):
        self.images = images
        self.params = params
        self.sd = sd
    
    def __call__(self):
        from kotonebot import device, image
        if image.find_multi(self.images):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            device.click()
            if self.params.finish:
                self.sd.finished = True

class ClickText:
    def __init__(
            self,
            sd: 'SimpleDispatcher',
            text: str | StringMatchFunction,
            params: ClickParams = ClickParams()
        ):
        self.text = text
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device, ocr
        if ocr.find(self.text):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            device.click()
            if self.params.finish:
                self.sd.finished = True

class ClickRect:
    def __init__(self, sd: 'SimpleDispatcher', rect: Rect, *, params: ClickParams = ClickParams()):
        self.rect = rect
        self.params = params
        self.sd = sd

    def __call__(self):
        from kotonebot import device
        if device.click(self.rect):
            if self.params.log:
                self.sd.logger.info(self.params.log)
            if self.params.finish:
                self.sd.finished = True

class UntilText:
    def __init__(
            self,
            sd: 'SimpleDispatcher',
            text: str | StringMatchFunction,
            *,
            rect: Rect | None = None,
            result: Any | None = None
        ):
        self.text = text
        self.sd = sd
        self.rect = rect
        self.result = result

    def __call__(self):
        from kotonebot import ocr
        if ocr.find(self.text, rect=self.rect):
            self.sd.finished = True
            self.sd.result = self.result

class UntilImage:
    def __init__(
            self,
            sd: 'SimpleDispatcher',
            image: Image,
            *,
            rect: Rect | None = None,
            result: Any | None = None
        ):
        self.image = image
        self.sd = sd
        self.rect = rect
        self.result = result

    def __call__(self):
        from kotonebot import image
        if self.rect:
            logger.warning(f'UntilImage with rect is deprecated. Use UntilText instead.')
        if image.find(self.image):
            self.sd.finished = True
            self.sd.result = self.result

class SimpleDispatcher:
    def __init__(self, name: str, *, min_interval: float = 0.3):
        self.name = name
        self.logger = logging.getLogger(f'SimpleDispatcher of {name}')
        self.blocks: list[Callable] = []
        self.finished: bool = False
        self.result: Any | None = None
        self.min_interval = min_interval
        self.timeout_value: float | None = None
        self.timeout_critical: bool = False
        self.__last_run_time: float = 0

    def click(
        self,
        target: Image | StringMatchFunction | Literal['center'] | Rect,
        *,
        finish: bool = False,
        log: str | None = None
    ):
        params = ClickParams(finish=finish, log=log)
        if isinstance(target, Image):
            self.blocks.append(ClickImage(self, target, params=params))
        elif is_rect(target):
            self.blocks.append(ClickRect(self, target, params=params))
        elif callable(target):
            self.blocks.append(ClickText(self, target, params=params))
        elif target == 'center':
            self.blocks.append(ClickCenter(self, target='center', params=params))
        else:
            raise ValueError(f'Invalid target: {target}')
        return self

    def click_any(
        self,
        target: list[Image],
        *,
        finish: bool = False,
        log: str | None = None
    ):
        params = ClickParams(finish=finish, log=log)
        self.blocks.append(ClickImageAny(self, target, params))
        return self

    def until(
        self,
        text: StringMatchFunction | Image,
        *,
        rect: Rect | None = None,
        result: Any | None = None
    ):
        if isinstance(text, Image):
            self.blocks.append(UntilImage(self, text, rect=rect, result=result))
        else:
            self.blocks.append(UntilText(self, text, rect=rect, result=result))
        return self

    def timeout(self, timeout: float, *, critical: bool = False, result: Any | None = None):
        self.timeout_value = timeout
        self.timeout_critical = critical
        self.timeout_result = result
        return self

    def run(self):
        from kotonebot import device, sleep
        while True:
            logger.debug(f'Running dispatcher "{self.name}"')
            time_delta = time.time() - self.__last_run_time
            if time_delta < self.min_interval:
                sleep(self.min_interval - time_delta)
            # 依次执行 block
            done = False
            for block in self.blocks:
                block()
                if self.finished:
                    done = True
                    break
            if done:
                break

            self.__last_run_time = time.time()
            if self.timeout_value and time.time() - self.__last_run_time > self.timeout_value:
                if self.timeout_critical:
                    raise TimeoutError(f'Dispatcher "{self.name}" timed out.')
                else:
                    self.logger.warning(f'Dispatcher "{self.name}" timed out.')
                    self.result = self.timeout_result
                    break
            device.screenshot()
        return self.result