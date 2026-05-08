# 更新日志
## v0.13.2
Library:
1. [fix] 修复了当设备逻辑分辨率被修改时（通过 wm size），AdbImpl.screen_size 总是取得物理分辨率的问题。

## v0.13.1
Library:
1. [feat] 优化当访问的变体不存在时，抛出的异常类型与提示信息。
2. [feat] 优化库依赖版本，现在的依赖更加宽松了。

Framework:
1. [feat] 优化生成的实体资源的 Typing 标注。

## v0.13.0
Library:
1. [feat] **BREAKING** 移除 fuzz OCR 文本匹配算法，以及 thefuzz 库的依赖。
2. [feat] AdbImpl 支持多显示器，可以指定需要操控的显示器 ID。
3. [feat] 支持 scrcpy 截图与控制方法。
4. [fix] 修复 WindowsImpl 缺少 windll 导入的问题。
5. [feat] **BREAKING** `Device` 类的 `start` 与 `stop` 方法现在会进行线程检查，不可以跨线程调用这两个方法。
6. [fix] 修复导入 TemplateMatchPrefab 与 OcrPrefab 时会自动导入开发依赖 rich 的问题。
7. [feat] SendMessageImpl 现在可选开启运行时阻止系统休眠的功能，默认开启。
8. [fix] 修复 ScrcpyImpl 会调用 PATH 里的 adb，若系统未安装 adb 从而抛出异常的问题。
9. [feat] MuMu12V5Host 新增 `check_app_keptlive` 可用于检查是否开启 APP 后台保活模式。
10. [fix] 修复 FlowController 触发中断无法打断 `sleep` 函数的问题。

Devtool：
1. [feat] 新增最近打开文件功能。
2. [feat] 新增符号树视图，可以查看整个项目的符号。
3. [feat] 优化扩展 resgen 的自定义能力，现在可以通过 API 自定义某种资源类型的渲染方式。

## v0.12.0
Library:
1. [feat] 优化跨平台体验。现在在非 Windows 平台上导入 Windows-Only 的模块不会立刻报错，而是等到调用/实例化时才抛出异常。

Devtool:
1. [feat] 右侧属性面板支持调整宽度
2. [feat] 新增「层级」Tab，在对象发生重叠的时候可以通过层级选中某个对象。
3. [feat] **BREAKING** variant 策略升级，变为 `inherit` / `require` / `exclude` 三态策略，可为每个 variant 单独配置。同时 schema 版本号升级为 3。

> Meta schema 从 `version: 2` 升级到 `version: 3`。`variant_inherit` 已移除，替换为 base prefab 的按 variant 三态策略 `variant_policy`（`inherit` / `require` / `exclude`）。
> 
> **BREAKING** Variant 解析与校验行为更新：
> - `inherit`：未声明 variant 定义时回退到 base。
> - `require`：未声明 variant 定义时报错。
> - `exclude`：该 variant 下禁止出现该 prefab，若存在显式定义则报错。
> 
> 新增迁移脚本 `tools/migrate_meta_v2_to_v3.py`，支持 dry-run、落盘写入、备份与报告输出。
> ```bash
> python tools/migrate_meta_v2_to_v3.py --root ./resources
> python tools/migrate_meta_v2_to_v3.py --root ./resources --write --backup .bak > --report migration_report.json
> ```

## v0.11.0
Library:
1. [refactor] **BREAKING** 为了便于扩展，Prefab 的方法参数从 kwargs 迁移到 Query 入口（`q(...)`），统一 TemplateMatch/OCR 的参数覆盖与谓词过滤写法。旧/新写法对比：

	```python
	# 旧写法
	obj = _Prefab.require(threshold=0.7, region=full_region)
	obj = _Prefab.find(predicate=lambda o: o.rect.w > 0)

	# 新写法
	obj = _Prefab.q(threshold=0.7, region=full_region).require()
	obj = _Prefab.q(_Prefab.Query(predicate=lambda o: o.rect.w > 0)).find()
	```
2. [feat] 引入新输入系统 `InputManager`，明确分离鼠标、触摸输入设备，新增键盘输入设备。可用于实现更加复杂的输入操作。原有 device 上的写法仍然支持。
   ```python
   	# 引入
	from kotonebot import device, input
	device.input # ，或者用全局变量
	input
	# 使用
	# 三个通用方法，会转发到底层输入 Controller
	device.input.tap()
	device.input.double_tap()
	device.input.drag()
	# 调用 Controller
	device.input.mouse.click(button='right')
	device.input.touch.tap(contact=2)
	# 调用 Driver
	device.input.mouse.button_down()
	device.input.touch.touch_down()
   ```
3. [refactor] **BREAKING** `Device` 的组件装配统一收敛到 `setup(...)`。直接写入私有字段（如 `device._screenshot`、`device._touch`、`device._multitouch`）不再保证可用，可能导致 `device.input` 未初始化并在点击/滑动时出错。请迁移到 `device.setup(...)`。

Devtool:
1. [fix] 修复 ChoiceProp 无法正常展示的问题。

## v0.10.0
Library:
1. [feat] **BREAKING** 移除 image.similar 分发与 scikit-image 依赖。
2. [feat] 新增物理 Android 设备支持，可直接通过 USB 连接真机。
3. [feat] ADB 连接新增 USB 模式支持，兼容 TCPIP 和 USB 两种连接方式。

Framework:
1. [feat] **BREAKING** Device 类及其底层组件新增生命周期方法 `start` 与 `stop`，现在使用时需要在恰当的时机调用生命周期方法。

Devtool:
1. [feat] 新增 Definition 的右键菜单，支持复制、粘贴与创建副本。
2. [feat] 新增 VSCode 扩展，现在可以在 VSCode 里直接通过 Devtool 进行编辑了。
3. [feat] resgen 工具现在支持将错误视为警告，强制构建了。

## v0.9.0
Framework: 
1. [feat] 为 AnyOf 类支持 `wait` 方法。

Devtools：
1. [feat] **BREAKING** 现在强制要求在 `pyproject.toml` 中填写 `resource_path` 字段。
2. [feat] Devtools 中打开文件对话框的默认路径现在变为 `resource_path` 字段的值。
3. [feat] 现在支持 Ctrl + Shift + P 打开 Command Pattle，输入 `#` 来搜索项目内所有资源文件的名称与展示名称，类似于 VSCode。
4. [feat] 新增「问题面板」，展示项目内的所有问题。
5. [feat] resgen 优化构建时的输出，现在会展示进度以及所有的 warning、error、info。
6. [feat] 新增 variant 机制，可用于适配多语言游戏。
7. [feat] 优化 Devtool 的 UI，新增引入顶部菜单栏。

## v0.8.0
Library:
1. [feat] 新增多点触控接口，目前仅 nemu_ipc 实现了多点触控。
2. [feat] 优化库 import 速度，从 2.9 秒降至 0.92 秒，提升了 68%。
3. [feat] **BREAKING** 移除了内置的配置实体类与管理，以及 Context 上的 config 对象。
4. [feat] 新增了新的 KotoneBot 任务调度类，位于 kotonebot.core.bot 内。原有旧对象 kotonebot.backend.bot 处于废弃状态，将与若干个版本后移除。

## v0.7.0
Library:
1. [feat] 支持了 Windows 控制的后台执行版本，recipe 名称为 `windows_background`。底层使用 SendMessage + PrintWindow 实现。

## v0.6.0
Library:
1. [feat] 新增类 kotonebot.interop.win.ShakeMouse，支持检测晃动鼠标检测动作，可以用于实现晃动鼠标自动停止脚本执行的功能
2. [feat] 新增 Loop 类的全局回调函数，可以通过全局回调处理一些通用内容，如网络错误弹窗、跨日等
3. [feat] **BREAKING** 移除 adb_raw 的实现，因为它又慢又不稳定。
4. [feat] 移除 kotonebot.backend.core.Image 类，新编写代码应该使用 kotonebot.primitives.Image。新的 Image 类暂时保留与原类一直的字段以向后兼容
5. [feat] **BREAKING** image.xxx 系列方法现在若 `colored=False`，将会采用灰度图像的模板匹配而不是 RGB 三通道的模板匹配
6. [feat] **BREAKING** 现在 geometry 里的 Rect 类在创建时会自动将传入参数转换为整数
7. [feat] 新增全局处理分辨率缩放方案，内置等比例、按宽度、按高度缩放逻辑
8. [feat] geometry 增强：Point/Rect/Vector 变为可迭代对象，新增大小比较与 `as_tuple` 等实用能力，并引入统一化工具函数
9. [feat] template_match 新增参数合法性检查
10. [feat] 调整 TemplateMatchPrefab 默认阈值

Framework：
1. [feat] Loop 类新增全局 callback，在每次循环前调用，可用于全局处理逻辑
2. [feat] 新增全局框架配置入口，可用于配置分辨率缩放、Loop 全局回调等
3. [feat] 新引入了 GameObject & Prefab 系统，作为裸露 image.xxx 的高层封装，可用于逻辑复用

Devtools：
1. [feat] 引入新标准资源文件生成工具，同时兼容新旧两套资源方案
2. [refactor] 重构 Devtool，优化标注体验

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
