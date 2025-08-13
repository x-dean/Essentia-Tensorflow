#!/usr/bin/env python3
"""
FAISS Demo for EssentiaAnalyzer

This script demonstrates how to use the FAISS-integrated EssentiaAnalyzer
for building a music library and finding similar tracks efficiently.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from playlist_app.services.essentia_analyzer import EssentiaAnalyzer

def demo_basic_analysis():
    """Demonstrate basic audio analysis"""
    print("=== Basic Audio Analysis Demo ===")
    
    analyzer = EssentiaAnalyzer()
    
    # Check if we have any test audio files
    test_files = [
        "music/test1.mp3",
        "music/test2.wav", 
        "audio/test3.flac"
    ]
    
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"\nAnalyzing {test_file}...")
            try:
                results = analyzer.analyze_audio_file(test_file, include_tensorflow=True)
                
                # Print key features
                print(f"  Duration: {results['basic_features']['duration']:.2f}s")
                print(f"  BPM: {results['rhythm_features']['estimated_bpm']:.1f}")
                print(f"  Key: {results['harmonic_features']['key']} {results['harmonic_features']['scale']}")
                
                if 'musicnn' in results and results['musicnn']['genre']:
                    # Get top 3 genres
                    genres = sorted(results['musicnn']['genre'].items(), 
                                  key=lambda x: x[1], reverse=True)[:3]
                    print(f"  Top genres: {', '.join([f'{g[0]} ({g[1]:.3f})' for g in genres])}")
                
            except Exception as e:
                print(f"  Error analyzing {test_file}: {e}")
            break
    else:
        print("No test audio files found. Please add some audio files to the music/ or audio/ directories.")

def demo_library_building():
    """Demonstrate building a music library with FAISS"""
    print("\n=== Music Library Building Demo ===")
    
    analyzer = EssentiaAnalyzer()
    
    # Find audio files in the project
    audio_files = []
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.lower().endswith(('.mp3', '.wav', '.flac', '.m4a')):
                audio_files.append(os.path.join(root, file))
    
    if not audio_files:
        print("No audio files found. Please add some audio files to the project.")
        return
    
    print(f"Found {len(audio_files)} audio files")
    
    # Limit to first 5 files for demo
    demo_files = audio_files[:5]
    print(f"Using first {len(demo_files)} files for demo:")
    for f in demo_files:
        print(f"  - {f}")
    
    # Build library
    print(f"\nBuilding library...")
    start_time = time.time()
    
    analyzer.add_multiple_to_library(demo_files, include_tensorflow=True)
    
    build_time = time.time() - start_time
    print(f"Library built in {build_time:.2f} seconds")
    
    # Show library stats
    stats = analyzer.get_library_stats()
    print(f"\nLibrary Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Save index
    analyzer.save_index("demo_library")
    print(f"\nIndex saved to demo_library.faiss and demo_library.json")
    
    return analyzer, demo_files

def demo_similarity_search(analyzer, demo_files):
    """Demonstrate similarity search"""
    print("\n=== Similarity Search Demo ===")
    
    if not demo_files:
        print("No files in library for similarity search")
        return
    
    # Use the first file as query
    query_file = demo_files[0]
    print(f"Finding tracks similar to: {query_file}")
    
    # Find similar tracks
    start_time = time.time()
    similar_tracks = analyzer.find_similar(query_file, top_n=3)
    search_time = time.time() - start_time
    
    print(f"Found {len(similar_tracks)} similar tracks in {search_time:.3f} seconds:")
    for i, (track_path, similarity) in enumerate(similar_tracks, 1):
        print(f"  {i}. {os.path.basename(track_path)} (similarity: {similarity:.3f})")

def demo_batch_search(analyzer, demo_files):
    """Demonstrate batch similarity search"""
    print("\n=== Batch Similarity Search Demo ===")
    
    if len(demo_files) < 2:
        print("Need at least 2 files for batch search demo")
        return
    
    # Use first 2 files as queries
    query_files = demo_files[:2]
    print(f"Batch searching for tracks similar to {len(query_files)} query files...")
    
    start_time = time.time()
    batch_results = analyzer.find_similar_batch(query_files, top_n=2)
    batch_time = time.time() - start_time
    
    print(f"Batch search completed in {batch_time:.3f} seconds:")
    for query_file, similar_tracks in batch_results.items():
        print(f"\nSimilar to {os.path.basename(query_file)}:")
        for track_path, similarity in similar_tracks:
            print(f"  - {os.path.basename(track_path)} (similarity: {similarity:.3f})")

def demo_index_persistence():
    """Demonstrate saving and loading FAISS index"""
    print("\n=== Index Persistence Demo ===")
    
    # Create new analyzer and load existing index
    analyzer2 = EssentiaAnalyzer()
    
    if os.path.exists("demo_library.faiss"):
        print("Loading existing index...")
        analyzer2.load_index("demo_library")
        
        stats = analyzer2.get_library_stats()
        print(f"Loaded index with {stats['total_tracks']} tracks")
        
        # Test search with loaded index
        if stats['total_tracks'] > 0:
            print("Testing search with loaded index...")
            # This would work if we had the original files
            print("(Search would work here if original files were available)")
    else:
        print("No existing index found")

def main():
    """Run all demos"""
    print("FAISS-Integrated EssentiaAnalyzer Demo")
    print("=" * 50)
    
    try:
        # Demo 1: Basic analysis
        demo_basic_analysis()
        
        # Demo 2: Library building
        analyzer, demo_files = demo_library_building()
        
        # Demo 3: Similarity search
        demo_similarity_search(analyzer, demo_files)
        
        # Demo 4: Batch search
        demo_batch_search(analyzer, demo_files)
        
        # Demo 5: Index persistence
        demo_index_persistence()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
