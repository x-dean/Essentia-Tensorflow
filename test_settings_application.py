#!/usr/bin/env python3
"""
Test script to verify that settings changes are being applied to the running application.
"""

import requests
import json
import time

# API base URL
API_BASE = "http://localhost:8000/api"

def test_settings_application():
    """Test that settings changes are applied to the running application"""
    
    print("Testing settings application...")
    
    # 1. Get current configuration
    print("\n1. Getting current configuration...")
    try:
        response = requests.get(f"{API_BASE}/config/all")
        if response.status_code == 200:
            current_config = response.json()
            print(" Current configuration retrieved")
            
            # Show current discovery settings
            discovery_config = current_config.get("configs", {}).get("discovery", {})
            print(f"  Current supported extensions: {discovery_config.get('supported_extensions', [])}")
            print(f"  Current batch size: {discovery_config.get('batch_size', 'N/A')}")
        else:
            print(f" Failed to get current configuration: {response.status_code}")
            return False
    except Exception as e:
        print(f" Error getting current configuration: {e}")
        return False
    
    # 2. Update discovery settings
    print("\n2. Updating discovery settings...")
    new_settings = {
        "supported_extensions": [".mp3", ".wav", ".flac", ".test"],
        "batch_size": 500
    }
    
    try:
        response = requests.post(f"{API_BASE}/config/update", json={
            "section": "discovery",
            "data": new_settings
        })
        if response.status_code == 200:
            result = response.json()
            print(f" Settings updated: {result.get('message', 'Success')}")
        else:
            print(f" Failed to update settings: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f" Error updating settings: {e}")
        return False
    
    # 3. Wait a moment for changes to apply
    print("\n3. Waiting for changes to apply...")
    time.sleep(2)
    
    # 4. Get updated configuration
    print("\n4. Getting updated configuration...")
    try:
        response = requests.get(f"{API_BASE}/config/all")
        if response.status_code == 200:
            updated_config = response.json()
            print(" Updated configuration retrieved")
            
            # Show updated discovery settings
            discovery_config = updated_config.get("configs", {}).get("discovery", {})
            print(f"  Updated supported extensions: {discovery_config.get('supported_extensions', [])}")
            print(f"  Updated batch size: {discovery_config.get('batch_size', 'N/A')}")
            
            # Verify changes were applied
            if (discovery_config.get('supported_extensions') == new_settings['supported_extensions'] and
                discovery_config.get('batch_size') == new_settings['batch_size']):
                print(" Settings changes were successfully applied!")
                return True
            else:
                print(" Settings changes were not applied correctly")
                return False
        else:
            print(f" Failed to get updated configuration: {response.status_code}")
            return False
    except Exception as e:
        print(f" Error getting updated configuration: {e}")
        return False

def test_runtime_config():
    """Test that runtime configuration reflects the changes"""
    
    print("\n5. Testing runtime configuration...")
    
    try:
        response = requests.get(f"{API_BASE}/config")
        if response.status_code == 200:
            runtime_config = response.json()
            print(" Runtime configuration retrieved")
            
            # Show runtime discovery settings
            runtime_discovery = runtime_config.get("runtime", {})
            print(f"  Runtime supported extensions: {runtime_discovery.get('supported_extensions', [])}")
            print(f"  Runtime batch size: {runtime_discovery.get('batch_size', 'N/A')}")
            
            # Check if runtime config matches the updated settings
            expected_extensions = [".mp3", ".wav", ".flac", ".test"]
            expected_batch_size = 500
            
            if (runtime_discovery.get('supported_extensions') == expected_extensions and
                runtime_discovery.get('batch_size') == expected_batch_size):
                print(" Runtime configuration reflects the changes!")
                return True
            else:
                print(" Runtime configuration does not reflect the changes")
                return False
        else:
            print(f" Failed to get runtime configuration: {response.status_code}")
            return False
    except Exception as e:
        print(f" Error getting runtime configuration: {e}")
        return False

if __name__ == "__main__":
    print("Settings Application Test")
    print("=" * 50)
    
    # Test settings application
    if test_settings_application():
        print("\n Settings application test PASSED")
    else:
        print("\n Settings application test FAILED")
        exit(1)
    
    # Test runtime configuration
    if test_runtime_config():
        print("\n Runtime configuration test PASSED")
    else:
        print("\n Runtime configuration test FAILED")
        exit(1)
    
    print("\n" + "=" * 50)
    print(" ALL TESTS PASSED - Settings are being applied correctly!")
