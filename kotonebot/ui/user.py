"""消息框、通知、推送等 UI 相关函数"""
import os
import time

import cv2
from cv2.typing import MatLike
from win11toast import toast

from .pushkit import Wxpusher
from .. import logging

logger = logging.getLogger(__name__)

def retry(func):
    """
    装饰器：当函数发生 ConnectionResetError 时自动重试三次
    """
    def wrapper(*args, **kwargs):
        for i in range(3):
            try:
                return func(*args, **kwargs)
            except ConnectionResetError:
                if i == 2:  # 最后一次重试失败
                    raise
                logger.warning(f'ConnectionResetError raised when calling {func}, retrying {i+1}/{3}')
                continue
    return wrapper

def _save_local(
    title: str,
    message: str,
    images: list[MatLike] | None = None
):
    """
    保存消息到本地
    """
    if not os.path.exists('messages'):
        os.makedirs('messages')
    file_name = f'messages/{time.strftime("%Y-%m-%d_%H-%M-%S")}'
    with open(file_name + '.txt', 'w', encoding='utf-8') as f:
        logger.verbose('saving message to local: %s', file_name + '.txt')
        f.write(message)
    if images is not None:
        for i, image in enumerate(images):
            logger.verbose('saving image to local: %s', f'{file_name}_{i}.png')
            cv2.imwrite(f'{file_name}_{i}.png', image)

@retry
def push(
    title: str,
    message: str | None = None,
    *,
    images: list[MatLike] | None = None
):
    """
    推送消息
    """
    message = message or ''
    try:
        logger.verbose('pushing to wxpusher: %s', message)
        wxpusher = Wxpusher()
        wxpusher.push(title, message, images=images)
    except Exception as e:
        logger.warning('push remote message failed: %s', e)
        _save_local(title, message, images)

def _show_toast(title: str, message: str | None = None, buttons: list[str] | None = None):
    """
    统一的 Toast 通知函数

    :param title: 通知标题
    :param message: 通知消息内容
    :param buttons: 按钮列表，如果提供则显示带按钮的通知
    """
    try:
        if buttons:
            logger.verbose('showing toast notification with buttons: %s - %s', title, message or '')
            toast(title, message or '', buttons=buttons)
        else:
            # 如果没有 message，只显示 title
            if message:
                logger.verbose('showing toast notification: %s - %s', title, message)
                toast(title, message)
            else:
                logger.verbose('showing toast notification: %s', title)
                toast(title)
    except Exception as e:
        logger.warning('toast notification failed: %s', e)

def ask(
    question: str,
    options: list[tuple[str, str]],
    *,
    timeout: float = -1,
) -> str:
    """
    询问用户
    """
    # 将选项转换为按钮列表
    buttons = [option[1] for option in options]
    _show_toast("琴音小助手询问", question, buttons=buttons)
    raise NotImplementedError

def info(
    title: str,
    message: str | None = None,
    images: list[MatLike] | None = None,
    *,
    once: bool = False
):
    logger.info('user.info: %s', message)
    push('KAA：' + title, message, images=images)
    _show_toast('KAA：' + title, message)

def warning(
    title: str,
    message: str | None = None,
    images: list[MatLike] | None = None,
    *,
    once: bool = False
):
    """
    警告信息。

    :param message: 消息内容
    :param once: 每次运行是否只显示一次。
    """
    logger.warning('user.warning: %s', message)
    push("琴音小助手警告：" + title, message, images=images)
    _show_toast("琴音小助手警告：" + title, message)

def error(
    title: str,
    message: str | None = None,
    images: list[MatLike] | None = None,
    *,
    once: bool = False
):
    """
    错误信息。
    """
    logger.error('user.error: %s', message)
    push("琴音小助手错误：" + title, message, images=images)
    _show_toast("琴音小助手错误：" + title, message)