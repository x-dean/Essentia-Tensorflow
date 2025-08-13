#!/usr/bin/env python3
"""
Test script to verify the toggle endpoints are working
"""

import requests
import json
import time

def test_toggle_endpoints():
    """Test the toggle endpoints"""
    base_url = "http://localhost:8000"
    
    print("Testing Toggle Endpoints")
    print("=" * 40)
    
    try:
        # Test 1: Get current configuration
        print("\n1. Getting current configuration...")
        response = requests.get(f"{base_url}/api/config/analysis")
        if response.status_code == 200:
            config = response.json()
            tensorflow_enabled = config.get("config", {}).get("essentia", {}).get("algorithms", {}).get("enable_tensorflow", False)
            faiss_enabled = config.get("config", {}).get("essentia", {}).get("algorithms", {}).get("enable_faiss", True)
            print(f"✓ Current config - TensorFlow: {tensorflow_enabled}, FAISS: {faiss_enabled}")
        else:
            print(f"✗ Failed to get config: {response.status_code}")
            return
        
        # Test 2: Toggle TensorFlow
        print("\n2. Testing TensorFlow toggle...")
        new_tensorflow_state = not tensorflow_enabled
        response = requests.post(f"{base_url}/api/config/analysis/toggle-tensorflow", 
                               json={"enabled": new_tensorflow_state})
        if response.status_code == 200:
            result = response.json()
            print(f"✓ TensorFlow toggle successful: {result.get('message', 'No message')}")
        else:
            print(f"✗ TensorFlow toggle failed: {response.status_code} - {response.text}")
            return
        
        # Wait a moment
        time.sleep(1)
        
        # Test 3: Verify TensorFlow change
        print("\n3. Verifying TensorFlow change...")
        response = requests.get(f"{base_url}/api/config/analysis")
        if response.status_code == 200:
            config = response.json()
            new_tensorflow_enabled = config.get("config", {}).get("essentia", {}).get("algorithms", {}).get("enable_tensorflow", False)
            print(f"✓ TensorFlow state: {new_tensorflow_enabled} (expected: {new_tensorflow_state})")
            if new_tensorflow_enabled == new_tensorflow_state:
                print("✓ TensorFlow toggle verified successfully!")
            else:
                print("✗ TensorFlow toggle verification failed!")
        else:
            print(f"✗ Failed to verify config: {response.status_code}")
        
        # Test 4: Toggle FAISS
        print("\n4. Testing FAISS toggle...")
        new_faiss_state = not faiss_enabled
        response = requests.post(f"{base_url}/api/config/analysis/toggle-faiss", 
                               json={"enabled": new_faiss_state})
        if response.status_code == 200:
            result = response.json()
            print(f"✓ FAISS toggle successful: {result.get('message', 'No message')}")
        else:
            print(f"✗ FAISS toggle failed: {response.status_code} - {response.text}")
            return
        
        # Wait a moment
        time.sleep(1)
        
        # Test 5: Verify FAISS change
        print("\n5. Verifying FAISS change...")
        response = requests.get(f"{base_url}/api/config/analysis")
        if response.status_code == 200:
            config = response.json()
            new_faiss_enabled = config.get("config", {}).get("essentia", {}).get("algorithms", {}).get("enable_faiss", True)
            print(f"✓ FAISS state: {new_faiss_enabled} (expected: {new_faiss_state})")
            if new_faiss_enabled == new_faiss_state:
                print("✓ FAISS toggle verified successfully!")
            else:
                print("✗ FAISS toggle verification failed!")
        else:
            print(f"✗ Failed to verify config: {response.status_code}")
        
        # Test 6: Check if file was actually updated
        print("\n6. Checking if configuration file was updated...")
        try:
            with open("config/analysis_config.json", "r") as f:
                file_config = json.load(f)
            file_tensorflow = file_config.get("essentia", {}).get("algorithms", {}).get("enable_tensorflow", False)
            file_faiss = file_config.get("essentia", {}).get("algorithms", {}).get("enable_faiss", True)
            print(f"✓ File config - TensorFlow: {file_tensorflow}, FAISS: {file_faiss}")
            
            if file_tensorflow == new_tensorflow_state and file_faiss == new_faiss_state:
                print("✓ Configuration file updated successfully!")
            else:
                print("✗ Configuration file not updated correctly!")
        except Exception as e:
            print(f"✗ Failed to read configuration file: {e}")
        
        print("\n" + "=" * 40)
        print("Toggle endpoint test completed!")
        
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"✗ Test failed with error: {e}")

if __name__ == "__main__":
    test_toggle_endpoints()
