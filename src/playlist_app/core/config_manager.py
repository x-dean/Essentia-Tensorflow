"""
Configuration Manager

This module provides persistent configuration storage and management
for the playlist application.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages persistent configuration storage"""
    
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
        self.config_dir.mkdir(exist_ok=True)
    
    def save_config(self, section: str, data: Dict[str, Any]) -> bool:
        """Save configuration section to file"""
        try:
            config_file = self.config_dir / f"{section}.json"
            
            # Add metadata
            config_data = {
                **data,
                "_metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Configuration saved to {config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration {section}: {e}")
            return False
    
    def load_config(self, section: str) -> Optional[Dict[str, Any]]:
        """Load configuration section from file"""
        try:
            config_file = self.config_dir / f"{section}.json"
            
            if not config_file.exists():
                return None
            
            with open(config_file, 'r') as f:
                data = json.load(f)
            
            # Remove metadata for return
            if "_metadata" in data:
                del data["_metadata"]
            
            return data
        except Exception as e:
            logger.error(f"Could not load config {section}: {e}")
            return None
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all configuration sections"""
        configs = {}
        
        for config_file in self.config_dir.glob("*.json"):
            section = config_file.stem
            config_data = self.load_config(section)
            if config_data is not None:
                configs[section] = config_data
        
        return configs
    
    def delete_config(self, section: str) -> bool:
        """Delete a configuration section"""
        try:
            config_file = self.config_dir / f"{section}.json"
            
            if config_file.exists():
                config_file.unlink()
                logger.info(f"Configuration {section} deleted")
                return True
            else:
                logger.warning(f"Configuration {section} not found")
                return False
        except Exception as e:
            logger.error(f"Failed to delete configuration {section}: {e}")
            return False
    
    def backup_configs(self, backup_dir: str) -> bool:
        """Create a backup of all configurations"""
        try:
            backup_path = Path(backup_dir)
            backup_path.mkdir(exist_ok=True)
            
            # Copy all config files
            for config_file in self.config_dir.glob("*.json"):
                shutil.copy2(config_file, backup_path / config_file.name)
            
            logger.info(f"Configuration backup created at {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to create configuration backup: {e}")
            return False
    
    def restore_configs(self, backup_dir: str) -> bool:
        """Restore configurations from backup"""
        try:
            backup_path = Path(backup_dir)
            
            if not backup_path.exists():
                logger.error(f"Backup directory {backup_dir} does not exist")
                return False
            
            # Copy all config files from backup
            for config_file in backup_path.glob("*.json"):
                shutil.copy2(config_file, self.config_dir / config_file.name)
            
            logger.info(f"Configuration restored from {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore configuration: {e}")
            return False
    
    def list_configs(self) -> Dict[str, Any]:
        """List all available configurations with metadata"""
        configs = {}
        
        for config_file in self.config_dir.glob("*.json"):
            section = config_file.stem
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                metadata = data.get("_metadata", {})
                configs[section] = {
                    "file": str(config_file),
                    "size": config_file.stat().st_size,
                    "last_updated": metadata.get("last_updated"),
                    "version": metadata.get("version")
                }
            except Exception as e:
                logger.error(f"Failed to read config {section}: {e}")
        
        return configs

# Global instance
config_manager = ConfigManager()
