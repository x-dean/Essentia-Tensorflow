#!/usr/bin/env python3
"""
Database schema cleanup script for development environment.

This script removes legacy analysis fields from the database schema.
Only run this in development environment where data can be safely reset.
"""

import sys
import os
import logging
from sqlalchemy import text, inspect

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.playlist_app.models.database import create_engine, get_db_session, close_db_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if we're in a safe environment to run cleanup"""
    
    # Check environment variables
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env not in ['development', 'dev', 'local']:
        logger.error(f"Environment is {env}, but cleanup should only run in development!")
        logger.error("Set ENVIRONMENT=development to proceed")
        return False
    
    # Check database URL for safety
    db_url = os.getenv('DATABASE_URL', '')
    if 'localhost' not in db_url and '127.0.0.1' not in db_url:
        logger.warning(f"Database URL doesn't look like localhost: {db_url}")
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != 'yes':
            return False
    
    return True

def cleanup_legacy_fields():
    """Remove legacy analysis fields from database schema"""
    
    logger.info("Starting database schema cleanup...")
    
    try:
        # Get database session
        db = get_db_session()
        
        # Check if legacy fields exist
        inspector = inspect(db.bind)
        columns = [col['name'] for col in inspector.get_columns('files')]
        
        legacy_fields = ['is_analyzed', 'has_audio_analysis']
        existing_legacy_fields = [field for field in legacy_fields if field in columns]
        
        if not existing_legacy_fields:
            logger.info("No legacy fields found to remove")
            return True
        
        logger.info(f"Found legacy fields to remove: {existing_legacy_fields}")
        
        # Remove each legacy field
        for field in existing_legacy_fields:
            try:
                logger.info(f"Removing column: {field}")
                db.execute(text(f"ALTER TABLE files DROP COLUMN {field}"))
                logger.info(f"Successfully removed column: {field}")
            except Exception as e:
                logger.error(f"Failed to remove column {field}: {e}")
                return False
        
        # Commit changes
        db.commit()
        
        # Verify removal
        inspector = inspect(db.bind)
        columns_after = [col['name'] for col in inspector.get_columns('files')]
        remaining_legacy = [field for field in legacy_fields if field in columns_after]
        
        if remaining_legacy:
            logger.error(f"Some legacy fields still exist: {remaining_legacy}")
            return False
        
        logger.info("Database schema cleanup completed successfully!")
        logger.info("Legacy fields removed:")
        for field in existing_legacy_fields:
            logger.info(f"  - {field}")
        
        return True
        
    except Exception as e:
        logger.error(f"Database cleanup failed: {e}")
        return False
        
    finally:
        close_db_session(db)

def reset_analysis_status():
    """Reset analysis status for all files to ensure clean state"""
    
    logger.info("Resetting analysis status for all files...")
    
    try:
        db = get_db_session()
        
        # Reset all files to pending status
        result = db.execute(text("UPDATE files SET analysis_status = 'pending'"))
        updated_count = result.rowcount
        
        # Reset boolean fields
        db.execute(text("UPDATE files SET essentia_analyzed = false, tensorflow_analyzed = false"))
        
        db.commit()
        
        logger.info(f"Reset analysis status for {updated_count} files")
        return True
        
    except Exception as e:
        logger.error(f"Failed to reset analysis status: {e}")
        return False
        
    finally:
        close_db_session(db)

def show_current_schema():
    """Show current database schema"""
    
    logger.info("Current database schema:")
    
    try:
        db = get_db_session()
        inspector = inspect(db.bind)
        
        # Show files table structure
        columns = inspector.get_columns('files')
        logger.info("Files table columns:")
        for col in columns:
            logger.info(f"  - {col['name']}: {col['type']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to show schema: {e}")
        return False
        
    finally:
        close_db_session(db)

def main():
    """Main cleanup function"""
    
    print("Database Schema Cleanup")
    print("=" * 30)
    print("⚠️  WARNING: This will permanently remove legacy database fields!")
    print("   Only run this in development environment!")
    print()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed. Exiting.")
        sys.exit(1)
    
    # Show current schema
    print("Current database schema:")
    show_current_schema()
    print()
    
    # Confirm cleanup
    response = input("Do you want to proceed with cleanup? (yes/no): ")
    if response.lower() != 'yes':
        print("Cleanup cancelled.")
        sys.exit(0)
    
    print()
    
    # Run cleanup
    if cleanup_legacy_fields():
        print("✅ Database schema cleanup completed!")
        
        # Reset analysis status
        if reset_analysis_status():
            print("✅ Analysis status reset completed!")
        
        print()
        print("Updated database schema:")
        show_current_schema()
        
        print("\nCleanup Summary:")
        print("- Removed legacy fields: is_analyzed, has_audio_analysis")
        print("- Reset all files to analysis_status = 'pending'")
        print("- Database is now ready for the simplified analysis system")
        
    else:
        print("❌ Database cleanup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
