def __getattr__(name):
    """Lazy loading of module attributes to avoid importing heavy dependencies
    when only using CLI tools."""
    if name == "ContextOcr":
        from .backend.context import ContextOcr
        return ContextOcr
    elif name == "ContextImage":
        from .backend.context import ContextImage
        return ContextImage
    elif name == "ContextDebug":
        from .backend.context import ContextDebug
        return ContextDebug
    elif name == "ContextColor":
        from .backend.context import ContextColor
        return ContextColor
    elif name == "device":
        from .backend.context import device
        return device
    elif name == "ocr":
        from .backend.context import ocr
        return ocr
    elif name == "image":
        from .backend.context import image
        return image
    elif name == "debug":
        from .backend.context import debug
        return debug
    elif name == "color":
        from .backend.context import color
        return color
    elif name == "config":
        from .backend.context import config
        return config
    elif name == "rect_expand":
        from .backend.context import rect_expand
        return rect_expand
    elif name == "sleep":
        from .backend.context import sleep
        return sleep
    elif name == "task":
        from .backend.context import task
        return task
    elif name == "action":
        from .backend.context import action
        return action
    elif name == "use_screenshot":
        from .backend.context import use_screenshot
        return use_screenshot
    elif name == "wait":
        from .backend.context import wait
        return wait
    elif name == "cropped":
        from .util import cropped
        return cropped
    elif name == "AdaptiveWait":
        from .util import AdaptiveWait
        return AdaptiveWait
    elif name == "Countdown":
        from .util import Countdown
        return Countdown
    elif name == "Interval":
        from .util import Interval
        return Interval
    elif name == "until":
        from .util import until
        return until
    elif name == "hsv_cv2web":
        from .backend.color import hsv_cv2web
        return hsv_cv2web
    elif name == "hsv_web2cv":
        from .backend.color import hsv_web2cv
        return hsv_web2cv
    elif name == "rgb_to_hsv":
        from .backend.color import rgb_to_hsv
        return rgb_to_hsv
    elif name == "hsv_to_rgb":
        from .backend.color import hsv_to_rgb
        return hsv_to_rgb
    elif name == "fuzz":
        from .backend.ocr import fuzz
        return fuzz
    elif name == "regex":
        from .backend.ocr import regex
        return regex
    elif name == "contains":
        from .backend.ocr import contains
        return contains
    elif name == "equals":
        from .backend.ocr import equals
        return equals
    elif name == "KotoneBot":
        from .backend.bot import KotoneBot
        return KotoneBot
    elif name == "Loop":
        from .backend.loop import Loop
        return Loop
    elif name == "user":
        from .ui import user
        return user
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")