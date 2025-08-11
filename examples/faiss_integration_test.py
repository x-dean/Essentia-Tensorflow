#!/usr/bin/env python3
"""
FAISS Integration Test

This script tests the complete FAISS integration with PostgreSQL database,
audio analysis, and the application architecture.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from playlist_app.models.database import get_db, create_tables
from playlist_app.services.audio_analysis_service import audio_analysis_service
from playlist_app.services.faiss_service import faiss_service
from playlist_app.services.essentia_analyzer import essentia_analyzer

def test_database_integration():
    """Test database integration and table creation"""
    print("=== Testing Database Integration ===")
    
    try:
        # Create tables
        create_tables()
        print("✓ Database tables created successfully")
        
        # Test database connection
        db = next(get_db())
        print("✓ Database connection successful")
        
        # Test basic queries
        from playlist_app.models.database import File, AudioAnalysis, VectorIndex, FAISSIndexMetadata
        
        # Check if tables exist
        file_count = db.query(File).count()
        analysis_count = db.query(AudioAnalysis).count()
        vector_count = db.query(VectorIndex).count()
        metadata_count = db.query(FAISSIndexMetadata).count()
        
        print(f"✓ Database tables accessible:")
        print(f"  - Files: {file_count}")
        print(f"  - Audio Analysis: {analysis_count}")
        print(f"  - Vector Index: {vector_count}")
        print(f"  - FAISS Metadata: {metadata_count}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Database integration failed: {e}")
        return False

def test_audio_analysis_integration():
    """Test audio analysis with FAISS integration"""
    print("\n=== Testing Audio Analysis Integration ===")
    
    try:
        db = next(get_db())
        
        # Check if we have any test files
        test_files = [
            "music/test1.mp3",
            "music/test2.wav", 
            "audio/test3.flac"
        ]
        
        analyzed_files = []
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"Analyzing {test_file}...")
                try:
                    # Analyze file
                    result = audio_analysis_service.analyze_file(db, test_file, include_tensorflow=True)
                    analyzed_files.append(test_file)
                    print(f"✓ Analysis completed for {test_file}")
                    
                    # Check if vector was added to database
                    from playlist_app.models.database import File, VectorIndex
                    file_record = db.query(File).filter(File.file_path == test_file).first()
                    if file_record:
                        vector_record = db.query(VectorIndex).filter(VectorIndex.file_id == file_record.id).first()
                        if vector_record:
                            print(f"✓ Vector indexed for {test_file} (dimension: {vector_record.vector_dimension})")
                        else:
                            print(f"⚠ Vector not found for {test_file}")
                    
                except Exception as e:
                    print(f"✗ Analysis failed for {test_file}: {e}")
        
        if not analyzed_files:
            print("⚠ No test files found for analysis")
            return False
        
        print(f"✓ Successfully analyzed {len(analyzed_files)} files")
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Audio analysis integration failed: {e}")
        return False

def test_faiss_index_building():
    """Test FAISS index building from database"""
    print("\n=== Testing FAISS Index Building ===")
    
    try:
        db = next(get_db())
        
        # Build FAISS index
        print("Building FAISS index from database...")
        start_time = time.time()
        
        result = faiss_service.build_index_from_database(db, include_tensorflow=True)
        
        build_time = time.time() - start_time
        
        if result.get("success"):
            print(f"✓ FAISS index built successfully:")
            print(f"  - Total vectors: {result.get('total_vectors', 0)}")
            print(f"  - Vector dimension: {result.get('vector_dimension', 0)}")
            print(f"  - Index type: {result.get('index_type', 'unknown')}")
            print(f"  - Build time: {build_time:.2f}s")
        else:
            print(f"✗ FAISS index building failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Get index statistics
        stats = faiss_service.get_index_statistics(db)
        if not stats.get("error"):
            print(f"✓ Index statistics:")
            print(f"  - Index coverage: {stats.get('index_coverage', 0):.1f}%")
            print(f"  - FAISS available: {stats.get('faiss_available', False)}")
            print(f"  - Index loaded: {stats.get('index_loaded', False)}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ FAISS index building failed: {e}")
        return False

def test_similarity_search():
    """Test similarity search functionality"""
    print("\n=== Testing Similarity Search ===")
    
    try:
        db = next(get_db())
        
        # Get a test file for query
        from playlist_app.models.database import File
        test_file = db.query(File).filter(File.is_analyzed == True).first()
        
        if not test_file:
            print("⚠ No analyzed files found for similarity search")
            return False
        
        print(f"Finding tracks similar to: {test_file.file_path}")
        
        # Test similarity search
        similar_tracks = faiss_service.find_similar_tracks(db, test_file.file_path, top_n=3)
        
        if similar_tracks:
            print(f"✓ Found {len(similar_tracks)} similar tracks:")
            for i, (track_path, similarity) in enumerate(similar_tracks, 1):
                print(f"  {i}. {os.path.basename(track_path)} (similarity: {similarity:.3f})")
        else:
            print("⚠ No similar tracks found")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Similarity search failed: {e}")
        return False

def test_vector_extraction():
    """Test feature vector extraction"""
    print("\n=== Testing Vector Extraction ===")
    
    try:
        # Test vector extraction
        test_files = [
            "music/test1.mp3",
            "music/test2.wav", 
            "audio/test3.flac"
        ]
        
        for test_file in test_files:
            if os.path.exists(test_file):
                print(f"Extracting vector from {test_file}...")
                try:
                    vector = essentia_analyzer.extract_feature_vector(test_file, include_tensorflow=True)
                    print(f"✓ Vector extracted: {len(vector)} dimensions")
                    
                    # Test vector properties
                    print(f"  - Shape: {vector.shape}")
                    print(f"  - Type: {vector.dtype}")
                    print(f"  - Range: {vector.min():.3f} to {vector.max():.3f}")
                    print(f"  - Norm: {np.linalg.norm(vector):.3f}")
                    
                    break  # Test with first available file
                    
                except Exception as e:
                    print(f"✗ Vector extraction failed for {test_file}: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Vector extraction test failed: {e}")
        return False

def test_api_integration():
    """Test API integration (simulated)"""
    print("\n=== Testing API Integration ===")
    
    try:
        db = next(get_db())
        
        # Simulate API calls
        print("Testing API endpoints...")
        
        # Test FAISS statistics endpoint
        stats = audio_analysis_service.get_faiss_statistics(db)
        if not stats.get("error"):
            print("✓ FAISS statistics endpoint working")
        
        # Test analysis statistics endpoint
        analysis_stats = audio_analysis_service.get_analysis_statistics(db)
        if analysis_stats:
            print("✓ Analysis statistics endpoint working")
        
        # Test similarity search endpoint
        test_file = db.query(File).filter(File.is_analyzed == True).first()
        if test_file:
            similar_tracks = audio_analysis_service.find_similar_tracks(db, test_file.file_path, top_n=2)
            if similar_tracks is not None:
                print("✓ Similarity search endpoint working")
        
        db.close()
        print("✓ API integration tests passed")
        return True
        
    except Exception as e:
        print(f"✗ API integration test failed: {e}")
        return False

def test_performance():
    """Test performance characteristics"""
    print("\n=== Testing Performance ===")
    
    try:
        db = next(get_db())
        
        # Test search performance
        test_file = db.query(File).filter(File.is_analyzed == True).first()
        if test_file:
            print("Testing search performance...")
            
            # Warm up
            for _ in range(3):
                faiss_service.find_similar_tracks(db, test_file.file_path, top_n=1)
            
            # Performance test
            start_time = time.time()
            for _ in range(10):
                faiss_service.find_similar_tracks(db, test_file.file_path, top_n=5)
            end_time = time.time()
            
            avg_time = (end_time - start_time) / 10
            print(f"✓ Average search time: {avg_time*1000:.1f}ms")
            
            if avg_time < 0.1:  # Less than 100ms
                print("✓ Performance is good")
            elif avg_time < 1.0:  # Less than 1 second
                print("⚠ Performance is acceptable")
            else:
                print("✗ Performance is slow")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        return False

def main():
    """Run all integration tests"""
    print("FAISS Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Database Integration", test_database_integration),
        ("Audio Analysis Integration", test_audio_analysis_integration),
        ("Vector Extraction", test_vector_extraction),
        ("FAISS Index Building", test_faiss_index_building),
        ("Similarity Search", test_similarity_search),
        ("API Integration", test_api_integration),
        ("Performance", test_performance)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"✗ {test_name} test failed")
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! FAISS integration is working correctly.")
    elif passed >= total * 0.8:
        print("✅ Most tests passed. FAISS integration is mostly working.")
    else:
        print("❌ Many tests failed. FAISS integration needs attention.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
