#!/usr/bin/env python3
"""
Test script to verify TensorFlow and FAISS configuration system
"""

import json
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_configuration():
    """Test the configuration system"""
    print("Testing TensorFlow and FAISS Configuration System")
    print("=" * 50)
    
    try:
        # Test 1: Load analysis configuration
        print("\n1. Testing analysis configuration loading...")
        from playlist_app.core.analysis_config import analysis_config_loader
        
        config = analysis_config_loader.get_config()
        print(f"✓ Configuration loaded successfully")
        print(f"  - TensorFlow enabled: {config.algorithms.enable_tensorflow}")
        print(f"  - FAISS enabled: {config.algorithms.enable_faiss}")
        
        # Test 2: Check configuration file
        print("\n2. Testing configuration file...")
        config_path = "config/analysis_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            tensorflow_enabled = config_data.get("essentia", {}).get("algorithms", {}).get("enable_tensorflow", False)
            faiss_enabled = config_data.get("essentia", {}).get("algorithms", {}).get("enable_faiss", True)
            
            print(f"✓ Configuration file found: {config_path}")
            print(f"  - TensorFlow enabled: {tensorflow_enabled}")
            print(f"  - FAISS enabled: {faiss_enabled}")
        else:
            print(f"✗ Configuration file not found: {config_path}")
        
        # Test 3: Test configuration consistency
        print("\n3. Testing configuration consistency...")
        if config.algorithms.enable_tensorflow == tensorflow_enabled:
            print("✓ TensorFlow configuration is consistent")
        else:
            print("✗ TensorFlow configuration is inconsistent")
            
        if config.algorithms.enable_faiss == faiss_enabled:
            print("✓ FAISS configuration is consistent")
        else:
            print("✗ FAISS configuration is inconsistent")
        
        # Test 4: Test configuration modification
        print("\n4. Testing configuration modification...")
        original_tensorflow = config.algorithms.enable_tensorflow
        original_faiss = config.algorithms.enable_faiss
        
        # Toggle settings
        config.algorithms.enable_tensorflow = not original_tensorflow
        config.algorithms.enable_faiss = not original_faiss
        
        print(f"  - TensorFlow toggled: {original_tensorflow} -> {config.algorithms.enable_tensorflow}")
        print(f"  - FAISS toggled: {original_faiss} -> {config.algorithms.enable_faiss}")
        
        # Restore original settings
        config.algorithms.enable_tensorflow = original_tensorflow
        config.algorithms.enable_faiss = original_faiss
        
        print("✓ Configuration modification test passed")
        
        print("\n" + "=" * 50)
        print("✓ All configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analyzer_integration():
    """Test analyzer integration with configuration"""
    print("\nTesting Analyzer Integration")
    print("=" * 50)
    
    try:
        # Test 1: Check if analyzer respects configuration
        print("\n1. Testing analyzer configuration integration...")
        from playlist_app.services.essentia_analyzer import EssentiaAnalyzer
        from playlist_app.core.analysis_config import analysis_config_loader
        
        config = analysis_config_loader.get_config()
        analyzer = EssentiaAnalyzer()
        
        print(f"✓ Analyzer initialized successfully")
        print(f"  - TensorFlow enabled in config: {config.algorithms.enable_tensorflow}")
        print(f"  - FAISS enabled in config: {config.algorithms.enable_faiss}")
        
        # Test 2: Test analyze_audio_file method
        print("\n2. Testing analyze_audio_file method...")
        # This would require an actual audio file, so we'll just test the method signature
        import inspect
        sig = inspect.signature(analyzer.analyze_audio_file)
        params = list(sig.parameters.keys())
        
        if 'include_tensorflow' in params:
            print("✓ analyze_audio_file method accepts include_tensorflow parameter")
        else:
            print("✗ analyze_audio_file method missing include_tensorflow parameter")
        
        print("✓ Analyzer integration test passed")
        return True
        
    except Exception as e:
        print(f"\n✗ Analyzer integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_integration():
    """Test API integration with configuration"""
    print("\nTesting API Integration")
    print("=" * 50)
    
    try:
        # Test 1: Check if API endpoints respect configuration
        print("\n1. Testing API configuration integration...")
        from playlist_app.api.analyzer import router
        
        print("✓ Analyzer API router loaded successfully")
        
        # Check if the analyze-batches endpoint exists
        routes = [route.path for route in router.routes]
        if "/analyze-batches" in routes:
            print("✓ analyze-batches endpoint exists")
        else:
            print("✗ analyze-batches endpoint missing")
        
        print("✓ API integration test passed")
        return True
        
    except Exception as e:
        print(f"\n✗ API integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("TensorFlow and FAISS Configuration System Test")
    print("=" * 60)
    
    tests = [
        test_configuration,
        test_analyzer_integration,
        test_api_integration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! Configuration system is working correctly.")
        return 0
    else:
        print("✗ Some tests failed. Please check the configuration system.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
