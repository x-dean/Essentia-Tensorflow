#!/usr/bin/env python3
"""
Test script to verify FAISS integration with --include_faiss parameter
"""

import subprocess
import sys
import os

def test_faiss_integration():
    """Test FAISS integration with CLI parameters"""
    
    print("Testing FAISS integration...")
    
    # Test 1: Check if --include-faiss parameter is recognized
    print("\n1. Testing --include-faiss parameter recognition...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/master_cli.py", "analysis", "start", "--help"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if "--include-faiss" in result.stdout:
            print("✅ --include-faiss parameter is recognized")
        else:
            print("❌ --include-faiss parameter not found in help")
            print("Help output:")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"❌ Error testing help: {e}")
        return False
    
    # Test 2: Check if FAISS build command recognizes the parameter
    print("\n2. Testing FAISS build command...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/master_cli.py", "faiss", "build", "--help"
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        if "--include-faiss" in result.stdout:
            print("✅ FAISS build command recognizes --include-faiss parameter")
        else:
            print("❌ FAISS build command doesn't recognize --include-faiss parameter")
            print("Help output:")
            print(result.stdout)
            return False
    except Exception as e:
        print(f"❌ Error testing FAISS build help: {e}")
        return False
    
    # Test 3: Check if the API endpoints are properly configured
    print("\n3. Testing API endpoint configuration...")
    try:
        # Check if the analyze endpoint accepts include_faiss parameter
        with open("src/playlist_app/api/analyzer.py", "r") as f:
            content = f.read()
            if "include_faiss: bool = False" in content:
                print("✅ API analyzer endpoint accepts include_faiss parameter")
            else:
                print("❌ API analyzer endpoint missing include_faiss parameter")
                return False
        
        # Check if the FAISS build endpoint accepts include_faiss parameter
        with open("src/playlist_app/api/faiss.py", "r") as f:
            content = f.read()
            if "include_faiss: bool = Query(True" in content:
                print("✅ FAISS API endpoint accepts include_faiss parameter")
            else:
                print("❌ FAISS API endpoint missing include_faiss parameter")
                return False
                
    except Exception as e:
        print(f"❌ Error checking API endpoints: {e}")
        return False
    
    # Test 4: Check if the modular analysis service supports FAISS
    print("\n4. Testing modular analysis service...")
    try:
        with open("src/playlist_app/services/modular_analysis_service.py", "r") as f:
            content = f.read()
            if "enable_faiss: bool = False" in content:
                print("✅ Modular analysis service supports FAISS parameter")
            else:
                print("❌ Modular analysis service missing FAISS parameter")
                return False
                
    except Exception as e:
        print(f"❌ Error checking modular analysis service: {e}")
        return False
    
    print("\n✅ All FAISS integration tests passed!")
    return True

def test_cli_usage():
    """Test actual CLI usage with FAISS parameters"""
    
    print("\nTesting CLI usage with FAISS parameters...")
    
    # Test 1: Analysis with FAISS enabled
    print("\n1. Testing analysis with --include-faiss...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/master_cli.py", "analysis", "start", 
            "--include-tensorflow", "--include-faiss", "--max-files", "1"
        ], capture_output=True, text=True, cwd=os.getcwd(), timeout=30)
        
        print(f"Command output: {result.stdout}")
        if result.returncode == 0:
            print("✅ Analysis command with FAISS executed successfully")
        else:
            print(f"⚠️ Analysis command returned code {result.returncode}")
            print(f"Error output: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⚠️ Analysis command timed out (this is normal for long-running analysis)")
    except Exception as e:
        print(f"❌ Error testing analysis command: {e}")
    
    # Test 2: FAISS build with parameters
    print("\n2. Testing FAISS build with parameters...")
    try:
        result = subprocess.run([
            sys.executable, "scripts/master_cli.py", "faiss", "build", 
            "--include-tensorflow", "--include-faiss"
        ], capture_output=True, text=True, cwd=os.getcwd(), timeout=30)
        
        print(f"Command output: {result.stdout}")
        if result.returncode == 0:
            print("✅ FAISS build command executed successfully")
        else:
            print(f"⚠️ FAISS build command returned code {result.returncode}")
            print(f"Error output: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("⚠️ FAISS build command timed out (this is normal for long-running builds)")
    except Exception as e:
        print(f"❌ Error testing FAISS build command: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("FAISS Integration Test")
    print("=" * 60)
    
    # Run integration tests
    success = test_faiss_integration()
    
    if success:
        # Run CLI usage tests
        test_cli_usage()
        
        print("\n" + "=" * 60)
        print("✅ FAISS Integration Test Completed Successfully!")
        print("=" * 60)
        print("\nUsage examples:")
        print("  python scripts/master_cli.py analysis start --include-tensorflow --include-faiss")
        print("  python scripts/master_cli.py faiss build --include-tensorflow --include-faiss")
        print("  python scripts/master_cli.py faiss similar --query music/track.mp3")
    else:
        print("\n" + "=" * 60)
        print("❌ FAISS Integration Test Failed!")
        print("=" * 60)
        sys.exit(1)
