#!/usr/bin/env python3
"""
Simple CLI for Essentia-Tensorflow Playlist App
"""

import sys
import os
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def reset_database():
    """Reset the database"""
    try:
        from playlist_app.models.database import Base, engine, create_tables
        
        print("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("Recreating database tables...")
        create_tables()
        
        print("Database reset completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Essentia-Tensorflow Playlist App CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Database reset command
    reset_parser = subparsers.add_parser("reset-db", help="Reset database")
    reset_parser.add_argument("--confirm", action="store_true", help="Confirm reset")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "reset-db":
        if not args.confirm:
            print("WARNING: This will permanently delete all database data!")
            response = input("Are you sure? (yes/no): ")
            if response.lower() not in ['yes', 'y']:
                print("Database reset cancelled.")
                return
        
        success = reset_database()
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

