#!/usr/bin/env python3
"""
Reset Database with New Independent Analyzer Schema

This script drops all existing tables and recreates them with the new
independent analyzer architecture.
"""

import sys
import os

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_path)

# Also add the absolute path for Docker container
if os.path.exists('/app/src'):
    sys.path.insert(0, '/app/src')

import logging
from sqlalchemy import text
from playlist_app.models.database import (
    engine, Base, get_db_session, close_db_session,
    File, AudioMetadata, DiscoveryCache, FAISSIndexMetadata,
    EssentiaAnalysisStatus, EssentiaAnalysisResults,
    TensorFlowAnalysisStatus, TensorFlowAnalysisResults,
    FAISSAnalysisStatus, FAISSAnalysisResults,
    TrackAnalysisSummary
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def drop_all_tables():
    """Drop all existing tables."""
    logger.info("Dropping all existing tables...")
    
    db = get_db_session()
    try:
        # Drop tables in reverse dependency order
        tables_to_drop = [
            "track_analysis_summary",
            "faiss_analysis_results",
            "faiss_analysis_status",
            "tensorflow_analysis_results",
            "tensorflow_analysis_status",
            "essentia_analysis_results",
            "essentia_analysis_status",
            "faiss_index_metadata",
            "audio_metadata",
            "discovery_cache",
            "files"
        ]
        
        for table in tables_to_drop:
            try:
                db.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                logger.info(f"Dropped table: {table}")
            except Exception as e:
                logger.warning(f"Could not drop table {table}: {e}")
        
        db.commit()
        logger.info("All tables dropped successfully")
        
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)

def create_new_tables():
    """Create all new tables with the independent analyzer schema."""
    logger.info("Creating new tables with independent analyzer schema...")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("All new tables created successfully")
        
        # Verify table creation
        db = get_db_session()
        try:
            # Check that all expected tables exist
            expected_tables = [
                "files",
                "audio_metadata", 
                "discovery_cache",
                "essentia_analysis_status",
                "essentia_analysis_results",
                "tensorflow_analysis_status",
                "tensorflow_analysis_results",
                "faiss_analysis_status",
                "faiss_analysis_results",
                "track_analysis_summary",
                "faiss_index_metadata"
            ]
            
            for table in expected_tables:
                result = db.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"))
                exists = result.scalar()
                if exists:
                    logger.info(f"✓ Table {table} created successfully")
                else:
                    logger.error(f"✗ Table {table} was not created")
                    raise Exception(f"Table {table} was not created")
            
            logger.info("All expected tables verified successfully")
            
        finally:
            close_db_session(db)
            
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

def create_indexes():
    """Create additional indexes for performance."""
    logger.info("Creating performance indexes...")
    
    db = get_db_session()
    try:
        # Create indexes for better query performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_files_file_path ON files(file_path)",
            "CREATE INDEX IF NOT EXISTS idx_files_file_hash ON files(file_hash)",
            "CREATE INDEX IF NOT EXISTS idx_files_status ON files(status)",
            "CREATE INDEX IF NOT EXISTS idx_files_is_active ON files(is_active)",
            
            "CREATE INDEX IF NOT EXISTS idx_essentia_status_file_id ON essentia_analysis_status(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_essentia_status_status ON essentia_analysis_status(status)",
            "CREATE INDEX IF NOT EXISTS idx_essentia_status_last_attempt ON essentia_analysis_status(last_attempt)",
            
            "CREATE INDEX IF NOT EXISTS idx_tensorflow_status_file_id ON tensorflow_analysis_status(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_tensorflow_status_status ON tensorflow_analysis_status(status)",
            "CREATE INDEX IF NOT EXISTS idx_tensorflow_status_last_attempt ON tensorflow_analysis_status(last_attempt)",
            
            "CREATE INDEX IF NOT EXISTS idx_faiss_status_file_id ON faiss_analysis_status(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_faiss_status_status ON faiss_analysis_status(status)",
            "CREATE INDEX IF NOT EXISTS idx_faiss_status_last_attempt ON faiss_analysis_status(last_attempt)",
            
            "CREATE INDEX IF NOT EXISTS idx_track_summary_file_id ON track_analysis_summary(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_track_summary_overall_status ON track_analysis_summary(overall_status)",
            "CREATE INDEX IF NOT EXISTS idx_track_summary_last_updated ON track_analysis_summary(last_updated)",
            
            "CREATE INDEX IF NOT EXISTS idx_audio_metadata_file_id ON audio_metadata(file_id)",
            "CREATE INDEX IF NOT EXISTS idx_audio_metadata_title ON audio_metadata(title)",
            "CREATE INDEX IF NOT EXISTS idx_audio_metadata_artist ON audio_metadata(artist)",
            "CREATE INDEX IF NOT EXISTS idx_audio_metadata_album ON audio_metadata(album)",
            "CREATE INDEX IF NOT EXISTS idx_audio_metadata_genre ON audio_metadata(genre)"
        ]
        
        for index_sql in indexes:
            try:
                db.execute(text(index_sql))
                logger.info(f"Created index: {index_sql.split('idx_')[1].split(' ')[0]}")
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
        
        db.commit()
        logger.info("Performance indexes created successfully")
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)

def verify_schema():
    """Verify the new schema is working correctly."""
    logger.info("Verifying new schema...")
    
    db = get_db_session()
    try:
        # Test inserting a sample file
        sample_file = File(
            file_path="/test/sample.mp3",
            file_name="sample.mp3",
            file_size=1024,
            file_hash="test_hash_123",
            file_extension=".mp3",
            status="discovered",
            is_active=True
        )
        
        db.add(sample_file)
        db.commit()
        
        # Test creating status records
        essentia_status = EssentiaAnalysisStatus(
            file_id=sample_file.id,
            status="pending"
        )
        db.add(essentia_status)
        
        tensorflow_status = TensorFlowAnalysisStatus(
            file_id=sample_file.id,
            status="pending"
        )
        db.add(tensorflow_status)
        
        faiss_status = FAISSAnalysisStatus(
            file_id=sample_file.id,
            status="pending"
        )
        db.add(faiss_status)
        
        # Test creating track summary
        track_summary = TrackAnalysisSummary(
            file_id=sample_file.id,
            essentia_status="pending",
            tensorflow_status="pending",
            faiss_status="pending",
            overall_status="pending"
        )
        db.add(track_summary)
        
        db.commit()
        
        # Verify records were created
        file_count = db.query(File).count()
        essentia_count = db.query(EssentiaAnalysisStatus).count()
        tensorflow_count = db.query(TensorFlowAnalysisStatus).count()
        faiss_count = db.query(FAISSAnalysisStatus).count()
        summary_count = db.query(TrackAnalysisSummary).count()
        
        logger.info(f"Schema verification results:")
        logger.info(f"  Files: {file_count}")
        logger.info(f"  Essentia status records: {essentia_count}")
        logger.info(f"  TensorFlow status records: {tensorflow_count}")
        logger.info(f"  FAISS status records: {faiss_count}")
        logger.info(f"  Track summaries: {summary_count}")
        
        # Clean up test data
        db.query(TrackAnalysisSummary).delete()
        db.query(FAISSAnalysisStatus).delete()
        db.query(TensorFlowAnalysisStatus).delete()
        db.query(EssentiaAnalysisStatus).delete()
        db.query(File).delete()
        db.commit()
        
        logger.info("✓ Schema verification completed successfully")
        
    except Exception as e:
        logger.error(f"✗ Schema verification failed: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)

def main():
    """Main function to reset the database."""
    logger.info("Starting database reset with new independent analyzer schema...")
    
    try:
        # Step 1: Drop all existing tables
        drop_all_tables()
        
        # Step 2: Create new tables
        create_new_tables()
        
        # Step 3: Create performance indexes
        create_indexes()
        
        # Step 4: Verify schema
        verify_schema()
        
        logger.info("✅ Database reset completed successfully!")
        logger.info("")
        logger.info("New schema includes:")
        logger.info("  - Independent analyzer status tables")
        logger.info("  - Separate results tables for each analyzer")
        logger.info("  - Track analysis summary table")
        logger.info("  - Performance indexes for fast queries")
        logger.info("")
        logger.info("You can now use the independent analyzer services:")
        logger.info("  - essentia_service")
        logger.info("  - tensorflow_service") 
        logger.info("  - faiss_service")
        logger.info("  - analysis_coordinator")
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
