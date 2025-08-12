import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .config_validator import config_validator
from .config_monitor import config_monitor

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Configuration loader that reads JSON files from config directory"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Use local config directory if running outside Docker
            import os
            # Prioritize local config directory if it exists
            if os.path.exists("config"):
                config_dir = "config"
            elif os.path.isabs("/app/config") and os.path.exists("/app/config"):
                config_dir = "/app/config"
            else:
                # Fallback to /app/config for Docker
                config_dir = "/app/config"
        
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load configuration from JSON file with monitoring and validation"""
        start_time = time.time()
        
        if config_name in self._config_cache:
            return self._config_cache[config_name]
            
        config_file = self.config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            load_time = time.time() - start_time
            config_monitor.record_config_load(config_name, {}, load_time, success=False, 
                                            errors=[f"Config file not found: {config_file}"])
            return {}
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            # Validate configuration
            is_valid, validation_errors = config_validator.validate_config(config_name, config)
            
            load_time = time.time() - start_time
            
            # Record metrics
            config_monitor.record_config_load(config_name, config, load_time, 
                                            success=is_valid, errors=validation_errors)
            
            if is_valid:
                self._config_cache[config_name] = config
                return config
            else:
                print(f"Warning: Config {config_name} validation failed: {validation_errors}")
                return config  # Return config even if validation fails for backward compatibility
                
        except (json.JSONDecodeError, IOError) as e:
            load_time = time.time() - start_time
            error_msg = f"Could not load config {config_name}: {e}"
            config_monitor.record_config_load(config_name, {}, load_time, 
                                            success=False, errors=[error_msg])
            print(f"Warning: {error_msg}")
            return {}
    
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get discovery configuration with fallback to environment variables"""
        config = self.load_config("discovery")
        
        # Fallback to environment variables if config file is empty
        if not config:
            search_dirs = os.getenv("SEARCH_DIRECTORIES", "/music,/audio").split(",")
            search_dirs = [dir.strip() for dir in search_dirs if dir.strip()]
            
            config = {
                "search_directories": search_dirs,
                "supported_extensions": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"],
                "cache_settings": {
                    "ttl": int(os.getenv("DISCOVERY_CACHE_TTL", "3600")),
                    "max_size": 1000,
                    "enable_cache": True
                },
                "scan_settings": {
                    "batch_size": int(os.getenv("DISCOVERY_BATCH_SIZE", "100")),
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
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration with fallback to environment variables"""
        config = self.load_config("analysis_config")
        
        # Fallback to environment variables if config file is empty
        if not config:
            config = {
                "performance": {
                    "tensorflow_optimizations": {
                        "enable_mixed_precision": True,
                        "enable_xla": True,
                        "enable_grappler": True,
                        "memory_growth": True,
                        "allow_growth": True
                    },
                    "essentia_optimizations": {
                        "enable_parallel_processing": True,
                        "max_workers": 4,
                        "chunk_size": 1024
                    }
                },
                "vector_analysis": {
                    "enable_embeddings": True,
                    "embedding_dimension": 128,
                    "similarity_threshold": 0.8,
                    "max_results": 100
                },
                "audio_processing": {
                    "sample_rate": 44100,
                    "chunk_duration": 30,
                    "overlap": 0.5
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

    def update_config(self, section: str, data: Dict[str, Any]) -> bool:
        """Update a configuration section"""
        try:
            config_file = self.config_dir / f"{section}.json"
            
            # Load existing config if it exists
            existing_config = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    existing_config = json.load(f)
            
            # Deep merge the data instead of shallow update
            def deep_merge(target, source):
                for key, value in source.items():
                    if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                        deep_merge(target[key], value)
                    else:
                        target[key] = value
                return target
            
            # Merge the new data with existing config
            merged_config = deep_merge(existing_config, data)
            
            # Save back to file
            with open(config_file, 'w') as f:
                json.dump(merged_config, f, indent=2)
            
            # Clear cache for this section
            if section in self._config_cache:
                del self._config_cache[section]
            
            return True
        except Exception as e:
            logger.error(f"Failed to update config {section}: {e}")
            return False

    def create_backup(self) -> Path:
        """Create a backup of all configuration files"""
        try:
            from datetime import datetime
            backup_dir = self.config_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            for config_file in self.config_dir.glob("*.json"):
                if config_file.name != "backup_metadata.json":
                    import shutil
                    shutil.copy2(config_file, backup_dir / config_file.name)
            
            # Create backup metadata
            metadata = {
                "backup_time": datetime.now().isoformat(),
                "files": [f.name for f in backup_dir.glob("*.json")]
            }
            with open(backup_dir / "backup_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return backup_dir
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise

    def restore_backup(self, backup_file) -> bool:
        """Restore configurations from backup file"""
        try:
            import zipfile
            import tempfile
            
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Restore each config file
                for config_file in Path(temp_dir).glob("*.json"):
                    if config_file.name != "backup_metadata.json":
                        target_file = self.config_dir / config_file.name
                        import shutil
                        shutil.copy2(config_file, target_file)
            
            # Reload configs
            self.reload_config()
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False

    def delete_config(self, section: str) -> bool:
        """Delete a configuration section"""
        try:
            config_file = self.config_dir / f"{section}.json"
            if config_file.exists():
                config_file.unlink()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete config {section}: {e}")
            return False

# Global config loader instance
config_loader = ConfigLoader()
