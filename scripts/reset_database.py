#!/usr/bin/env python3
"""
Database reset script for development environment.

This script completely resets the database by dropping and recreating all tables.
Only run this in development environment where data can be safely lost.
"""

import sys
import os
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.playlist_app.models.database import create_engine, Base, get_db_session, close_db_session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if we're in a safe environment to run reset"""
    
    # Check environment variables
    env = os.getenv('ENVIRONMENT', 'development').lower()
    if env not in ['development', 'dev', 'local']:
        logger.error(f"Environment is {env}, but reset should only run in development!")
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

def reset_database():
    """Completely reset the database"""
    
    logger.info("Starting complete database reset...")
    
    try:
        # Create engine
        engine = create_engine()
        
        # Kill all active connections to the database
        logger.info("Killing active database connections...")
        try:
            with engine.connect() as conn:
                # Terminate all connections except our own
                conn.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();")
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not kill connections: {e}")
        
        # Drop all tables
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(engine)
        logger.info("All tables dropped successfully")
        
        # Recreate all tables
        logger.info("Recreating all tables...")
        Base.metadata.create_all(engine)
        logger.info("All tables recreated successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Database reset failed: {e}")
        return False

def verify_database():
    """Verify that database was reset correctly"""
    
    logger.info("Verifying database reset...")
    
    try:
        db = get_db_session()
        
        # Check if tables exist and are empty
        from sqlalchemy import text
        
        # Check files table
        result = db.execute(text("SELECT COUNT(*) FROM files"))
        file_count = result.scalar()
        logger.info(f"Files table: {file_count} records")
        
        # Check audio_analysis table
        result = db.execute(text("SELECT COUNT(*) FROM audio_analysis"))
        analysis_count = result.scalar()
        logger.info(f"Audio analysis table: {analysis_count} records")
        
        # Check audio_metadata table
        result = db.execute(text("SELECT COUNT(*) FROM audio_metadata"))
        metadata_count = result.scalar()
        logger.info(f"Audio metadata table: {metadata_count} records")
        
        # Check vector_index table
        result = db.execute(text("SELECT COUNT(*) FROM vector_index"))
        vector_count = result.scalar()
        logger.info(f"Vector index table: {vector_count} records")
        
        # Check discovery_cache table
        result = db.execute(text("SELECT COUNT(*) FROM discovery_cache"))
        cache_count = result.scalar()
        logger.info(f"Discovery cache table: {cache_count} records")
        
        if all(count == 0 for count in [file_count, analysis_count, metadata_count, vector_count, cache_count]):
            logger.info("✅ Database reset verified - all tables are empty")
            return True
        else:
            logger.warning("⚠️  Some tables still contain data")
            return False
        
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        return False
        
    finally:
        close_db_session(db)

def main():
    """Main reset function"""
    
    print("Database Reset")
    print("=" * 20)
    print("⚠️  WARNING: This will completely reset the database!")
    print("   All data will be permanently lost!")
    print("   Only run this in development environment!")
    print()
    
    # Check environment
    if not check_environment():
        print("❌ Environment check failed. Exiting.")
        sys.exit(1)
    
    # Final confirmation
    print("This will:")
    print("- Drop all existing tables")
    print("- Recreate all tables with clean schema")
    print("- Remove all data permanently")
    print()
    
    response = input("Are you absolutely sure you want to reset the database? (yes/no): ")
    if response.lower() != 'yes':
        print("Database reset cancelled.")
        sys.exit(0)
    
    print()
    
    # Run reset
    if reset_database():
        print("✅ Database reset completed!")
        
        # Verify reset
        if verify_database():
            print("✅ Database verification passed!")
            
            print("\nReset Summary:")
            print("- All tables dropped and recreated")
            print("- Database schema is clean and up-to-date")
            print("- No legacy fields present")
            print("- Ready for fresh development")
            
        else:
            print("⚠️  Database verification failed!")
            sys.exit(1)
        
    else:
        print("❌ Database reset failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()



