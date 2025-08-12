import os
from typing import List

class DiscoveryConfig:
    """Configuration for discovery system"""
    
    # Database configuration
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")
    
    # Search directories (comma-separated)
    SEARCH_DIRECTORIES = os.getenv("SEARCH_DIRECTORIES", "/music,/audio").split(",")
    SEARCH_DIRECTORIES = [dir.strip() for dir in SEARCH_DIRECTORIES if dir.strip()]
    
    # Discovery settings - fallback to environment variables
    @classmethod
    def get_supported_extensions(cls) -> List[str]:
        """Get supported file extensions from config"""
        # Fallback to hardcoded values
        return [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"]
    
    @classmethod
    def get_cache_ttl(cls) -> int:
        """Get discovery cache TTL from config"""
        return int(os.getenv("DISCOVERY_CACHE_TTL", "3600"))
    
    @classmethod
    def get_batch_size(cls) -> int:
        """Get discovery batch size from config"""
        return int(os.getenv("DISCOVERY_BATCH_SIZE", "100"))
    
    @classmethod
    def get_hash_algorithm(cls) -> str:
        """Get hash algorithm from config"""
        return "md5"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
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
