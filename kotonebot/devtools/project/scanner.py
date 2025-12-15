import os
import json
import sys
import pkgutil
import inspect
import importlib
import subprocess
import contextlib
from typing import Any, Dict

# ==============================================================================
#  Public API
# ==============================================================================

def scan_prefabs(package_name: str, python_executable: str = sys.executable) -> Dict[str, Dict[str, Any]]:
    """
    在一个隔离的子进程中扫描指定的 Python 包，查找所有包含特定嵌套元数据类的类。

    这种方法使用 `subprocess` 和 `stdout` + JSON 进行通信，以实现最大限度的隔离，
    避免了 `multiprocessing` 和 `pickle` 可能带来的依赖和序列化问题。

    Args:
        package_name: 要扫描的包的点分名称 (例如 'my_app.components')。
        python_executable: 用于运行子进程的 Python 解释器路径。
                           默认为当前正在运行的 Python 解释器。

    Returns:
        一个字典，其键是找到的类的完全限定名称（字符串），值是包含其元数据属性的字典。
        如果发生错误或未找到任何内容，则返回一个空字典。
    """
    print(f"--- Main process (PID: {os.getpid()}) starting worker for package '{package_name}'... ---")
    
    # 构建执行子进程的命令。
    # `__file__` 指向当前脚本文件 (prefab_scanner.py)，它将以工作模式被再次执行。
    command = [python_executable, __file__, '--worker', package_name]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # 手动处理错误，不让它自动抛出异常
            encoding='utf-8',
            # 将当前工作目录传递给子进程，使其能正确找到项目根目录
            cwd=os.getcwd() 
        )
    except FileNotFoundError:
        print(f"Error: Python executable not found at '{python_executable}'.", file=sys.stderr)
        return {}

    # 打印来自子进程的任何日志/调试信息
    if result.stderr:
        print("\n--- Logs/Errors from worker process ---", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        print("-------------------------------------\n", file=sys.stderr)
    
    if result.returncode != 0:
        print(f"Error: Worker process exited abnormally with return code: {result.returncode}", file=sys.stderr)
        return {}

    try:
        # 从子进程的标准输出解析 JSON 数据
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error: Failed to parse JSON from worker process output.", file=sys.stderr)
        print("--- STDOUT from worker process ---", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print("--------------------------------", file=sys.stderr)
        return {}

# ==============================================================================
#  Internal Worker Logic (在子进程中运行)
# ==============================================================================

def _get_class_properties(cls: type) -> Dict[str, Any]:
    """从类中提取所有非可调用、非双下划线开头的类属性。"""
    properties = {}
    for key, value in vars(cls).items():
        if not key.startswith('__') and not callable(value):
            properties[key] = value
    return properties

@contextlib.contextmanager
def _redirect_stdout_to_stderr():
    """上下文管理器，临时将 stdout 重定向到 stderr 以隔离用户代码的输出。"""
    original_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = original_stdout

def _worker_main(package_name: str):
    """
    在隔离的子进程中执行的实际工作逻辑。
    结果通过打印 JSON 到 stdout 来返回。
    """
    # 确保子进程的 sys.path 包含项目根目录
    sys.path.insert(0, os.getcwd())
    
    final_results = {}
    try:
        from kotonebot.devtools import EditorMetadata
        
        package = importlib.import_module(package_name)
        module_names = [
            name for _, name, _ in pkgutil.walk_packages(
                path=package.__path__, prefix=package.__name__ + '.'
            )
        ]
        
        for module_name in module_names:
            try:
                # 隔离导入，防止用户代码的 print 污染 stdout
                with _redirect_stdout_to_stderr():
                    module = importlib.import_module(module_name)
            except Exception as e:
                print(f"[Worker] Failed to import module {module_name}: {e}", file=sys.stderr)
                continue

            for _, outer_cls in inspect.getmembers(module, inspect.isclass):
                if outer_cls.__module__ != module_name:
                    continue

                for _, nested_cls in inspect.getmembers(outer_cls, inspect.isclass):
                    if nested_cls is not EditorMetadata and issubclass(nested_cls, EditorMetadata):
                        properties = _get_class_properties(nested_cls)
                        class_fqn = f"{outer_cls.__module__}.{outer_cls.__name__}"
                        final_results[class_fqn] = properties
                        break
    except Exception as e:
        # 将关键错误打印到 stderr，并以非零代码退出
        print(f"[Worker] A critical error occurred: {e}", file=sys.stderr)
        # 即使出错，也打印空 JSON 到 stdout，避免父进程解析失败
        print(json.dumps({}))
        sys.exit(1)
        
    # 成功完成，将结果序列化为 JSON 并打印到 stdout
    print(json.dumps(final_results))
    sys.exit(0)

# ==============================================================================
#  Script Entry Point (仅当作为脚本执行时)
# ==============================================================================

if __name__ == "__main__":
    """
    这个 `if` 块是实现双重角色的关键。
    - 如果脚本被 `python prefab_scanner.py --worker <pkg>` 调用，它将作为子进程执行工作。
    - 如果直接运行 `python prefab_scanner.py`，它会显示帮助信息。
    """
    if len(sys.argv) > 2 and sys.argv[1] == '--worker':
        _worker_main(sys.argv[2])
    else:
        print("This is a library module and its own scanning worker.", file=sys.stderr)
        print("Please do not run this file directly.", file=sys.stderr)
        print("You should import and call the `scan_prefabs` function from your application.", file=sys.stderr)
        sys.exit(1)

