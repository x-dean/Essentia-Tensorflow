import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import zipfile
import tempfile
import shutil

logger = logging.getLogger(__name__)

class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.consolidated_config_file = self.config_dir / "config.json"
        self._config_cache = {}
        self._last_modified = {}
        
    def load_consolidated_config(self) -> Dict[str, Any]:
        """Load the consolidated config.json file"""
        if not self.consolidated_config_file.exists():
            return {}
            
        try:
            with open(self.consolidated_config_file, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Error loading consolidated config: {e}")
            return {}
    
    def save_consolidated_config(self, config: Dict[str, Any]) -> bool:
        """Save the consolidated config.json file"""
        try:
            # Add metadata
            config["_metadata"] = {
                "version": "2.0",
                "last_updated": datetime.now().isoformat(),
                "description": "Consolidated configuration file for Essentia-Tensorflow Playlist App"
            }
            
            with open(self.consolidated_config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Clear cache
            self._config_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Error saving consolidated config: {e}")
            return False
    
    def get_section_from_consolidated(self, section: str) -> Dict[str, Any]:
        """Get a specific section from the consolidated config"""
        config = self.load_consolidated_config()
        return config.get(section, {})
    
    def update_section_in_consolidated(self, section: str, data: Dict[str, Any]) -> bool:
        """Update a specific section in the consolidated config"""
        config = self.load_consolidated_config()
        config[section] = data
        return self.save_consolidated_config(config)
    
    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a section from consolidated config"""
        return self.get_section_from_consolidated(section)
    
    def update_config(self, section: str, data: Dict[str, Any]) -> bool:
        """Update configuration for a section in consolidated config"""
        return self.update_section_in_consolidated(section, data)
    
    def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load individual configuration file (legacy support)"""
        config_file = self.config_dir / f"{config_name}.json"
        
        if not config_file.exists():
            return {}
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Error loading config {config_name}: {e}")
            return {}
    
    def save_config(self, config_name: str, data: Dict[str, Any]) -> bool:
        """Save individual configuration file (legacy support)"""
        config_file = self.config_dir / f"{config_name}.json"
        
        try:
            # Add metadata
            data["_metadata"] = {
                "last_updated": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving config {config_name}: {e}")
            return False
    
    def get_app_settings(self) -> Dict[str, Any]:
        """Get application settings"""
        return self.get_config("app_settings")
    
    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration"""
        return self.get_config("analysis_config")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.get_config("database")
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration"""
        return self.get_config("logging")
    
    def get_discovery_config(self) -> Dict[str, Any]:
        """Get discovery configuration"""
        return self.get_config("discovery")
    
    def get_external_config(self) -> Dict[str, Any]:
        """Get external API configuration"""
        return self.get_config("external")
    
    def list_available_configs(self) -> List[str]:
        """List available configuration files"""
        configs = []
        
        # Check consolidated config
        if self.consolidated_config_file.exists():
            configs.append("config.json (consolidated)")
        
        # Check individual files
        for config_file in self.config_dir.glob("*.json"):
            if config_file.name != "config.json":
                configs.append(config_file.name)
        
        return configs
    
    def create_backup(self) -> Path:
        """Create backup of all configuration files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config_dir / "backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup consolidated config if it exists
        if self.consolidated_config_file.exists():
            shutil.copy2(self.consolidated_config_file, backup_dir / "config.json")
        
        # Backup individual config files
        for config_file in self.config_dir.glob("*.json"):
            if config_file.name != "config.json":
                shutil.copy2(config_file, backup_dir / config_file.name)
        
        # Create backup metadata
        backup_metadata = {
            "timestamp": timestamp,
            "backup_type": "manual",
            "files_backed_up": [f.name for f in backup_dir.glob("*.json")]
        }
        
        with open(backup_dir / "backup_metadata.json", 'w') as f:
            json.dump(backup_metadata, f, indent=2)
        
        return backup_dir
    
    def restore_backup(self, backup_file) -> bool:
        """Restore configuration from backup file"""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(backup_file, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Restore consolidated config if present
                consolidated_backup = Path(temp_dir) / "config.json"
                if consolidated_backup.exists():
                    shutil.copy2(consolidated_backup, self.consolidated_config_file)
                
                # Restore individual config files
                for config_file in Path(temp_dir).glob("*.json"):
                    if config_file.name not in ["config.json", "backup_metadata.json"]:
                        shutil.copy2(config_file, self.config_dir / config_file.name)
                
                return True
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    def reload_config(self) -> None:
        """Reload all configuration files"""
        self._config_cache.clear()
        self._last_modified.clear()
        logger.info("Configuration cache cleared")
    
    def delete_config(self, config_name: str) -> bool:
        """Delete a configuration file"""
        try:
            if config_name == "config.json":
                # Delete consolidated config
                if self.consolidated_config_file.exists():
                    self.consolidated_config_file.unlink()
                    return True
            else:
                # Delete individual config file
                config_file = self.config_dir / f"{config_name}.json"
                if config_file.exists():
                    config_file.unlink()
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error deleting config {config_name}: {e}")
            return False

# Global config loader instance
config_loader = ConfigLoader()
