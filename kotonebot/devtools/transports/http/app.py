"""FastAPI 应用工厂与生命周期管理。"""

import logging
import socket
import time
import webbrowser
from dataclasses import dataclass
from threading import Thread
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from kotonebot.devtools.errors import DevtoolsError
from kotonebot.devtools.services.context import DevtoolsContext

from .routes.fs_routes import router as fs_router
from .routes.project_routes import router as project_router
from .routes.image_routes import router as image_router
from .routes.meta_routes import router as meta_router
from .routes.variant_routes import router as variant_router
from .routes.document_routes import router as document_router
from .routes.ai_routes import router as ai_router
from .routes.device_routes import router as device_router
from .routes.conversion_routes import router as conversion_router
from .routes.command_routes import router as command_router
from .routes.health_routes import router as health_router
from .spa import mount_spa


@dataclass
class HttpServerHandle:
    server: Optional[uvicorn.Server]
    thread: Optional[Thread]


def _can_connect(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except OSError:
        return False


def create_app(ctx: DevtoolsContext) -> FastAPI:
    """创建 FastAPI 应用，注入共享上下文。"""
    app = FastAPI(title="KotoneBot DevTools")
    app.state.ctx = ctx

    @app.exception_handler(DevtoolsError)
    async def handle_devtools_error(request: Request, exc: DevtoolsError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "code": exc.code, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        logging.exception("Unhandled error in %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"success": False, "code": "INTERNAL", "message": "Internal server error"},
        )

    app.include_router(fs_router, prefix="/api")
    app.include_router(project_router, prefix="/api")
    app.include_router(image_router, prefix="/api")
    app.include_router(meta_router, prefix="/api")
    app.include_router(variant_router, prefix="/api")
    app.include_router(document_router, prefix="/api")
    app.include_router(ai_router, prefix="/api")
    app.include_router(device_router, prefix="/api")
    app.include_router(conversion_router, prefix="/api")
    app.include_router(command_router, prefix="/api")
    app.include_router(health_router, prefix="/api")

    mount_spa(app)

    return app


def start_http(ctx: DevtoolsContext, *, host: str = "127.0.0.1", port: int = 1178,
               open_browser: bool = False) -> None:
    """前台启动 HTTP 服务。"""
    app = create_app(ctx)

    if open_browser:
        url = f"http://{host}:{port}"
        webbrowser.open(url)

    uvicorn.run(app, host=host, port=port, log_level="info")


def start_http_background(ctx: DevtoolsContext, *, host: str = "127.0.0.1", port: int = 1178
                          ) -> HttpServerHandle:
    """后台线程启动 HTTP 服务。"""
    app = create_app(ctx)
    config = uvicorn.Config(app=app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config=config)
    thread = Thread(target=server.run, daemon=True, name="kotonebot-devtools-http")
    thread.start()
    deadline = time.time() + 10.0
    while not server.started:
        if not thread.is_alive():
            if _can_connect(host, port):
                return HttpServerHandle(server=None, thread=None)
            raise RuntimeError("Devtools HTTP server failed to start")
        if time.time() >= deadline:
            raise RuntimeError("Devtools HTTP server start timed out")
        time.sleep(0.05)
    return HttpServerHandle(server=server, thread=thread)


def stop_http_background(handle: HttpServerHandle) -> None:
    """停止后台 HTTP 服务。"""
    if handle.server is None or handle.thread is None:
        return
    handle.server.should_exit = True
    handle.thread.join(timeout=5.0)
