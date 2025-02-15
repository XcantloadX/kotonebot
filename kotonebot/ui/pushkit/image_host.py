import os
import tempfile
from pathlib import Path
from typing import Sequence

import cv2
import requests
import numpy as np
from cv2.typing import MatLike
from dotenv import load_dotenv

load_dotenv()

def _save_temp_image(image: MatLike) -> Path:
    """将OpenCV图片保存为临时文件"""
    temp_file = Path(tempfile.mktemp(suffix='.jpg'))
    cv2.imwrite(str(temp_file), image)
    return temp_file

def _upload_single(image: MatLike | str) -> str:
    """
    上传单张图片到freeimage.host
    
    :param image: OpenCV MatLike 或本地图片文件路径
    """
    api_url = 'https://freeimage.host/api/1/upload'
    api_key = os.getenv('FREEIMAGEHOST_KEY')
    
    if not api_key:
        raise RuntimeError('Environment variable FREEIMAGEHOST_KEY is not set')
    
    # 处理输入
    temp_file = None
    if isinstance(image, str):
        # 本地文件路径
        files = {'source': open(image, 'rb')}
    else:
        # 保存OpenCV图片为临时文件
        temp_file = _save_temp_image(image)
        files = {'source': open(temp_file, 'rb')}
    
    data = {
        'key': api_key,
        'action': 'upload',
        'format': 'json'
    }
    
    try:
        # 发送POST请求
        response = requests.post(api_url, data=data, files=files)
        
        if response.status_code != 200:
            raise RuntimeError(f'Upload failed: HTTP {response.status_code}')
            
        result = response.json()
        
        if result['status_code'] != 200:
            raise RuntimeError(f'Upload failed: API {result["status_txt"]}')
            
        return result['image']['url']
        
    finally:
        # 清理临时文件
        files['source'].close()
        if temp_file and temp_file.exists():
            temp_file.unlink()

def upload(images: MatLike | str | Sequence[MatLike | str]) -> list[str]:
    """上传一张或多张图片到freeimage.host
    
    Args:
        images: 单张图片或图片列表。每个图片可以是OpenCV图片对象或本地图片文件路径
        
    Returns:
        上传后的图片URL列表
    """
    if isinstance(images, (str, np.ndarray)):
        _images = [images]
    elif isinstance(images, Sequence):
        _images = [img for img in images]
    else:
        raise ValueError("Invalid input type")
        
    return [_upload_single(img) for img in _images]

if __name__ == "__main__":
    print(upload(cv2.imread("res/sprites/jp/common/button_close.png")))
