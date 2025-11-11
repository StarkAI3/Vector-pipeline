"""
Main FastAPI Server
Serves admin panel and API endpoints
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import asyncio
import uvicorn

from data_manager.api.admin_routes import router as admin_router
from data_manager.workers.processing_worker import start_worker
from data_manager.core.config import Config
from data_manager.utils.logger import get_logger

logger = get_logger('server')

# Create FastAPI app
app = FastAPI(
    title="DMA Bot Data Management System",
    description="Self-service data upload and management for DMA chatbot",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(admin_router)

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Redirect to admin panel"""
    return FileResponse(str(static_dir / "admin.html"))


@app.get("/admin")
async def admin_panel():
    """Serve admin panel"""
    admin_html = static_dir / "admin.html"
    if admin_html.exists():
        return FileResponse(str(admin_html))
    else:
        return HTMLResponse(
            content="<h1>Admin panel not found</h1><p>Please build the frontend first.</p>",
            status_code=404
        )


@app.on_event("startup")
async def startup_event():
    """Start background worker on server startup"""
    logger.info("Starting DMA Bot Data Management Server")
    logger.info(f"Admin panel: http://{Config.API_HOST}:{Config.API_PORT}/admin")
    
    # Start background worker
    asyncio.create_task(start_worker())
    logger.info("Background worker started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("Shutting down server")
    
    # Stop worker
    from data_manager.workers.processing_worker import get_worker
    worker = get_worker()
    worker.stop()


if __name__ == "__main__":
    # Run server
    uvicorn.run(
        "server:app",
        host=Config.API_HOST,
        port=Config.API_PORT,
        reload=Config.API_RELOAD,
        log_level="info"
    )

