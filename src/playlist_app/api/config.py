import os
import json
import tempfile
import zipfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from ..core.config_loader import config_loader
from ..core.config_validator import config_validator
from ..core.config_monitor import config_monitor

router = APIRouter(prefix="/api/config", tags=["configuration"])

@router.get("/")
async def get_available_configs() -> Dict[str, Any]:
    """Get list of available configuration files"""
    try:
        configs = config_loader.list_available_configs()
        has_consolidated = config_loader.consolidated_config_file.exists()
        
        return {
            "status": "success",
            "available_configs": configs,
            "config_directory": str(config_loader.config_dir),
            "has_consolidated_config": has_consolidated,
            "consolidated_config_file": str(config_loader.consolidated_config_file)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing configs: {str(e)}")

@router.get("/consolidated")
async def get_consolidated_config() -> Dict[str, Any]:
    """Get the consolidated configuration file"""
    try:
        if not config_loader.consolidated_config_file.exists():
            raise HTTPException(status_code=404, detail="Consolidated config file not found")
        
        config = config_loader.load_consolidated_config()
        return {
            "status": "success",
            "config": config,
            "source": "consolidated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading consolidated config: {str(e)}")

@router.get("/discovery")
async def get_discovery_config() -> Dict[str, Any]:
    """Get discovery configuration"""
    try:
        config = config_loader.get_discovery_config()
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "file"
        
        return {
            "status": "success",
            "config": config,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading discovery config: {str(e)}")

@router.get("/database")
async def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    try:
        config = config_loader.get_database_config()
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "file"
        
        return {
            "status": "success",
            "config": config,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading database config: {str(e)}")

@router.get("/logging")
async def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration"""
    try:
        config = config_loader.get_logging_config()
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "file"
        
        return {
            "status": "success",
            "config": config,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading logging config: {str(e)}")

@router.get("/app")
async def get_app_settings() -> Dict[str, Any]:
    """Get application settings"""
    try:
        config = config_loader.get_app_settings()
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "file"
        
        return {
            "status": "success",
            "config": config,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading app settings: {str(e)}")

@router.get("/analysis")
async def get_analysis_config() -> Dict[str, Any]:
    """Get analysis configuration"""
    try:
        config = config_loader.get_analysis_config()
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "file"
        
        return {
            "status": "success",
            "config": config,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading analysis config: {str(e)}")

@router.get("/faiss")
async def get_faiss_config() -> Dict[str, Any]:
    """Get FAISS configuration"""
    try:
        config = config_loader.get_faiss_config()
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "file"
        
        return {
            "status": "success",
            "config": config,
            "source": source
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading FAISS config: {str(e)}")

@router.post("/analysis/update")
async def update_analysis_config(data: Dict[str, Any]) -> Dict[str, Any]:
    """Update analysis configuration"""
    try:
        from ..core.analysis_config import analysis_config_loader
        
        # Update the configuration
        config = analysis_config_loader.get_config()
        
        # Update algorithms section
        if "essentia" in data and "algorithms" in data["essentia"]:
            algorithms = data["essentia"]["algorithms"]
            for key, value in algorithms.items():
                if hasattr(config.algorithms, key):
                    setattr(config.algorithms, key, value)
        
        # Update audio processing section
        if "essentia" in data and "audio_processing" in data["essentia"]:
            audio_processing = data["essentia"]["audio_processing"]
            for key, value in audio_processing.items():
                if hasattr(config.audio_processing, key):
                    setattr(config.audio_processing, key, value)
        
        # Update performance section
        if "performance" in data and "parallel_processing" in data["performance"]:
            parallel_processing = data["performance"]["parallel_processing"]
            for key, value in parallel_processing.items():
                if hasattr(config.parallel_processing, key):
                    setattr(config.parallel_processing, key, value)
        
        # Update quality section
        if "quality" in data:
            quality = data["quality"]
            if "min_confidence_threshold" in quality:
                config.quality.min_confidence_threshold = quality["min_confidence_threshold"]
            if "fallback_values" in quality:
                for key, value in quality["fallback_values"].items():
                    if key in config.quality.fallback_values:
                        config.quality.fallback_values[key] = value
        
        # Save the updated configuration
        analysis_config_loader.save_config(config)
        
        return {
            "status": "success",
            "message": "Analysis configuration updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating analysis config: {str(e)}")

@router.post("/analysis/toggle-tensorflow")
async def toggle_tensorflow(data: Dict[str, bool]) -> Dict[str, Any]:
    """Toggle TensorFlow enable/disable"""
    try:
        from ..core.analysis_config import analysis_config_loader
        
        enabled = data.get("enabled", False)
        config = analysis_config_loader.get_config()
        config.algorithms.enable_tensorflow = enabled
        
        # Save the updated configuration
        analysis_config_loader.save_config(config)
        
        return {
            "status": "success",
            "message": f"TensorFlow {'enabled' if enabled else 'disabled'} successfully",
            "tensorflow_enabled": enabled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling TensorFlow: {str(e)}")

@router.post("/analysis/toggle-faiss")
async def toggle_faiss(data: Dict[str, bool]) -> Dict[str, Any]:
    """Toggle FAISS enable/disable"""
    try:
        from ..core.analysis_config import analysis_config_loader
        
        enabled = data.get("enabled", False)
        config = analysis_config_loader.get_config()
        config.algorithms.enable_faiss = enabled
        
        # Save the updated configuration
        analysis_config_loader.save_config(config)
        
        return {
            "status": "success",
            "message": f"FAISS {'enabled' if enabled else 'disabled'} successfully",
            "faiss_enabled": enabled
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error toggling FAISS: {str(e)}")

@router.get("/api-timeouts")
async def get_api_timeouts() -> Dict[str, Any]:
    """Get API timeout settings for frontend"""
    try:
        config = config_loader.get_app_settings()
        timeouts = config.get("api", {}).get("timeouts", {
            "default": 60,
            "analysis": 600,  # Increased from 300 to 600 seconds (10 minutes)
            "faiss": 300,
            "discovery": 120
        })
        return {
            "status": "success",
            "timeouts": timeouts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading API timeouts: {str(e)}")

@router.get("/all")
async def get_all_configs() -> Dict[str, Any]:
    """Get all configurations"""
    try:
        configs = {
            "discovery": config_loader.get_discovery_config(),
            "database": config_loader.get_database_config(),
            "logging": config_loader.get_logging_config(),
            "app_settings": config_loader.get_app_settings(),
            "analysis_config": config_loader.get_analysis_config(),
            "faiss": config_loader.get_faiss_config(),
            "external_apis": config_loader.get_external_config()
        }
        
        source = "consolidated" if config_loader.consolidated_config_file.exists() else "individual"
        
        return {
            "status": "success",
            "configs": configs,
            "source": source,
            "has_consolidated_config": config_loader.consolidated_config_file.exists()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading all configs: {str(e)}")

@router.post("/update")
async def update_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update configuration"""
    try:
        section = config_data.get("section")
        data = config_data.get("data")
        
        if not section or data is None:
            raise HTTPException(status_code=400, detail="Missing section or data")
        
        # Update the configuration
        success = config_loader.update_config(section, data)
        
        if success:
            # Reload configurations to apply changes
            config_loader.reload_config()
            
            source = "consolidated" if config_loader.consolidated_config_file.exists() else "individual"
            return {
                "status": "success",
                "message": f"Configuration {section} updated successfully",
                "source": source
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update configuration {section}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")

@router.post("/backup")
async def backup_configs():
    """Backup all configurations and return as downloadable ZIP file"""
    try:
        import zipfile
        import tempfile
        import shutil
        from fastapi.responses import FileResponse
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Create backup directory in a persistent location
        backup_base_dir = Path("/app/temp_backups")
        backup_base_dir.mkdir(exist_ok=True)
        logger.info(f"Created backup base directory: {backup_base_dir}")
        
        # Create timestamped backup directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = backup_base_dir / f"config_backup_{timestamp}"
        backup_dir.mkdir(exist_ok=True)
        logger.info(f"Created backup directory: {backup_dir}")
        
        # Create backup using config_loader
        backup_path = config_loader.create_backup()
        logger.info(f"Config loader backup created at: {backup_path}")
        
        # Create ZIP file directly from the backup path
        zip_path = backup_base_dir / f"config_backup_{timestamp}.zip"
        logger.info(f"Creating ZIP file at: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in backup_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(backup_path)
                    zipf.write(file_path, arcname)
                    logger.info(f"Added to ZIP: {arcname}")
        
        logger.info(f"ZIP file created successfully, size: {zip_path.stat().st_size} bytes")
        
        # Clean up the backup directory (keep only the ZIP)
        shutil.rmtree(backup_dir)
        logger.info("Cleaned up backup directory")
        
        # Return the ZIP file as a download
        return FileResponse(
            path=str(zip_path),
            filename=f"config_backup_{timestamp}.zip",
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=config_backup_{timestamp}.zip"}
        )
        
    except Exception as e:
        logger.error(f"Failed to backup configurations: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to backup configurations: {str(e)}"}
        )

@router.post("/restore")
async def restore_configs(file: UploadFile) -> Dict[str, Any]:
    """Restore configurations from backup ZIP file"""
    try:
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
                if item.is_dir() and item.name.startswith("config_backup"):
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
            
            # Restore configurations using config_manager
            from ..core.config_manager import config_manager
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
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to restore configurations: {str(e)}"}
        )

@router.get("/list")
async def list_configs() -> Dict[str, Any]:
    """List available configurations"""
    try:
        configs = config_loader.list_available_configs()
        return {
            "status": "success",
            "configs": configs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing configs: {str(e)}")

@router.delete("/{section}")
async def delete_config(section: str) -> Dict[str, Any]:
    """Delete a configuration section"""
    try:
        success = config_loader.delete_config(section)
        if success:
            return {
                "status": "success",
                "message": f"Configuration {section} deleted successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete configuration {section}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting config: {str(e)}")

@router.post("/reload")
async def reload_configs() -> Dict[str, Any]:
    """Reload all configuration files"""
    try:
        config_loader.reload_config()
        return {
            "status": "success",
            "message": "Configuration files reloaded successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reloading configs: {str(e)}")

@router.get("/validate")
async def validate_configs() -> Dict[str, Any]:
    """Validate all configuration files using schema validation"""
    try:
        # Get all configurations
        configs = {
            "app_settings": config_loader.get_app_settings(),
            "database": config_loader.get_database_config(),
            "logging": config_loader.get_logging_config(),
            "analysis_config": config_loader.get_analysis_config()
        }
        
        # Validate using schema validator
        validation_results = config_validator.validate_all_configs(configs)
        
        return {
            "status": "success",
            "validation_results": validation_results,
            "all_valid": all(result.get("valid", False) for result in validation_results.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating configs: {str(e)}")

@router.get("/monitor/health")
async def get_config_health() -> Dict[str, Any]:
    """Get configuration system health status"""
    try:
        health_status = config_monitor.get_health_status()
        return {
            "status": "success",
            "health": health_status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting health status: {str(e)}")

@router.get("/monitor/metrics")
async def get_config_metrics(config_name: Optional[str] = None) -> Dict[str, Any]:
    """Get configuration metrics"""
    try:
        metrics = config_monitor.get_metrics(config_name)
        return {
            "status": "success",
            "metrics": metrics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")

@router.get("/monitor/history")
async def get_config_history(config_name: Optional[str] = None, 
                           hours: Optional[int] = 24) -> Dict[str, Any]:
    """Get configuration change history"""
    try:
        from datetime import datetime, timedelta
        since = datetime.now() - timedelta(hours=hours) if hours else None
        history = config_monitor.get_change_history(config_name, since)
        return {
            "status": "success",
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")

@router.get("/schemas")
async def get_config_schemas() -> Dict[str, Any]:
    """Get available configuration schemas"""
    try:
        schemas = {}
        for schema_name in config_validator.list_schemas():
            schemas[schema_name] = config_validator.get_schema(schema_name)
        
        return {
            "status": "success",
            "schemas": schemas,
            "available_schemas": config_validator.list_schemas()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting schemas: {str(e)}")

@router.post("/monitor/reset")
async def reset_config_metrics(config_name: Optional[str] = None) -> Dict[str, Any]:
    """Reset configuration metrics"""
    try:
        config_monitor.reset_metrics(config_name)
        return {
            "status": "success",
            "message": f"Metrics reset for {config_name if config_name else 'all configs'}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resetting metrics: {str(e)}")

@router.post("/monitor/clear-history")
async def clear_config_history() -> Dict[str, Any]:
    """Clear configuration change history"""
    try:
        config_monitor.clear_history()
        return {
            "status": "success",
            "message": "Configuration change history cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing history: {str(e)}")
