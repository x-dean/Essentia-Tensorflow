#!/usr/bin/env python3
"""
Database Management CLI for Essentia-Tensorflow Playlist App

This script provides command-line tools for managing the database,
including resetting and recreating tables.
"""

import argparse
import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playlist_app.models.database import Base, engine, create_tables, SessionLocal
from playlist_app.core.logging import get_logger

logger = get_logger(__name__)

def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")

def parse_database_url(database_url):
    """Parse database URL to extract connection details"""
    from urllib.parse import urlparse
    parsed = urlparse(database_url)
    
    return {
        "hostname": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "username": parsed.username or "playlist_user",
        "password": parsed.password or "playlist_password",
        "database": parsed.path[1:] if parsed.path else "playlist_db"
    }

def create_backup(backup_dir="database/backups"):
    """Create a database backup using pg_dump"""
    try:
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/backup_{timestamp}.sql"
        
        # Get database connection details
        database_url = get_database_url()
        db_info = parse_database_url(database_url)
        
        # Create backup command
        backup_cmd = [
            "pg_dump",
            "-h", db_info["hostname"],
            "-p", str(db_info["port"]),
            "-U", db_info["username"],
            "-d", db_info["database"],
            "-f", backup_file
        ]
        
        # Set password environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = db_info["password"]
        
        print(f"Creating database backup: {backup_file}")
        
        # Execute backup
        result = subprocess.run(backup_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            backup_size = os.path.getsize(backup_file) if os.path.exists(backup_file) else 0
            print(f"Backup created successfully: {backup_file} ({backup_size} bytes)")
            return {
                "backup_file": backup_file,
                "backup_size": backup_size,
                "timestamp": timestamp,
                "success": True
            }
        else:
            print(f"Backup failed: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr
            }
            
    except Exception as e:
        print(f"Failed to create backup: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def restore_backup(backup_file):
    """Restore database from backup file"""
    try:
        if not os.path.exists(backup_file):
            print(f"Backup file not found: {backup_file}")
            return False
        
        # Get database connection details
        database_url = get_database_url()
        db_info = parse_database_url(database_url)
        
        # Create restore command
        restore_cmd = [
            "psql",
            "-h", db_info["hostname"],
            "-p", str(db_info["port"]),
            "-U", db_info["username"],
            "-d", db_info["database"],
            "-f", backup_file
        ]
        
        # Set password environment variable
        env = os.environ.copy()
        env["PGPASSWORD"] = db_info["password"]
        
        print(f"Restoring database from backup: {backup_file}")
        
        # Execute restore
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Database restored successfully")
            return True
        else:
            print(f"Restore failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Failed to restore backup: {e}")
        return False

def get_database_status():
    """Get current database status and table information"""
    try:
        # Get table information
        inspector = engine.dialect.inspector(engine)
        tables = inspector.get_table_names()
        
        table_info = {}
        total_records = 0
        
        db = SessionLocal()
        try:
            for table_name in tables:
                try:
                    record_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").scalar()
                    table_info[table_name] = {
                        "record_count": record_count,
                        "exists": True
                    }
                    total_records += record_count
                except Exception as e:
                    table_info[table_name] = {
                        "record_count": 0,
                        "exists": False,
                        "error": str(e)
                    }
        finally:
            db.close()
        
        # Check if tables exist
        expected_tables = [
            "files", "discovery_cache", "audio_metadata", 
            "audio_analysis", "vector_index", "faiss_index_metadata"
        ]
        
        missing_tables = [table for table in expected_tables if table not in tables]
        
        return {
            "database_status": "connected",
            "total_tables": len(tables),
            "expected_tables": expected_tables,
            "missing_tables": missing_tables,
            "total_records": total_records,
            "table_info": table_info,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "database_status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def reset_database(confirm=False, recreate_tables=True, backup_first=True):
    """Reset and recreate the database"""
    try:
        if not confirm:
            print("ERROR: Database reset requires explicit confirmation.")
            print("Use --confirm flag to proceed with the reset.")
            return False
        
        print("WARNING: This will permanently delete all database data!")
        print("Proceeding with database reset...")
        
        # Create backup if requested
        backup_info = None
        if backup_first:
            print("Creating backup before reset...")
            backup_info = create_backup()
            if not backup_info["success"]:
                print("Warning: Backup failed, but continuing with reset...")
        
        # Drop all tables
        print("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped successfully")
        
        # Recreate tables if requested
        if recreate_tables:
            print("Recreating database tables...")
            create_tables()
            print("Database tables recreated successfully")
        
        print("Database reset completed successfully!")
        
        if backup_info and backup_info["success"]:
            print(f"Backup available at: {backup_info['backup_file']}")
        
        return True
        
    except Exception as e:
        print(f"Error resetting database: {e}")
        return False

def list_backups(backup_dir="database/backups"):
    """List available database backups"""
    try:
        if not os.path.exists(backup_dir):
            print(f"Backup directory not found: {backup_dir}")
            return
        
        backup_files = []
        for file in os.listdir(backup_dir):
            if file.endswith('.sql'):
                file_path = os.path.join(backup_dir, file)
                file_stat = os.stat(file_path)
                backup_files.append({
                    "filename": file,
                    "path": file_path,
                    "size": file_stat.st_size,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
        
        if not backup_files:
            print("No backup files found")
            return
        
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x["modified"], reverse=True)
        
        print(f"Available backups in {backup_dir}:")
        print("-" * 80)
        for backup in backup_files:
            size_mb = backup["size"] / (1024 * 1024)
            print(f"{backup['filename']:<30} {size_mb:.2f} MB  {backup['modified']}")
        
    except Exception as e:
        print(f"Error listing backups: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Database Management CLI for Essentia-Tensorflow Playlist App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/database_cli.py status                    # Check database status
  python scripts/database_cli.py reset --confirm          # Reset database (with confirmation)
  python scripts/database_cli.py backup                   # Create backup
  python scripts/database_cli.py restore backup_file.sql  # Restore from backup
  python scripts/database_cli.py list-backups             # List available backups
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get database status")
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset and recreate database")
    reset_parser.add_argument("--confirm", action="store_true", 
                            help="Confirm database reset (required)")
    reset_parser.add_argument("--no-recreate", action="store_true",
                            help="Don't recreate tables after dropping")
    reset_parser.add_argument("--no-backup", action="store_true",
                            help="Don't create backup before reset")
    
    # Backup command
    backup_parser = subparsers.add_parser("backup", help="Create database backup")
    backup_parser.add_argument("--dir", default="database/backups",
                              help="Backup directory (default: database/backups)")
    
    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup")
    restore_parser.add_argument("backup_file", help="Path to backup file")
    
    # List backups command
    list_parser = subparsers.add_parser("list-backups", help="List available backups")
    list_parser.add_argument("--dir", default="database/backups",
                            help="Backup directory (default: database/backups)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "status":
            status = get_database_status()
            print(json.dumps(status, indent=2))
            
        elif args.command == "reset":
            recreate_tables = not args.no_recreate
            backup_first = not args.no_backup
            success = reset_database(
                confirm=args.confirm,
                recreate_tables=recreate_tables,
                backup_first=backup_first
            )
            sys.exit(0 if success else 1)
            
        elif args.command == "backup":
            backup_info = create_backup(args.dir)
            if not backup_info["success"]:
                sys.exit(1)
                
        elif args.command == "restore":
            success = restore_backup(args.backup_file)
            sys.exit(0 if success else 1)
            
        elif args.command == "list-backups":
            list_backups(args.dir)
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

