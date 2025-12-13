import time
import logging
import threading
from typing import List, Callable, Optional

from ._mouse import get_pos

logger = logging.getLogger(__name__)


class ShakeMouse:
    """
    全局鼠标晃动检测器。
    
    模拟 macOS 的鼠标晃动检测机制。
    使用“累积行程+反转计数”算法，有效区分“快速移动”与“快速晃动”，防止误触。
    """
    
    _enabled: bool = False
    _thread: Optional[threading.Thread] = None
    _callbacks: List[Callable[[], None]] = []
    _lock = threading.Lock()
    
    # --- 算法参数配置 ---
    
    SAMPLE_INTERVAL: float = 0.016 
    """
    采样间隔 (秒)。
    
    越小越灵敏，但在低性能机器上可能占用更多 CPU。
    0.016 约为 60Hz。
    """
    
    STROKE_THRESHOLD: int = 500 
    """
    有效行程阈值 (像素)。

    必须在单一方向上至少移动这么多像素，然后反转方向，才会被记为一次“晃动”。
    设置得过小会导致微小抖动触发，设置得过大需要大幅度甩动鼠标。
    """
    
    REQUIRED_SHAKES: int = 6
    """
    触发所需的连续晃动次数。

    1次晃动定义为：满足行程阈值的一次方向改变。
    比如：左 -> 右 (1), 右 -> 左 (2), 左 -> 右 (3), 右 -> 左 (4)。
    """
    
    TIMEOUT_RESET: float = 0.5
    """
    计数重置时间 (秒)。

    如果在这个时间内没有发生下一次有效的晃动，计数器归零。
    """
    
    COOLDOWN: float = 2.0
    """
    防抖冷却时间 (秒)。

    触发成功后，在该时间内不再重复触发。
    """


    @staticmethod
    def start() -> None:
        """开启鼠标晃动检测。"""
        with ShakeMouse._lock:
            if ShakeMouse._enabled:
                return
            ShakeMouse._enabled = True
            
        ShakeMouse._thread = threading.Thread(target=ShakeMouse._monitor_loop, daemon=True, name="ShakeMouseMonitor")
        ShakeMouse._thread.start()
        logger.info("ShakeMouse detection enabled.")


    @staticmethod
    def stop() -> None:
        """关闭鼠标晃动检测。"""
        with ShakeMouse._lock:
            ShakeMouse._enabled = False
        
        # 线程是 daemon 且 loop 检查 _enabled，不需要 join，让它自然退出即可
        if ShakeMouse._thread and ShakeMouse._thread.is_alive():
            ShakeMouse._thread = None
        logger.info("ShakeMouse detection disabled.")


    @staticmethod
    def add_callback(func: Callable[[], None]) -> None:
        """添加晃动触发时的回调函数。"""
        ShakeMouse._callbacks.append(func)


    @staticmethod
    def clear_callbacks() -> None:
        """清除所有回调函数。"""
        ShakeMouse._callbacks.clear()


    @staticmethod
    def _trigger() -> None:
        """内部触发逻辑。"""
        logger.debug("Mouse shake detected!")
        for cb in ShakeMouse._callbacks:
            try:
                cb()
            except Exception:
                logger.exception(f"Error in ShakeMouse callback {cb}")


    @staticmethod
    def _monitor_loop() -> None:
        """检测线程主循环。"""
        
        last_pos = get_pos()
        
        # 算法状态变量
        # 累计在当前方向上的移动距离
        acc_x = 0 
        acc_y = 0
        
        # 当前方向标志 (1: 正向, -1: 负向, 0: 静止)
        dir_x = 0
        dir_y = 0
        
        # 有效晃动计数
        shake_count = 0
        
        # 上一次有效晃动发生的时间
        last_shake_time = time.time()
        
        # 上一次触发成功的时间 (用于冷却)
        last_trigger_time = 0


        while True:
            # 1. 检查开关状态
            if not ShakeMouse._enabled:
                break

            now = time.time()

            # 2. 获取当前位置并计算增量
            curr_pos = get_pos()
            dx = curr_pos.x - last_pos.x
            dy = curr_pos.y - last_pos.y
            last_pos = curr_pos
            
            # 3. 冷却期检查
            if now - last_trigger_time < ShakeMouse.COOLDOWN:
                time.sleep(ShakeMouse.SAMPLE_INTERVAL)
                # 冷却期内重置累积状态，防止冷却一结束就立即触发
                acc_x, acc_y, shake_count = 0, 0, 0
                continue
            
            # 4. 超时重置检查
            # 如果用户晃动了一两下停下来了，一段时间后重置计数
            if shake_count > 0 and (now - last_shake_time > ShakeMouse.TIMEOUT_RESET):
                shake_count = 0
                acc_x = 0
                acc_y = 0
                # logger.debug("Shake timeout reset")

            # 5. 核心算法：X 轴检测
            # 我们主要检测水平晃动 (X轴) 或 垂直晃动 (Y轴)，取两者中显著的一个
            
            # --- X 轴逻辑 ---
            if dx != 0:
                current_dir_x = 1 if dx > 0 else -1
                
                if current_dir_x != dir_x:
                    # 方向发生改变
                    if abs(acc_x) > ShakeMouse.STROKE_THRESHOLD:
                        # 如果之前的累积行程足够长，记为一次有效晃动
                        shake_count += 1
                        last_shake_time = now
                        # logger.debug(f"Shake count (X): {shake_count}, Acc: {acc_x}")
                    
                    # 重置累积，开始新的方向
                    acc_x = dx
                    dir_x = current_dir_x
                else:
                    # 方向相同，累积行程
                    acc_x += dx
            
            # --- Y 轴逻辑 (同理) ---
            if dy != 0:
                current_dir_y = 1 if dy > 0 else -1
                
                if current_dir_y != dir_y:
                    if abs(acc_y) > ShakeMouse.STROKE_THRESHOLD:
                        shake_count += 1
                        last_shake_time = now
                        # logger.debug(f"Shake count (Y): {shake_count}, Acc: {acc_y}")
                    
                    acc_y = dy
                    dir_y = current_dir_y
                else:
                    acc_y += dy

            # 6. 触发判定
            if shake_count >= ShakeMouse.REQUIRED_SHAKES:
                last_trigger_time = now
                shake_count = 0
                acc_x = 0
                acc_y = 0
                
                # 在独立线程执行触发，不阻塞检测循环太久 (或者回调本身应当快)
                # 这里直接调用，因为 python GIL 限制，只要 callback 不 sleep 太久即可
                ShakeMouse._trigger()

            # 7. 循环等待
            time.sleep(ShakeMouse.SAMPLE_INTERVAL)

if __name__ == "__main__":
    sm = ShakeMouse()
    def on_shake():
        print("Mouse shaken!")
    
    sm.add_callback(on_shake)
    sm.start()
    input("Press Enter to stop...\n")
