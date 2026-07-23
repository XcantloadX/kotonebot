"""SPA 静态文件服务。"""

from importlib import resources

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


def mount_spa(app: FastAPI) -> None:
    """挂载 SPA 静态文件。"""
    dist_dir = resources.files("kotonebot.devtools.web") / "dist"

    if dist_dir.is_dir():
        assets_dir = dist_dir / "assets"
        if assets_dir.is_dir():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{_path:path}")
        async def spa_catchall(_path: str):
            if _path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)

            index_file = dist_dir / "index.html"
            if index_file.is_file():
                return HTMLResponse(index_file.read_text(encoding="utf-8"))

            return JSONResponse({"detail": "Not Found"}, status_code=404)
    else:
        @app.get("/")
        async def missing_dist():
            return JSONResponse({
                "error": "DevTools frontend not found",
                "message": f"Expected frontend dist at {dist_dir}",
                "info": "Build the frontend using: npm run build in kotonebot-devtool directory"
            }, status_code=503)
