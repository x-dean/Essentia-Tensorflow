#!/usr/bin/env python3
"""
Test script to verify configuration loading and saving
"""

import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_paths():
    """Debug which paths exist"""
    print("Debugging paths...")
    print(f"Current working directory: {os.getcwd()}")
    print(f"/app/config exists: {os.path.exists('/app/config')}")
    print(f"/app/config is absolute: {os.path.isabs('/app/config')}")
    print(f"config/ exists: {os.path.exists('config')}")
    print(f"config directory contents: {list(Path('config').glob('*')) if os.path.exists('config') else 'N/A'}")
    
    # Test path resolution
    test_path = Path("/app/config")
    print(f"Path('/app/config').is_absolute(): {test_path.is_absolute()}")
    print(f"Path('/app/config').resolve(): {test_path.resolve()}")

debug_paths()

from src.playlist_app.core.config_manager import config_manager

def test_config_loading():
    """Test configuration loading"""
    print("Testing configuration loading...")
    
    # Check config directory
    print(f"Config directory: {config_manager.config_dir}")
    print(f"Config directory exists: {config_manager.config_dir.exists()}")
    
    # List all files in config directory
    if config_manager.config_dir.exists():
        print("Files in config directory:")
        for file in config_manager.config_dir.glob("*"):
            print(f"  {file}")
    else:
        print("Config directory does not exist")
    
    # Check if external.json exists in current directory
    current_dir = Path(".")
    external_file = current_dir / "config" / "external.json"
    print(f"External file path: {external_file}")
    print(f"External file exists: {external_file.exists()}")
    
    # Get all configs
    configs = config_manager.get_all_configs()
    print(f"Loaded {len(configs)} configuration sections: {list(configs.keys())}")
    
    # Test external config specifically
    if 'external' in configs:
        external_config = configs['external']
        print(f"External config: {external_config}")
        
        # Check if external_apis exists
        if 'external_apis' in external_config:
            apis = external_config['external_apis']
            print(f"External APIs: {list(apis.keys())}")
            
            # Check each API
            for api_name, api_config in apis.items():
                print(f"  {api_name}: enabled={api_config.get('enabled', 'N/A')}")
        else:
            print("No external_apis found in external config")
    else:
        print("No external config found")
    
    return configs

def test_config_saving():
    """Test configuration saving"""
    print("\nTesting configuration saving...")
    
    # Test data
    test_data = {
        "external_apis": {
            "musicbrainz": {
                "enabled": True,
                "rateLimit": 1.2,
                "timeout": 15,
                "userAgent": "TestApp/1.0"
            },
            "lastfm": {
                "enabled": False,
                "apiKey": "test_key",
                "baseUrl": "https://test.example.com/",
                "rateLimit": 0.3,
                "timeout": 8
            }
        }
    }
    
    # Save test config
    success = config_manager.save_config("test_external", test_data)
    print(f"Save result: {success}")
    
    # Load it back
    loaded_config = config_manager.load_config("test_external")
    print(f"Loaded test config: {loaded_config}")
    
    # Clean up
    config_manager.delete_config("test_external")
    print("Test config cleaned up")

if __name__ == "__main__":
    test_config_loading()
    test_config_saving()
