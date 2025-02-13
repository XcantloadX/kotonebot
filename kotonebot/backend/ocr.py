import re
import time
import logging
import unicodedata
from functools import lru_cache
from dataclasses import dataclass
from typing_extensions import Self
from typing import Callable, NamedTuple

import cv2
import numpy as np
from cv2.typing import MatLike
from thefuzz import fuzz as _fuzz
from rapidocr_onnxruntime import RapidOCR

from .util import Rect, grayscaled, res_path
from .debug import result as debug_result, debug
from .core import HintBox

logger = logging.getLogger(__name__)

_engine_jp = RapidOCR(
    rec_model_path=res_path('res/models/japan_PP-OCRv4_rec_infer.onnx'),
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
REGEX_NUMBERS = re.compile(r'\d+')

@dataclass
class OcrResult:
    text: str
    rect: Rect
    confidence: float
    original_rect: Rect
    """
    识别结果在原图中的区域坐标。

    如果识别时没有设置 `rect` 或 `hint` 参数，则此属性值与 `rect` 相同。
    """

    def __repr__(self) -> str:
        return f'OcrResult(text="{self.text}", rect={self.rect}, confidence={self.confidence})'

    def replace(self, old: str, new: str, count: int = -1) -> Self:
        """
        替换识别结果中的文本。
        """
        self.text = self.text.replace(old, new, count)
        return self

    def regex(self, pattern: re.Pattern | str) -> list[str]:
        """
        提取识别结果中符合正则表达式的文本。
        """
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        return pattern.findall(self.text)

    def numbers(self) -> list[int]:
        """
        提取识别结果中的数字。
        """
        return [int(x) for x in REGEX_NUMBERS.findall(self.text)]

class OcrResultList(list[OcrResult]):
    def squash(self, remove_newlines: bool = True) -> OcrResult:
        """
        将所有识别结果合并为一个大结果。
        """
        if not self:
            return OcrResult('', (0, 0, 0, 0), 0, (0, 0, 0, 0))
        text = [r.text for r in self]
        confidence = sum(r.confidence for r in self) / len(self)
        points = []
        for r in self:
            points.append((r.rect[0], r.rect[1]))
            points.append((r.rect[0] + r.rect[2], r.rect[1]))
            points.append((r.rect[0], r.rect[1] + r.rect[3]))
            points.append((r.rect[0] + r.rect[2], r.rect[1] + r.rect[3]))
        rect = bounding_box(points)
        text = '\n'.join(text)
        if remove_newlines:
            text = text.replace('\n', '')
        return OcrResult(
            text=text,
            rect=rect,
            confidence=confidence,
            original_rect=rect,
        )

    def first(self) -> OcrResult | None:
        """
        返回第一个识别结果。
        """
        return self[0] if self else None

    def where(self, pattern: StringMatchFunction) -> 'OcrResultList':
        """
        返回符合条件的识别结果。
        """
        return OcrResultList([x for x in self if pattern(x.text)])

class TextNotFoundError(Exception):
    def __init__(self, pattern: str | re.Pattern | StringMatchFunction, image: 'MatLike'):
        self.pattern = pattern
        self.image = image
        super().__init__(f"Expected text not found: {pattern}")

class TextComparator:
    def __init__(self, name: str, text: str, func: Callable[[str], bool]):
        self.name = name
        self.text = text
        self.func = func

    def __call__(self, text: str) -> bool:
        return self.func(text)
    
    def __repr__(self) -> str:
        return f'{self.name}("{self.text}")'

@lru_cache(maxsize=1000)
def fuzz(text: str) -> TextComparator:
    """返回 fuzzy 算法的字符串匹配函数。"""
    func = lambda s: _fuzz.ratio(s, text) > 90
    return TextComparator("fuzzy", text, func)

@lru_cache(maxsize=1000)
def regex(regex: str) -> TextComparator:
    """返回正则表达式字符串匹配函数。"""
    func = lambda s: re.match(regex, s) is not None
    return TextComparator("regex", regex, func)

@lru_cache(maxsize=1000)
def contains(text: str) -> TextComparator:
    """返回包含指定文本的函数。"""
    func = lambda s: text in s
    return TextComparator("contains", text, func)

@lru_cache(maxsize=1000)
def equals(
    text: str,
    *,
    remove_space: bool = False,
    ignore_case: bool = True,
) -> TextComparator:
    """
    返回等于指定文本的函数。
    
    :param text: 要比较的文本。
    :param remove_space: 是否忽略空格。默认为 False。
    :param ignore_case: 是否忽略大小写。默认为 True。
    """
    def compare(s: str) -> bool:
        nonlocal text

        if ignore_case:
            text = text.lower()
            s = s.lower()
        if remove_space:
            text = text.replace(' ', '').replace('　', '')
            s = s.replace(' ', '').replace('　', '')

        return text == s
    return TextComparator("equals", text, compare)

def _is_match(text: str, pattern: re.Pattern | str | StringMatchFunction | TextComparator) -> bool:
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
    计算点集的外接矩形。

    :param points: 点集。以左上角为原点，向下向右为正方向。
    :return: 外接矩形的左上角坐标和宽高
    """
    topleft, bottomright = _bounding_box(points)
    return (topleft[0], topleft[1], bottomright[0] - topleft[0], bottomright[1] - topleft[1])

def pad_to(img: MatLike, target_size: int, rgb: tuple[int, int, int] = (255, 255, 255)) -> tuple[MatLike, tuple[int, int]]:
    """
    将图像居中填充到指定大小。缺少部分使用指定颜色填充。
    
    :return: 填充后的图像和填充的偏移量 (x, y)。
    """
    h, w = img.shape[:2]
    
    # 计算需要填充的宽高
    pad_h = max(0, target_size - h)
    pad_w = max(0, target_size - w)
    
    # 如果不需要填充则直接返回
    if pad_h == 0 and pad_w == 0:
        return img, (0, 0)
    
    # 创建目标画布并填充
    if len(img.shape) == 2:
        # 灰度图像
        ret = np.full((h + pad_h, w + pad_w), rgb[0], dtype=np.uint8)
    else:
        # RGB图像
        ret = np.full((h + pad_h, w + pad_w, 3), rgb, dtype=np.uint8)
    
    # 将原图像居中放置
    if len(img.shape) == 2:
        ret[
            pad_h // 2:pad_h // 2 + h,
            pad_w // 2:pad_w // 2 + w] = img
    else:
        ret[
            pad_h // 2:pad_h // 2 + h,
            pad_w // 2:pad_w // 2 + w, :] = img
    return ret, (pad_w // 2, pad_h // 2)

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
    ) -> OcrResultList:
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
            img, pos_in_padded_img = pad_to(img, 631)
        else:
            pos_in_padded_img = (0, 0)
        img_content = img
        result, elapse = self.__engine(img_content)
        if result is None:
            return OcrResultList()
        ret = []
        for r in result:
            # HACK: 识别结果中包含奇怪的符号，暂时替换掉
            text = unicodedata.normalize('NFKC', r[1]).replace('ą', 'a')
            # r[0] = [左上, 右上, 右下, 左下]
            # 这里有个坑，返回的点不一定是矩形，只能保证是四边形
            # 所以这里需要计算出四个点的外接矩形
            result_rect = tuple(int(x) for x in bounding_box(r[0])) # type: ignore
            # result_rect (x, y, w, h)
            if rect is not None:
                original_rect = (
                    result_rect[0] + rect[0] - pos_in_padded_img[0],
                    result_rect[1] + rect[1] - pos_in_padded_img[1],
                    result_rect[2],
                    result_rect[3]
                )
            else:
                original_rect = result_rect
            confidence = float(r[2])
            ret.append(OcrResult(
                text=text,
                rect=result_rect,
                original_rect=original_rect,
                confidence=confidence
            ))
        ret = OcrResultList(ret)
        if debug.enabled:
            result_image = _draw_result(img, ret)
            elapse = elapse or [0, 0, 0]
            debug_result(
                'ocr',
                [result_image, original_img],
                f"pad={pad}\n" + \
                f"rect={rect}\n" + \
                f"elapsed: det={elapse[0]:.3f}s cls={elapse[1]:.3f}s rec={elapse[2]:.3f}s\n" + \
                f"result: \n" + \
                "<table class='result-table'><tr><th>Text</th><th>Confidence</th></tr>" + \
                "\n".join([f"<tr><td>{r.text}</td><td>{r.confidence:.3f}</td></tr>" for r in ret]) + \
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
        识别图像中的文本，并寻找满足指定要求的文本。

        :param hint: 如果指定，则首先只识别 HintBox 范围内的文本，若未命中，再全局寻找。
        :param rect: 如果指定，则只识别指定矩形区域。此参数优先级低于 `hint`。
        :param pad: 见 `ocr` 的 `pad` 参数。
        :return: 找到的文本，如果未找到则返回 None
        """
        if hint is not None:
            if ret := self.find(img, text, rect=hint):
                logger.debug(f"find: {text} SUCCESS [hint={hint}]")
                return ret
            logger.debug(f"find: {text} FAILED [hint={hint}]")
        
        start_time = time.time()
        results = self.ocr(img, rect=rect, pad=pad)
        end_time = time.time()
        target = None
        for result in results:
            if _is_match(result.text, text):
                target = result
                break
        logger.debug(
            f"find: {text} {'SUCCESS' if target else 'FAILED'} " + \
            f"[elapsed={end_time - start_time:.3f}s] [rect={rect}]"
        )
        return target

    def find_all(
        self,
        img: 'MatLike',
        texts: list[str | re.Pattern | StringMatchFunction],
        *,
        hint: HintBox | None = None,
        rect: Rect | None = None,
        pad: bool = True,
    ) -> list[OcrResult | None]:
        """
        识别图像中的文本，并寻找多个满足指定要求的文本。

        :return:
            所有找到的文本，结果顺序与输入顺序相同。
            若某个文本未找到，则该位置为 None。
        """
        # HintBox 处理
        if hint is not None:
            result = self.find_all(img, texts, rect=hint, pad=pad)
            if all(result):
                return result

        ret: list[OcrResult | None] = []
        ocr_results = self.ocr(img, rect=rect, pad=pad)
        logger.debug(f"ocr_results: {ocr_results}")
        for text in texts:
            for result in ocr_results:
                if _is_match(result.text, text):
                    ret.append(result)
                    break
            else:
                ret.append(None)
        return ret
    
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
        识别图像中的文本，并寻找满足指定要求的文本。如果未找到则抛出异常。

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
    pass
