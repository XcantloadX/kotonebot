"""生成 DevTools 前端 API 的 OpenAPI 规范文件。

将 FastAPI 路由定义导出为 ``js/apps/devtools-app/src/api/openapi.json``，
供 ``openapi-typescript`` 生成类型化的 API 客户端类型
（见 devtools-app 的 ``npm run gen:api``）。
OpenAPI 结构只依赖路由声明而非具体项目内容，因此使用临时项目即可导出。
"""

import json
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = REPO_ROOT / "js" / "apps" / "devtools-app" / "src" / "api" / "openapi.json"

def build_openapi() -> dict:
    """构建 FastAPI app 并返回 OpenAPI 规范。"""
    from kotonebot.devtools.project.project import Project
    from kotonebot.devtools.services.context import DevtoolsContext
    from kotonebot.devtools.transports.http.app import create_app

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        resources = root / "resources"
        resources.mkdir()
        pyproject_path = root / "pyproject.toml"
        # resource_path 按进程 CWD 解析，因此写入绝对路径
        pyproject_path.write_text(
            f'[tool.kotonebot.editor]\nresource_path = "{resources.as_posix()}"\n',
            encoding="utf-8",
        )
        project = Project(conf_path=str(pyproject_path))
        ctx = DevtoolsContext(project)
        app = create_app(ctx)
        return app.openapi()


def main() -> None:
    spec = build_openapi()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OpenAPI spec written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
