import os
import json
import sys
import pkgutil
import inspect
import importlib
import subprocess
import contextlib
from typing import Any, Dict

from pydantic import BaseModel

# ==============================================================================
#  Public API
# ==============================================================================

def scan_prefabs(package_name: str, python_executable: str = sys.executable) -> Dict[str, Any]:
    """
    在一个隔离的子进程中扫描指定的 Python 包，先扫描默认包
    `kotonebot.core.entities`，然后扫描传入的包（两次扫描在一次子进程内完成）。

    Args:
        package_name: 要扫描的包的点分名称 (例如 'my_app.components')。
        python_executable: 用于运行子进程的 Python 解释器路径。
                           默认为当前正在运行的 Python 解释器。

    Returns:
        一个字典，包含扫描结果；在错误情况下返回空字典。
    """
    default_pkg = 'kotonebot.core.entities'
    print(f"--- Main process (PID: {os.getpid()}) starting worker for packages: '{default_pkg}' and '{package_name}'... ---")

    packages = [default_pkg]
    if package_name and package_name != default_pkg:
        packages.append(package_name)

    # `__file__` 指向当前脚本文件，它将以工作模式被再次执行，传入要扫描的包列表
    command = [python_executable, __file__, '--worker', *packages]
    
    try:
        child_env = os.environ.copy()
        child_env.setdefault('PYTHONUTF8', '1')
        child_env.setdefault('PYTHONIOENCODING', 'utf-8:replace')

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # 手动处理错误，不让它自动抛出异常
            encoding='utf-8',
            env=child_env,
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
    # Collect attributes from the class and its bases (inheritance),
    # allowing subclass attributes to override base attributes.
    properties: Dict[str, Any] = {}
    for base in reversed(cls.__mro__):
        # skip builtin object and EditorMetadata base to avoid copying framework internals
        if base is object or base.__name__ == 'EditorMetadata':
            continue

        for key, value in vars(base).items():
            if key.startswith('__') or callable(value):
                continue

            properties[key] = value

    return properties


def _json_default(obj: Any):
    try:
        if isinstance(obj, BaseModel):
            return obj.model_dump()
    except Exception:
        pass
    return str(obj)

@contextlib.contextmanager
def _redirect_stdout_to_stderr():
    """上下文管理器，临时将 stdout 重定向到 stderr 以隔离用户代码的输出。"""
    original_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = original_stdout

def _worker_main(package_names):
    """
    在隔离的子进程中执行的实际工作逻辑。
    结果通过打印 JSON 到 stdout 来返回。
    """
    # 确保子进程的 sys.path 包含项目根目录
    sys.path.insert(0, os.getcwd())
    
    final_results: dict[str, dict[str, Any]] = {}
    try:
        from kotonebot.devtools import EditorMetadata

        # Normalize package_names to a list
        if isinstance(package_names, str):
            package_names = [package_names]

        all_module_names: list[str] = []
        for pkg_name in package_names:
            try:
                package = importlib.import_module(pkg_name)
            except Exception as e:
                print(f"[Worker] Failed to import package {pkg_name}: {e}", file=sys.stderr)
                continue

            if hasattr(package, '__path__'):
                module_names = [
                    name for _, name, _ in pkgutil.walk_packages(
                        path=package.__path__, prefix=package.__name__ + '.'
                    )
                ]
            else:
                # package is actually a single module (no __path__), include it directly
                module_names = [package.__name__]

            # 保持顺序并去重（默认包先）
            for name in module_names:
                if name not in all_module_names:
                    all_module_names.append(name)

        for module_name in all_module_names:
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
                        prefab_id = properties.get('id') or outer_cls.__name__
                        if prefab_id:
                            properties['id'] = prefab_id
                            final_results[prefab_id] = properties
                        break
    except Exception as e:
        # 将关键错误打印到 stderr，并以非零代码退出
        print(f"[Worker] A critical error occurred: {e}", file=sys.stderr)
        # 即使出错，也打印空 JSON 到 stdout，避免父进程解析失败
        print(json.dumps({}, default=_json_default, ensure_ascii=False))
        sys.exit(1)
        
    output = {
        "version": 1, # Schema version
        "prefabs": final_results
    }
    print(json.dumps(output, default=_json_default, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == '--worker':
        # Pass all package args (sys.argv[2:]) to the worker so it scans multiple packages in one run
        _worker_main(sys.argv[2:])
    else:
        print("This is a library module and its own scanning worker.", file=sys.stderr)
        print("Please do not run this file directly.", file=sys.stderr)
        print("You should import and call the `scan_prefabs` function from your application.", file=sys.stderr)
        sys.exit(1)

