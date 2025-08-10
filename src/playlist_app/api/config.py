from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import json
from pathlib import Path

from ..core.config_loader import config_loader

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
    """Validate all configuration files"""
    try:
        validation_results = {}
        
        # Validate discovery config
        discovery_config = config_loader.get_discovery_config()
        validation_results["discovery"] = {
            "valid": True,
            "search_directories": len(discovery_config.get("search_directories", [])),
            "supported_extensions": len(discovery_config.get("supported_extensions", [])),
            "cache_enabled": discovery_config.get("cache_settings", {}).get("enable_cache", True)
        }
        
        # Validate database config
        db_config = config_loader.get_database_config()
        validation_results["database"] = {
            "valid": True,
            "connection_url": "configured" if db_config.get("connection", {}).get("url") else "missing",
            "pool_size": db_config.get("connection", {}).get("pool_size", 10)
        }
        
        # Validate logging config
        logging_config = config_loader.get_logging_config()
        validation_results["logging"] = {
            "valid": True,
            "level": logging_config.get("level", "INFO"),
            "file_enabled": logging_config.get("handlers", {}).get("file", {}).get("enabled", True),
            "console_enabled": logging_config.get("handlers", {}).get("console", {}).get("enabled", True)
        }
        
        # Validate app settings
        app_config = config_loader.get_app_settings()
        validation_results["app_settings"] = {
            "valid": True,
            "api_port": app_config.get("api", {}).get("port", 8000),
            "background_discovery": app_config.get("discovery", {}).get("background_enabled", False)
        }
        
        return {
            "status": "success",
            "validation_results": validation_results,
            "all_valid": all(result["valid"] for result in validation_results.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating configs: {str(e)}")
