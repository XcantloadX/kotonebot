# 更新日志
## v0.6.0
Library:
1. [feat] 新增类 kotonebot.interop.win.ShakeMouse，支持检测晃动鼠标检测动作，可以用于实现晃动鼠标自动停止脚本执行的功能
2. [feat] 新增 Loop 类的全局回调函数，可以通过全局回调处理一些通用内容，如网络错误弹窗、跨日等
3. [feat] **BREAKING** 移除 adb_raw 的实现，因为它又慢又不稳定。
4. [feat] 移除 kotonebot.backend.core.Image 类，新编写代码应该使用 kotonebot.primitives.Image。新的 Image 类暂时保留与原类一直的字段以向后兼容
5. [feat] **BREAKING** image.xxx 系列方法现在若 `colored=False`，将会采用灰度图像的模板匹配而不是 RGB 三通道的模板匹配

## v0.5.0
Library：
1. [feat] 优化 kotonebot.geometry 下的 Point 与 Rect 类，新增常见运算符重载与相等比较，以及多个实用方法，包括复制、偏移、相交包含判断等
2. [feat] 优化可选依赖导入，现在核心库即使不安装 Android 或 Windows 平台依赖，也可以导入
3. [feat] Device 类新增 `log_level` 属性，用于设置日志等级。同时 `click`、`double_click` 等方法支持 `log` 参数指定日志等级
4. [feat] 恢复 OCR 引擎默认转换全角为半角的行为

## v0.4.0
Framework：
1. [feat] Loop 每次循环从动态延时改为固定延时
2. [chore] 废弃 when()、until()、click_if() 等方法，推荐使用原生 if 语句
3. [feat] 优化当前上下文无截图数据的异常信息

Library：
1. [feat] 改进跨平台兼容性，新增平台检查工具函数和条件导入，现在在非 Windows 平台上导入不再出错
2. [fix] 修复雷电模拟器创建设备失败问题
3. [fix] 修复 device.click_center() 方法未正确缩放处理的问题

其他：
1. [chore] 迁移到项目工具链到 uv

## v0.3.1
Library:
1. [fix] 修复 base_config.py 中的 BackendType 类型定义缺少 mumu12v5 的问题。

## v0.3.0
Library:
1. [feat] 支持 MuMu12 v5.x 模拟器的控制。
2. [feat] OCR 模块新增识别结果清理功能。
3. [feat] 移除 debug 模块对 psutil 的强制依赖。

## v0.2.0
Framework：
1. [feat] Loop 类新增参数 skip_first_wait，可选是否跳过第一次等待，默认为 True。

Library:
1. [feat] image 模块中的函数新增 `rect` 参数，允许指定模板匹配的范围。
2. [fix] 修复 Device.swipe_scaled 在设置了分辨率缩放时滑动坐标不正确的问题

## v0.1.0
初始版本。