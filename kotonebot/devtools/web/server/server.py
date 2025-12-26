import webbrowser
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
import uvicorn

from kotonebot.devtools.project.project import Project
from .rest_api import create_rest_router


def create_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(title="KotoneBot DevTools")

    project = Project()

    # REST API for DevTools2 (file IO, images, prefab schema)
    app.include_router(create_rest_router(project))
    
    # Get the dist directory path
    dist_dir = Path(__file__).parent.parent / "web" / "dist"

    # Mount static files if dist directory exists
    if dist_dir.exists():
        # 优先将打包好的静态资源挂载到 /assets（如果构建将资源放在 dist/assets）
        assets_dir = dist_dir / "assets"
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        # SPA: 直接将除 /api/* 之外的所有路径映射到 index.html
        @app.get("/{_path:path}")
        async def spa_catchall(_path: str):
            # 保留 API 路由的行为
            if _path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)

            index_file = dist_dir / "index.html"
            if index_file.exists():
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
    open_browser: bool = False
) -> None:
    """Start the DevTools web server.
    
    Args:
        host: Host to listen on (default: 127.0.0.1)
        port: Port to listen on (default: 1178)
        open_browser: Automatically open browser (default: False)
    """
    app = create_app()
    
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


if __name__ == "__main__":
    start_devtools()
