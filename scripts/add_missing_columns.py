#!/usr/bin/env python3
"""
Script to add missing columns to analysis status tables.
"""

import logging
from sqlalchemy import text
from src.playlist_app.models.database import get_db_session, close_db_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_columns():
    """Add missing columns to analysis status tables."""
    logger.info("Adding missing columns to analysis status tables...")
    
    db = get_db_session()
    try:
        # Check if last_attempt column exists in essentia_analysis_status
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'essentia_analysis_status' 
            AND column_name = 'last_attempt'
        """))
        
        if not result.fetchone():
            logger.info("Adding last_attempt column to essentia_analysis_status...")
            db.execute(text("""
                ALTER TABLE essentia_analysis_status 
                ADD COLUMN last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            logger.info("✓ Added last_attempt column to essentia_analysis_status")
        else:
            logger.info("✓ last_attempt column already exists in essentia_analysis_status")
        
        # Check if last_attempt column exists in tensorflow_analysis_status
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'tensorflow_analysis_status' 
            AND column_name = 'last_attempt'
        """))
        
        if not result.fetchone():
            logger.info("Adding last_attempt column to tensorflow_analysis_status...")
            db.execute(text("""
                ALTER TABLE tensorflow_analysis_status 
                ADD COLUMN last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            logger.info("✓ Added last_attempt column to tensorflow_analysis_status")
        else:
            logger.info("✓ last_attempt column already exists in tensorflow_analysis_status")
        
        # Check if last_attempt column exists in faiss_analysis_status
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'faiss_analysis_status' 
            AND column_name = 'last_attempt'
        """))
        
        if not result.fetchone():
            logger.info("Adding last_attempt column to faiss_analysis_status...")
            db.execute(text("""
                ALTER TABLE faiss_analysis_status 
                ADD COLUMN last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            logger.info("✓ Added last_attempt column to faiss_analysis_status")
        else:
            logger.info("✓ last_attempt column already exists in faiss_analysis_status")
        
        db.commit()
        logger.info("All missing columns added successfully")
        
    except Exception as e:
        logger.error(f"Error adding missing columns: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)

if __name__ == "__main__":
    add_missing_columns()
