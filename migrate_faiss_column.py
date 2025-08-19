#!/usr/bin/env python3
"""
Migration script to add faiss_analyzed column to existing databases.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.playlist_app.models.database import get_db_session, close_db_session

def migrate_faiss_column():
    """Add faiss_analyzed column to files table if it doesn't exist"""
    print("Starting FAISS column migration...")
    
    db = get_db_session()
    try:
        # Check if faiss_analyzed column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'files' AND column_name = 'faiss_analyzed'
        """))
        
        if result.fetchone():
            print("faiss_analyzed column already exists, skipping migration")
            return
        
        # Add the column
        print("Adding faiss_analyzed column to files table...")
        db.execute(text("ALTER TABLE files ADD COLUMN faiss_analyzed BOOLEAN DEFAULT FALSE"))
        
        # Update existing records to set faiss_analyzed based on analysis_status
        print("Updating existing records...")
        db.execute(text("""
            UPDATE files 
            SET faiss_analyzed = TRUE 
            WHERE analysis_status LIKE '%faiss%' OR status = 'faiss_analyzed'
        """))
        
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)

if __name__ == "__main__":
    migrate_faiss_column()
