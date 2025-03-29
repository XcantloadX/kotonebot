from time import sleep
import cv2
from cv2.typing import MatLike
import numpy as np
from typing import NamedTuple
from kotonebot.client.fast_screenshot import AdbFastScreenshots


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


def process(img, name):
    original_img = img.copy()


    # 转换为HSV颜色空间
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)


    # 目标HSV值: H=51°, S=46%, V=98%
    # OpenCV中H范围是0-180,S和V是0-255
    # 所以需要转换:
    # H: 51° -> 28.33 (51/360*180)
    # S: 46% -> 117 (46/100*255) 
    # V: 98% -> 250 (98/100*255)

    # upper_h = int(60/360*180)
    # upper_s = int(100/100*255)
    # upper_v = int(100/100*255)

    # lower_h = int(45/360*180)
    # lower_s = int(60/100*255)
    # lower_v = int(60/100*255)

    lower_h, lower_s, lower_v = 20, 100, 100
    upper_h, upper_s, upper_v = 30, 255, 255

    # 创建掩码
    lower = np.array([lower_h, lower_s, lower_v])
    upper = np.array([upper_h, upper_s, upper_v])
    mask = cv2.inRange(hsv, lower, upper)



    # 应用掩码
    result = cv2.bitwise_and(img, img, mask=mask)

    # 显示结果
    # 水平拼接两张图片
    combined = np.hstack((img, result))
    return result, combined


# images = [
#     cv_imread(r"D:\1.png"),
#     cv_imread(r"D:\2.png"),
#     cv_imread(r"D:\3.png"),
#     cv_imread(r"D:\4.png"),
# ]
# for i, img in enumerate(images):
#     process(img, f'{i}')

# cv2.waitKey(0)
# cv2.destroyAllWindows()



def stream_mp4(video: str, fps: int):
    cap = cv2.VideoCapture(video)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        sleep(1 / fps)
        yield frame

def stream_device():
    while True:
        img = device.screenshot()
        yield img

def fast_screenshot():
    with AdbFastScreenshots(
        adb_path=r"D:\SDK\Android\platform-tools\adb.exe",
        device_serial="127.0.0.1:5555",
        time_interval=179,
        width=720,
        height=1280,
        bitrate="10M",
        use_busybox=False,
        connect_to_device=True,
        screenshotbuffer=10,
        go_idle=0,
    ) as adbscreen:
        for image in adbscreen:
            yield image

# Converts BGR to CMYK (as a tuple of 4 arrays)
def bgr2cmky(bgrImage):
    bgrdash = bgrImage.astype(float) / 255.
    # Calculate K as (1 - whatever is biggest out of Rdash, Gdash, Bdash)
    K = 1 - np.max(bgrdash, axis=2)

    # Calculate C
    C = (1 - bgrdash[..., 2] - K) / (1 - K)
    C  = 255 * C
    C  = C .astype(np.uint8)

    # Calculate M
    M = (1 - bgrdash[..., 1] - K) / (1 - K)
    M  = 255 * M
    M  = M.astype(np.uint8)

    # Calculate Y
    Y = (1 - bgrdash[..., 0] - K) / (1 - K)
    Y  = 255 * Y
    Y  = Y.astype(np.uint8)

    return (C, M, Y, K)

class CardDetectResult(NamedTuple):
    type: int
    score: float
    left_score: float
    right_score: float
    top_score: float
    bottom_score: float

def calc(image: MatLike, card_count: int):
    YELLOW_LOWER = np.array([15, 80, 80])
    YELLOW_UPPER = np.array([35, 255, 255])
    CARD_POSITIONS_1 = [
        # 格式：(x, y, w, h, return_value)
        (264, 883, 192, 252, 0)
    ]
    CARD_POSITIONS_2 = [
        (156, 883, 192, 252, 1),
        (372, 883, 192, 252, 2),
        # delta_x = 216, delta_x-width = 24
    ]
    CARD_POSITIONS_3 = [
        (47, 883, 192, 252, 0),  # 左卡片 (x, y, w, h)
        (264, 883, 192, 252, 1),  # 中卡片
        (481, 883, 192, 252, 2)   # 右卡片
        # delta_x = 217, delta_x-width = 25
    ]
    CARD_POSITIONS_4 = [
        (17, 883, 192, 252, 0),
        (182, 883, 192, 252, 1),
        (346, 883, 192, 252, 2),
        (511, 883, 192, 252, 3),
        # delta_x = 165, delta_x-width = -27
    ]
    SKIP_POSITION = (621, 739, 85, 85, 10)
    GLOW_EXTENSION = 15

    if card_count == 1:
        cards = CARD_POSITIONS_1
    elif card_count == 2:
        cards = CARD_POSITIONS_2
    elif card_count == 3:
        cards = CARD_POSITIONS_3
    elif card_count == 4:
        cards = CARD_POSITIONS_4
    else:
        raise ValueError(f"Unsupported card count: {card_count}")
    cards.append(SKIP_POSITION)

    
    results = []
    for ix, (x, y, w, h, return_value) in enumerate(cards):
        outer = (max(0, x - GLOW_EXTENSION), max(0, y - GLOW_EXTENSION))
        inner = (x + w, y + h)
        outer_pixels = (outer[0] - inner[0]) * (outer[1] - inner[1])
        inner_pixels = w * h
        # 裁剪出检测区域
        glow_area = image[outer[1]:y + h + GLOW_EXTENSION, outer[0]:x + w + GLOW_EXTENSION]
        area_h = glow_area.shape[0]
        area_w = glow_area.shape[1]
        glow_area[GLOW_EXTENSION:area_h-GLOW_EXTENSION, GLOW_EXTENSION:area_w-GLOW_EXTENSION] = 0
        _glow = glow_area.copy()

        # 计算黄色值
        glow_area = cv2.cvtColor(glow_area, cv2.COLOR_BGR2HSV)
        yellow_mask = cv2.inRange(glow_area, YELLOW_LOWER, YELLOW_UPPER)
        # 排除 #edf37b (237, 243, 123) BGR
        # 在 HSV 空间中大约是 (63, 147, 243)
        # (57, 80%, 98%) -> (57, 204, 250)
        exclude_mask = cv2.inRange(glow_area, np.array([50, 100, 100]), np.array([60, 220, 255]))
        yellow_mask = cv2.bitwise_and(yellow_mask, cv2.bitwise_not(exclude_mask))
        _masked = cv2.bitwise_and(_glow, _glow, mask=yellow_mask)
        cv_imshow(str(return_value), np.hstack((_glow, _masked)))
        # cv_imshow("detect_area " + str(ix), yellow_mask)
        
        left_border = yellow_mask[:, 0:GLOW_EXTENSION]
        right_border = yellow_mask[:, area_w-GLOW_EXTENSION:area_w]
        top_border = yellow_mask[0:GLOW_EXTENSION, :]
        bottom_border = yellow_mask[area_h-GLOW_EXTENSION:area_h, :]
        y_border_pixels = area_h * GLOW_EXTENSION
        x_border_pixels = area_w * GLOW_EXTENSION

        left_score = np.count_nonzero(left_border) / y_border_pixels
        right_score = np.count_nonzero(right_border) / y_border_pixels
        top_score = np.count_nonzero(top_border) / x_border_pixels
        bottom_score = np.count_nonzero(bottom_border) / x_border_pixels

        result = (left_score + right_score + top_score + bottom_score) / 4

        results.append(CardDetectResult(
            return_value,
            result,
            left_score,
            right_score,
            top_score,
            bottom_score
        ))


    results.sort(key=lambda x: x.score, reverse=True)
    def print_result(result):
        # round to 3 decimal places
        new_results = []
        for result in results:
            result = tuple(round(x, 3) for x in result)
            new_results.append(result)
        print(new_results)

    # print_result(results)
    if results[0].score > 0.1 and (
        results[0].left_score > 0.01 and results[0].right_score > 0.01 and
        results[0].top_score > 0.01 and results[0].bottom_score > 0.01
    ):
        print_result(results)
        # if results[0].type != 1:
        #     while True:
        #         if cv2.waitKey(1) & 0xFF == ord('q'):
        #             break






from kotonebot.backend.debug.mock import MockDevice
from kotonebot.backend.context import device, init_context, manual_context
from kotonebot.backend.util import Profiler
init_context()
mock = MockDevice()
vid = mock.load_video(r'D:\end.mp4', 60)
# inject_context(device=mock)
ctx = manual_context()

ctx.begin()
result = None

profiler = Profiler(file_path='profiler')
profiler.begin()
# sd = wait_card_stable2()
for img in stream_device():
    new_result, combined = process(img, 'screenshot')
    # 将结果累加
    if result is not None:
        result = cv2.add(result, new_result)
    else:
        result = new_result
    overlay_msg = ''
    # overlay_msg += f'skill_card_count: {skill_card_count()}'
    # stable = next(sd, None)
    # print(stable)
    # overlay_msg += f'wait_card_stable2: {stable}'
    # if stable == True:
    #     sd = wait_card_stable2()
    # cv_imshow('result', result)
    cv_imshow('combined', combined, overlay_msg)
    
    # (C, M, Y, K) = bgr2cmky(img)

    # Show K:
    # cv_imshow("Y", Y)
    calc(img, 3)

    if cv2.waitKey(1) & 0xFF == ord('q'):

        break
profiler.end()
cv2.destroyAllWindows()
profiler.snakeviz()

ctx.end()
