#!/usr/bin/env python3
"""
FAISS Usage Guide for Music Similarity Search

This script demonstrates how to use FAISS for music similarity search
in the playlist application.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from playlist_app.services.faiss_service import faiss_service
from playlist_app.models.database import SessionLocal, File, VectorIndex
from playlist_app.services.essentia_analyzer import essentia_analyzer

def demo_faiss_basic_usage():
    """Demonstrate basic FAISS usage"""
    print("=== Basic FAISS Usage ===")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # 1. Build FAISS index from database
        print("1. Building FAISS index from database...")
        result = faiss_service.build_index_from_database(
            db=db, 
            include_tensorflow=True, 
            force_rebuild=False
        )
        
        if "error" in result:
            print(f"Error building index: {result['error']}")
            return
        
        print(f"Index built successfully!")
        print(f"  - Total vectors: {result.get('total_vectors', 'N/A')}")
        print(f"  - Vector dimension: {result.get('vector_dimension', 'N/A')}")
        print(f"  - Build time: {result.get('build_time', 'N/A'):.2f}s")
        
        # 2. Get index statistics
        print("\n2. Getting index statistics...")
        stats = faiss_service.get_index_statistics(db)
        
        if "error" not in stats:
            print(f"Index Statistics:")
            print(f"  - Index coverage: {stats['index_coverage']:.1f}%")
            print(f"  - Total files: {stats['total_files']}")
            print(f"  - Analyzed files: {stats['analyzed_files']}")
            print(f"  - Indexed files: {stats['indexed_files']}")
            print(f"  - FAISS available: {stats['faiss_available']}")
            print(f"  - Index loaded: {stats['index_loaded']}")
        
        # 3. Find similar tracks
        print("\n3. Finding similar tracks...")
        
        # Get a file from database to use as query
        files = db.query(File).filter(File.is_analyzed == True).limit(1).all()
        
        if files:
            query_file = files[0].file_path
            print(f"Using query file: {query_file}")
            
            similar_tracks = faiss_service.find_similar_tracks(
                db=db, 
                query_path=query_file, 
                top_n=5
            )
            
            print(f"Found {len(similar_tracks)} similar tracks:")
            for i, (track_path, similarity) in enumerate(similar_tracks, 1):
                track_name = os.path.basename(track_path)
                print(f"  {i}. {track_name} (similarity: {similarity:.3f})")
        else:
            print("No analyzed files found in database")
        
        # 4. Add a new track to index
        print("\n4. Adding new track to index...")
        
        # Find an unindexed file
        unindexed_files = db.query(File).filter(
            File.is_analyzed == True,
            ~File.id.in_(
                db.query(VectorIndex.file_id).subquery()
            )
        ).limit(1).all()
        
        if unindexed_files:
            new_file = unindexed_files[0].file_path
            print(f"Adding file: {new_file}")
            
            add_result = faiss_service.add_track_to_index(
                db=db, 
                file_path=new_file, 
                include_tensorflow=True
            )
            
            if "error" not in add_result:
                print(f"Track added successfully!")
                print(f"  - Vector dimension: {add_result.get('vector_dimension', 'N/A')}")
            else:
                print(f"Error adding track: {add_result['error']}")
        else:
            print("No unindexed files found")
        
        # 5. Save index to disk
        print("\n5. Saving index to disk...")
        save_success = faiss_service.save_index_to_disk(".")
        
        if save_success:
            print("Index saved successfully!")
            print("  - music_library.faiss (FAISS index)")
            print("  - music_library.json (metadata)")
        else:
            print("Failed to save index")
        
    finally:
        db.close()

def demo_faiss_advanced_features():
    """Demonstrate advanced FAISS features"""
    print("\n=== Advanced FAISS Features ===")
    
    db = SessionLocal()
    
    try:
        # 1. Load existing index
        print("1. Loading existing index...")
        load_result = faiss_service.load_index_from_database(db)
        
        if "error" in load_result:
            print(f"Error loading index: {load_result['error']}")
            return
        
        print(f"Index loaded successfully!")
        print(f"  - Total vectors: {load_result.get('total_vectors', 'N/A')}")
        
        # 2. Search by vector (pre-computed)
        print("\n2. Searching by pre-computed vector...")
        
        # Get a file and extract its vector
        files = db.query(File).filter(File.is_analyzed == True).limit(1).all()
        
        if files:
            query_file = files[0].file_path
            print(f"Extracting vector from: {query_file}")
            
            # Extract feature vector
            query_vector = essentia_analyzer.extract_feature_vector(
                query_file, 
                include_tensorflow=True
            )
            
            print(f"Vector dimension: {len(query_vector)}")
            
            # Search by vector
            similar_tracks = faiss_service.find_similar_by_vector(
                db=db, 
                query_vector=query_vector, 
                top_n=3
            )
            
            print(f"Found {len(similar_tracks)} similar tracks:")
            for i, (track_path, similarity) in enumerate(similar_tracks, 1):
                track_name = os.path.basename(track_path)
                print(f"  {i}. {track_name} (similarity: {similarity:.3f})")
        
        # 3. Force rebuild index
        print("\n3. Force rebuilding index...")
        rebuild_result = faiss_service.build_index_from_database(
            db=db, 
            include_tensorflow=True, 
            force_rebuild=True
        )
        
        if "error" not in rebuild_result:
            print("Index rebuilt successfully!")
            print(f"  - Build time: {rebuild_result.get('build_time', 'N/A'):.2f}s")
        else:
            print(f"Error rebuilding index: {rebuild_result['error']}")
        
    finally:
        db.close()

def demo_faiss_playlist_generation():
    """Demonstrate playlist generation using FAISS"""
    print("\n=== Playlist Generation with FAISS ===")
    
    db = SessionLocal()
    
    try:
        # Ensure index is loaded
        faiss_service.load_index_from_database(db)
        
        # Get a seed track
        files = db.query(File).filter(File.is_analyzed == True).limit(1).all()
        
        if not files:
            print("No analyzed files found")
            return
        
        seed_track = files[0].file_path
        print(f"Generating playlist from seed track: {os.path.basename(seed_track)}")
        
        # Generate playlist
        playlist_tracks = faiss_service.find_similar_tracks(
            db=db, 
            query_path=seed_track, 
            top_n=10
        )
        
        print(f"\nGenerated playlist ({len(playlist_tracks)} tracks):")
        for i, (track_path, similarity) in enumerate(playlist_tracks, 1):
            track_name = os.path.basename(track_path)
            print(f"  {i:2d}. {track_name} (similarity: {similarity:.3f})")
        
        # Show playlist statistics
        if playlist_tracks:
            similarities = [sim for _, sim in playlist_tracks]
            avg_similarity = sum(similarities) / len(similarities)
            min_similarity = min(similarities)
            max_similarity = max(similarities)
            
            print(f"\nPlaylist Statistics:")
            print(f"  - Average similarity: {avg_similarity:.3f}")
            print(f"  - Min similarity: {min_similarity:.3f}")
            print(f"  - Max similarity: {max_similarity:.3f}")
            print(f"  - Similarity range: {max_similarity - min_similarity:.3f}")
        
    finally:
        db.close()

def demo_faiss_performance():
    """Demonstrate FAISS performance"""
    print("\n=== FAISS Performance Demo ===")
    
    db = SessionLocal()
    
    try:
        # Load index
        faiss_service.load_index_from_database(db)
        
        # Get multiple query files
        files = db.query(File).filter(File.is_analyzed == True).limit(5).all()
        
        if not files:
            print("No analyzed files found")
            return
        
        print(f"Testing performance with {len(files)} query files...")
        
        # Test search performance
        total_time = 0
        total_searches = 0
        
        for file_record in files:
            query_file = file_record.file_path
            track_name = os.path.basename(query_file)
            
            start_time = time.time()
            similar_tracks = faiss_service.find_similar_tracks(
                db=db, 
                query_path=query_file, 
                top_n=5
            )
            search_time = time.time() - start_time
            
            total_time += search_time
            total_searches += 1
            
            print(f"  {track_name}: {search_time:.3f}s ({len(similar_tracks)} results)")
        
        if total_searches > 0:
            avg_time = total_time / total_searches
            print(f"\nPerformance Summary:")
            print(f"  - Total searches: {total_searches}")
            print(f"  - Total time: {total_time:.3f}s")
            print(f"  - Average time per search: {avg_time:.3f}s")
            print(f"  - Searches per second: {1/avg_time:.1f}")
        
    finally:
        db.close()

def main():
    """Run all FAISS demos"""
    print("FAISS Usage Guide for Music Similarity Search")
    print("=" * 60)
    
    try:
        # Basic usage
        demo_faiss_basic_usage()
        
        # Advanced features
        demo_faiss_advanced_features()
        
        # Playlist generation
        demo_faiss_playlist_generation()
        
        # Performance testing
        demo_faiss_performance()
        
        print("\n" + "=" * 60)
        print("FAISS usage guide completed successfully!")
        
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
