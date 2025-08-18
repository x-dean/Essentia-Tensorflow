#!/usr/bin/env python3
"""
Test script to demonstrate streaming TensorFlow analysis
"""

import sys
import os
import json
import time
import psutil
from pathlib import Path
sys.path.insert(0, '/app/src')

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

try:
    from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig
    
    print("=== Streaming TensorFlow Analysis Test ===")
    
    # Create configuration with streaming enabled
    config = TensorFlowConfig()
    config.enable_streaming = True
    config.chunk_duration = 30.0
    config.overlap_ratio = 0.5
    config.max_chunks = 5
    config.memory_limit_mb = 512
    
    print(f"Streaming enabled: {config.enable_streaming}")
    print(f"Chunk duration: {config.chunk_duration}s")
    print(f"Overlap ratio: {config.overlap_ratio}")
    print(f"Max chunks: {config.max_chunks}")
    print(f"Memory limit: {config.memory_limit_mb}MB")
    
    # Create analyzer
    analyzer = TensorFlowAnalyzer(config)
    print("TensorFlow analyzer created successfully")
    
    # Test with a long audio file
    audio_file = "/music/Mark Ambor - Belong Together.mp3"
    print(f"\nTesting with: {audio_file}")
    
    # Get initial memory usage
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.1f}MB")
    
    # Run analysis
    start_time = time.time()
    result = analyzer.analyze_audio_file(audio_file)
    analysis_time = time.time() - start_time
    
    # Get final memory usage
    final_memory = get_memory_usage()
    memory_used = final_memory - initial_memory
    
    print(f"\n=== ANALYSIS RESULTS ===")
    print(f"Analysis time: {analysis_time:.2f}s")
    print(f"Memory used: {memory_used:.1f}MB")
    print(f"Final memory: {final_memory:.1f}MB")
    
    # Check metadata
    if 'metadata' in result:
        metadata = result['metadata']
        print(f"\nAnalysis strategy: {metadata.get('analysis_strategy', 'unknown')}")
        print(f"Audio duration: {metadata.get('audio_duration', 0):.1f}s")
        print(f"Models used: {metadata.get('models_used', [])}")
    
    # Check TensorFlow results
    if 'tensorflow_analysis' in result:
        tf_results = result['tensorflow_analysis']
        if 'musicnn' in tf_results:
            musicnn = tf_results['musicnn']
            if 'error' not in musicnn:
                print(f"\nMusicNN analysis successful!")
                if 'chunk_count' in musicnn:
                    print(f"Chunks processed: {musicnn['chunk_count']}")
                if 'aggregation_method' in musicnn:
                    print(f"Aggregation method: {musicnn['aggregation_method']}")
                
                if 'top_predictions' in musicnn:
                    print("\nTop MusicNN predictions:")
                    for i, pred in enumerate(musicnn['top_predictions'][:5], 1):
                        print(f"  {i}. {pred['tag']}: {pred['confidence']:.3f}")
            else:
                print(f"MusicNN error: {musicnn['error']}")
    
    # Check mood analysis
    if 'mood_analysis' in result:
        mood = result['mood_analysis']
        if 'error' not in mood:
            print(f"\nMood analysis successful!")
            print(f"Primary mood: {mood.get('primary_mood', 'N/A')}")
            print(f"Mood confidence: {mood.get('mood_confidence', 0):.3f}")
            
            if 'emotions' in mood:
                emotions = mood['emotions']
                print(f"Valence: {emotions.get('valence', 0):.3f}")
                print(f"Arousal: {emotions.get('arousal', 0):.3f}")
                print(f"Energy level: {emotions.get('energy_level', 0):.3f}")
        else:
            print(f"Mood analysis error: {mood['error']}")
    
    print(f"\n=== MEMORY EFFICIENCY ===")
    if memory_used < 100:
        print("✅ Excellent memory efficiency (< 100MB)")
    elif memory_used < 300:
        print("✅ Good memory efficiency (< 300MB)")
    elif memory_used < 500:
        print("⚠️  Moderate memory usage (< 500MB)")
    else:
        print("❌ High memory usage (> 500MB)")
    
    print(f"\nTest completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
