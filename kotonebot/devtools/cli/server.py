import webbrowser
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="KotoneBot DevTools")
    
    # Get the dist directory path
    dist_dir = Path(__file__).parent.parent / "web" / "dist"
    
    # Add health check endpoint
    @app.get("/api/health")
    async def health_check():
        return JSONResponse({"status": "ok", "service": "kotonebot-devtools"})
    
    # Mount static files if dist directory exists
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")
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
    open_browser: bool = True
) -> None:
    """Start the DevTools web server.
    
    Args:
        host: Host to listen on (default: 127.0.0.1)
        port: Port to listen on (default: 1178)
        open_browser: Automatically open browser (default: True)
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
