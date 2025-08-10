import os
from typing import List

class DiscoveryConfig:
    """Configuration for discovery system"""
    
    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./playlist_app.db")
    
    # Search directories (comma-separated)
    SEARCH_DIRECTORIES = os.getenv("SEARCH_DIRECTORIES", "/music,/audio").split(",")
    SEARCH_DIRECTORIES = [dir.strip() for dir in SEARCH_DIRECTORIES if dir.strip()]
    
    # Supported audio file extensions
    SUPPORTED_EXTENSIONS = [
        ".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"
    ]
    
    # Discovery settings
    DISCOVERY_CACHE_TTL = int(os.getenv("DISCOVERY_CACHE_TTL", "3600"))  # 1 hour
    DISCOVERY_BATCH_SIZE = int(os.getenv("DISCOVERY_BATCH_SIZE", "100"))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def get_search_directories(cls) -> List[str]:
        """Get list of search directories"""
        return cls.SEARCH_DIRECTORIES
    
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get list of supported file extensions"""
        return cls.SUPPORTED_EXTENSIONS
    
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
