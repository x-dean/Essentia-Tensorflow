import os
from typing import List
from .config_loader import config_loader

class DiscoveryConfig:
    """Configuration for discovery system"""
    
    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")
    
    # Search directories (comma-separated)
    SEARCH_DIRECTORIES = os.getenv("SEARCH_DIRECTORIES", "/music,/audio").split(",")
    SEARCH_DIRECTORIES = [dir.strip() for dir in SEARCH_DIRECTORIES if dir.strip()]
    
    # Discovery settings - now read from JSON config
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get supported file extensions from config"""
        try:
            # Try to get from JSON config first
            discovery_config = config_loader.get_discovery_config()
            if discovery_config and "supported_extensions" in discovery_config:
                return discovery_config["supported_extensions"]
            
            # Fallback to app settings
            app_settings = config_loader.get_app_settings()
            if app_settings and "discovery" in app_settings and "supported_extensions" in app_settings["discovery"]:
                return app_settings["discovery"]["supported_extensions"]
        except Exception:
            pass
        
        # Fallback to hardcoded values
        return [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"]
    
    @classmethod
    def get_cache_ttl(cls) -> int:
        """Get discovery cache TTL from config"""
        try:
            # Try to get from JSON config first
            app_settings = config_loader.get_app_settings()
            if app_settings and "discovery" in app_settings and "cache_ttl" in app_settings["discovery"]:
                return app_settings["discovery"]["cache_ttl"]
        except Exception:
            pass
        
        return int(os.getenv("DISCOVERY_CACHE_TTL", "3600"))
    
    @classmethod
    def get_batch_size(cls) -> int:
        """Get discovery batch size from config"""
        try:
            # Try to get from JSON config first
            discovery_config = config_loader.get_discovery_config()
            if discovery_config and "batch_size" in discovery_config:
                return discovery_config["batch_size"]
            
            # Fallback to app settings
            app_settings = config_loader.get_app_settings()
            if app_settings and "discovery" in app_settings and "batch_size" in app_settings["discovery"]:
                return app_settings["discovery"]["batch_size"]
        except Exception:
            pass
        
        return int(os.getenv("DISCOVERY_BATCH_SIZE", "100"))
    
    @classmethod
    def get_hash_algorithm(cls) -> str:
        """Get hash algorithm from config"""
        try:
            # Try to get from JSON config first
            app_settings = config_loader.get_app_settings()
            if app_settings and "discovery" in app_settings and "hash_algorithm" in app_settings["discovery"]:
                return app_settings["discovery"]["hash_algorithm"]
        except Exception:
            pass
        
        return "md5"
    
    # Logging
    @classmethod
    def get_log_level(cls) -> str:
        """Get log level from config"""
        try:
            logging_config = config_loader.get_logging_config()
            if logging_config and "log_level" in logging_config:
                return logging_config["log_level"]
        except Exception:
            pass
        
        return os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_search_directories(cls) -> List[str]:
        """Get list of search directories"""
        return cls.SEARCH_DIRECTORIES
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration"""
        # Check if at least one search directory exists
        existing_dirs = []
        for directory in cls.SEARCH_DIRECTORIES:
            if os.path.exists(directory):
                existing_dirs.append(directory)
        
        if not existing_dirs:
            print(f"Warning: No search directories exist: {cls.SEARCH_DIRECTORIES}")
            return False
        
        return True
