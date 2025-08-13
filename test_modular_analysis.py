#!/usr/bin/env python3
"""
Test script for the modular analysis system.
Tests Essentia, TensorFlow, and FAISS modules independently.
"""

import sys
import os
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_modular_analysis():
    """Test the modular analysis system"""
    print("Testing Modular Analysis System")
    print("=" * 50)
    
    try:
        # Import the modular analysis service
        from src.playlist_app.services.modular_analysis_service import modular_analysis_service
        
        # Test module status
        print("\n1. Testing Module Status:")
        module_status = modular_analysis_service.get_module_status()
        for module_name, status in module_status.items():
            print(f"  {module_name.upper()}:")
            print(f"    Enabled: {status['enabled']}")
            print(f"    Available: {status['available']}")
            print(f"    Description: {status['description']}")
        
        # Test Essentia analyzer
        print("\n2. Testing Essentia Analyzer:")
        try:
            from src.playlist_app.services.essentia_analyzer import essentia_analyzer
            print(f"  Essentia analyzer initialized: {essentia_analyzer is not None}")
            
            # Test with a sample audio file if available
            test_files = [
                "music/test1.mp3",
                "music/test2.wav", 
                "audio/test3.flac"
            ]
            
            for test_file in test_files:
                if os.path.exists(test_file):
                    print(f"  Testing with {test_file}...")
                    try:
                        results = essentia_analyzer.analyze_audio_file(test_file)
                        print(f"    Success! Extracted {len(results)} features")
                        if "essentia" in results:
                            essentia_data = results["essentia"]
                            print(f"    Features: {list(essentia_data.keys())}")
                    except Exception as e:
                        print(f"    Error: {e}")
                    break
            else:
                print("  No test audio files found")
                
        except Exception as e:
            print(f"  Essentia analyzer error: {e}")
        
        # Test TensorFlow analyzer
        print("\n3. Testing TensorFlow Analyzer:")
        try:
            from src.playlist_app.services.tensorflow_analyzer import tensorflow_analyzer
            print(f"  TensorFlow analyzer initialized: {tensorflow_analyzer is not None}")
            print(f"  TensorFlow available: {tensorflow_analyzer.is_available()}")
            
            if tensorflow_analyzer.is_available():
                print(f"  Loaded models: {list(tensorflow_analyzer.models.keys())}")
            else:
                print("  TensorFlow not available - check model files and dependencies")
                
        except Exception as e:
            print(f"  TensorFlow analyzer error: {e}")
        
        # Test FAISS service
        print("\n4. Testing FAISS Service:")
        try:
            from src.playlist_app.services.faiss_service import faiss_service
            print(f"  FAISS service initialized: {faiss_service is not None}")
            print(f"  FAISS index name: {faiss_service.index_name}")
            
        except Exception as e:
            print(f"  FAISS service error: {e}")
        
        # Test configuration loading
        print("\n5. Testing Configuration:")
        try:
            from src.playlist_app.core.analysis_config import analysis_config_loader
            config = analysis_config_loader.get_config()
            print(f"  Configuration loaded successfully")
            print(f"  Modules enabled:")
            print(f"    Essentia: {config.modules.enable_essentia}")
            print(f"    TensorFlow: {config.modules.enable_tensorflow}")
            print(f"    FAISS: {config.modules.enable_faiss}")
            
        except Exception as e:
            print(f"  Configuration error: {e}")
        
        print("\n" + "=" * 50)
        print("Modular Analysis System Test Complete!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_modular_analysis()
