import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from .config import DiscoveryConfig

class ConfigLoader:
    """Configuration loader that reads JSON files from /app/config directory"""
    
    def __init__(self, config_dir: str = "/app/config"):
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        if config_name in self._config_cache:
            return self._config_cache[config_name]
            
        config_file = self.config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            return {}
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self._config_cache[config_name] = config
                return config
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config {config_name}: {e}")
            return {}
    
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get discovery configuration with fallback to environment variables"""
        config = self.load_config("discovery")
        
        # Fallback to environment variables if config file is empty
        if not config:
            config = {
                "search_directories": DiscoveryConfig.get_search_directories(),
                "supported_extensions": DiscoveryConfig.get_supported_extensions(),
                "cache_settings": {
                    "ttl": DiscoveryConfig.DISCOVERY_CACHE_TTL,
                    "max_size": 1000,
                    "enable_cache": True
                },
                "scan_settings": {
                    "batch_size": DiscoveryConfig.DISCOVERY_BATCH_SIZE,
                    "recursive": True,
                    "follow_symlinks": False,
                    "max_file_size": 1073741824
                },
                "hash_settings": {
                    "algorithm": "md5",
                    "include_filename": True,
                    "include_filesize": True,
                    "include_path": False
                }
            }
        
        return config
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration with environment variable override"""
        config = self.load_config("database")
        
        # Always prioritize DATABASE_URL environment variable over config file
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            if not config:
                config = {}
            if "connection" not in config:
                config["connection"] = {}
            config["connection"]["url"] = database_url
        
        # Fallback to environment variables if config file is empty
        if not config:
            config = {
                "connection": {
                    "url": os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db"),
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600
                },
                "tables": {
                    "files": {
                        "name": "files",
                        "create_indexes": True
                    },
                    "discovery_cache": {
                        "name": "discovery_cache",
                        "create_indexes": True
                    }
                },
                "migration": {
                    "auto_create_tables": True,
                    "backup_before_migration": True
                }
            }
        
        return config
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration with fallback to environment variables"""
        config = self.load_config("logging")
        
        # Fallback to environment variables if config file is empty
        if not config:
            config = {
                "level": os.getenv("LOG_LEVEL", "INFO"),
                "format": {
                    "console": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "file": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                },
                "handlers": {
                    "console": {
                        "enabled": True,
                        "level": "INFO"
                    },
                    "file": {
                        "enabled": True,
                        "level": "DEBUG",
                        "filename": "/app/logs/playlist_app.log",
                        "max_size": 10485760,
                        "backup_count": 5,
                        "encoding": "utf-8"
                    }
                },
                "loggers": {
                    "playlist_app": {
                        "level": "INFO",
                        "propagate": False
                    },
                    "playlist_app.discovery": {
                        "level": "DEBUG",
                        "propagate": False
                    },
                    "playlist_app.database": {
                        "level": "INFO",
                        "propagate": False
                    }
                }
            }
        
        return config
    
    def get_app_settings(self) -> Dict[str, Any]:
        """Get application settings with fallback to environment variables"""
        config = self.load_config("app_settings")
        
        # Fallback to environment variables if config file is empty
        if not config:
            config = {
                "api": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "workers": 1,
                    "reload": False,
                    "cors": {
                        "enabled": True,
                        "origins": ["*"],
                        "methods": ["GET", "POST", "PUT", "DELETE"],
                        "headers": ["*"]
                    }
                },
                "performance": {
                    "max_concurrent_requests": 100,
                    "request_timeout": 30,
                    "background_tasks": {
                        "enabled": True,
                        "max_workers": 4
                    }
                },
                "discovery": {
                    "background_enabled": os.getenv("ENABLE_BACKGROUND_DISCOVERY", "false").lower() == "true",
                    "interval": int(os.getenv("DISCOVERY_INTERVAL", "3600")),
                    "auto_scan_on_startup": True
                },
                "paths": {
                    "python_path": os.getenv("PYTHONPATH", "/app/src"),
                    "data_directory": "/app/data",
                    "cache_directory": "/app/cache",
                    "logs_directory": "/app/logs"
                }
            }
        
        return config
    
    def reload_config(self):
        """Reload all configuration files"""
        self._config_cache.clear()
    
    def list_available_configs(self) -> list:
        """List all available configuration files"""
        if not self.config_dir.exists():
            return []
        
        configs = []
        for config_file in self.config_dir.glob("*.json"):
            configs.append(config_file.stem)
        
        return configs

# Global config loader instance
config_loader = ConfigLoader()
