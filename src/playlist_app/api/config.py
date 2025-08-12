from fastapi import APIRouter, HTTPException, UploadFile
from typing import Dict, Any, List, Optional
import json
from pathlib import Path

from ..core.config_loader import config_loader
from ..core.config_validator import config_validator
from ..core.config_monitor import config_monitor

router = APIRouter(prefix="/api/config", tags=["configuration"])

@router.get("/")
async def get_available_configs() -> Dict[str, Any]:
    """Get list of available configuration files"""
    try:
        configs = config_loader.list_available_configs()
        return {
            "status": "success",
            "available_configs": configs,
            "config_directory": str(config_loader.config_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing configs: {str(e)}")

@router.get("/discovery")
async def get_discovery_config() -> Dict[str, Any]:
    """Get discovery configuration"""
    try:
        config = config_loader.get_discovery_config()
        return {
            "status": "success",
            "config": config,
            "source": "file" if config_loader.load_config("discovery") else "environment"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading discovery config: {str(e)}")

@router.get("/database")
async def get_database_config() -> Dict[str, Any]:
    """Get database configuration"""
    try:
        config = config_loader.get_database_config()
        return {
            "status": "success",
            "config": config,
            "source": "file" if config_loader.load_config("database") else "environment"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading database config: {str(e)}")

@router.get("/logging")
async def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration"""
    try:
        config = config_loader.get_logging_config()
        return {
            "status": "success",
            "config": config,
            "source": "file" if config_loader.load_config("logging") else "environment"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading logging config: {str(e)}")

@router.get("/app")
async def get_app_settings() -> Dict[str, Any]:
    """Get application settings"""
    try:
        config = config_loader.get_app_settings()
        return {
            "status": "success",
            "config": config,
            "source": "file" if config_loader.load_config("app_settings") else "environment"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading app settings: {str(e)}")

@router.get("/api-timeouts")
async def get_api_timeouts() -> Dict[str, Any]:
    """Get API timeout settings for frontend"""
    try:
        config = config_loader.get_app_settings()
        timeouts = config.get("api", {}).get("timeouts", {
            "default": 60,
            "analysis": 300,
            "faiss": 300,
            "discovery": 120
        })
        return {
            "status": "success",
            "timeouts": timeouts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading API timeouts: {str(e)}")

@router.get("/analysis")
async def get_analysis_config() -> Dict[str, Any]:
    """Get analysis configuration"""
    try:
        config = config_loader.get_analysis_config()
        return {
            "status": "success",
            "config": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading analysis config: {str(e)}")

@router.get("/all")
async def get_all_configs() -> Dict[str, Any]:
    """Get all configurations"""
    try:
        return {
            "status": "success",
            "configs": {
                "discovery": config_loader.get_discovery_config(),
                "database": config_loader.get_database_config(),
                "logging": config_loader.get_logging_config(),
                "app_settings": config_loader.get_app_settings()
            },
            "sources": {
                "discovery": "file" if config_loader.load_config("discovery") else "environment",
                "database": "file" if config_loader.load_config("database") else "environment",
                "logging": "file" if config_loader.load_config("logging") else "environment",
                "app_settings": "file" if config_loader.load_config("app_settings") else "environment"
            }
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
            return {
                "status": "success",
                "message": f"Configuration {section} updated successfully"
            }
        else:
            raise HTTPException(status_code=500, detail=f"Failed to update configuration {section}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating config: {str(e)}")

@router.post("/backup")
async def backup_configs() -> Dict[str, Any]:
    """Backup all configurations"""
    try:
        backup_path = config_loader.create_backup()
        return {
            "status": "success",
            "message": "Configuration backup created successfully",
            "backup_path": str(backup_path)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating backup: {str(e)}")

@router.post("/restore")
async def restore_configs(file: UploadFile) -> Dict[str, Any]:
    """Restore configurations from backup"""
    try:
        success = config_loader.restore_backup(file.file)
        if success:
            return {
                "status": "success",
                "message": "Configuration restored successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to restore configuration")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error restoring config: {str(e)}")

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
