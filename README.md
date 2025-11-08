# kotonebot
> [!WARNING]
> 本项目仍然处于早期开发阶段，可能随时会发生 breaking change。如果要使用，建议 pin 到一个具体的版本。

kotonebot 是一个使用 Python 编写，基于 OpenCV、RapidOCR 等技术，致力于简化 Python 游戏自动化脚本编写流程的框架。

## 特性
* 层次化引入
  * 包含 Library、Framework、Application 三个不同层次，分别封装到不同程度，可自由选择
* 平台无关的输入输出（截图与模拟点击）
* 基于代码生成的图片资源引用
  * 避免硬编码字符串
* 图像/OCR 识别结果追踪 & 可视化查看工具
* 开箱即用的模拟器管理（目前仅支持 MuMu12 与雷电模拟器）

## 安装
要求：Python >= 3.10

```bash
# Windows Host, Windows Client
pip install kotonebot[windows]
# Windows Host, Android Client
pip install kotonebot[android]
# Development dependencies
pip install kotonebot[dev]
```

## 快速开始
WIP

### 协同开发
有时候你可能想以源码方式安装 kotonebot，以便与自己的项目一起调试修改。此时，如果你以 `pip install -e /path/to/kotonebot` 的方式安装，Pylance 可能无法正常静态分析。
解决方案是在 VSCode 里搜索 `python.analysis.extraPaths` 并将其设置为你本地 kotonebot 的根目录。

## 文档
WIP

## 其他
本项目分离自 [KotonesAutoAssistant](https://github.com/XcantloadX/kotones-auto-assistant)，因此 c69130 以前的提交均为 KotonesAutoAssistant 的历史提交。

由于使用 filter-repo 移除了大量无用文件，因此历史提交信息和更改的文件可能无法完全对应。