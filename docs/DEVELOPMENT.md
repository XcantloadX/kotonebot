# 开发
> [!NOTE]
> 建议使用 VSCode 进行开发。

1. 确保你已经安装 [just](https://github.com/casey/just#packages) 构建工具
2. 创建 Python 3.10 虚拟环境，然后执行：
    ```bash
    git clone https://github.com/XcantloadX/KotonesAutoAssistant.git
    cd KotonesAutoAssistant
    just env
    ```
3. 配置 VSCode：
    1. 进入“扩展 Extension”，搜索 `@recommended` ，然后安装里面的所有插件。
    2. 打开 VSCode 设置，搜索 `python.analysis.supportRestructuredText` 并勾选。
    3. 打开 VSCode 设置，搜索 `imageComments.pathMode` 并设置为 `relativeToWorkspace`。
4. 编译资源：在 VSCode 中选择“Terminal” -> “Run Task” -> “Make R.py”并执行。

## 运行单个任务
如果使用 VSCode，只需要在运行配置里选择 `Python: Current Module` 即可。

如果使用 PyCharm，按照下图新建一个 Run Configuration：

![pycharm_run_config.png](images/pycharm_run_config.png)

## 打包 & 安装
```bash
just package
pip install --find-links=dist ksaa
```

## 截图
建议使用 [XnView MP](https://www.xnview.com/en/xnviewmp/) 进行截图裁剪工作。

XnView MP 可以方便的完成“打开图片 → 选区 → 裁剪图片 → 另存选取为文件”这一操作。
只需要提前设置好右键菜单：
![XnView MP 设置1](./images/xnview_setup1.png)

## 备注
1. 所有 Python 脚本（包括 kaa 主体、tools 下脚本等）均需要以项目根目录为工作目录执行