#!/usr/bin/env python3
"""
Playlist App - Main Application Entry Point
Hybrid approach with on-demand and background discovery
"""

import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
import threading
import time

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# Import our application components
from src.playlist_app.models.database import create_tables, SessionLocal
from src.playlist_app.services.discovery import DiscoveryService
from src.playlist_app.api.discovery import router as discovery_router
from src.playlist_app.api.config import router as config_router
from src.playlist_app.api.metadata import router as metadata_router
from src.playlist_app.api.analyzer import router as analyzer_router
from src.playlist_app.api.tracks import router as tracks_router
from src.playlist_app.api.faiss import router as faiss_router
from src.playlist_app.core.config import DiscoveryConfig
from src.playlist_app.core.logging import setup_logging, get_logger, log_performance

# Setup logging
setup_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    log_file=os.getenv("LOG_FILE", None),
    max_file_size=int(os.getenv("LOG_MAX_SIZE", "10485760")),  # 10MB
    backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
    enable_console=True,
    enable_file=True,
    structured_console=os.getenv("LOG_STRUCTURED_CONSOLE", "false").lower() == "true"
)

# Suppress TensorFlow and Essentia logs using proper methods
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress INFO, WARNING, and ERROR logs
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"  # Disable oneDNN optimization messages
os.environ["TF_GPU_ALLOCATOR"] = "cpu"  # Force CPU allocation
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU

# Suppress Essentia logs
try:
    import essentia
    essentia.log.infoActive = False      # Disable INFO messages
    essentia.log.warningActive = False   # Disable WARNING messages
    # Keep ERROR active for critical issues
except ImportError:
    pass

# Suppress other library logs
os.environ["LIBROSA_LOG_LEVEL"] = "WARNING"
os.environ["PYTHONWARNINGS"] = "ignore"

# Also suppress via Python logging if not in debug mode
if os.getenv("LOG_LEVEL", "INFO").upper() != "DEBUG":
    import logging
    logging.getLogger("essentia").setLevel(logging.ERROR)
    logging.getLogger("tensorflow").setLevel(logging.ERROR)
    logging.getLogger("librosa").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.ERROR)
    logging.getLogger("PIL").setLevel(logging.ERROR)

logger = get_logger(__name__)

# Global variables for background discovery
background_discovery_task: Optional[asyncio.Task] = None
discovery_interval: int = int(os.getenv("DISCOVERY_INTERVAL", "3600"))  # Default: 1 hour
background_discovery_enabled: bool = os.getenv("ENABLE_BACKGROUND_DISCOVERY", "false").lower() == "true"

def initialize_database():
    """Initialize database tables"""
    import time
    
    logger.info("Initializing database tables...")
    
    # Wait for PostgreSQL to be ready (it's running in a separate container)
    logger.info("Waiting for PostgreSQL to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            # Test database connection
            db = SessionLocal()
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
            db.close()
            logger.info("PostgreSQL is ready!")
            break
        except Exception as e:
            if i == max_retries - 1:
                raise Exception(f"PostgreSQL failed to connect within timeout: {e}")
            logger.info(f"Waiting for PostgreSQL... (attempt {i+1}/{max_retries})")
            time.sleep(2)
    
    # Create SQLAlchemy tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database initialization completed successfully")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Playlist App...")
    
    # Initialize database
    try:
        initialize_database()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Start background discovery if enabled
    if background_discovery_enabled:
        logger.info(f"Starting background discovery with {discovery_interval}s interval")
        await start_background_discovery()
    else:
        logger.info("Background discovery disabled - use API endpoints for on-demand discovery")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Playlist App...")
    if background_discovery_task and not background_discovery_task.done():
        background_discovery_task.cancel()
        try:
            await background_discovery_task
        except asyncio.CancelledError:
            pass
    logger.info("Playlist App shutdown complete")

async def background_discovery_worker():
    """Background worker for periodic file discovery"""
    logger.info("Background discovery worker started")
    
    while True:
        try:
            # Create database session
            db = SessionLocal()
            try:
                # Create discovery service
                discovery_service = DiscoveryService(db)
                
                # Run discovery with performance logging
                logger.info("Running background discovery...")
                results = discovery_service.discover_files()
                
                logger.info(f"Background discovery complete - Added: {len(results['added'])}, Removed: {len(results['removed'])}, Unchanged: {len(results['unchanged'])}")
                
            except Exception as e:
                logger.error(f"Background discovery failed: {e}", exc_info=True)
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Background discovery worker error: {e}", exc_info=True)
        
        # Wait for next interval
        await asyncio.sleep(discovery_interval)

async def start_background_discovery():
    """Start the background discovery task"""
    global background_discovery_task
    background_discovery_task = asyncio.create_task(background_discovery_worker())

def run_discovery_sync():
    """Synchronous wrapper for discovery (for background tasks)"""
    try:
        db = SessionLocal()
        discovery_service = DiscoveryService(db)
        
        results = discovery_service.discover_files()
        
        logger.info(f"Manual discovery completed - Added: {len(results['added'])}, Removed: {len(results['removed'])}, Unchanged: {len(results['unchanged'])}")
        
        db.close()
        return results
    except Exception as e:
        logger.error(f"Sync discovery failed: {e}", exc_info=True)
        return None

# Create FastAPI application
app = FastAPI(
    title="Playlist App API",
    description="Audio discovery and playlist generation with Essentia and TensorFlow",
    version="0.1.0",
    lifespan=lifespan
)

# Add request ID middleware (temporarily disabled)
# app.add_middleware(RequestIdMiddleware)

# Include routers
app.include_router(discovery_router)
app.include_router(config_router)
app.include_router(metadata_router)
app.include_router(analyzer_router)
app.include_router(tracks_router)
app.include_router(faiss_router)

@app.get("/")
async def root():
    """Root endpoint with app information"""
    return {
        "message": "Playlist App API - Audio discovery and playlist generation",
        "version": "0.1.0",
        "background_discovery": background_discovery_enabled,
        "discovery_interval": discovery_interval if background_discovery_enabled else None,
        "endpoints": {
            "health": "/health",
            "discovery": "/api/discovery",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "background_discovery": background_discovery_enabled,
            "essentia_version": "2.1-beta6-dev",
            "tensorflow_algorithms": [
                "TensorflowInputFSDSINet",
                "TensorflowInputMusiCNN", 
                "TensorflowInputTempoCNN",
                "TensorflowInputVGGish"
            ]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.post("/discovery/trigger")
async def trigger_discovery(background_tasks: BackgroundTasks):
    """Trigger discovery manually (on-demand)"""
    try:
        # Run discovery in background task to avoid blocking
        background_tasks.add_task(run_discovery_sync)
        
        return {
            "status": "success",
            "message": "Discovery triggered successfully",
            "note": "Check logs for results or use /api/discovery/stats for statistics"
        }
    except Exception as e:
        logger.error(f"Failed to trigger discovery: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to trigger discovery: {str(e)}"}
        )

@app.get("/config")
async def get_config():
    """Get current application configuration"""
    return {
        "database_url": os.getenv("DATABASE_URL", "not set"),
        "search_directories": DiscoveryConfig.get_search_directories(),
        "supported_extensions": DiscoveryConfig.get_supported_extensions(),
        "background_discovery_enabled": background_discovery_enabled,
        "discovery_interval": discovery_interval,
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "cache_ttl": DiscoveryConfig.DISCOVERY_CACHE_TTL,
        "batch_size": DiscoveryConfig.DISCOVERY_BATCH_SIZE
    }

@app.post("/discovery/background/toggle")
async def toggle_background_discovery():
    """Toggle background discovery on/off"""
    global background_discovery_enabled, background_discovery_task
    
    try:
        if background_discovery_enabled:
            # Stop background discovery
            if background_discovery_task and not background_discovery_task.done():
                background_discovery_task.cancel()
                try:
                    await background_discovery_task
                except asyncio.CancelledError:
                    pass
            background_discovery_enabled = False
            message = "Background discovery stopped"
        else:
            # Start background discovery
            await start_background_discovery()
            background_discovery_enabled = True
            message = "Background discovery started"
        
        return {
            "status": "success",
            "message": message,
            "background_discovery_enabled": background_discovery_enabled
        }
    except Exception as e:
        logger.error(f"Failed to toggle background discovery: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to toggle background discovery: {str(e)}"}
        )

@app.post("/database/reset")
async def reset_database(confirm: bool = False):
    """Reset and recreate the database"""
    if not confirm:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Database reset requires confirmation",
                "message": "Set confirm=true to proceed with database reset"
            }
        )
    
    try:
        from src.playlist_app.models.database import Base, engine, create_tables
        
        logger.warning("Database reset requested - dropping all tables")
        Base.metadata.drop_all(bind=engine)
        
        logger.info("Recreating database tables")
        create_tables()
        
        return {
            "status": "success",
            "message": "Database reset completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Database reset failed: {str(e)}"}
        )

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"Starting Playlist App on {host}:{port}")
    logger.info(f"Background discovery: {'enabled' if background_discovery_enabled else 'disabled'}")
    logger.info(f"Discovery interval: {discovery_interval}s")
    
    # Run the application
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,  # Disable reload in production
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )

