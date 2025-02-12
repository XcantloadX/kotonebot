import os
import re
import time
import logging
import warnings
from datetime import datetime
from threading import Event
from typing import (
    Callable,
    Optional,
    cast,
    overload,
    Any,
    TypeVar,
    Literal,
    ParamSpec,
    Concatenate,
    Generic,
    Type,
    Sequence,
)
from typing_extensions import deprecated

import cv2
from cv2.typing import MatLike

from kotonebot.client.device import Device
from kotonebot.backend.util import Rect
import kotonebot.backend.image as raw_image
from kotonebot.backend.image import (
    TemplateMatchResult,
    MultipleTemplateMatchResult,
    find_all_crop,
    expect,
    find,
    find_multi,
    find_all,
    find_all_multi,
    count
)
import kotonebot.backend.color as raw_color
from kotonebot.backend.color import find_rgb
from kotonebot.backend.ocr import Ocr, OcrResult, OcrResultList, jp, en, StringMatchFunction
from kotonebot.client.factory import create_device
from kotonebot.config.manager import load_config, save_config
from kotonebot.config.base_config import UserConfig
from kotonebot.backend.core import Image, HintBox
from kotonebot.errors import KotonebotWarning

OcrLanguage = Literal['jp', 'en']
ScreenshotMode = Literal['auto', 'manual', 'manual-inherit']
DEFAULT_TIMEOUT = 120
DEFAULT_INTERVAL = 0.4
logger = logging.getLogger(__name__)

# https://stackoverflow.com/questions/74714300/paramspec-for-a-pre-defined-function-without-using-generic-callablep
T = TypeVar('T')
P = ParamSpec('P')
ContextClass = TypeVar("ContextClass")

def context(
    _: Callable[Concatenate[MatLike, P], T] # 输入函数
) -> Callable[
    [Callable[Concatenate[ContextClass, P], T]], # 被装饰函数
    Callable[Concatenate[ContextClass, P], T] # 结果函数
]:
    """
    用于标记 Context 类方法的装饰器。
    此装饰器仅用于辅助类型标注，运行时无实际功能。

    装饰器输入的函数类型为 `(img: MatLike, a, b, c, ...) -> T`，
    被装饰的函数类型为 `(self: ContextClass, *args, **kwargs) -> T`，
    结果类型为 `(self: ContextClass, a, b, c, ...) -> T`。

    也就是说，`@context` 会把输入函数的第一个参数 `img: MatLike` 删除，
    然后再添加 `self` 作为第一个参数。

    【例】
    ```python
    def find_image(
        img: MatLike,
        mask: MatLike,
        threshold: float = 0.9
    ) -> TemplateMatchResult | None:
        ...
    ```
    ```python
    class ContextImage:
        @context(find_image)
        def find_image(self, *args, **kwargs):
            return find_image(
                self.context.device.screenshot(),
                *args,
                **kwargs
            )

    ```
    ```python

    c = ContextImage()
    c.find_image()
    # 此函数类型推断为 (
    #   self: ContextImage,
    #   img: MatLike,
    #   mask: MatLike,
    #   threshold: float = 0.9
    # ) -> TemplateMatchResult | None
    ```
    """
    def _decorator(func):
        return func
    return _decorator

def interruptible(func: Callable[P, T]) -> Callable[P, T]:
    """
    将函数包装为可中断函数。

    在调用函数前，自动检查用户是否请求中断。
    如果用户请求中断，则抛出 `KeyboardInterrupt` 异常。
    """
    def _decorator(*args: P.args, **kwargs: P.kwargs) -> T:
        global vars
        if vars.interrupted.is_set():
            raise KeyboardInterrupt("User requested interrupt.")
        return func(*args, **kwargs)
    return _decorator

def interruptible_class(cls: Type[T]) -> Type[T]:
    """
    将类中的所有方法包装为可中断方法。

    在调用方法前，自动检查用户是否请求中断。
    如果用户请求中断，则抛出 `KeyboardInterrupt` 异常。
    """
    for name, func in cls.__dict__.items():
        if callable(func) and not name.startswith('__'):
            setattr(cls, name, interruptible(func))
    return cls

def sleep(seconds: float, /):
    """
    可中断的 sleep 函数。

    建议使用 `context.sleep()` 代替 `time.sleep()`，
    这样能以最快速度响应用户请求中断。
    """
    global vars
    vars.interrupted.wait(timeout=seconds)
    if vars.interrupted.is_set():
        raise KeyboardInterrupt("User requested interrupt.")

def warn_manual_screenshot_mode(name: str, alternative: str):
    """
    警告在手动截图模式下使用的方法。
    """
    warnings.warn(
        f"You are calling `{name}` function in manual screenshot mode. "
        f"This is meaningless. Write you own while loop and call `{alternative}` in the loop.",
        KotonebotWarning
    )

def is_manual_screenshot_mode() -> bool:
    """
    检查当前是否处于手动截图模式。
    """
    mode = ContextStackVars.ensure_current().screenshot_mode
    return mode == 'manual' or mode == 'manual-inherit'

class ContextGlobalVars:
    def __init__(self):
        self.auto_collect: bool = False
        """遇到未知P饮料/卡片时，是否自动截图并收集"""
        self.interrupted: Event = Event()
        """用户请求中断事件"""


class ContextStackVars:
    stack: list['ContextStackVars'] = []

    def __init__(self):
        self.screenshot_mode: ScreenshotMode = 'auto'
        """
        截图模式。

        * `auto`
            自动截图。即调用 `color`、`image`、`ocr` 上的方法时，会自动更新截图。
        * `manual`
            完全手动截图，不自动截图。如果在没有截图数据的情况下调用 `color` 等的方法，会抛出异常。
        * `manual-inherit`：
            第一张截图继承自调用者，此后同手动截图。
            如果调用者没有截图数据，则继承的截图数据为空。
            如果在没有截图数据的情况下调用 `color` 等的方法，会抛出异常。
        """
        self._screenshot: MatLike | None = None
        """截图数据"""
        self._inherit_screenshot: MatLike | None = None
        """继承的截图数据"""

    @property
    def screenshot(self) -> MatLike:
        match self.screenshot_mode:
            case 'manual' | 'manual-inherit':
                if self._screenshot is None:
                    raise ValueError("No screenshot data found.")
                return self._screenshot
            case 'auto':
                self._screenshot = device.screenshot()
                return self._screenshot
            case _:
                raise ValueError(f"Invalid screenshot mode: {self.screenshot_mode}")

    @staticmethod
    def push(*, screenshot_mode: ScreenshotMode | None = None) -> 'ContextStackVars':
        vars = ContextStackVars()
        if screenshot_mode is not None:
            vars.screenshot_mode = screenshot_mode
        current = ContextStackVars.current()
        if current and vars.screenshot_mode == 'manual-inherit':
            vars._inherit_screenshot = current._screenshot
        ContextStackVars.stack.append(vars)
        return vars

    @staticmethod
    def pop() -> 'ContextStackVars':
        last = ContextStackVars.stack.pop()
        return last
    
    @staticmethod
    def current() -> 'ContextStackVars | None':
        if len(ContextStackVars.stack) == 0:
            return None
        return ContextStackVars.stack[-1]

    @staticmethod
    def ensure_current() -> 'ContextStackVars':
        if len(ContextStackVars.stack) == 0:
            raise ValueError("No context stack found.")
        return ContextStackVars.stack[-1]

@interruptible_class
class ContextOcr:
    def __init__(self, context: 'Context'):
        self.context = context
        self.__engine = jp

    def raw(self, lang: OcrLanguage = 'jp') -> Ocr:
        """
        返回 `kotonebot.backend.ocr` 中的 Ocr 对象。\n
        Ocr 对象与此对象（ContextOcr）的区别是，此对象会自动截图，而 Ocr 对象需要手动传入图像参数。
        """
        match lang:
            case 'jp':
                return jp
            case 'en':
                return en
            case _:
                raise ValueError(f"Invalid language: {lang}")

    def ocr(
        self,
        rect: Rect | None = None,
    ) -> OcrResultList:
        """OCR 当前设备画面或指定图像。"""
        return self.__engine.ocr(ContextStackVars.ensure_current().screenshot, rect=rect)

    def find(
        self,
        pattern: str | re.Pattern | StringMatchFunction,
        *,
        hint: HintBox | None = None,
        rect: Rect | None = None,
    ) -> OcrResult | None:
        """检查当前设备画面是否包含指定文本。"""
        ret = self.__engine.find(
            ContextStackVars.ensure_current().screenshot,
            pattern,
            hint=hint,
            rect=rect,
        )
        self.context.device.last_find = ret.original_rect if ret else None
        return ret
    
    def find_all(
        self,
        patterns: Sequence[str | re.Pattern | StringMatchFunction],
        *,
        hint: HintBox | None = None,
        rect: Rect | None = None,

    ) -> list[OcrResult | None]:
        return self.__engine.find_all(
            ContextStackVars.ensure_current().screenshot,
            list(patterns),
            hint=hint,
            rect=rect,
        )

    def expect(
        self,
        pattern: str | re.Pattern | StringMatchFunction,
        *,
        rect: Rect | None = None,
        hint: HintBox | None = None,
    ) -> OcrResult:

        """
        检查当前设备画面是否包含指定文本。

        与 `find()` 的区别在于，`expect()` 未找到时会抛出异常。
        """
        ret = self.__engine.expect(ContextStackVars.ensure_current().screenshot, pattern, rect=rect, hint=hint)
        self.context.device.last_find = ret.original_rect if ret else None
        return ret
    
    def expect_wait(
        self,
        pattern: str | re.Pattern | StringMatchFunction,
        timeout: float = DEFAULT_TIMEOUT,
        *,
        interval: float = DEFAULT_INTERVAL,
        rect: Rect | None = None,
        hint: HintBox | None = None,
    ) -> OcrResult:
        """
        等待指定文本出现。
        """
        is_manual = is_manual_screenshot_mode()

        start_time = time.time()
        while True:
            if is_manual:
                device.screenshot()
            result = self.find(pattern, rect=rect, hint=hint)

            if result is not None:
                self.context.device.last_find = result.original_rect if result else None
                return result
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {pattern}")
            sleep(interval)

    def wait_for(
        self,
        pattern: str | re.Pattern | StringMatchFunction,
        timeout: float = DEFAULT_TIMEOUT,
        *,
        interval: float = DEFAULT_INTERVAL,
        rect: Rect | None = None,
        hint: HintBox | None = None,
    ) -> OcrResult | None:
        """
        等待指定文本出现。
        """
        is_manual = is_manual_screenshot_mode()

        start_time = time.time()
        while True:
            if is_manual:
                device.screenshot()
            result = self.find(pattern, rect=rect, hint=hint)
            if result is not None:
                self.context.device.last_find = result.original_rect if result else None
                return result
            if time.time() - start_time > timeout:
                return None
            sleep(interval)


@interruptible_class
class ContextImage:
    def __init__(self, context: 'Context', crop_rect: Rect | None = None):
        self.context = context
        self.crop_rect = crop_rect

    def raw(self):
        return raw_image

    def wait_for(
            self,
            template: MatLike | str | Image,
            mask: MatLike | str | None = None,
            threshold: float = 0.8,
            timeout: float = DEFAULT_TIMEOUT,
            colored: bool = False,
            *,
            transparent: bool = False,
            interval: float = DEFAULT_INTERVAL,
        ) -> TemplateMatchResult | None:
        """
        等待指定图像出现。
        """
        is_manual = is_manual_screenshot_mode()
        
        start_time = time.time()
        while True:
            if is_manual:
                device.screenshot()
            ret = self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored)
            if ret is not None:
                self.context.device.last_find = ret
                return ret
            if time.time() - start_time > timeout:
                return None
            sleep(interval)

    def wait_for_any(
            self,
            templates: list[str | Image],
            masks: list[str | None] | None = None,
            threshold: float = 0.8,
            timeout: float = DEFAULT_TIMEOUT,
            colored: bool = False,
            *,
            transparent: bool = False,
            interval: float = DEFAULT_INTERVAL
        ):
        """
        等待指定图像中的任意一个出现。
        """
        is_manual = is_manual_screenshot_mode()

        if masks is None:
            _masks = [None] * len(templates)
        else:
            _masks = masks
        start_time = time.time()
        while True:
            if is_manual:
                device.screenshot()
            for template, mask in zip(templates, _masks):
                if self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored):
                    return True
            if time.time() - start_time > timeout:
                return False
            sleep(interval)

    def expect_wait(
            self,
            template: str | Image,
            mask: str | None = None,
            threshold: float = 0.8,
            timeout: float = DEFAULT_TIMEOUT,
            colored: bool = False,
            *,
            transparent: bool = False,
            interval: float = DEFAULT_INTERVAL
        ) -> TemplateMatchResult:
        """
        等待指定图像出现。
        """
        is_manual = is_manual_screenshot_mode()

        start_time = time.time()
        while True:
            if is_manual:
                device.screenshot()
            ret = self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored)
            if ret is not None:
                self.context.device.last_find = ret
                return ret
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for {template}")
            sleep(interval)

    def expect_wait_any(
            self,
            templates: list[str | Image],
            masks: list[str | None] | None = None,
            threshold: float = 0.8,
            timeout: float = DEFAULT_TIMEOUT,
            colored: bool = False,
            *,
            transparent: bool = False,
            interval: float = DEFAULT_INTERVAL
        ) -> TemplateMatchResult:
        """
        等待指定图像中的任意一个出现。
        """
        is_manual = is_manual_screenshot_mode()

        if masks is None:
            _masks = [None] * len(templates)
        else:
            _masks = masks
        start_time = time.time()
        while True:
            if is_manual:
                device.screenshot()
            for template, mask in zip(templates, _masks):
                ret = self.find(template, mask, transparent=transparent, threshold=threshold, colored=colored)
                if ret is not None:
                    self.context.device.last_find = ret
                    return ret
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Timeout waiting for any of {templates}")
            sleep(interval)

    @context(expect)
    def expect(self, *args, **kwargs):
        ret = expect(ContextStackVars.ensure_current().screenshot, *args, **kwargs)
        self.context.device.last_find = ret
        return ret

    @context(find)
    def find(self, *args, **kwargs):
        ret = find(ContextStackVars.ensure_current().screenshot, *args, **kwargs)
        self.context.device.last_find = ret
        return ret

    @context(find_all)
    def find_all(self, *args, **kwargs):
        return find_all(ContextStackVars.ensure_current().screenshot, *args, **kwargs)

    @context(find_multi)
    def find_multi(self, *args, **kwargs):
        ret = find_multi(ContextStackVars.ensure_current().screenshot, *args, **kwargs)
        self.context.device.last_find = ret
        return ret

    @context(find_all_multi)
    def find_all_multi(self, *args, **kwargs):
        return find_all_multi(ContextStackVars.ensure_current().screenshot, *args, **kwargs)

    @context(find_all_crop)
    def find_all_crop(self, *args, **kwargs):
        return find_all_crop(ContextStackVars.ensure_current().screenshot, *args, **kwargs)

    @context(count)
    def count(self, *args, **kwargs):
        return count(ContextStackVars.ensure_current().screenshot, *args, **kwargs)

@interruptible_class
class ContextColor:
    def __init__(self, context: 'Context'):
        self.context = context

    def raw(self):
        return raw_color

    @context(find_rgb)
    def find_rgb(self, *args, **kwargs):
        return find_rgb(ContextStackVars.ensure_current().screenshot, *args, **kwargs)


class ContextDebug:
    def __init__(self, context: 'Context'):
        self.__context = context
        self.save_images: bool = False
        self.save_images_dir: str = "debug_images"


V = TypeVar('V')
class ContextConfig(Generic[T]):
    def __init__(self, context: 'Context', config_type: Type[T] = dict[str, Any]):
        self.context = context
        self.config_path: str = 'config.json'
        self.current_key: int | str = 0
        self.config_type: Type = config_type
        self.root = load_config(self.config_path, type=config_type)

    def to(self, conf_type: Type[V]) -> 'ContextConfig[V]':
        self.config_type = conf_type
        return cast(ContextConfig[V], self)

    def create(self, config: UserConfig[T]):
        """创建新用户配置"""
        self.root.user_configs.append(config)
        self.save()

    def get(self, key: str | int | None = None) -> UserConfig[T] | None:
        """
        获取指定或当前用户配置数据。

        :param key: 用户配置 ID 或索引（从 0 开始），为 None 时获取当前用户配置
        :return: 用户配置数据
        """
        if isinstance(key, int):
            if key < 0 or key >= len(self.root.user_configs):
                return None
            return self.root.user_configs[key]
        elif isinstance(key, str):
            for user in self.root.user_configs:
                if user.id == key:
                    return user
            else:
                return None
        else:
            return self.get(self.current_key)

    def save(self):
        """保存所有配置数据到本地"""
        save_config(self.root, self.config_path)

    def load(self):
        """从本地加载所有配置数据"""
        self.root = load_config(self.config_path, type=self.config_type)

    def switch(self, key: str | int):
        """切换到指定用户配置"""
        self.current_key = key

    @property
    def current(self) -> UserConfig[T]:
        """
        当前配置数据。
        
        如果当前配置不存在，则使用默认值自动创建一个新配置。
        （不推荐，建议在 UI 中启动前要求用户手动创建，或自行创建一个默认配置。）
        """
        c = self.get(self.current_key)
        if c is None:
            if not self.config_type:
                raise ValueError("No config type specified.")
            logger.warning("No config found, creating a new one using default values. (NOT RECOMMENDED)")
            c = self.config_type()
            u = UserConfig(options=c)
            self.create(u)
            c = u
        return c


class Forwarded:
    def __init__(self, getter: Callable[[], T] | None = None, name: str | None = None):
        self._FORWARD_getter = getter
        self._FORWARD_name = name

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_FORWARD_'):
            return object.__getattribute__(self, name)
        if self._FORWARD_getter is None:
            raise ValueError(f"Forwarded object {self._FORWARD_name} called before initialization.")
        return getattr(self._FORWARD_getter(), name)
    
    def __setattr__(self, name: str, value: Any):
        if name.startswith('_FORWARD_'):
            return object.__setattr__(self, name, value)
        if self._FORWARD_getter is None:
            raise ValueError(f"Forwarded object {self._FORWARD_name} called before initialization.")
        setattr(self._FORWARD_getter(), name, value)

# HACK: 这应该要有个更好的实现方式
class ContextDevice(Device):
    def __init__(self, device: Device):
        self._device = device

    def screenshot(self, *, force: bool = False):
        """
        截图。返回截图数据，同时更新当前上下文的截图数据。
        """
        current = ContextStackVars.ensure_current()
        if force:
            current._inherit_screenshot = None
        if current._inherit_screenshot is not None:
            img = current._inherit_screenshot
            current._inherit_screenshot = None
        else:
            img = self._device.screenshot()
        current._screenshot = img
        return img

    def __getattribute__(self, name: str) -> Any:
        if name in ['_device', 'screenshot']:
            return object.__getattribute__(self, name)
        else:
            return getattr(self._device, name)
        
    def __setattr__(self, name: str, value: Any):
        if name in ['_device', 'screenshot']:
            return object.__setattr__(self, name, value)
        else:
            return setattr(self._device, name, value)


class Context(Generic[T]):
    def __init__(self, config_type: Type[T]):
        self.__ocr = ContextOcr(self)
        self.__image = ContextImage(self)
        self.__color = ContextColor(self)
        self.__vars = ContextGlobalVars()
        self.__debug = ContextDebug(self)
        self.__config = ContextConfig[T](self, config_type)
        
        ip = self.config.current.backend.adb_ip
        port = self.config.current.backend.adb_port
        # TODO: 处理链接失败情况
        self.__device = ContextDevice(create_device(f'{ip}:{port}', 'adb'))

    def inject(
        self,
        *,
        device: Optional[ContextDevice | Device] = None,
        ocr: Optional[ContextOcr] = None,
        image: Optional[ContextImage] = None,
        color: Optional[ContextColor] = None,
        vars: Optional[ContextGlobalVars] = None,
        debug: Optional[ContextDebug] = None,
        config: Optional[ContextConfig] = None,
    ):
        if device is not None:
            if isinstance(device, Device):
                self.__device = ContextDevice(device)
            else:
                self.__device = device
        if ocr is not None:
            self.__ocr = ocr
        if image is not None:
            self.__image = image
        if color is not None:
            self.__color = color
        if vars is not None:
            self.__vars = vars
        if debug is not None:
            self.__debug = debug    
        if config is not None:
            self.__config = config

    @property
    def device(self) -> ContextDevice:
        return self.__device

    @property
    def ocr(self) -> 'ContextOcr':
        return self.__ocr
    
    @property
    def image(self) -> 'ContextImage':
        return self.__image

    @property
    def color(self) -> 'ContextColor':
        return self.__color

    @property
    def vars(self) -> 'ContextGlobalVars':
        return self.__vars
    
    @property
    def debug(self) -> 'ContextDebug':
        return self.__debug

    @property
    def config(self) -> 'ContextConfig[T]':
        return self.__config

def rect_expand(rect: Rect, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> Rect:
    """
    向四个方向扩展矩形区域。
    """
    return (rect[0] - left, rect[1] - top, rect[2] + right + left, rect[3] + bottom + top)

def use_screenshot(*args: MatLike | None) -> MatLike:
    for img in args:
        if img is not None:
            ContextStackVars.ensure_current()._screenshot = img # HACK
            return img
    return device.screenshot()

# 这里 Context 类还没有初始化，但是 tasks 中的脚本可能已经引用了这里的变量
# 为了能够动态更新这里变量的值，这里使用 Forwarded 类再封装一层，
# 将调用转发到实际的稍后初始化的 Context 类上
_c: Context | None = None
device: ContextDevice = cast(ContextDevice, Forwarded(name="device"))
"""当前正在执行任务的设备。"""
ocr: ContextOcr = cast(ContextOcr, Forwarded(name="ocr"))
"""OCR 引擎。"""
image: ContextImage = cast(ContextImage, Forwarded(name="image"))
"""图像识别。"""
color: ContextColor = cast(ContextColor, Forwarded(name="color"))
"""颜色识别。"""
vars: ContextGlobalVars = cast(ContextGlobalVars, Forwarded(name="vars"))
"""全局变量。"""
debug: ContextDebug = cast(ContextDebug, Forwarded(name="debug"))
"""调试工具。"""
config: ContextConfig = cast(ContextConfig, Forwarded(name="config"))
"""配置数据。"""


def init_context(
    *,
    config_type: Type[T] = dict[str, Any],
    force: bool = False
):
    """
    初始化 Context 模块。

    :param config_type: 
        配置数据类类型。配置数据类必须继承自 pydantic 的 `BaseModel`。
        默认为 `dict[str, Any]`，即普通的 JSON 数据，不包含任何类型信息。
    :param force: 
        是否强制重新初始化。
        若为 `True`，则忽略已存在的 Context 实例，并重新创建一个新的实例。
    """
    global _c, device, ocr, image, color, vars, debug, config
    if _c is not None and not force:
        return
    _c = Context(config_type=config_type)
    device._FORWARD_getter = lambda: _c.device # type: ignore
    ocr._FORWARD_getter = lambda: _c.ocr # type: ignore
    image._FORWARD_getter = lambda: _c.image # type: ignore
    color._FORWARD_getter = lambda: _c.color # type: ignore
    vars._FORWARD_getter = lambda: _c.vars # type: ignore
    debug._FORWARD_getter = lambda: _c.debug # type: ignore
    config._FORWARD_getter = lambda: _c.config # type: ignore


def inject_context(
    *,
    device: Optional[ContextDevice | Device] = None,
    ocr: Optional[ContextOcr] = None,
    image: Optional[ContextImage] = None,
    color: Optional[ContextColor] = None,
    vars: Optional[ContextGlobalVars] = None,
    debug: Optional[ContextDebug] = None,
    config: Optional[ContextConfig] = None,
):
    global _c
    if _c is None:
        raise RuntimeError('Context not initialized')
    _c.inject(device=device, ocr=ocr, image=image, color=color, vars=vars, debug=debug, config=config)

class ManualContextManager:
    def __init__(self, screenshot_mode: ScreenshotMode = 'auto'):
        self.screenshot_mode: ScreenshotMode = screenshot_mode

    def __enter__(self):
        ContextStackVars.push(screenshot_mode=self.screenshot_mode)

    def __exit__(self, exc_type, exc_value, traceback):
        ContextStackVars.pop()

    def begin(self):
        self.__enter__()

    def end(self):
        self.__exit__(None, None, None)

def manual_context(screenshot_mode: ScreenshotMode = 'auto') -> ManualContextManager:
    """
    默认情况下，Context* 类仅允许在 @task/@action 函数中使用。
    如果想要在其他地方使用，使用此函数手动创建一个上下文。
    """
    return ManualContextManager(screenshot_mode)

