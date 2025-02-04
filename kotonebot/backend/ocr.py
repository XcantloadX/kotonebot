import re
import unicodedata
from functools import lru_cache
from typing import Callable, NamedTuple

import cv2
import numpy as np
from cv2.typing import MatLike
from thefuzz import fuzz as _fuzz
from rapidocr_onnxruntime import RapidOCR

from .util import Rect, grayscaled, res_path
from .debug import result as debug_result, debug
from .core import HintBox


_engine_jp = RapidOCR(
    rec_model_path=res_path('res/models/japan_PP-OCRv3_rec_infer.onnx'),
    use_det=True,
    use_cls=False,
    use_rec=True,
)
_engine_en = RapidOCR(
    rec_model_path=res_path('res/models/en_PP-OCRv3_rec_infer.onnx'),
    use_det=True,
    use_cls=False,
    use_rec=True,
)

StringMatchFunction = Callable[[str], bool]

class OcrResult(NamedTuple):
    text: str
    rect: Rect
    confidence: float

class TextNotFoundError(Exception):
    def __init__(self, pattern: str | re.Pattern | StringMatchFunction, image: 'MatLike'):
        self.pattern = pattern
        self.image = image
        if isinstance(pattern, (str, re.Pattern)):
            super().__init__(f"Expected text not found: {pattern}")
        else:
            super().__init__(f"Expected text not found: {pattern.__name__}")


@lru_cache(maxsize=1000)
def fuzz(text: str) -> Callable[[str], bool]:
    """返回 fuzzy 算法的字符串匹配函数。"""
    f = lambda s: _fuzz.ratio(s, text) > 90
    f.__repr__ = lambda: f"fuzzy({text})"
    f.__name__ = f"fuzzy({text})"
    return f

@lru_cache(maxsize=1000)
def regex(regex: str) -> Callable[[str], bool]:
    """返回正则表达式字符串匹配函数。"""
    f = lambda s: re.match(regex, s) is not None
    f.__repr__ = lambda: f"regex('{regex}')"
    f.__name__ = f"regex('{regex}')"
    return f

@lru_cache(maxsize=1000)
def contains(text: str) -> Callable[[str], bool]:
    """返回包含指定文本的函数。"""
    f = lambda s: text in s
    f.__repr__ = lambda: f"contains('{text}')"
    f.__name__ = f"contains('{text}')"
    return f

def _is_match(text: str, pattern: re.Pattern | str | StringMatchFunction) -> bool:
    if isinstance(pattern, re.Pattern):
        return pattern.match(text) is not None
    elif callable(pattern):
        return pattern(text)
    else:
        return text == pattern

# https://stackoverflow.com/questions/46335488/how-to-efficiently-find-the-bounding-box-of-a-collection-of-points
def _bounding_box(points):
    x_coordinates, y_coordinates = zip(*points)

    return [(min(x_coordinates), min(y_coordinates)), (max(x_coordinates), max(y_coordinates))]

def bounding_box(points: list[tuple[int, int]]) -> tuple[int, int, int, int]:
    """
    计算点集的外接矩形

    :param points: 点集
    :return: 外接矩形的左上角坐标和宽高
    """
    topleft, bottomright = _bounding_box(points)
    return (topleft[0], topleft[1], bottomright[0] - topleft[0], bottomright[1] - topleft[1])

def pad_to(img: MatLike, target_size: tuple[int, int], rgb: tuple[int, int, int] = (255, 255, 255)) -> MatLike:
    """将图像居中填充/缩放到指定大小。缺少部分使用指定颜色填充。"""
    h, w = img.shape[:2]
    tw, th = target_size
    
    # 如果图像宽高都大于目标大小，则不进行填充
    if h >= th and w >= tw:
        return img
        
    # 计算宽高比
    aspect = w / h
    target_aspect = tw / th
    
    # 按比例缩放
    if aspect > target_aspect:
        # 图像较宽,以目标宽度为准
        new_w = tw
        new_h = int(tw / aspect)
    else:
        # 图像较高,以目标高度为准
        new_h = th
        new_w = int(th * aspect)
    
    # 缩放图像
    if new_w != w or new_h != h:
        img = cv2.resize(img, (new_w, new_h))
    
    # 创建目标画布并填充
    ret = np.full((th, tw, 3), rgb, dtype=np.uint8)
    
    # 计算需要填充的宽高
    pad_h = th - new_h
    pad_w = tw - new_w
    
    # 将缩放后的图像居中放置
    ret[
        pad_h // 2:pad_h // 2 + new_h,
        pad_w // 2:pad_w // 2 + new_w, :] = img
    return ret

def _draw_result(image: 'MatLike', result: list[OcrResult]) -> 'MatLike':
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    
    # 转换为PIL图像
    result_image = cv2.cvtColor(image.copy(), cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(result_image)
    draw = ImageDraw.Draw(pil_image, 'RGBA')
    
    # 加载字体
    try:
        font = ImageFont.truetype(res_path('res/fonts/SourceHanSansHW-Regular.otf'), 16)
    except:
        font = ImageFont.load_default()
    
    for r in result:
        # 画矩形框
        draw.rectangle(
            [r.rect[0], r.rect[1], r.rect[0] + r.rect[2], r.rect[1] + r.rect[3]], 
            outline=(255, 0, 0), 
            width=2
        )
        
        # 获取文本大小
        text = r.text + f" ({r.confidence:.2f})"  # 添加置信度显示
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # 计算文本位置
        text_x = r.rect[0]
        text_y = r.rect[1] - text_height - 5 if r.rect[1] > text_height + 5 else r.rect[1] + r.rect[3] + 5
        
        # 添加padding
        padding = 4
        bg_rect = [
            text_x - padding,
            text_y - padding,
            text_x + text_width + padding,
            text_y + text_height + padding
        ]
        
        # 画半透明背景
        draw.rectangle(
            bg_rect,
            fill=(0, 0, 0, 128)
        )
        
        # 画文字
        draw.text(
            (text_x, text_y),
            text,
            font=font,
            fill=(255, 255, 255)
        )
    
    # 转回OpenCV格式
    result_image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return result_image

class Ocr:
    def __init__(self, engine: RapidOCR):
        self.__engine = engine

    # TODO: 考虑缓存 OCR 结果，避免重复调用。
    def ocr(
        self,
        img: 'MatLike',
        *,
        rect: Rect | None = None,
        pad: bool = True,
    ) -> list[OcrResult]:
        """
        OCR 一个 cv2 的图像。注意识别结果中的**全角字符会被转换为半角字符**。


        :param rect: 如果指定，则只识别指定矩形区域。
        :param pad:
            是否将过小的图像（尺寸 < 631x631）的图像填充到 631x631。
            默认为 True。

            对于 PaddleOCR 模型，图片尺寸太小会降低准确率。
            将图片周围填充放大，有助于提高准确率，降低耗时。
        :return: 所有识别结果
        """
        if rect is not None:
            x, y, w, h = rect
            img = img[y:y+h, x:x+w]
        original_img = img
        if pad:
            # TODO: 详细研究哪个尺寸最佳，以及背景颜色、图片位置是否对准确率与耗时有影响
            # https://blog.csdn.net/YY007H/article/details/124973777
            original_img = img.copy()
            img = pad_to(img, (631, 631))
        img_content = grayscaled(img)
        result, elapse = self.__engine(img_content)
        if result is None:

            return []
        ret = [OcrResult(
            text=unicodedata.normalize('NFKC', r[1]).replace('ą', 'a'), # HACK: 识别结果中包含奇怪的符号，暂时替换掉
            # r[0] = [左上, 右上, 右下, 左下]
            # 这里有个坑，返回的点不一定是矩形，只能保证是四边形
            # 所以这里需要计算出四个点的外接矩形
            rect=tuple(int(x) for x in bounding_box(r[0])), # type: ignore
            confidence=r[2] # type: ignore
        ) for r in result] # type: ignore
        if debug.enabled:
            result_image = _draw_result(img, ret)
            debug_result(
                'ocr',
                [result_image, original_img],
                f"result: \n" + \
                "<table class='result-table'><tr><th>Text</th><th>Confidence</th></tr>" + \
                "\n".join([f"<tr><td>{r.text}</td><td>{r.confidence:.2f}</td></tr>" for r in ret]) + \
                "</table>"
            )
        return ret

    def find(
        self,
        img: 'MatLike',
        text: str | re.Pattern | StringMatchFunction,
        *,
        hint: HintBox | None = None,
        rect: Rect | None = None,
        pad: bool = True,
    ) -> OcrResult | None:
        """
        寻找指定文本。

        :param hint: 如果指定，则首先只识别 HintBox 范围内的文本，若未命中，再全局寻找。
        :param rect: 如果指定，则只识别指定矩形区域。此参数优先级低于 `hint`。
        :param pad: 见 `ocr` 的 `pad` 参数。
        :return: 找到的文本，如果未找到则返回 None
        """
        if hint is not None:
            if ret := self.find(img, text, rect=hint):
                return ret
        for result in self.ocr(img, rect=rect, pad=pad):
            if _is_match(result.text, text):
                return result
        return None

    
    def expect(
        self,
        img: 'MatLike',
        text: str | re.Pattern | StringMatchFunction,
        *,
        hint: HintBox | None = None,
        rect: Rect | None = None,
        pad: bool = True,
    ) -> OcrResult:
        """
        寻找指定文本，如果未找到则抛出异常。

        :param hint: 如果指定，则首先只识别 HintBox 范围内的文本，若未命中，再全局寻找。
        :param rect: 如果指定，则只识别指定矩形区域。此参数优先级高于 `hint`。
        :param pad: 见 `ocr` 的 `pad` 参数。
        :return: 找到的文本
        """
        ret = self.find(img, text, hint=hint, rect=rect, pad=pad)
        if ret is None:
            raise TextNotFoundError(text, img)
        return ret



jp = Ocr(_engine_jp)
"""日语 OCR 引擎。"""
en = Ocr(_engine_en)
"""英语 OCR 引擎。"""



if __name__ == '__main__':
    import time
    from pprint import pprint as print
    import cv2
    print('small')
    img_path = r"C:\Users\user\Downloads\Screenshot_2025.01.28_21.00.40.172.png"
    img = cv2.imread(img_path)
    time_start = time.time()
    result1 = jp.ocr(img)
    time_end = time.time()
    print(time_end - time_start)
    # print(result1)

    for i in np.linspace(300, 1000, 20):
        i = int(i)
        print('small-pad: ' + f'{str(i)}x{str(i)}')
        img = pad_to(img, (int(i), int(i)))
        time_start = time.time()
        result1 = jp.ocr(img)
        time_end = time.time()
        print(time_end - time_start)

        # print(result1)


    print('big')
    img_path = r"C:\Users\user\Pictures\BlueStacks\Screenshot_2025.01.28_21.00.40.172.png"
    img = cv2.imread(img_path)
    time_start = time.time()
    result1 = jp.ocr(img)
    time_end = time.time()
    print(time_end - time_start)
    # print(result1)
