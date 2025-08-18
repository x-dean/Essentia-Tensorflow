#!/usr/bin/env python3
"""
Test Runner for TensorFlow Integration

This script demonstrates and tests the enhanced TensorFlow integration:
- TensorFlow analyzer functionality
- MusicNN model integration
- Mood analysis capabilities
- CLI commands
- Demo functionality
"""

import sys
import os
import subprocess
from pathlib import Path

def run_unit_tests():
    """Run unit tests for TensorFlow integration"""
    print("=== Running Unit Tests ===")
    
    test_file = Path(__file__).parent.parent / "tests" / "test_tensorflow_integration.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    try:
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def test_tensorflow_availability():
    """Test TensorFlow availability"""
    print("\n=== Testing TensorFlow Availability ===")
    
    try:
        import tensorflow as tf
        print(f"✅ TensorFlow {tf.__version__} is available")
        
        # Test if we can import our analyzer
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from playlist_app.services.tensorflow_analyzer import tensorflow_analyzer
        
        if tensorflow_analyzer.is_available():
            print("✅ TensorFlow analyzer is available")
            return True
        else:
            print("⚠️  TensorFlow analyzer is not available (models may be missing)")
            return False
            
    except ImportError:
        print("❌ TensorFlow is not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking TensorFlow: {e}")
        return False

def test_model_files():
    """Test if required model files exist"""
    print("\n=== Testing Model Files ===")
    
    models_dir = Path(__file__).parent.parent / "models"
    required_files = ["msd-musicnn-1.pb", "msd-musicnn-1.json"]
    
    all_exist = True
    for file_name in required_files:
        file_path = models_dir / file_name
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"✅ {file_name} exists ({size:,} bytes)")
        else:
            print(f"❌ {file_name} missing")
            all_exist = False
    
    return all_exist

def test_cli_commands():
    """Test CLI commands"""
    print("\n=== Testing CLI Commands ===")
    
    cli_script = Path(__file__).parent / "master_cli.py"
    
    if not cli_script.exists():
        print(f"❌ CLI script not found: {cli_script}")
        return False
    
    # Test help command
    try:
        result = subprocess.run([
            sys.executable, str(cli_script), "tensorflow", "--help"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if "analyze" in result.stdout:
            print("✅ TensorFlow CLI command is available")
            return True
        else:
            print("❌ TensorFlow CLI command not found")
            return False
            
    except Exception as e:
        print(f"❌ Error testing CLI: {e}")
        return False

def test_demo_script():
    """Test demo script"""
    print("\n=== Testing Demo Script ===")
    
    demo_script = Path(__file__).parent.parent / "examples" / "tensorflow_mood_demo.py"
    
    if not demo_script.exists():
        print(f"❌ Demo script not found: {demo_script}")
        return False
    
    # Test help
    try:
        result = subprocess.run([
            sys.executable, str(demo_script), "--help"
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        if "Usage:" in result.stdout:
            print("✅ Demo script is available")
            return True
        else:
            print("❌ Demo script not working properly")
            return False
            
    except Exception as e:
        print(f"❌ Error testing demo script: {e}")
        return False

def test_audio_file_analysis():
    """Test actual audio file analysis if test files exist"""
    print("\n=== Testing Audio File Analysis ===")
    
    # Look for test audio files
    test_dirs = ["music", "audio", "test_audio"]
    test_files = []
    
    for test_dir in test_dirs:
        test_path = Path(__file__).parent.parent / test_dir
        if test_path.exists():
            for ext in ["*.mp3", "*.wav", "*.flac", "*.m4a"]:
                test_files.extend(test_path.glob(ext))
    
    if not test_files:
        print("⚠️  No test audio files found")
        return True
    
    # Use the first available test file
    test_file = test_files[0]
    print(f"Found test file: {test_file}")
    
    # Test TensorFlow analyzer directly
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from playlist_app.services.tensorflow_analyzer import tensorflow_analyzer
        
        if not tensorflow_analyzer.is_available():
            print("⚠️  TensorFlow analyzer not available, skipping audio test")
            return True
        
        print(f"Analyzing {test_file.name}...")
        results = tensorflow_analyzer.analyze_audio_file(str(test_file))
        
        if "tensorflow_analysis" in results:
            print("✅ TensorFlow analysis completed successfully")
            
            # Show some results
            if "musicnn" in results["tensorflow_analysis"]:
                musicnn = results["tensorflow_analysis"]["musicnn"]
                if "top_predictions" in musicnn:
                    print("Top predictions:")
                    for pred in musicnn["top_predictions"][:3]:
                        print(f"  {pred['tag']}: {pred['confidence']:.3f}")
            
            if "mood_analysis" in results:
                mood = results["mood_analysis"]
                if "primary_mood" in mood:
                    print(f"Primary mood: {mood['primary_mood']} (confidence: {mood.get('mood_confidence', 0):.3f})")
            
            return True
        else:
            print("❌ TensorFlow analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during audio analysis: {e}")
        return False

def run_integration_test():
    """Run integration test with CLI"""
    print("\n=== Running Integration Test ===")
    
    # Look for test audio files
    test_dirs = ["music", "audio", "test_audio"]
    test_files = []
    
    for test_dir in test_dirs:
        test_path = Path(__file__).parent.parent / test_dir
        if test_path.exists():
            for ext in ["*.mp3", "*.wav", "*.flac", "*.m4a"]:
                test_files.extend(test_path.glob(ext))
    
    if not test_files:
        print("⚠️  No test audio files found for integration test")
        return True
    
    test_file = test_files[0]
    cli_script = Path(__file__).parent / "master_cli.py"
    
    try:
        print(f"Running CLI analysis on {test_file.name}...")
        result = subprocess.run([
            sys.executable, str(cli_script), "tensorflow", "analyze", 
            "--files", str(test_file)
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print("✅ CLI integration test passed")
            return True
        else:
            print("❌ CLI integration test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error during integration test: {e}")
        return False

def main():
    """Main test runner"""
    print("🧪 TensorFlow Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Unit Tests", run_unit_tests),
        ("TensorFlow Availability", test_tensorflow_availability),
        ("Model Files", test_model_files),
        ("CLI Commands", test_cli_commands),
        ("Demo Script", test_demo_script),
        ("Audio File Analysis", test_audio_file_analysis),
        ("Integration Test", run_integration_test)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! TensorFlow integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
