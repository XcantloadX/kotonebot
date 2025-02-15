import os
import json
from typing import Sequence
import requests
from cv2.typing import MatLike
from dotenv import dotenv_values

from .image_host import upload
from .protocol import PushkitProtocol

config = dotenv_values(".env")

class Wxpusher(PushkitProtocol):
    def __init__(self, app_token: str | None = None, uid: str | None = None):
        self.app_token = app_token or config["WXPUSHER_APP_TOKEN"]
        self.uid = uid or config["WXPUSHER_UID"]

    def push(self, title: str, message: str, *, images: Sequence[str | MatLike] | None = None) -> None:
        summary = title
        content = message

        if images:
            image_urls = upload(images)
            img_md = "\n".join([f"![{img_url}]({img_url})" for img_url in image_urls])
            content = content + "\n" + img_md

        data = {
            "appToken": self.app_token,
            "uid": self.uid,
            "summary": summary,
            "content": content,
            "contentType": 3, # 1: 文本 2: HTML 3: Markdown
            "uids": [self.uid],
            "verifyPay": False,
            "verifyPayType": 0
        }

        response = requests.post(
            "http://wxpusher.zjiecode.com/api/send/message",
            json=data
        )
        result = response.json()
        
        if result["code"] != 1000 or not result["success"]:
            raise RuntimeError(f"推送失败: {result['msg']}")

# TODO: 极简推送 https://wxpusher.zjiecode.com/docs/#/?id=spt
        
if __name__ == "__main__":
    import cv2
    wxpusher = Wxpusher()
    wxpusher.push("测试图片", "测试图片", images=[cv2.imread("res/sprites/jp/common/button_close.png")])

