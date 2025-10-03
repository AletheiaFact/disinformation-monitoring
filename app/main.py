"""FastAPI application entry point"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import database
from app.scheduler import setup_scheduler, start_scheduler, shutdown_scheduler
from app.routes import sources, content, stats, aletheia, tuning

# Configure logging
logging.basicConfig(
    level=settings.log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""

    # Startup
    logger.info("Starting Disinformation Monitoring POC...")

    # Connect to database
    await database.connect()

    # Setup and start scheduler
    setup_scheduler()
    start_scheduler()

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down application...")

    # Stop scheduler
    shutdown_scheduler()

    # Disconnect from database
    await database.disconnect()

    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Disinformation Monitoring POC",
    description="Automated extraction and submission of news content to AletheiaFact",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sources.router)
app.include_router(content.router)
app.include_router(stats.router)
app.include_router(aletheia.router)
app.include_router(tuning.router)

# Mount frontend static files
try:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
except Exception as e:
    logger.warning(f"Could not mount frontend static files: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "disinformation-monitoring-poc",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
