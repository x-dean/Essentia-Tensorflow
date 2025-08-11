#!/usr/bin/env python3
"""
Test script for discovery and metadata functionality
"""

import requests
import json
import time

def test_discovery_and_metadata():
    """Test discovery and metadata functionality"""
    base_url = "http://localhost:8000"
    
    print("Testing Playlist App Discovery and Metadata...")
    print("=" * 50)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print("❌ Health check failed")
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return
    
    # Test 2: Discovery stats
    print("\n2. Testing discovery stats...")
    try:
        response = requests.get(f"{base_url}/api/discovery/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Discovery stats: {stats}")
        else:
            print(f"❌ Discovery stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Discovery stats error: {e}")
    
    # Test 3: Get files
    print("\n3. Testing file list...")
    try:
        response = requests.get(f"{base_url}/api/discovery/files?limit=3")
        if response.status_code == 200:
            files = response.json()
            print(f"✅ Found {len(files.get('files', []))} files")
            for file in files.get('files', [])[:2]:
                print(f"   - {file['file_name']} (ID: {file['id']})")
        else:
            print(f"❌ File list failed: {response.status_code}")
    except Exception as e:
        print(f"❌ File list error: {e}")
    
    # Test 4: Metadata stats
    print("\n4. Testing metadata stats...")
    try:
        response = requests.get(f"{base_url}/api/metadata/stats/overview")
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Metadata stats: {stats}")
        else:
            print(f"❌ Metadata stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Metadata stats error: {e}")
    
    # Test 5: Get metadata for first file
    print("\n5. Testing metadata retrieval...")
    try:
        # Get first file
        response = requests.get(f"{base_url}/api/discovery/files?limit=1")
        if response.status_code == 200:
            files = response.json()
            if files.get('files'):
                file_id = files['files'][0]['id']
                print(f"   Getting metadata for file ID: {file_id}")
                
                # Get metadata
                response = requests.get(f"{base_url}/api/metadata/{file_id}")
                if response.status_code == 200:
                    metadata = response.json()
                    title = metadata.get('metadata', {}).get('title', 'No title')
                    print(f"✅ Metadata retrieved: {title}")
                else:
                    print(f"❌ Metadata retrieval failed: {response.status_code}")
            else:
                print("❌ No files found for metadata retrieval")
        else:
            print(f"❌ File list failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Metadata retrieval error: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("Note: Metadata is automatically extracted during discovery.")
    print("Use POST /api/discovery/re-discover to re-discover all files if needed.")

if __name__ == "__main__":
    test_discovery_and_metadata()
