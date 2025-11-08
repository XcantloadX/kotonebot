# 开发
## 前置条件
1. **just**  
安装教程见[文档](https://github.com/casey/just#packages)

2. **PowerShell/PowerShell Core**  
如果你的开发将机器为 Windows，什么都不需要做。如果是 Linux，参考[这里](https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-linux?view=powershell-7.5)安装 PowerShell。

3. **uv**

## 项目配置
```powershell
git clone https://github.com/XcantloadX/kotonebot.git
cd kotonebot
just sync
just test
just package
```