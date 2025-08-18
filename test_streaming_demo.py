#!/usr/bin/env python3
"""
Comprehensive Streaming TensorFlow Analysis Demo
"""

import sys
import os
import time
import json
sys.path.insert(0, '/app/src')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig

def test_streaming_analysis():
    print("=== Streaming TensorFlow Analysis Demo ===\n")
    
    # Create configuration with streaming enabled
    config = TensorFlowConfig()
    config.enable_streaming = True
    config.chunk_duration = 30.0
    config.overlap_ratio = 0.5
    config.max_chunks = 5
    config.memory_limit_mb = 512
    
    print("Configuration:")
    print(f"  Streaming enabled: {config.enable_streaming}")
    print(f"  Chunk duration: {config.chunk_duration}s")
    print(f"  Overlap ratio: {config.overlap_ratio}")
    print(f"  Max chunks: {config.max_chunks}")
    print(f"  Memory limit: {config.memory_limit_mb}MB\n")
    
    # Create analyzer
    analyzer = TensorFlowAnalyzer(config)
    print("TensorFlow analyzer created successfully\n")
    
    # Test files with different durations
    test_files = [
        ("Short track", "/music/Mark Ambor - Belong Together.mp3"),
        ("Long track", "/music/DJ Shu-ma - Deeper Love.flac")
    ]
    
    for test_name, audio_file in test_files:
        print(f"=== Testing {test_name} ===")
        print(f"File: {audio_file}")
        
        # Get duration first
        duration = analyzer._get_audio_duration(audio_file)
        print(f"Duration: {duration:.1f}s")
        
        # Run analysis
        start_time = time.time()
        result = analyzer.analyze_audio_file(audio_file)
        analysis_time = time.time() - start_time
        
        print(f"Analysis time: {analysis_time:.2f}s")
        
        # Check metadata
        if 'metadata' in result:
            metadata = result['metadata']
            print(f"Analysis strategy: {metadata.get('analysis_strategy', 'unknown')}")
            print(f"Audio duration: {metadata.get('audio_duration', 0):.1f}s")
            print(f"Models used: {metadata.get('models_used', [])}")
        
        # Check TensorFlow results
        if 'tensorflow_analysis' in result:
            tf_results = result['tensorflow_analysis']
            if 'musicnn' in tf_results:
                musicnn = tf_results['musicnn']
                if 'error' not in musicnn:
                    print("MusicNN analysis successful!")
                    
                    # Check for streaming-specific info
                    if 'chunk_count' in musicnn:
                        print(f"Chunks processed: {musicnn['chunk_count']}")
                    if 'aggregation_method' in musicnn:
                        print(f"Aggregation method: {musicnn['aggregation_method']}")
                    
                    # Show top predictions
                    if 'top_predictions' in musicnn:
                        print("Top MusicNN predictions:")
                        for i, pred in enumerate(musicnn['top_predictions'][:5], 1):
                            print(f"  {i}. {pred['tag']}: {pred['confidence']:.3f}")
                else:
                    print(f"MusicNN error: {musicnn['error']}")
        
        # Check mood analysis
        if 'mood_analysis' in result:
            mood = result['mood_analysis']
            if 'error' not in mood:
                print("Mood analysis successful!")
                print(f"Primary mood: {mood.get('primary_mood', 'N/A')}")
                print(f"Mood confidence: {mood.get('mood_confidence', 0):.3f}")
                
                if 'emotions' in mood:
                    emotions = mood['emotions']
                    print(f"Valence: {emotions.get('valence', 0):.3f}")
                    print(f"Arousal: {emotions.get('arousal', 0):.3f}")
                    print(f"Energy level: {emotions.get('energy_level', 0):.3f}")
            else:
                print(f"Mood analysis error: {mood['error']}")
        
        print("\n" + "="*50 + "\n")
    
    print("=== Streaming Analysis Demo Completed ===")
    print("\nKey Benefits:")
    print("✅ Memory efficient - processes audio in chunks")
    print("✅ Scalable - handles long tracks without memory issues")
    print("✅ Configurable - adjustable chunk size and overlap")
    print("✅ Intelligent - chooses strategy based on track length")
    print("✅ Accurate - aggregates results from multiple chunks")

if __name__ == "__main__":
    test_streaming_analysis()
