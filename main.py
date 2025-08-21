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
import zipfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from sqlalchemy import text

# Import our application components
from src.playlist_app.models.database import get_db, SessionLocal, File
from src.playlist_app.services.discovery import DiscoveryService
from src.playlist_app.api.discovery import router as discovery_router
from src.playlist_app.api.config import router as config_router
from src.playlist_app.api.metadata import router as metadata_router
from src.playlist_app.api.analyzer import router as analyzer_router
from src.playlist_app.api.tracks import router as tracks_router
from src.playlist_app.api.faiss import router as faiss_router

from src.playlist_app.api.playlists import router as playlists_router
from src.playlist_app.core.config import DiscoveryConfig
from src.playlist_app.core.logging import setup_logging, get_logger, log_performance

# Load configuration first
from src.playlist_app.core.config_loader import config_loader

# Setup logging with configuration
try:
    logging_config = config_loader.get_logging_config()
    setup_logging(
        log_level=logging_config.get("log_level", "INFO"),
        log_file=os.getenv("LOG_FILE", None),
        max_file_size=logging_config.get("max_file_size", 10485760),  # 10MB
        backup_count=logging_config.get("max_backups", 5),
        enable_console=True,
        enable_file=True,
        structured_console=os.getenv("LOG_STRUCTURED_CONSOLE", "false").lower() == "true"
    )
    
    # Apply log suppression based on configuration
    suppression_config = logging_config.get("suppression", {})
    
    # TensorFlow suppression
    if suppression_config.get("tensorflow", True):
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress INFO, WARNING, and ERROR logs
    
    # Essentia suppression
    if suppression_config.get("essentia", True):
        try:
            import essentia
            essentia.log.infoActive = False      # Disable INFO messages
            essentia.log.warningActive = False   # Disable WARNING messages
            # Keep ERROR active for critical issues
        except ImportError:
            pass
    
    # Librosa suppression
    if suppression_config.get("librosa", True):
        os.environ["LIBROSA_LOG_LEVEL"] = "WARNING"
    
    # Python warnings suppression
    if suppression_config.get("pil", True):
        os.environ["PYTHONWARNINGS"] = "ignore"
        
except Exception as e:
    # Fallback to environment variables
    setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_file=os.getenv("LOG_FILE", None),
        max_file_size=int(os.getenv("LOG_MAX_SIZE", "10485760")),  # 10MB
        backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
        enable_console=True,
        enable_file=True,
        structured_console=os.getenv("LOG_STRUCTURED_CONSOLE", "false").lower() == "true"
    )
    
    # Fallback to hardcoded suppression
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    
    try:
        import essentia
        essentia.log.infoActive = False
        essentia.log.warningActive = False
    except ImportError:
        pass
    
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

# Global variables for background tasks
background_discovery_enabled = False
background_discovery_task = None
discovery_interval = 300  # 5 minutes - will be updated from config
discovery_progress = {"status": "idle", "progress": 0, "message": ""}
analysis_progress = {"status": "idle", "progress": 0, "message": "", "total_files": 0, "completed_files": 0}

# Load saved configurations at module level
def load_saved_configurations():
    """Load saved configurations into global variables"""
    global background_discovery_enabled, discovery_interval
    
    try:
        logger.info("Loading saved configurations at module level...")
        
        # Load app settings
        app_config = config_loader.get_app_settings()
        
        # Load discovery settings
        discovery_config = app_config.get("discovery", {})
        background_discovery_enabled = discovery_config.get("background_enabled", False)
        discovery_interval = discovery_config.get("interval", 300)
        
        logger.info(f"Loaded discovery settings: background_enabled={background_discovery_enabled}, interval={discovery_interval}")
        
        # Load database settings
        db_config = config_loader.get_database_config()
        logger.info(f"Loaded database configuration: pool_size={db_config.get('pool_size', 25)}")
        
        logger.info("Configuration loading completed at module level")
    except Exception as e:
        logger.error(f"Failed to load saved configurations at module level: {e}")
        logger.info("Using default configuration values")

# Load configurations at module level
load_saved_configurations()

def reload_configurations():
    """Reload configurations dynamically"""
    global background_discovery_enabled, discovery_interval
    
    try:
        logger.info("Reloading configurations dynamically...")
        
        # Clear config cache first
        config_loader.reload_config()
        
        # Load app settings
        app_config = config_loader.get_app_settings()
        
        # Load discovery settings
        discovery_config = app_config.get("discovery", {})
        background_discovery_enabled = discovery_config.get("background_enabled", False)
        discovery_interval = discovery_config.get("interval", 300)
        
        logger.info(f"Reloaded discovery settings: background_enabled={background_discovery_enabled}, interval={discovery_interval}")
        
        # Load database settings
        db_config = config_loader.get_database_config()
        logger.info(f"Reloaded database configuration: pool_size={db_config.get('pool_size', 25)}")
        
        # Reload logging configuration
        try:
            logging_config = config_loader.get_logging_config()
            logger.info(f"Reloaded logging configuration: log_level={logging_config.get('log_level', 'INFO')}")
        except Exception as e:
            logger.warning(f"Failed to reload logging configuration: {e}")
        
        logger.info("Configuration reloading completed")
        return True
    except Exception as e:
        logger.error(f"Failed to reload configurations: {e}")
        return False

def initialize_database():
    """Initialize database tables"""
    import time
    
    logger.info("Initializing database tables...")
    
    # Wait for PostgreSQL to be ready (it's running in a separate container)
    logger.info("Waiting for PostgreSQL to be ready...")
    
    # Get retry settings from configuration
    try:
        db_config = config_loader.get_database_config()
        retry_settings = db_config.get("retry_settings", {})
        max_retries = retry_settings.get("max_retries", 30)
        initial_delay = retry_settings.get("initial_delay", 2)
        backoff_multiplier = retry_settings.get("backoff_multiplier", 1)
    except Exception:
        # Fallback to hardcoded values
        max_retries = 30
        initial_delay = 2
        backoff_multiplier = 1
    
    delay = initial_delay
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
            time.sleep(delay)
            delay = min(delay * backoff_multiplier, 30)  # Cap delay at 30 seconds
    
    # Create schemas first
    logger.info("Creating database schemas...")
    from src.playlist_app.models.database import engine
    
    # Create schemas
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analysis"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS playlists"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS recommendations"))
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ui"))
        conn.commit()
    
    # Create SQLAlchemy tables
    logger.info("Creating database tables...")
    # Initialize database tables
    from src.playlist_app.models.database import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialization completed successfully")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Playlist App...")
    logger.info("Lifespan function called - configuration loading will begin...")
    
    # Load saved configurations
    try:
        logger.info("Starting configuration loading process...")
        
        # Load app settings
        app_config = config_loader.get_app_settings()
        
        # Load discovery settings
        discovery_config = app_config.get("discovery", {})
        global background_discovery_enabled, discovery_interval
        
        background_discovery_enabled = discovery_config.get("background_enabled", False)
        discovery_interval = discovery_config.get("interval", 300)
        
        logger.info(f"Loaded discovery settings: background_enabled={background_discovery_enabled}, interval={discovery_interval}")
        
        # Load database settings
        db_config = config_loader.get_database_config()
        logger.info(f"Loaded database configuration: pool_size={db_config.get('pool_size', 25)}")
        
        # Load analysis settings
        analysis_config = config_loader.get_config("analysis_config")
        logger.info(f"Loaded analysis configuration: max_workers={analysis_config.get('performance', {}).get('parallel_processing', {}).get('max_workers', 8)}")
        
        logger.info("Configuration loading completed")
    except Exception as e:
        logger.error(f"Failed to load saved configurations: {e}")
        logger.info("Using default configuration values")
    
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
    global discovery_progress
    try:
        discovery_progress = {"status": "running", "progress": 0, "message": "Starting discovery...", "discovered_count": 0}
        
        db = SessionLocal()
        discovery_service = DiscoveryService(db)
        
        # Update progress
        discovery_progress = {"status": "running", "progress": 25, "message": "Scanning directories...", "discovered_count": 0}
        
        results = discovery_service.discover_files()
        
        # Get current total count after discovery
        total_count = db.query(File).filter(File.is_active == True).count()
        
        # Update progress to complete
        discovery_progress = {"status": "completed", "progress": 100, "message": f"Discovery completed - Added: {len(results['added'])}, Removed: {len(results['removed'])}", "discovered_count": total_count}
        
        logger.info(f"Manual discovery completed - Added: {len(results['added'])}, Removed: {len(results['removed'])}, Unchanged: {len(results['unchanged'])}")
        
        db.close()
        return results
    except Exception as e:
        discovery_progress = {"status": "failed", "progress": 0, "message": f"Discovery failed: {str(e)}", "discovered_count": 0}
        logger.error(f"Sync discovery failed: {e}", exc_info=True)
        return None

def run_analysis_sync(include_tensorflow=False, max_workers=None, max_files=None):
    """Synchronous wrapper for analysis (for background tasks)"""
    global analysis_progress
    import time
    
    start_time = time.time()
    try:
        analysis_progress = {"status": "running", "progress": 0, "message": "Starting analysis...", "total_files": 0, "completed_files": 0}
        
        # Get configuration
        analysis_config = config_loader.get_analysis_config()
        
        # Use config value if max_workers not provided
        if max_workers is None:
            max_workers = analysis_config.get("performance", {}).get("parallel_processing", {}).get("max_workers", 8)
        
        # Get all files that need analysis
        db = SessionLocal()
        from src.playlist_app.models.database import File, TrackAnalysisSummary
        from sqlalchemy.orm import joinedload
        
        # Query files that either don't have analysis summary or have incomplete analysis
        files_query = db.query(File).outerjoin(TrackAnalysisSummary).filter(
            (TrackAnalysisSummary.id.is_(None)) |  # No analysis summary exists
            (TrackAnalysisSummary.analysis_status != 'complete')  # Analysis is not complete
        )
        
        files = files_query.all()
        all_files = [file.file_path for file in files]
        db.close()
        
        # Limit files if max_files is specified
        if max_files and max_files > 0:
            all_files = all_files[:max_files]
            logger.info(f"Limited to {max_files} files for analysis")
        
        if not all_files:
            analysis_progress = {"status": "completed", "progress": 100, "message": "No files need analysis", "total_files": 0, "completed_files": 0}
            return {"message": "No files need analysis", "total_files": 0}
        
        total_files = len(all_files)
        analysis_progress = {"status": "running", "progress": 10, "message": f"Preparing to analyze {total_files} files...", "total_files": total_files, "completed_files": 0}
        
        logger.info(f"Analyzing {total_files} files with modular analysis service")
        
        # Use the new independent analyzer services
        from src.playlist_app.services.analysis_coordinator import analysis_coordinator
        
        # Get module configuration - read fresh to ensure we have latest settings
        analysis_config = config_loader.get_analysis_config()
        enable_essentia = True  # Essentia is always enabled
        enable_tensorflow = include_tensorflow and analysis_config.get("essentia", {}).get("algorithms", {}).get("enable_tensorflow", True)
        enable_faiss = analysis_config.get("essentia", {}).get("algorithms", {}).get("enable_faiss", True)
        
        logger.info(f"Modules enabled - Essentia: {enable_essentia}, TensorFlow: {enable_tensorflow}, FAISS: {enable_faiss}")
        
        # Process files using analysis coordinator (no batching needed)
        logger.info(f"Processing {len(all_files)} files with analysis coordinator")
        
        # Update progress for analysis start
        analysis_progress = {
            "status": "running", 
            "progress": 50, 
            "message": f"Processing {len(all_files)} files with analysis coordinator...", 
            "total_files": total_files, 
            "completed_files": 0
        }
        
        # Process files
        try:
            # Create a new database session for the analysis
            analysis_db = SessionLocal()
            analysis_results = analysis_coordinator.analyze_pending_files(
                analysis_db,
                max_files=max_files,
                force_reanalyze=False,
                enable_essentia=enable_essentia,
                enable_tensorflow=enable_tensorflow,
                enable_faiss=enable_faiss
            )
            analysis_db.close()
            
            # Extract results from the analysis coordinator response
            if analysis_results.get("success"):
                summary = analysis_results.get("summary", {})
                completed_count = summary.get("successful", 0)
                failed_count = summary.get("failed", 0)
                logger.info(f"Analysis completed: {completed_count} successful, {failed_count} failed")
            else:
                logger.error(f"Analysis failed: {analysis_results.get('message', 'Unknown error')}")
                completed_count = 0
                failed_count = len(all_files)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            completed_count = 0
            failed_count = len(all_files)
        
        # Update progress to complete
        analysis_progress = {
            "status": "completed", 
            "progress": 100, 
            "message": f"Analysis completed - {completed_count}/{total_files} files processed", 
            "total_files": total_files, 
            "completed_files": completed_count
        }
        
        end_time = time.time()
        logger.info(f"Analysis completed in {end_time - start_time:.2f} seconds")
        
        return {
            "status": "success",
            "total_files": total_files,
            "completed_files": completed_count,
            "failed_files": failed_count,
            "duration": end_time - start_time,
            "modules_used": {
                "essentia": enable_essentia,
                "tensorflow": enable_tensorflow,
                "faiss": enable_faiss
            }
        }
        
    except Exception as e:
        analysis_progress = {"status": "failed", "progress": 0, "message": f"Analysis failed: {str(e)}", "total_files": 0, "completed_files": 0}
        logger.error(f"Sync analysis failed: {e}", exc_info=True)
        return None

# Create FastAPI application
app = FastAPI(
    title="Playlist App API",
    description="Audio discovery and playlist generation with Essentia and TensorFlow",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

app.include_router(playlists_router)

@app.get("/api")
async def api_info():
    """API information endpoint"""
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
        # Reset progress
        global discovery_progress
        discovery_progress = {"status": "starting", "progress": 0, "message": "Initializing discovery...", "discovered_count": 0}
        
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

@app.get("/discovery/status")
async def get_discovery_status():
    """Get current discovery progress status"""
    global discovery_progress
    return {
        "status": "success",
        "discovery": discovery_progress
    }

@app.post("/analysis/trigger")
async def trigger_analysis(
    background_tasks: BackgroundTasks,
    include_tensorflow: bool = False,
    max_workers: Optional[int] = None,
    max_files: Optional[int] = None
):
    """Trigger analysis manually (on-demand)"""
    try:
        # Reset progress
        global analysis_progress
        analysis_progress = {"status": "starting", "progress": 0, "message": "Initializing analysis...", "total_files": 0, "completed_files": 0}
        
        # Run analysis in background task to avoid blocking
        background_tasks.add_task(run_analysis_sync, include_tensorflow, max_workers, max_files)
        
        return {
            "status": "success",
            "message": "Analysis triggered successfully",
            "note": "Check logs for results or use /api/analyzer/statistics for statistics"
        }
    except Exception as e:
        logger.error(f"Failed to trigger analysis: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to trigger analysis: {str(e)}"}
        )

@app.get("/analysis/status")
async def get_analysis_status():
    """Get current analysis progress status"""
    global analysis_progress
    return {
        "status": "success",
        "analysis": analysis_progress
    }

@app.get("/analysis/modules/status")
async def get_analysis_modules_status():
    """Get status of all analysis modules"""
    try:
        # Get current analysis config
        analysis_config = config_loader.get_analysis_config()
        
        # Get status from independent analyzers
        from src.playlist_app.services.independent_essentia_service import essentia_service
        from src.playlist_app.services.independent_tensorflow_service import tensorflow_service
        from src.playlist_app.services.independent_faiss_service import faiss_service
        
        # Read enabled status from config
        tensorflow_enabled = analysis_config.get("essentia", {}).get("algorithms", {}).get("enable_tensorflow", True)
        faiss_enabled = analysis_config.get("essentia", {}).get("algorithms", {}).get("enable_faiss", False)
        
        module_status = {
            "essentia": {
                "available": True,
                "enabled": True,
                "description": "Independent Essentia analyzer"
            },
            "tensorflow": {
                "available": tensorflow_service.is_available(),
                "enabled": tensorflow_enabled,
                "description": "Independent TensorFlow analyzer"
            },
            "faiss": {
                "available": True,
                "enabled": faiss_enabled,
                "description": "Independent FAISS analyzer"
            }
        }
        
        return {
            "status": "success",
            "modules": module_status
        }
    except Exception as e:
        logger.error(f"Failed to get module status: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get module status: {str(e)}"}
        )

@app.post("/analysis/modules/toggle")
async def toggle_analysis_module(module_name: str, enabled: bool):
    """Toggle an analysis module on/off"""
    try:
        # Get current analysis config
        analysis_config = config_loader.get_analysis_config()
        
        # Update configuration
        if module_name == "essentia":
            # Essentia is always enabled, but we can update its settings
            return {"status": "success", "message": "Essentia is always enabled"}
        elif module_name == "tensorflow":
            if "essentia" not in analysis_config:
                analysis_config["essentia"] = {}
            if "algorithms" not in analysis_config["essentia"]:
                analysis_config["essentia"]["algorithms"] = {}
            analysis_config["essentia"]["algorithms"]["enable_tensorflow"] = enabled
            config_loader.update_config("analysis_config", analysis_config)
        elif module_name == "faiss":
            if "essentia" not in analysis_config:
                analysis_config["essentia"] = {}
            if "algorithms" not in analysis_config["essentia"]:
                analysis_config["essentia"]["algorithms"] = {}
            analysis_config["essentia"]["algorithms"]["enable_faiss"] = enabled
            config_loader.update_config("analysis_config", analysis_config)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unknown module: {module_name}"}
            )
        
        return {
            "status": "success",
            "message": f"Module {module_name} {'enabled' if enabled else 'disabled'}",
            "module": module_name,
            "enabled": enabled
        }
    except Exception as e:
        logger.error(f"Failed to toggle module {module_name}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to toggle module: {str(e)}"}
        )

@app.get("/config")
async def get_config():
    """Get current application configuration"""
    try:
        # Get all configurations using config_loader
        configs = {
            "app_settings": config_loader.get_app_settings(),
            "database": config_loader.get_database_config(),
            "logging": config_loader.get_logging_config(),
            "analysis_config": config_loader.get_config("analysis_config"),
            "discovery": config_loader.get_discovery_config()
        }
        
        # Get current runtime config
        runtime_config = {
            "database_url": os.getenv("DATABASE_URL", "not set"),
            "search_directories": DiscoveryConfig.get_search_directories(),
            "supported_extensions": DiscoveryConfig.get_supported_extensions(),
            "background_discovery_enabled": background_discovery_enabled,
            "discovery_interval": discovery_interval,
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "cache_ttl": DiscoveryConfig.get_cache_ttl(),
            "batch_size": DiscoveryConfig.get_batch_size()
        }
        
        return {
            "runtime": runtime_config,
            "configs": configs
        }
    except Exception as e:
        logger.error(f"Failed to get configuration: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get configuration: {str(e)}"}
        )

@app.post("/config/update")
async def update_config(request: dict):
    """Update application configuration"""
    try:
        section = request.get("section")
        data = request.get("data", {})
        
        if section == "general":
            # Update general settings
            global background_discovery_enabled, discovery_interval
            
            if "background_discovery_enabled" in data:
                background_discovery_enabled = data["background_discovery_enabled"]
            
            if "discovery_interval" in data:
                discovery_interval = data["discovery_interval"]
            
            if "log_level" in data:
                os.environ["LOG_LEVEL"] = data["log_level"]
            
            if "cache_ttl" in data:
                DiscoveryConfig.DISCOVERY_CACHE_TTL = data["cache_ttl"]
            
            if "api_host" in data:
                os.environ["API_HOST"] = data["api_host"]
            
            if "api_port" in data:
                os.environ["API_PORT"] = str(data["api_port"])
            
            if "python_path" in data:
                os.environ["PYTHONPATH"] = data["python_path"]
            
            if "data_directory" in data:
                os.environ["DATA_DIRECTORY"] = data["data_directory"]
            
            if "cache_directory" in data:
                os.environ["CACHE_DIRECTORY"] = data["cache_directory"]
            
            if "logs_directory" in data:
                os.environ["LOGS_DIRECTORY"] = data["logs_directory"]
            
            # Save to persistent storage
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("general", data)
                
        elif section == "discovery":
            # Update discovery settings - now using config_loader
            # Save to persistent storage first
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("discovery", data)
            
            # Reload configurations to apply changes
            reload_configurations()
                              
        elif section == "analysis":
            # Update analysis configuration
            logger.info("Starting analysis config update")
            try:
                # Get current analysis config
                current_config = config_loader.get_analysis_config()
                logger.info(f"Analysis config update - data keys: {list(data.keys())}")
                
                # Merge the new data with existing config
                updated_config = current_config.copy()
                
                if "performance" in data:
                    if "performance" not in updated_config:
                        updated_config["performance"] = {}
                    updated_config["performance"].update(data["performance"])
                
                if "essentia" in data:
                    if "essentia" not in updated_config:
                        updated_config["essentia"] = {}
                    updated_config["essentia"].update(data["essentia"])
                
                if "tensorflow" in data:
                    if "tensorflow" not in updated_config:
                        updated_config["tensorflow"] = {}
                    updated_config["tensorflow"].update(data["tensorflow"])
                
                # Save updated config
                config_loader.update_config("analysis_config", updated_config)
                
            except Exception as e:
                logger.error(f"Error in analysis config update: {e}")
                raise
            
            # Save to persistent storage using config manager
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("analysis", data)
            
            # Reload configurations to apply changes
            reload_configurations()
            
        elif section == "database":
            # Update database settings
            if "database_url" in data:
                os.environ["DATABASE_URL"] = data["database_url"]
            
            # Note: Database connection pool settings would require restart to take effect
            logger.info("Database settings updated - restart required for pool changes")
            
            # Save to persistent storage
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("database", data)
            
            # Reload configurations to apply changes
            reload_configurations()
        
        elif section == "external":
            # Update external APIs configuration
            if "external_apis" in data:
                # This would typically update a configuration file
                # For now, we'll log the changes
                logger.info(f"External APIs configuration updated: {data['external_apis']}")
                
                # In a real implementation, you would save this to a config file
                # or update environment variables as needed
            
            # Save to persistent storage
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("external", data)
            
            # Reload configurations to apply changes
            reload_configurations()
        
        elif section == "logging":
            # Update logging configuration
            if "log_level" in data:
                os.environ["LOG_LEVEL"] = data["log_level"]
                logger.info(f"Log level updated to: {data['log_level']}")
            
            if "log_file" in data:
                os.environ["LOG_FILE"] = data["log_file"]
                logger.info(f"Log file path updated to: {data['log_file']}")
            
            if "max_file_size" in data:
                os.environ["LOG_MAX_SIZE"] = str(data["max_file_size"])
                logger.info(f"Log max file size updated to: {data['max_file_size']}")
            
            if "max_backups" in data:
                os.environ["LOG_BACKUP_COUNT"] = str(data["max_backups"])
                logger.info(f"Log backup count updated to: {data['max_backups']}")
            
            # Save to persistent storage
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("logging", data)
            
            # Reload configurations to apply changes
            reload_configurations()
        
        elif section == "app_settings":
            # Update app settings
            # Save to persistent storage
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("app_settings", data)
            
            # Reload configurations to apply changes
            reload_configurations()
            
        elif section == "performance":
            # Update performance configuration

            
            # Update performance configuration
            current_config = config_loader.get_analysis_config()
            updated_config = current_config.copy()
            
            if "performance" in data:
                if "performance" not in updated_config:
                    updated_config["performance"] = {}
                updated_config["performance"].update(data["performance"])
            
            if "essentia" in data:
                if "essentia" not in updated_config:
                    updated_config["essentia"] = {}
                updated_config["essentia"].update(data["essentia"])
            
            # Save updated config
            config_loader.update_config("analysis_config", updated_config)
            logger.info("Performance configuration updated successfully")
            
            # Save to persistent storage
            from src.playlist_app.core.config_manager import config_manager
            config_manager.save_config("performance", data)
            
            # Reload configurations to apply changes
            reload_configurations()
        
        return {
            "status": "success",
            "message": f"{section.capitalize()} configuration updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to update configuration: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update configuration: {str(e)}"}
        )

@app.get("/config/backup")
async def backup_configs():
    """Create a backup of all configurations and return as downloadable file"""
    try:
        from src.playlist_app.core.config_manager import config_manager
        import zipfile
        import tempfile
        import shutil
        from fastapi.responses import FileResponse
        
        # Create backup directory in a persistent location
        backup_base_dir = Path("/app/temp_backups")
        backup_base_dir.mkdir(exist_ok=True)
        
        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_base_dir / f"config_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup
        success = config_manager.backup_configs(str(backup_dir))
        
        if not success:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to create configuration backup"}
            )
        
        # Create ZIP file
        zip_path = backup_base_dir / f"config_backup_{timestamp}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in backup_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(backup_dir)
                    zipf.write(file_path, arcname)
        
        # Clean up the backup directory (keep only the ZIP)
        shutil.rmtree(backup_dir)
        
        # Return the ZIP file as a download
        return FileResponse(
            path=str(zip_path),
            filename=f"config_backup_{timestamp}.zip",
            media_type="application/zip"
        )
        
    except Exception as e:
        logger.error(f"Failed to backup configurations: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to backup configurations: {str(e)}"}
        )

@app.post("/config/restore")
async def restore_configs(file: UploadFile = File()):
    """Restore configurations from uploaded backup file"""
    try:
        from src.playlist_app.core.config_manager import config_manager
        import zipfile
        
        # Check file type
        if not file.filename.endswith('.zip'):
            return JSONResponse(
                status_code=400,
                content={"error": "Only ZIP files are supported for restore"}
            )
        
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / "backup.zip"
            
            # Save uploaded file
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Extract ZIP file
            extract_dir = temp_path / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            # Find the config backup directory
            config_backup_dir = None
            
            # First, check if there's a config_backup subdirectory
            for item in extract_dir.iterdir():
                if item.is_dir() and item.name == "config_backup":
                    config_backup_dir = item
                    break
            
            # If no config_backup subdirectory, check if the extract_dir itself contains config files
            if not config_backup_dir:
                if any(extract_dir.glob("*.json")):
                    config_backup_dir = extract_dir
            
            if not config_backup_dir:
                return JSONResponse(
                    status_code=400,
                    content={"error": "No valid configuration backup found in ZIP file"}
                )
            
            # Restore configurations
            success = config_manager.restore_configs(str(config_backup_dir))
            
            if success:
                return {
                    "status": "success",
                    "message": "Configuration restored successfully"
                }
            else:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to restore configuration"}
                )
                
    except Exception as e:
        logger.error(f"Failed to restore configurations: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to restore configurations: {str(e)}"}
        )

@app.get("/config/list")
async def list_configs():
    """List all available configuration files"""
    try:
        from src.playlist_app.core.config_manager import config_manager
        configs = config_manager.list_configs()
        
        return {
            "status": "success",
            "configs": configs
        }
    except Exception as e:
        logger.error(f"Failed to list configurations: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to list configurations: {str(e)}"}
        )

@app.delete("/config/{section}")
async def delete_config(section: str):
    """Delete a configuration section"""
    try:
        from src.playlist_app.core.config_manager import config_manager
        success = config_manager.delete_config(section)
        
        if success:
            return {
                "status": "success",
                "message": f"Configuration {section} deleted successfully"
            }
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Configuration {section} not found"}
            )
    except Exception as e:
        logger.error(f"Failed to delete configuration {section}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to delete configuration: {str(e)}"}
        )

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
        from src.playlist_app.models.database import Base, engine
        
        logger.warning("Database reset requested - dropping all tables")
        Base.metadata.drop_all(bind=engine)
        
        logger.info("Recreating database tables")
        Base.metadata.create_all(bind=engine)
        
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

# Note: Static files are served by nginx in the web-ui container
# No static file mounting needed in the backend API

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

