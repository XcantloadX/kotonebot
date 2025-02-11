import time
import cv2

from kotonebot.client.protocol import DeviceABC
from kotonebot import sleep
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

class MockDevice(DeviceABC):
    def __init__(
        self
    ):
        self.__video_stream = None

    def load_video(self, path: str, fps: int):
        self.__video_stream = Video(path, fps)
        return self.__video_stream

    def screenshot(self):
        if self.__video_stream:
            return next(self.__video_stream)
        else:
            raise RuntimeError('No video stream loaded')