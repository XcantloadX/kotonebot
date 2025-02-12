import os
from time import sleep
import cv2
from cv2.typing import MatLike
import numpy as np
from typing import NamedTuple
from kotonebot.client.fast_screenshot import AdbFastScreenshots

def path(file_name):
    return os.path.join(os.path.dirname(__file__), file_name)

def cv_imread(filePath):
    cv_img=cv2.imdecode(np.fromfile(filePath,dtype=np.uint8),-1)
    ## imdecode读取的是rgb，如果后续需要opencv处理的话，需要转换成bgr，转换后图片颜色会变化
    ##cv_img=cv2.cvtColor(cv_img,cv2.COLOR_RGB2BGR)
    return cv_img

def cv_imshow(name, img, overlay_msg: str = ''):
    scale = 0.5
    if overlay_msg:
        cv2.putText(img, overlay_msg, (10, img.shape[0] - 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.imshow(name, cv2.resize(img, (int(img.shape[1] * scale), int(img.shape[0] * scale))))

img = cv_imread(path(r".\0.png"))
img = cv_imread(path(r".\1.png"))
# img = cv_imread(r"E:\GithubRepos\KotonesAutoAssistant\screenshots\produce\action_study2.png")

def button(img, include_colors = []):
    # 转换到 HSV 颜色空间
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 定义白色的 HSV 范围
    # H: 色相接近0, S: 饱和度很低, V: 亮度较高
    lower_white = np.array([0, 0, 200])  
    upper_white = np.array([180, 30, 255])

    # 创建白色掩码
    white_mask = cv2.inRange(hsv, lower_white, upper_white)
    
    # 合并所有颜色的掩码
    final_mask = white_mask
    for color_range in include_colors:
        # 创建该颜色的掩码并合并
        color_mask = cv2.inRange(hsv, color_range[0], color_range[1])
        final_mask = cv2.bitwise_or(final_mask, color_mask)
        # final_mask = color_mask

    # 应用掩码到原图
    masked = cv2.bitwise_and(img, img, mask=final_mask)

    # 显示结果
    cv_imshow('Mask', final_mask)

    # 寻找轮廓
    contours, hierarchy = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 在原图上绘制轮廓的外接矩形并裁剪
    result_img = img.copy()
    cropped_imgs = []  # 存储裁剪后的图像
    for contour in contours:
        # 获取轮廓的外接矩形
        x, y, w, h = cv2.boundingRect(contour)
        # 计算宽高比和面积
        aspect_ratio = w / h
        area = cv2.contourArea(contour)
        # 只处理宽高比>=7且面积>=500的矩形
        if aspect_ratio >= 7 and area >= 500:
            cv2.rectangle(result_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            # 裁剪图像
            cropped = img[y:y+h, x:x+w]
            cropped_imgs.append(cropped)

    from kotonebot.backend.ocr import jp

    for btn in cropped_imgs:
        print(jp.ocr(btn))

    # 显示结果
    cv_imshow('Bounding Boxes', result_img)

def prompt_text(img):
    # 转换到 HSV 颜色空间
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 定义白色的 HSV 范围
    # H: 色相接近0, S: 饱和度很低, V: 亮度较高
    lower_white = np.array([0, 0, 200])  
    upper_white = np.array([180, 30, 255])

    # 创建掩码
    white_mask = cv2.inRange(hsv, lower_white, upper_white)

    # 应用掩码到原图
    white_only = cv2.bitwise_and(img, img, mask=white_mask)

    # 显示结果
    cv_imshow('White Mask', white_mask)

    # 寻找轮廓
    contours, hierarchy = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 在原图上绘制轮廓的外接矩形并裁剪
    result_img = img.copy()
    cropped_imgs = []  # 存储裁剪后的图像
    for contour in contours:
        # 获取轮廓的外接矩形
        x, y, w, h = cv2.boundingRect(contour)
        # 计算宽高比和面积
        aspect_ratio = w / h
        area = cv2.contourArea(contour)
        # 只处理宽高比>=7且面积>=500的矩形
        if aspect_ratio >= 3 and area >= 100:
            cv2.rectangle(result_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
            # 裁剪图像
            cropped = img[y:y+h, x:x+w]
            cropped_imgs.append(cropped)
    
    cv_imshow('Bounding Boxes', result_img)

def web2cv(hsv):
    return (int(hsv[0]/360*180), int(hsv[1]/100*255), int(hsv[2]/100*255))

from kotonebot.backend.context import init_context, manual_context, device
init_context()
manual_context().begin()
PINK_TARGET = (335, 78, 95)
PINK_LOW = (300, 70, 90)
PINK_HIGH = (350, 80, 100)
button(device.screenshot(), [
    (web2cv(PINK_LOW), web2cv(PINK_HIGH))
])
# prompt_text(device.screenshot())

cv2.waitKey(0)