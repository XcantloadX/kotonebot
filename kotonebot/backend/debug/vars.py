import os
import re
import json
import time
import uuid
import shutil
import psutil
import logging
import hashlib
import traceback
from pathlib import Path
from functools import cache
from datetime import datetime
from dataclasses import dataclass
from typing import NamedTuple, TextIO, Literal

import cv2
from cv2.typing import MatLike
from pydantic import BaseModel
import inspect  # 添加此行以导入 inspect 模块

from ..core import Image
from ...util import cv2_imread

logger = logging.getLogger(__name__)

class Result(NamedTuple):
    title: str
    image: list[str]
    description: str
    timestamp: float

class ImageData(NamedTuple):
    data: MatLike
    timestamp: float

class WSImage(BaseModel):
    type: Literal["memory"]
    value: list[str]

class WSCallstack(BaseModel):
    name: str
    file: str
    line: int
    code: str
    type: Literal["function", "method", "module", "lambda"]
    url: str | None

class WSMessageData(BaseModel):
    image: WSImage
    name: str
    details: str
    timestamp: int
    callstack: list[WSCallstack]
    

class WSMessage(BaseModel):
    type: Literal["visual"]
    data: WSMessageData

@dataclass
class _Vars:
    """调试变量类"""
    enabled: bool = False
    """是否启用调试结果显示。"""

    max_results: int = -1
    """最多保存的结果数量。-1 表示不限制。"""

    wait_for_message_sent: bool = False
    """
    是否等待消息发送完成才继续后续代码。

    默认禁用。启用此选项会显著降低运行速度。
    """
    
    hide_server_log: bool = True
    """是否隐藏服务器日志。"""

    auto_save_to_folder: str | None = None
    """
    是否将结果自动保存到指定文件夹。
    
    如果为 None，则不保存。
    """

    hash_image: bool = True
    """
    是否使用图片的 MD5 值作为图片的唯一标识。
    若禁用，则使用随机 UUID 作为图片的唯一标识
    （可能会导致保存大量重复图片）。
    
    此选项默认启用。启用此选项会轻微降低调试时运行速度。
    """

debug = _Vars()

_results: dict[str, Result] = {}
_images: dict[str, ImageData] = {}
"""存放临时图片的字典。"""
_result_file: TextIO | None = None

def _save_image(image: MatLike | Image) -> str:
    """缓存图片数据到 _images 字典中。返回 key。"""
    if isinstance(image, Image):
        image = image.data
    # 计算 key
    if debug.hash_image:
        key = hashlib.md5(image.tobytes()).hexdigest()
    else:
        key = str(uuid.uuid4())
    # 保存图片
    if key not in _images:
        _images[key] = ImageData(image, time.time())
        if debug.auto_save_to_folder:
            if not os.path.exists(debug.auto_save_to_folder):
                os.makedirs(debug.auto_save_to_folder)
            file_name = f"{key}.png"
            cv2.imwrite(os.path.join(debug.auto_save_to_folder, file_name), image)
    # 当图片 >= 100 张时，删除最早的图片
    while len(_images) >= 100:
        logger.info("Debug image buffer is full. Deleting oldest image...")
        _images.pop(next(iter(_images)))
    return key

def _read_image(key: str) -> MatLike | None:
    """从 _images 字典中读取图片。"""
    data = None
    if key in _images:
        data = _images[key].data
    elif debug.auto_save_to_folder:
        path = os.path.join(debug.auto_save_to_folder, f"{key}.png")
        if os.path.exists(path):
            data = cv2_imread(path)
            _images[key] = ImageData(data, time.time())
    return data

def _save_images(images: list[MatLike]) -> list[str]:
    """缓存图片数据到 _images 字典中。返回 key 列表。"""
    return [_save_image(image) for image in images]

def img(image: str | MatLike | Image | None) -> str:
    """
    用于在 `result()` 函数中嵌入图片。

    :param image: 图片路径或 OpenCV 图片对象。
    :return: 图片的 HTML 代码。
    """
    if image is None:
        return 'None'
    if debug.auto_save_to_folder:
        if isinstance(image, str):
            image = cv2_imread(image)
        elif isinstance(image, Image):
            image = image.data
        key = _save_image(image)
        return f'[img]{key}[/img]'
    else:
        if isinstance(image, str):
            return f'<img src="/api/read_file?path={image}" />'
        elif isinstance(image, Image) and image.path:
            return f'<img src="/api/read_file?path={image.path}" />'
        else:
            key = _save_image(image)
            return f'<img src="/api/read_memory?key={key}" />'

def color(color: str | tuple[int, int, int] | None) -> str:
    """
    用于在调试结果中嵌入颜色。
    """
    if color is None:
        return 'None'
    if isinstance(color, tuple):
        color = '#{:02X}{:02X}{:02X}'.format(color[0], color[1], color[2])
        return f'<kbd-color style="display:inline-block; white-space:initial;" color="{color}"></kbd-color>'
    else:
        return f'<kbd-color style="display:inline-block; white-space:initial;" color="{color}"></kbd-color>'

def to_html(text: str) -> str:
    """将文本转换为 HTML 代码。"""
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('\n', '<br>')
    text = text.replace(' ', '&nbsp;')
    return text

IDEType = Literal['vscode', 'cursor', 'windsurf']

@cache
def get_current_ide() -> IDEType | None:
    """获取当前IDE类型"""
    me = psutil.Process()
    while True:
        parent = me.parent()
        if parent is None:
            break
        name = parent.name()
        if name.lower() == 'code.exe':
            return 'vscode'
        elif name.lower() == 'cursor.exe':
            return 'cursor'
        elif name.lower() == 'windsurf.exe':
            return 'windsurf'
        me = parent
    return None

def _make_code_file_url(
    text: str,
    full_path: str,
    line: int = 0,
) -> str:
    """
    将代码文本转换为 VSCode 的文件 URL。
    """
    ide = get_current_ide()
    if ide == 'vscode':
        prefix = 'vscode'
    elif ide == 'cursor':
        prefix = 'cursor'
    elif ide == 'windsurf':
        prefix = 'windsurf'
    else:
        return text
    url = f"{prefix}://file/{full_path}:{line}:0"
    return f'<a href="{url}">{text}</a>'

def _make_code_file_url_only(
    text: str,
    full_path: str,
    line: int = 0,
) -> str:
    """
    将代码文本转换为 VSCode 的文件 URL。
    """
    ide = get_current_ide()
    if ide == 'vscode':
        prefix = 'vscode'
    elif ide == 'cursor':
        prefix = 'cursor'
    elif ide == 'windsurf':
        prefix = 'windsurf'
    else:
        return text
    return f"{prefix}://file/{full_path}:{line}:0"

def result(
        title: str,
        image: MatLike | list[MatLike],
        text: str = ''
    ):
    """
    显示图片结果。

    例：
    ```python
    result(
        "image.find",
        image,
        f"template: {img(template)} \\n"
        f"matches: {len(matches)} \\n"
    )
    ```
    
    :param title: 标题。建议使用 `模块.方法` 格式。
    :param image: 图片。
    :param text: 详细文本。可以是 HTML 代码，空格和换行将会保留。如果需要嵌入图片，使用 `img()` 函数。
    """
    global _result_file
    if not debug.enabled:
        return
    if not isinstance(image, list):
        image = [image]
    
    key = 'result_' + title + '_' + str(time.time())
    # 保存图片
    saved_images = _save_images(image)
    current_timestamp = int(time.time() * 1000)
    _results[key] = Result(title, saved_images, text, current_timestamp)
    if len(_results) > debug.max_results:
        _results.pop(next(iter(_results)))
    # 拼接消息
    
    callstacks: list[WSCallstack] = []
    for frame in inspect.stack():
        frame_info = frame.frame
        # 跳过标准库和 debugpy 的代码
        if re.search(r'Python\d*[\/\\]lib|debugpy', frame_info.f_code.co_filename):
            break
        lineno = frame_info.f_lineno
        code = frame_info.f_code.co_name
        # 判断第一个参数是否为 self
        if frame_info.f_code.co_argcount > 0 and frame_info.f_code.co_varnames[0] == 'self':
            type = 'method'
        elif '<module>' in code:
            type = 'module'
        elif '<lambda>' in code:
            type = 'lambda'
        else:
            type = 'function'  # 默认类型为 function
        callstacks.append(WSCallstack(
            name=frame_info.f_code.co_name,
            file=frame_info.f_code.co_filename,
            line=lineno,
            code=code,
            url=_make_code_file_url_only(frame_info.f_code.co_filename, frame_info.f_code.co_filename, lineno),
            type=type
        ))

    final_text = text
    # 发送 WS 消息
    from .server import send_ws_message
    send_ws_message(title, saved_images, final_text, callstack=callstacks, wait=debug.wait_for_message_sent)
    
    # 保存到文件
    if debug.auto_save_to_folder:
        if _result_file is None:
            if not os.path.exists(debug.auto_save_to_folder):
                os.makedirs(debug.auto_save_to_folder)
            log_file_name = f"dump_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
            _result_file = open(os.path.join(debug.auto_save_to_folder, log_file_name), "w", encoding="utf-8")
        message = WSMessage(
            type="visual",
            data=WSMessageData(
                image=WSImage(type="memory", value=saved_images),
                name=title,
                details=final_text,
                timestamp=current_timestamp,
                callstack=callstacks
            )
        )
        _result_file.write(message.model_dump_json())
        _result_file.write("\n")
        _result_file.flush()

def clear_saved():
    """
    清空本地保存文件夹中的内容。
    """
    logger.info("Clearing debug saved files...")
    if debug.auto_save_to_folder:
        try:
            shutil.rmtree(debug.auto_save_to_folder, ignore_errors=True)
            logger.info(f"Cleared debug saved files: {debug.auto_save_to_folder}")
        except PermissionError:
            logger.error(f"Failed to clear debug saved files: {debug.auto_save_to_folder}")
    else:
        logger.info("No auto save folder, skipping...")
