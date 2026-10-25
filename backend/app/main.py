"""
FastAPI application entry point.
Configures CORS, API routers, static asset serving, and SPA client-side routing fallback.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.endpoints import router as api_router

app = FastAPI(
    title="REint Decision-Time Wind Forecast Intelligence Portal",
    description="Reconstruct the national wind outlook available at buying deadlines and quantitatively evaluate forecast performance.",
    version="1.0.0",
)

# CORS setup for dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(api_router)

# Frontend static distribution path
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    # Mount assets directory if present
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # SPA Fallback for any client-side routes (e.g. /replay, /performance, /evidence)
    @app.get("/{full_path:path}", response_class=FileResponse)
    async def serve_spa(request: Request, full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path == "api":
            return HTMLResponse(status_code=404, content="API route not found")

        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
else:

    @app.get("/", response_class=HTMLResponse)
    def index_fallback():
        return """
        <!DOCTYPE html>
        <html>
            <head><title>REint Wind Forecast Portal API</title></head>
            <body style="font-family: sans-serif; padding: 2rem;">
                <h2>REint Decision-Time Wind Forecast Intelligence Portal</h2>
                <p>Backend API is active. Interactive documentation is available at <a href="/docs">/docs</a>.</p>
                <p>Frontend static build will be served here once generated.</p>
            </body>
        </html>
        """
