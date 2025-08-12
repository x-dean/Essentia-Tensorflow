#!/usr/bin/env python3
"""
Test script to verify all configuration sections
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_all_configs():
    """Test all configuration sections"""
    print("Testing all configuration sections...")
    
    # Import after path setup
    from src.playlist_app.core.config_manager import config_manager
    from src.playlist_app.core.config_loader import config_loader
    
    # Test current configurations
    print(f"ConfigManager config directory: {config_manager.config_dir}")
    print(f"ConfigLoader config directory: {config_loader.config_dir}")
    
    # Get all configs from ConfigManager
    all_configs = config_manager.get_all_configs()
    print(f"\nAll configurations from ConfigManager: {list(all_configs.keys())}")
    
    # Test each configuration section
    test_sections = ['general', 'discovery', 'analysis', 'database', 'logging', 'external']
    
    for section in test_sections:
        print(f"\n--- Testing {section} configuration ---")
        
        # Test ConfigManager
        config_manager_config = config_manager.load_config(section)
        print(f"ConfigManager {section}: {config_manager_config}")
        
        # Test ConfigLoader (if it has a method for this section)
        if hasattr(config_loader, f'get_{section}_config'):
            config_loader_method = getattr(config_loader, f'get_{section}_config')
            config_loader_config = config_loader_method()
            print(f"ConfigLoader {section}: {config_loader_config}")
        
        # Test saving new configuration
        test_data = get_test_data_for_section(section)
        if test_data:
            print(f"Saving test data for {section}: {test_data}")
            success = config_manager.save_config(section, test_data)
            print(f"Save result for {section}: {success}")
            
            # Load it back
            loaded_config = config_manager.load_config(section)
            print(f"Loaded {section} config: {loaded_config}")

def get_test_data_for_section(section):
    """Get test data for each configuration section"""
    test_data = {
        'general': {
            'log_level': 'DEBUG',
            'background_discovery_enabled': True,
            'discovery_interval': 600,
            'cache_ttl': 7200,
            'api_host': '0.0.0.0'
        },
        'discovery': {
            'supported_extensions': ['.mp3', '.wav', '.flac', '.ogg', '.test'],
            'batch_size': 75,
            'search_directories': ['/test/music', '/test/audio']
        },
        'analysis': {
            'performance': {
                'parallel_processing': {
                    'max_workers': 8,
                    'chunk_size': 25,
                    'timeout_per_file': 600
                }
            },
            'essentia': {
                'algorithms': {
                    'enable_tensorflow': True,
                    'enable_complex_rhythm': False,
                    'enable_complex_harmonic': True
                }
            }
        },
        'database': {
            'pool_size': 25,
            'max_overflow': 35,
            'pool_timeout': 45,
            'pool_recycle': 7200
        },
        'logging': {
            'log_level': 'DEBUG',
            'max_file_size': 20480,
            'max_backups': 10,
            'compress': True
        },
        'external': {
            'external_apis': {
                'musicbrainz': {
                    'enabled': False,
                    'rateLimit': 0.5,
                    'timeout': 15,
                    'userAgent': 'TestApp/1.0'
                },
                'lastfm': {
                    'enabled': True,
                    'apiKey': 'test_key',
                    'baseUrl': 'https://test.example.com/',
                    'rateLimit': 0.3,
                    'timeout': 8
                },
                'discogs': {
                    'enabled': True,
                    'apiKey': 'test_discogs_key',
                    'baseUrl': 'https://test.discogs.com/',
                    'rateLimit': 0.8,
                    'timeout': 12,
                    'userAgent': 'TestApp/1.0'
                }
            }
        }
    }
    
    return test_data.get(section)

if __name__ == "__main__":
    test_all_configs()
