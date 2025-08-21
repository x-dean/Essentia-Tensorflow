#!/usr/bin/env python3
"""
Test script for the new v2 database architecture
This script tests the new tables, authentication, and playlist functionality
"""

import sys
import os
import logging
from datetime import datetime

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from playlist_app.models.database import (
    SessionLocal, Playlist, PlaylistTrack, File, AudioMetadata
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test database connection and basic operations"""
    logger.info("Testing database connection...")
    
    try:
        db = SessionLocal()
        
        # Test basic query
        result = db.execute("SELECT 1 as test").scalar()
        assert result == 1
        logger.info("✅ Database connection successful")
        
        db.close()
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False





def test_playlist_creation():
    """Test playlist creation and management"""
    logger.info("Testing playlist creation...")
    
    try:
        db = SessionLocal()
        
        # Create test playlist
        playlist = Playlist(
            name="Test Playlist",
            description="A test playlist for testing",
            is_public=True,
            total_duration=0,
            track_count=0,
            play_count=0,
            rating_avg=0
        )
        
        db.add(playlist)
        db.commit()
        db.refresh(playlist)
        
        logger.info(f"✅ Test playlist created: {playlist.name}")
        
        # Test playlist retrieval
        retrieved_playlist = db.query(Playlist).filter(Playlist.id == playlist.id).first()
        assert retrieved_playlist is not None
        assert retrieved_playlist.name == "Test Playlist"
        logger.info("✅ Playlist retrieval successful")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Playlist creation failed: {e}")
        return False

def test_file_association():
    """Test file association and metadata"""
    logger.info("Testing file association...")
    
    try:
        db = SessionLocal()
        
        # Get a sample file
        sample_file = db.query(File).first()
        if not sample_file:
            logger.warning("⚠️  No files found in database")
            db.close()
            return True
        
        # Update file metadata
        sample_file.is_favorite = True
        sample_file.rating = 5
        sample_file.tags = ["test", "favorite"]
        
        db.commit()
        
        logger.info(f"✅ File metadata updated: {sample_file.file_name}")
        
        # Test file retrieval
        updated_file = db.query(File).filter(File.id == sample_file.id).first()
        assert updated_file.is_favorite == True
        assert updated_file.rating == 5
        logger.info("✅ File metadata retrieval successful")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ File association failed: {e}")
        return False

def test_playlist_track_management():
    """Test adding tracks to playlists"""
    logger.info("Testing playlist track management...")
    
    try:
        db = SessionLocal()
        
        # Get test playlist
        playlist = db.query(Playlist).filter(Playlist.name == "Test Playlist").first()
        
        if not playlist:
            logger.error("❌ Test playlist not found")
            return False
        
        # Get sample files
        sample_files = db.query(File).limit(3).all()
        if not sample_files:
            logger.warning("⚠️  No files found for playlist testing")
            db.close()
            return True
        
        # Add tracks to playlist
        for i, file in enumerate(sample_files, 1):
            playlist_track = PlaylistTrack(
                playlist_id=playlist.id,
                file_id=file.id,
                position=i,
                notes=f"Test track {i}"
            )
            db.add(playlist_track)
        
        db.commit()
        
        # Verify tracks were added
        playlist_tracks = db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == playlist.id).all()
        assert len(playlist_tracks) == len(sample_files)
        logger.info(f"✅ Added {len(playlist_tracks)} tracks to playlist")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Playlist track management failed: {e}")
        return False

def cleanup_test_data():
    """Clean up test data"""
    logger.info("Cleaning up test data...")
    
    try:
        db = SessionLocal()
        
        # Remove test playlist tracks
        test_playlist = db.query(Playlist).filter(Playlist.name == "Test Playlist").first()
        if test_playlist:
            db.query(PlaylistTrack).filter(PlaylistTrack.playlist_id == test_playlist.id).delete()
            db.delete(test_playlist)
        
        db.commit()
        logger.info("✅ Test data cleaned up")
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting v2 database architecture tests...")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Playlist Creation", test_playlist_creation),
        ("File Association", test_file_association),
        ("Playlist Track Management", test_playlist_track_management),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing: {test_name} ---")
        try:
            if test_func():
                passed += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with exception: {e}")
    
    logger.info(f"\n--- Test Results ---")
    logger.info(f"Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        logger.info("🎉 All tests passed! v2 database architecture is working correctly.")
    else:
        logger.error("❌ Some tests failed. Please check the logs above.")
    
    # Cleanup
    cleanup_test_data()
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
