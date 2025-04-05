import time
from typing_extensions import override

import cv2
from cv2.typing import MatLike

from kotonebot import sleep
from kotonebot.client.device import Device

class Video:
    def __init__(self, path: str, fps: int):
        self.path = path
        self.fps = fps
        self.paused = False
        """是否暂停"""
        self.__cap = cv2.VideoCapture(path)
        self.__last_frame = None
        self.__last_time = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.paused:
            return self.__last_frame
        ret, frame = self.__cap.read()
        if not ret:
            raise StopIteration
        self.__last_frame = frame
        self.__last_time = time.time()
        if self.__last_time - time.time() < 1 / self.fps:
            sleep(1 / self.fps)
        return frame

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

class MockDevice(Device):
    def __init__(
        self
    ):
        super().__init__()
        self.__video_stream = None
        self.__image = None
        self.__screen_size = None

    def load_video(self, path: str, fps: int):
        self.__video_stream = Video(path, fps)
        return self.__video_stream

    def load_image(self, img: str | MatLike):
        if isinstance(img, str):
            self.__image = cv2.imread(img)
        else:
            self.__image = img
        return self.__image

    def set_screen_size(self, width: int, height: int):
        self.__screen_size = (width, height)

    @override
    def screenshot(self):
        if self.__image is not None:
            return self.__image
        elif self.__video_stream is not None:
            return next(self.__video_stream)
        else:
            raise RuntimeError('No video stream loaded')
        
    @property
    @override
    def screen_size(self):
        if self.__screen_size is not None:
            return self.__screen_size
        else:
            raise RuntimeError('No screen size set')