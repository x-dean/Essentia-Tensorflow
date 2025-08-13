#!/usr/bin/env python3
"""
Test script to verify CLI commands work correctly
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add the parent directory to the path so we can import the CLI
sys.path.insert(0, str(Path(__file__).parent))

def test_api_endpoints():
    """Test that the API endpoints exist and are accessible"""
    base_url = "http://localhost:8000"
    
    # Test endpoints that should exist
    test_endpoints = [
        ("GET", "/health", "Health check"),
        ("GET", "/api", "API info"),
        ("GET", "/api/discovery/status", "Discovery status"),
        ("GET", "/api/analyzer/status", "Analyzer status"),
        ("GET", "/config/list", "Config list"),
    ]
    
    print("Testing API endpoints...")
    print("=" * 50)
    
    for method, endpoint, description in test_endpoints:
        try:
            url = f"{base_url}{endpoint}"
            response = requests.request(method, url, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ {description} ({method} {endpoint})")
            else:
                print(f"✗ {description} ({method} {endpoint}) - Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ {description} ({method} {endpoint}) - Error: {e}")
    
    print()

def test_cli_commands():
    """Test that CLI commands can be executed"""
    print("Testing CLI commands...")
    print("=" * 50)
    
    # Test basic CLI commands
    test_commands = [
        ["python", "scripts/master_cli.py", "health"],
        ["python", "scripts/master_cli.py", "status"],
        ["python", "scripts/master_cli.py", "discovery", "stats"],
        ["python", "scripts/master_cli.py", "analysis", "stats"],
        ["python", "scripts/master_cli.py", "config", "list"],
    ]
    
    for cmd in test_commands:
        try:
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✓ {' '.join(cmd)}")
            else:
                print(f"✗ {' '.join(cmd)} - Exit code: {result.returncode}")
                if result.stderr:
                    print(f"  Error: {result.stderr.strip()}")
                    
        except Exception as e:
            print(f"✗ {' '.join(cmd)} - Exception: {e}")
    
    print()

def main():
    """Main test function"""
    print("CLI Command Test Suite")
    print("=" * 50)
    print()
    
    # Check if the server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✓ Server is running on http://localhost:8000")
        else:
            print("✗ Server responded with error status")
            return
    except requests.exceptions.RequestException:
        print("✗ Server is not running on http://localhost:8000")
        print("Please start the server first with: docker-compose up")
        return
    
    print()
    
    # Run tests
    test_api_endpoints()
    test_cli_commands()
    
    print("Test completed!")

if __name__ == "__main__":
    main()
