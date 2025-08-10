#!/usr/bin/env python3
"""
Test script for the discovery system
"""

import os
import tempfile
import shutil
from pathlib import Path
from src.playlist_app.models.database import create_tables, SessionLocal
from src.playlist_app.services.discovery import DiscoveryService
from src.playlist_app.core.config import DiscoveryConfig

def create_test_files(test_dir: str):
    """Create test audio files"""
    test_files = [
        "song1.mp3",
        "song2.wav", 
        "song3.flac",
        "song4.ogg",
        "document.txt",  # Should be ignored
        "image.jpg"      # Should be ignored
    ]
    
    for filename in test_files:
        file_path = os.path.join(test_dir, filename)
        with open(file_path, 'w') as f:
            f.write(f"Test content for {filename}")
    
    return test_files

def test_discovery():
    """Test the discovery system"""
    print("Testing Discovery System...")
    
    # Create test directory
    test_dir = tempfile.mkdtemp(prefix="discovery_test_")
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create test files
        test_files = create_test_files(test_dir)
        print(f"Created {len(test_files)} test files")
        
        # Update config to use test directory
        DiscoveryConfig.SEARCH_DIRECTORIES = [test_dir]
        
        # Create database
        create_tables()
        print("Database tables created")
        
        # Test discovery service
        db = SessionLocal()
        discovery_service = DiscoveryService(db)
        
        # Run discovery
        print("Running file discovery...")
        results = discovery_service.discover_files()
        
        print(f"Discovery results:")
        print(f"  Added: {len(results['added'])} files")
        print(f"  Removed: {len(results['removed'])} files")
        print(f"  Unchanged: {len(results['unchanged'])} files")
        
        # Get discovered files
        files = discovery_service.get_discovered_files()
        print(f"\nDiscovered files:")
        for file in files:
            print(f"  - {file['file_name']} ({file['file_extension']}) - {file['file_size']} bytes")
        
        # Test file removal
        print(f"\nTesting file removal...")
        test_file_to_remove = os.path.join(test_dir, "song1.mp3")
        if os.path.exists(test_file_to_remove):
            os.remove(test_file_to_remove)
            print(f"Removed: {test_file_to_remove}")
        
        # Run discovery again
        results = discovery_service.discover_files()
        print(f"After removal:")
        print(f"  Added: {len(results['added'])} files")
        print(f"  Removed: {len(results['removed'])} files")
        
        # Get updated file list
        files = discovery_service.get_discovered_files()
        print(f"\nRemaining files:")
        for file in files:
            print(f"  - {file['file_name']} ({file['file_extension']})")
        
        print("\nDiscovery test completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        raise
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"Cleaned up test directory: {test_dir}")

if __name__ == "__main__":
    test_discovery()
