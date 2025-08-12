#!/usr/bin/env python3
"""
Simple Database Reset Script for Essentia-Tensorflow Playlist App

This script resets and recreates the database tables.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playlist_app.models.database import Base, engine, create_tables

def reset_database():
    """Reset and recreate the database"""
    try:
        print("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped successfully")
        
        print("Recreating database tables...")
        create_tables()
        print("Database tables recreated successfully")
        
        print("Database reset completed!")
        return True
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

if __name__ == "__main__":
    print("WARNING: This will permanently delete all database data!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        success = reset_database()
        sys.exit(0 if success else 1)
    else:
        print("Database reset cancelled.")
        sys.exit(0)

