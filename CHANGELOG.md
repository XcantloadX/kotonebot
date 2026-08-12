# 更新日志
## v0.20.0
Framework:
1. [feat] **BREAKING** 移除 Pipeline 体系（`kotonebot.pipeline` 模块及其相关 API）。依赖该体系的代码需自行迁移到普通同步控制流（如 `Loop` / 任务循环）。

Devtool:
1. [feat] 命令面板优化，支持符号模糊搜索，与关键字高亮。
2. [feat] 统一打开文件逻辑。命令面板搜索打开文档、最近打开列表、转换结果等处打开图片时，与「文件 → 打开」对话框行为一致，支持对旧版/损坏 meta 的容错恢复。
3. [feat] 优化 Devtool 命令启动速度。
4. [fix] 修复 AI 推断对象 Name/DisplayName/Fixed 属性无法写入的问题。

Library:
1. [feat] `Rect` 新增值语义：支持 `==` 比较、按 `(x, y, w, h)` 索引访问、迭代与哈希。
2. [fix] 修复 `find_all_crop` 因 `Rect` 不支持下标访问而抛出 `TypeError` 的问题。
3. [feat] **BREAKING** 移除 `image.find_all_crop` 与 `CropResult` 类型。需要裁剪匹配区域时，请使用 `image.find_all` 获取匹配结果后自行按 `result.rect` 切片裁剪。
4. [feat] **BREAKING** 移除 `Loop.when`、`Loop.until`、`Loop.click_if` 方法与 `LoopAction` 类。请改用普通的 `if` / `while` 条件判断结合 `image.find` / `device.click` 实现等价逻辑。
5. [feat] **BREAKING** 移除废弃的 `kotonebot.backend.bot` 模块（旧版 `KotoneBot` 类及其配套 `KotoneBotEvents`）。请改用 `kotonebot.core.bot.KotoneBot`。

## v0.19.1
Library：
1. [feat] 模板匹配越界校验从抛出异常降级为仅错误日志输出。
2. [feat] `NemuIpcImpl` 新增捕获 DLL 的调试输出，避免污染 stdout/stderr。

## v0.19.0
Library:
1. [feat] **BREAKING** `kotonebot.backend.core.Ocr` 已移除。`kotonebot.backend.core.unify_image` 进入废弃状态，改用 `kotonebot.primitives.Image.coerce()` 作为替代。
2. [feat] **BREAKING** `Device.click` 与 `Device.double_click` 方法现在总是点击范围中心，而不是在范围内随机选取点击。
3. [feat] MuMu12V5Host 新增获取 MuMu 模拟器版本号的方法。
4. [feat] 为模板匹配加入了非法坐标（越界、负数）的校验。
5. [fix] 修复新版 MuMu 上无法正确找到 external_renderer_ipc.dll 导致 `NemuIpcImpl` 无法正确初始化的问题。

Framework:
1. [feat] 新增 Pipeline 体系，类似于 MaaFW 的 Pipeline，提供了一套简化但仍然高度可自定义的流水线编写代码的方式。
2. [fix] **BREAKING** 纠正了 `kotonebot.config.LoopConfig` 的回调类型标注的返回值类型错误的问题，从 `None` 改为了 `bool`。运行时行为未发生改变。

## v0.18.0
Devtool:
1. [feat] 为命令面板新增支持文件搜索。
2. [feat] 新增新建文档功能，支持从本地文件、剪贴板以及设备画面新建文档，同时支持 AI 智能命名文档。
3. [feat] 新增欢迎页面，展示最近打开的文件与新建、打开文档入口。
4. [feat] 项目面板新增 hover 对象时展示预览图片。
5. [feat] 新增 AI 自动建议对象 Name 与 DisplayName 以及 Fixed 属性的值。
6. [feat] 优化 Devtool CLI 的启动速度。

Library：
1. [feat] Win32 置窗口前台改用 AttachThreadInput + SwitchToThisWindow 混合方案。

## v0.17.0
Framework:
1. [feat] 为 RunStatus 类新增 对 Flow 的封装，即暂停、停止与恢复任务执行的方法。
2. [fix] 修复了 Context 类中的 Forwarded 当被包装对象为 None 时抛出 AttributeError 的问题。

## v0.16.0
Library:
1. [feat] 新增不依赖 AHK 的 `WindowsNativeImpl`，原有 `WindowsImpl` 进入废弃状态，将在后续若干个版本后移除。
2. [feat] 新增对于国际版 MuMu 模拟器的支持。

### 迁移

#### `WindowsImpl` → `WindowsNativeImpl`

`WindowsImpl` 底层依赖 AHK（AutoHotkey）执行鼠标点击/拖拽，并提供全局热键（Ctrl+F4 暂停/恢复、Ctrl+F3 停止）与消息框提示功能。新的 `WindowsNativeImpl` 改用 win32 API（窗口激活/截图）与 `mouse` 库（鼠标点击/拖拽）实现，不再依赖 AHK，因此**不再提供全局热键与消息框提示功能**，如有需要请自行实现。

涉及的类：
- `WindowsImpl` → `WindowsNativeImpl`
- `WindowsImplConfig` → `WindowsNativeImplConfig`
- `WindowsHostConfig` → `WindowsNativeHostConfig`

对应的 recipe 名称由 `'windows'` 改为 `'windows_native'`。

**迁移方式：**

```python
from kotonebot.interop.window import WindowQuery

# 旧写法（依赖 AHK，需要提供 ahk_exe_path）
from kotonebot.client.implements.windows import WindowsImpl, WindowsImplConfig
impl = WindowsImpl(
    device,
    window_query=WindowQuery(title_contains="gakumas"),
    ahk_exe_path=ahk_path,
)
config = WindowsImplConfig(window_query=WindowQuery(title_contains="gakumas"), ahk_exe_path=ahk_path)

# 新写法（无需 AHK）
from kotonebot.client.implements.windows import WindowsNativeImpl, WindowsNativeImplConfig
impl = WindowsNativeImpl(device, window_query=WindowQuery(title_contains="gakumas"))
config = WindowsNativeImplConfig(window_query=WindowQuery(title_contains="gakumas"))
```

主机配置（`create_device` recipe）迁移：

```python
# 旧写法
host_config = WindowsHostConfig(window_query=query, ahk_exe_path=ahk_path)
device = instance.create_device('windows', host_config)

# 新写法
from kotonebot.client.host.protocol import WindowsNativeHostConfig
host_config = WindowsNativeHostConfig(window_query=query)
device = instance.create_device('windows_native', host_config)
```

`WindowsNativeImplConfig` / `WindowsNativeHostConfig` 新增以下可选参数：

| 字段 | 说明 |
|------|------|
| `avoid_border_click` | 点击坐标为 `(0, *)` 或 `(*, 0)` 时，是否自动偏移 1~2 像素以避免点到窗口边框。默认开启（`True`）。 |
| `click_animation` | 点击前移动鼠标到目标位置时使用的动画参数（`AnimationParams`）。默认为空字典，即瞬间跳转，不做动画。 |
| `swipe_animation` | `swipe`（拖拽）操作默认使用的动画参数（`AnimationParams`）。若调用 `swipe()` 时显式传入了 `duration`，会覆盖此处配置的 `duration`/`speed`。 |

`WindowsImpl` 暂时保留，仍可正常使用，但已进入废弃状态，将在后续若干个版本后移除，请尽快迁移到 `WindowsNativeImpl`。

## v0.15.0
Library:
1. [feat] **BREAKING** 对于 MuMu 模拟器，当模拟器未安装或未找到时，现在抛出 `EmulatorNotFoundError` 而不是 `RumtimeError` 了。
2. [feat] **BREAKING** 完全移除 `kotonebot.backend.debug` 模块以及相关设计。
3. [feat] **BREAKING** 归一化处理各种 ADB 连接错误与网络错误，统一为 `DeviceConnectionError` 及其子类。
4. [fix] 修复了 `UserFriendlyError` 遗漏传递参数导致在异常描述中消息文本缺失的问题。
5. [feat] **BREAKING** 当使用 `LandscapeGameScaler` 和 `PortraitGameScaler` 进行分辨率缩放时，如果分辨率存在微小误差（例如实际分辨率不是 1920x1080 而是 1919x1080），旧行为按照真实的带有误差的分辨率计算缩放比例（以 1280x720 为目标，最终结果可能为 1279x720），而新行为直接假设为正确的分辨率（以 1280x720 为目标，最终结果为 1280x720）。

Framework：
1. [feat] 优化了框架部分 API 对于多线程的支持，现在可以在多个线程内同时执行任务了。

Devtools:
1. [feat] 新增支持替换图片功能，可以快速替换当前文档的图像。

## v0.14.0
Library:
1. [feat] **BREAKING** 移除 remote_windows 实现。
2. [feat] **BREAKING** 引入 Window 抽象层，统一不同平台的窗口寻找与管理等逻辑。同时新增 macOS 窗口支持。
3. [feat] 新增 QuartzImpl，支持控制 macOS 窗口。新增 Playcover 类，支持列出、启动、终止 Playcover 程序。
4. [feat] `ContextDevice` 平台专属方法优化。
	1. 新增 `is_android`、`is_windows`、`is_macos` 属性，用于平台判断。
	2. 新增 `android()`、`windows()` 方法，返回各自的 Commandable 对象。原来的 `of_android()`、`of_windows()` 废弃。


### 迁移

#### 移除 `remote_windows` 实现

`remote_windows` recipe 已移除，请迁移到其他 Windows 实现（如 `windows` 或 `windows_background`）。

#### `window_title` → `window_query`

所有接受 `window_title: str` 参数的地方，现在统一改为接受 `window_query: WindowQuery`。

涉及的类：
- `WindowsHostConfig`
- `WindowsImpl`
- `WindowsImplConfig`
- `PrintWindowImpl`
- `SendMessageImpl`

**迁移方式：**

```python
from kotonebot.interop.window import WindowQuery

# 旧写法
config = WindowsHostConfig(window_title="gakumas", ahk_exe_path=ahk_path)
impl = WindowsImpl(device, window_title="gakumas", ahk_exe_path=ahk_path)

# 新写法（标题包含匹配）
config = WindowsHostConfig(window_query=WindowQuery(title_contains="gakumas"), ahk_exe_path=ahk_path)
impl = WindowsImpl(device, window_query=WindowQuery(title_contains="gakumas"), ahk_exe_path=ahk_path)
```

`WindowQuery` 支持多种匹配模式：

| 字段 | 说明 |
|------|------|
| `title` | 精确匹配窗口标题 |
| `title_contains` | 窗口标题包含此字符串 |
| `title_regex` | 窗口标题匹配正则表达式 |
| `app_name` | 精确匹配应用程序名称 |
| `app_name_contains` | 应用程序名称包含此字符串 |
| `process_id` | 精确匹配进程 ID |
| `visible_only` | 仅匹配可见窗口（默认 `True`） |

Windows 平台还可使用原生查询条件 `WindowsNativeQuery`：

```python
from kotonebot.interop.window import WindowQuery, WindowsNativeQuery

# 按窗口类名查找
query = WindowQuery(native=WindowsNativeQuery(class_name="UnityWndClass"))
# 按可执行文件路径查找
query = WindowQuery(native=WindowsNativeQuery(executable="gakumas.exe"))
```

#### `of_android()` / `of_windows()` → `android()` / `windows()`

新方法直接返回底层 commands 对象（`AndroidCommandable` / `WindowsCommandable`），
无需再经过 `.commands` 中间属性，类型检查器也能正确识别。

```python
# 旧写法
d = device.of_android()
d.commands.adb_shell('...')
d.current_package()
d.launch_app(pkg)

# 新写法
device.android().adb_shell('...')
device.android().current_package()
device.android().launch_app(pkg)
```

#### 平台判断

```python
# 旧写法
from kotonebot.client.device import AndroidDevice
isinstance(device._device, AndroidDevice)

# 新写法
device.is_android
```

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
