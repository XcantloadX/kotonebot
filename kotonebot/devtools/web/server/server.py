import webbrowser
import time
import socket
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from threading import Thread

import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

from kotonebot.devtools.errors import DevtoolsError
from kotonebot.devtools.project.project import Project
from .rest_api import create_rest_router


@dataclass
class DevtoolsServerHandle:
    server: uvicorn.Server | None
    thread: Thread | None


def _can_connect(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def create_app(*, workspace: str | None = None):
    """Create and configure the FastAPI application."""
    app = FastAPI(title="KotoneBot DevTools")

    @app.exception_handler(DevtoolsError)
    async def handle_devtools_error(request, exc: DevtoolsError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "code": exc.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request, exc):
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logging.exception("Unhandled error in %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"success": False, "code": "INTERNAL", "message": "Internal server error"},
        )

    if workspace is None:
        project = Project()
    else:
        conf_path = (Path(workspace).resolve() / "pyproject.toml").as_posix()
        project = Project(conf_path=conf_path)

    # REST API for DevTools2 (file IO, images, prefab schema)
    app.include_router(create_rest_router(project))
    
    # Get the dist directory path
    dist_dir = resources.files("kotonebot.devtools.web") / "dist"

    # Mount static files if dist directory exists
    if dist_dir.is_dir():
        # 优先将打包好的静态资源挂载到 /assets（如果构建将资源放在 dist/assets）
        assets_dir = dist_dir / "assets"
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        # SPA: 直接将除 /api/* 之外的所有路径映射到 index.html
        @app.get("/{_path:path}")
        async def spa_catchall(_path: str):
            # 保留 API 路由的行为
            if _path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)

            index_file = dist_dir / "index.html"
            if index_file.is_file():
                return HTMLResponse(index_file.read_text(encoding="utf-8"))

            return JSONResponse({"detail": "Not Found"}, status_code=404)
    else:
        # If dist doesn't exist, provide a helpful message
        @app.get("/")
        async def missing_dist():
            return JSONResponse({
                "error": "DevTools frontend not found",
                "message": f"Expected frontend dist at {dist_dir}",
                "info": "Build the frontend using: npm run build in kotonebot-devtool directory"
            }, status_code=503)
    
    return app


def start_devtools(
    host: str = "127.0.0.1",
    port: int = 1178,
    open_browser: bool = False,
    workspace: str | None = None,
) -> None:
    """Start the DevTools web server.
    
    Args:
        host: Host to listen on (default: 127.0.0.1)
        port: Port to listen on (default: 1178)
        open_browser: Automatically open browser (default: False)
    """
    app = create_app(workspace=workspace)
    
    # Open browser before starting server
    if open_browser:
        url = f"http://{host}:{port}"
        webbrowser.open(url)
    
    # Start server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


def start_devtools_background(host: str = "127.0.0.1", port: int = 1178, workspace: str | None = None) -> DevtoolsServerHandle:
    app = create_app(workspace=workspace)
    config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config=config)
    thread = Thread(target=server.run, daemon=True, name="kotonebot-devtools-http")
    thread.start()
    deadline = time.time() + 10.0
    while not server.started:
        if not thread.is_alive():
            if _can_connect(host, port):
                return DevtoolsServerHandle(server=None, thread=None)
            raise RuntimeError("Devtools HTTP server failed to start")
        if time.time() >= deadline:
            raise RuntimeError("Devtools HTTP server start timed out")
        time.sleep(0.05)
    return DevtoolsServerHandle(server=server, thread=thread)


def stop_devtools_background(handle: DevtoolsServerHandle) -> None:
    if handle.server is None or handle.thread is None:
        return
    handle.server.should_exit = True
    handle.thread.join(timeout=5.0)


if __name__ == "__main__":
    start_devtools()
