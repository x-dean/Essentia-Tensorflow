#!/usr/bin/env python3
"""
Test script to verify discovery configuration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_discovery_config():
    """Test discovery configuration loading and saving"""
    print("Testing discovery configuration...")
    
    # Import after path setup
    from src.playlist_app.core.config_manager import config_manager
    from src.playlist_app.core.config import DiscoveryConfig
    
    # Test current configuration
    print(f"Current DiscoveryConfig.SUPPORTED_EXTENSIONS: {DiscoveryConfig.SUPPORTED_EXTENSIONS}")
    
    # Test persistent configuration
    persistent_config = config_manager.load_config("discovery")
    print(f"Persistent discovery config: {persistent_config}")
    
    if persistent_config:
        print(f"Persistent supported_extensions: {persistent_config.get('supported_extensions', 'Not found')}")
    
    # Test saving new configuration
    test_config = {
        "supported_extensions": [".mp3", ".wav", ".flac", ".ogg", ".test"],
        "batch_size": 75
    }
    
    print(f"\nSaving test config: {test_config}")
    success = config_manager.save_config("discovery", test_config)
    print(f"Save result: {success}")
    
    # Test loading back
    loaded_config = config_manager.load_config("discovery")
    print(f"Loaded config: {loaded_config}")
    
    # Test DiscoveryConfig class variables
    print(f"\nDiscoveryConfig.SUPPORTED_EXTENSIONS after save: {DiscoveryConfig.SUPPORTED_EXTENSIONS}")
    
    # Update DiscoveryConfig class variables (simulate what happens in main.py)
    if loaded_config and "supported_extensions" in loaded_config:
        DiscoveryConfig.SUPPORTED_EXTENSIONS = loaded_config["supported_extensions"]
        print(f"DiscoveryConfig.SUPPORTED_EXTENSIONS after update: {DiscoveryConfig.SUPPORTED_EXTENSIONS}")
    
    # Clean up - restore original config
    original_config = {
        "supported_extensions": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"],
        "batch_size": 100
    }
    config_manager.save_config("discovery", original_config)
    print("\nRestored original configuration")

if __name__ == "__main__":
    test_discovery_config()
