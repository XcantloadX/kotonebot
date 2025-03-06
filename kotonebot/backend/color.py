import colorsys
from typing import Literal
from dataclasses import dataclass

import numpy as np
import cv2
from cv2.typing import MatLike

from .core import unify_image
from .debug import result as debug_result, debug, color as debug_color
from ..util import Rect

RgbColorTuple = tuple[int, int, int]
RgbColorStr = str
RgbColor = RgbColorTuple | RgbColorStr
"""颜色。三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`"""

HsvColor = tuple[int, int, int]
"""
HSV颜色。三元组 `(h, s, v)`。
"""

@dataclass
class FindColorPointResult:
    position: tuple[int, int]
    confidence: float
    target_color: RgbColor

def hsv_web2cv(h: int, s: int, v: int) -> 'HsvColor':
    """
    将 HSV 颜色从 Web 格式转换为 OpenCV 格式。
    
    :param h: 色相，范围 [0, 360]
    :param s: 饱和度，范围 [0, 100]
    :param v: 亮度，范围 [0, 100]
    :return: OpenCV 格式 HSV 颜色。三元组 `(h, s, v)`，范围分别为 (0-180, 0-255, 0-255)。
    """
    h = round(h / 2)  # web 的色相范围是 0-360，转为 0-180
    s = round(s / 100 * 255)  # web 的饱和度范围是 0-100，转为 0-255
    v = round(v / 100 * 255)  # web 的亮度范围是 0-100，转为 0-255
    return (h, s, v)

def hsv_cv2web(h: int, s: int, v: int) -> 'HsvColor':
    """
    将 HSV 颜色从 OpenCV 格式转换为 Web 格式。
    
    :param h: 色相，范围 [0, 180]
    :param s: 饱和度，范围 [0, 255]
    :param v: 亮度，范围 [0, 255]
    :return: Web 格式 HSV 颜色。三元组 `(h, s, v)`，范围分别为 (0-360, 0-100, 0-100)。
    """
    h = round(h * 2)  # opencv 的色相范围是 0-180，转为 0-360
    s = round(s / 255 * 100)  # opencv 的饱和度范围是 0-255，转为 0-100
    v = round(v / 255 * 100)  # opencv 的亮度范围是 0-255，转为 0-100
    return (h, s, v)

def rgb_to_hsv(c: RgbColor) -> 'HsvColor':
    """
    将 RGB 颜色转换为 HSV 颜色。

    :param c: RGB 颜色。十六进制颜色字符串 `#RRGGBB` 或整数三元组 `(r, g, b)`。
    :return: Web 格式 HSV 颜色。三元组 `(h, s, v)`，范围分别为 (0-360, 0-100, 0-100)。
    """
    c = _unify_color(c)
    ret = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)
    return (round(ret[0] * 360), round(ret[1] * 100), round(ret[2] * 100))

def hsv_to_rgb(c: HsvColor) -> 'RgbColor':
    """
    将 HSV 颜色转换为 RGB 颜色。

    :param c: Web 格式 HSV 颜色。三元组 `(h, s, v)`，范围分别为 (0-360, 0-100, 0-100)。
    :return: RGB 颜色。整数三元组 `(r, g, b)`。
    """
    ret = colorsys.hsv_to_rgb(c[0] / 360, c[1] / 100, c[2] / 100)
    return (round(ret[0] * 255), round(ret[1] * 255), round(ret[2] * 255))

def _unify_color(color: RgbColor) -> RgbColorTuple:
    if isinstance(color, str):
        if not color.startswith('#'):
            raise ValueError('Hex color string must start with #')
        color = color[1:]  # 去掉#
        if len(color) != 6:
            raise ValueError('Hex color string must be 6 digits')
        r = int(color[0:2], 16)
        g = int(color[2:4], 16) 
        b = int(color[4:6], 16)
        return (r, g, b)
    elif (
        isinstance(color, tuple)
        and len(color) == 3
        and all(isinstance(c, int) for c in color)
        and all(0 <= c <= 255 for c in color)
    ):
        return color
    else:
        raise ValueError('Invalid color format')

def in_range(color: RgbColor, range: tuple[HsvColor, HsvColor]) -> bool:
    """
    判断颜色是否在范围内。

    :param color: RGB 颜色。
    :param range: Web HSV 颜色范围。
    """
    h, s, v = rgb_to_hsv(color)
    h1, s1, v1 = range[0]
    h2, s2, v2 = range[1]
    return h1 <= h <= h2 and s1 <= s <= s2 and v1 <= v <= v2

def find(
    image: MatLike | str,
    color: RgbColor,
    *,
    rect: Rect | None = None,
    threshold: float = 0.95,
    method: Literal['rgb_dist'] = 'rgb_dist',
) -> tuple[int, int] | None:
    """
    在图像中查找指定颜色的点。

    :param image: 
        图像。可以是 MatLike 或图像文件路径。
        注意如果参数为 MatLike，则颜色格式必须为 BGR，而不是 RGB。
    :param color: 颜色。可以是整数三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`。
    :param rect: 查找范围。如果为 None，则在整个图像中查找。
    :param threshold: 阈值，越大表示越相似，1 表示完全相似。默认为 0.95。
    :param method: 比较算法。默认为 'rgb_dist'，且目前也只有这个方法。

    ## 比较算法
    * rgb_dist:
        计算图片中每个点的颜色到目标颜色的欧氏距离，并以 442 为最大值归一化到 0-1 之间。
    """
    ret = None
    ret_similarity = 0
    found_color = None
    color = _unify_color(color)
    image = unify_image(image)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    # 将目标颜色转换为HSL
    r, g, b = color
    target_rgb = np.array([[[r, g, b]]], dtype=np.uint8)
    target_hls = cv2.cvtColor(target_rgb, cv2.COLOR_RGB2HLS)[0,0]
    target_h, target_l, target_s = target_hls

    # 将图像转换为HSL
    image_hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS).astype(np.float32)
    
    # 计算HSL空间中的距离
    # H通道需要特殊处理,因为它是环形的(0和180是相邻的)
    h_diff = np.minimum(
        np.abs(image_hls[:,:,0] - target_h),
        180 - np.abs(image_hls[:,:,0] - target_h)
    )
    l_diff = np.abs(image_hls[:,:,1] - target_l)
    s_diff = np.abs(image_hls[:,:,2] - target_s)
    
    # 归一化距离(H:0-180, L:0-255, S:0-255)
    h_diff = h_diff / 90  # 最大差值180/2
    l_diff = l_diff / 255
    s_diff = s_diff / 255
    
    # 计算加权距离
    dist = np.sqrt((h_diff * 2)**2 + l_diff**2 + s_diff**2) / np.sqrt(6)
    
    # 寻找结果
    matches: np.ndarray = dist <= (1 - threshold)
    # 只在rect范围内搜索
    if rect is not None:
        x, y, w, h = rect
        search_area = matches[y:y+h, x:x+w]
        if search_area.any():
            # 在裁剪区域中找到最小距离的点
            local_dist = dist[y:y+h, x:x+w]
            local_dist[~search_area] = float('inf')
            min_y, min_x = np.unravel_index(np.argmin(local_dist), local_dist.shape)
            # 转换回原图坐标
            ret = (int(x + min_x), int(y + min_y))
            ret_similarity = 1 - local_dist[min_y, min_x]
            found_color = tuple(image_rgb[y+min_y, x+min_x])
    # 在全图中找到最小距离的点
    else:
        if matches.any():
            dist[~matches] = float('inf')
            min_y, min_x = np.unravel_index(np.argmin(dist), dist.shape)
            ret = (int(min_x), int(min_y))
            ret_similarity = 1 - dist[min_y, min_x]
            found_color = tuple(image_rgb[min_y, min_x])
    # 调试输出
    if debug.enabled:
        result_image = image.copy()
        # 绘制结果点
        if ret is not None:
            x, y = ret
            # 蓝色圈出结果点
            cv2.rectangle(result_image, 
                (max(0, x-20), max(0, y-20)),
                (min(result_image.shape[1], x+20), min(result_image.shape[0], y+20)),
                (255, 0, 0), 2)
        # 绘制搜索范围
        if rect is not None:
            x, y, w, h = rect
            # 红色圈出rect
            cv2.rectangle(result_image, (x, y), (x+w, y+h), (0, 0, 255), 2)
        debug_result(
            'find_rgb',
            [result_image, image],
            f'target={debug_color(color)}\n'
            f'rect={rect}\n'
            f'result={ret}\n'
            f'similarity={ret_similarity}\n'
            f'found_color={debug_color(found_color)}\n'
            '(Red rect for search area, blue rect for result area)'
        )
    return ret

def color_distance_map(
    image: MatLike | str,
    color: RgbColor,
    *,
    rect: Rect | None = None,
) -> np.ndarray:
    """
    计算图像中每个像素点到目标颜色的HSL距离，并返回归一化后的距离矩阵。
    
    :param image: 图像。可以是 MatLike 或图像文件路径。
    :param color: 目标颜色。可以是整数三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`。
    :param rect: 计算范围。如果为 None，则在整个图像中计算。
    :return: 归一化后的距离矩阵，范围 [0, 1]，0 表示完全匹配，1 表示完全不匹配。
    """
    # 统一颜色格式
    color = _unify_color(color)
    # 统一图像格式
    image = unify_image(image)
    
    # # 如果指定了rect，裁剪图像
    if rect is not None:
        x, y, w, h = rect
        image = image[y:y+h, x:x+w]

    # 将图像转换为HLS格式
    image_hls = cv2.cvtColor(image, cv2.COLOR_BGR2HLS).astype(np.float32)
    
    # 将目标颜色转换为HSL
    r, g, b = color
    target_rgb = np.array([[[r, g, b]]], dtype=np.uint8)
    target_hls = cv2.cvtColor(target_rgb, cv2.COLOR_RGB2HLS)[0,0]
    target_h, target_l, target_s = target_hls
    
    # 计算HSL空间中的距离
    # H通道需要特殊处理,因为它是环形的(0和180是相邻的)
    h_diff = np.minimum(
        np.abs(image_hls[:,:,0] - target_h),
        180 - np.abs(image_hls[:,:,0] - target_h)
    )
    l_diff = np.abs(image_hls[:,:,1] - target_l)
    s_diff = np.abs(image_hls[:,:,2] - target_s)
    
    # 归一化距离(H:0-180, L:0-255, S:0-255)
    h_diff = h_diff / 90  # 最大差值180/2
    l_diff = l_diff / 255
    s_diff = s_diff / 255
    
    # 计算加权距离
    dist = np.sqrt((h_diff * 2)**2 + l_diff**2 + s_diff**2) / np.sqrt(6)
    return dist

def _rect_intersection(rect1: Rect, rect2: Rect) -> Rect | None:
    """
    计算两个矩形的交集区域。
    
    :param rect1: 第一个矩形 (x, y, w, h)
    :param rect2: 第二个矩形 (x, y, w, h)
    :return: 交集矩形 (x, y, w, h)，如果没有交集则返回 None
    """
    x1 = max(rect1[0], rect2[0])
    y1 = max(rect1[1], rect2[1])
    x2 = min(rect1[0] + rect1[2], rect2[0] + rect2[2])
    y2 = min(rect1[1] + rect1[3], rect2[1] + rect2[3])
    
    if x1 >= x2 or y1 >= y2:
        return None
    
    return (x1, y1, x2 - x1, y2 - y1)

def find_all(
    image: MatLike | str,
    color: RgbColor,
    *,
    rect: Rect | None = None,
    threshold: float = 0.95,
    method: Literal['rgb_dist'] = 'rgb_dist',
    filter_method: Literal['point', 'contour'] = 'contour',
    max_results: int | None = None,
) -> list[FindColorPointResult]:
    """
    在图像中查找所有符合指定颜色的点。

    :param image: 
        图像。可以是 MatLike 或图像文件路径。
        注意如果参数为 MatLike，则颜色格式必须为 BGR，而不是 RGB。
    :param color: 颜色。可以是整数三元组 `(r, g, b)` 或十六进制颜色字符串 `#RRGGBB`。
    :param rect: 查找范围。如果为 None，则在整个图像中查找。
    :param threshold: 阈值，越大表示越相似，1 表示完全相似。默认为 0.95。
    :param method: 比较算法。默认为 'rgb_dist'，且目前也只有这个方法。
    :param filter_method: 查找方法。

        * point：按点查找结果
        * contour：按轮廓查找结果。也就是如果很多个符合要求的点连在一起，会被当做一个整体返回。
    :param max_results: 最大返回结果数量。如果为 None，则返回所有结果。
    :return: 结果列表。
    """
    # 计算距离矩阵
    dist = color_distance_map(image, color)
    # 筛选满足要求的点，二值化
    binary = np.where(dist <= (1 - threshold), 255, 0).astype(np.uint8)

    def filter_by_point(binary: np.ndarray, target_color: RgbColor, dist: np.ndarray, rect: Rect | None = None, max_results: int | None = None) -> list[FindColorPointResult]:
        results = []
        
        if rect is not None:
            x, y, w, h = rect
            search_area = binary[y:y+h, x:x+w]
            local_dist = dist[y:y+h, x:x+w]
            
            # 获取所有匹配点的坐标
            match_coords = np.where(search_area)
            for local_y, local_x in zip(*match_coords):
                confidence = 1 - local_dist[local_y, local_x]
                global_x = x + local_x
                global_y = y + local_y
                results.append(FindColorPointResult(
                    position=(int(global_x), int(global_y)),
                    confidence=float(confidence),
                    target_color=target_color
                ))
        else:
            # 获取所有匹配点的坐标
            match_coords = np.where(binary)
            for y, x in zip(*match_coords):
                confidence = 1 - dist[y, x]
                results.append(FindColorPointResult(
                    position=(int(x), int(y)),
                    confidence=float(confidence),
                    target_color=target_color
                ))

        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # 限制结果数量
        if max_results is not None:
            results = results[:max_results]
            
        return results

    def filter_by_contour(binary: np.ndarray, target_color: RgbColor, dist: np.ndarray, rect: Rect | None = None, max_results: int | None = None) -> list[FindColorPointResult]:
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        results = []
        for contour in contours:
            # 获取轮廓的外界矩形
            contour_rect = cv2.boundingRect(contour)
            contour_rect = tuple(contour_rect)
            assert len(contour_rect) == 4
            
            # 如果指定了rect，计算轮廓外接矩形与rect的交集
            if rect is not None:
                intersection = _rect_intersection(contour_rect, rect)
                if intersection is None:
                    continue
                    
                x1, y1, w, h = intersection
                # 计算交集区域的中心点
                cx = x1 + w // 2
                cy = y1 + h // 2
                
                # 创建掩码，只保留当前轮廓内的区域
                mask = np.zeros_like(binary)
                cv2.drawContours(mask, [contour], 0, (255,), -1)
                
                # 只计算交集区域内的平均距离
                mask[y1:y1+h, x1:x1+w] = mask[y1:y1+h, x1:x1+w] & binary[y1:y1+h, x1:x1+w]
                avg_dist = np.mean(dist[y1:y1+h, x1:x1+w][mask[y1:y1+h, x1:x1+w] == 255])
            else:
                # 计算轮廓中心点
                cx = contour_rect[0] + contour_rect[2] // 2
                cy = contour_rect[1] + contour_rect[3] // 2
                
                # 创建掩码，只保留当前轮廓内的区域
                mask = np.zeros_like(binary)
                cv2.drawContours(mask, [contour], 0, (255,), -1)
                
                # 计算整个轮廓区域内的平均距离
                avg_dist = np.mean(dist[mask == 255])
            
            confidence = float(1 - avg_dist)
            
            results.append(FindColorPointResult(
                position=(cx, cy),
                confidence=confidence,
                target_color=target_color
            ))
        
        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # 限制结果数量
        if max_results is not None:
            results = results[:max_results]
            
        return results

    # 根据filter_method选择过滤方法
    if filter_method == 'point':
        results = filter_by_point(binary, color, dist, rect, max_results)
    else:  # filter_method == 'contour'
        results = filter_by_contour(binary, color, dist, rect, max_results)

    # 调试输出
    if debug.enabled:
        result_image = unify_image(image).copy()
        # 绘制所有结果点
        for result in results:
            x, y = result.position
            cv2.rectangle(result_image, 
                (max(0, x-10), max(0, y-10)),
                (min(result_image.shape[1], x+10), min(result_image.shape[0], y+10)),
                (255, 0, 0), 1)
        # 绘制搜索范围
        if rect is not None:
            x, y, w, h = rect
            cv2.rectangle(result_image, (x, y), (x+w, y+h), (0, 0, 255), 2)
        
        debug_result(
            'find_rgb_many',
            [result_image, unify_image(image)],
            f'target={debug_color(color)}\n'
            f'rect={rect}\n'
            f'found {len(results)} points\n'
            f'threshold={threshold}\n'
            f'filter_method={filter_method}\n'
            '(Red rect for search area, blue rects for result areas)'
        )

    return results

# https://stackoverflow.com/questions/43111029/how-to-find-the-average-colour-of-an-image-in-python-with-opencv
def dominant_color(
    image: MatLike | str,
    count: int = 1,
    *,
    rect: Rect | None = None,
) -> list[RgbColorStr]:
    """
    提取图像的主色调。

    :param image:
        图像。可以是 MatLike 或图像文件路径。
        如果是 MatLike，则颜色格式必须为 BGR。
    :param count: 提取的颜色数量。默认为 1。
    :param rect: 提取范围。如果为 None，则在整个图像中提取。
    """
    # 载入/裁剪图像
    img = unify_image(image)
    if rect is not None:
        x, y, w, h = rect
        img = img[y:y+h, x:x+w]
    
    pixels = np.float32(img.reshape(-1, 3))

    n_colors = count
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 200, .1)
    flags = cv2.KMEANS_RANDOM_CENTERS

    _, labels, palette = cv2.kmeans(pixels, n_colors, None, criteria, 10, flags) # type: ignore
    _, counts = np.unique(labels, return_counts=True)

    # 将颜色按出现次数排序
    indices = (-counts).argsort()
    dominant = palette[indices]
    
    # 转换为 RGB 格式并转为 16 进制颜色代码
    result: list[RgbColorStr] = []
    for i in range(min(n_colors, len(dominant))):
        color = dominant[i]
        # BGR -> RGB
        rgb = tuple(map(int, color[::-1]))
        hex_color = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
        result.append(hex_color)
    
    if debug.enabled:
        origin_image = unify_image(image)
        result_image = origin_image.copy()
        if rect is not None:
            x, y, w, h = rect
            cv2.rectangle(result_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
        debug_result(
            'color.dominant_color',
            [result_image, origin_image],
            f'arguments:\n \tcount={count}\n \trect={rect}\n'
            f'result={", ".join(map(debug_color, result))}'
        )

    return result

if __name__ == '__main__':
    img = cv2.imread('tests/images/ui/commu_fast_forward_enabled.png')
    colors = dominant_color(img, 3)
    print("主调颜色:")
    for i, color in enumerate(colors, 1):
        print(f"{i}. {color}")
        # 创建一个纯色图像来展示颜色
        color_block = np.full((100, 100, 3), _unify_color(color)[::-1], dtype=np.uint8)
        cv2.imshow(f"Color {i}", color_block)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
