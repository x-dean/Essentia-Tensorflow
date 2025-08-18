#!/usr/bin/env python3
"""
Test Memory Usage - Monitor memory consumption during TensorFlow analysis
"""

import sys
import os
import time
import psutil
import gc
sys.path.insert(0, '/app/src')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig

def get_memory_usage():
    """Get current memory usage in MB"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def test_memory_usage():
    print("=== Memory Usage Test ===\n")
    
    # Initial memory
    initial_memory = get_memory_usage()
    print(f"Initial memory: {initial_memory:.1f} MB")
    
    # Create configuration with aggressive memory limits
    config = TensorFlowConfig()
    config.enable_streaming = True
    config.chunk_duration = 15.0  # Smaller chunks
    config.overlap_ratio = 0.3    # Less overlap
    config.max_chunks = 3         # Limit chunks
    config.memory_limit_mb = 256  # Aggressive limit
    config.enable_mood_analysis = True
    config.mood_confidence_threshold = 0.1
    
    print(f"Configuration:")
    print(f"  Chunk duration: {config.chunk_duration}s")
    print(f"  Overlap ratio: {config.overlap_ratio}")
    print(f"  Max chunks: {config.max_chunks}")
    print(f"  Memory limit: {config.memory_limit_mb} MB")
    
    # Create analyzer
    print("\nCreating TensorFlow analyzer...")
    analyzer_memory = get_memory_usage()
    print(f"Memory after creating analyzer: {analyzer_memory:.1f} MB (+{analyzer_memory - initial_memory:.1f} MB)")
    
    # Test file
    test_file = "/music/DJ Shu-ma - Deeper Love.flac"
    
    print(f"\nAnalyzing file: {test_file}")
    
    # Monitor memory during analysis
    start_time = time.time()
    start_memory = get_memory_usage()
    
    try:
        # Run analysis
        result = analyzer.analyze_audio_file(test_file)
        
        end_time = time.time()
        end_memory = get_memory_usage()
        
        print(f"\nAnalysis completed in {end_time - start_time:.2f}s")
        print(f"Memory usage:")
        print(f"  Start: {start_memory:.1f} MB")
        print(f"  End: {end_memory:.1f} MB")
        print(f"  Peak: {end_memory - start_memory:.1f} MB")
        print(f"  Total: {end_memory - initial_memory:.1f} MB")
        
        # Check results
        if 'metadata' in result:
            metadata = result['metadata']
            print(f"\nAnalysis strategy: {metadata.get('analysis_strategy', 'N/A')}")
            print(f"Audio duration: {metadata.get('audio_duration', 'N/A')}s")
        
        if 'streaming_metadata' in result:
            streaming = result['streaming_metadata']
            print(f"Chunks processed: {streaming.get('chunk_count', 'N/A')}")
            print(f"Total chunks available: {streaming.get('total_chunks_available', 'N/A')}")
        
        # Force garbage collection
        print("\nForcing garbage collection...")
        gc.collect()
        after_gc_memory = get_memory_usage()
        print(f"Memory after GC: {after_gc_memory:.1f} MB")
        print(f"Memory freed: {end_memory - after_gc_memory:.1f} MB")
        
    except Exception as e:
        print(f"Analysis failed: {e}")
        end_memory = get_memory_usage()
        print(f"Memory at failure: {end_memory:.1f} MB")
    
    # Test multiple files to see memory accumulation
    print("\n=== Testing Multiple Files ===")
    
    test_files = [
        "/music/DJ Shu-ma - Deeper Love.flac",
        "/music/Mark Ambor - Belong Together.mp3"
    ]
    
    for i, file_path in enumerate(test_files, 1):
        print(f"\n--- File {i}: {os.path.basename(file_path)} ---")
        
        start_memory = get_memory_usage()
        start_time = time.time()
        
        try:
            result = analyzer.analyze_audio_file(file_path)
            
            end_time = time.time()
            end_memory = get_memory_usage()
            
            print(f"Analysis time: {end_time - start_time:.2f}s")
            print(f"Memory: {start_memory:.1f} MB -> {end_memory:.1f} MB (+{end_memory - start_memory:.1f} MB)")
            
            # Force GC after each file
            gc.collect()
            after_gc_memory = get_memory_usage()
            print(f"After GC: {after_gc_memory:.1f} MB")
            
        except Exception as e:
            print(f"Failed: {e}")
    
    final_memory = get_memory_usage()
    print(f"\n=== Final Memory Usage ===")
    print(f"Total memory used: {final_memory - initial_memory:.1f} MB")
    print(f"Memory per file: {(final_memory - initial_memory) / len(test_files):.1f} MB")

if __name__ == "__main__":
    test_memory_usage()
