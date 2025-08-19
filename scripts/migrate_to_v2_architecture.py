#!/usr/bin/env python3
"""
Migration script to implement the new database architecture v2
This script creates all new tables and adds enhanced fields to existing tables
"""

import sys
import os
import logging
from datetime import datetime
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from playlist_app.models.database_v2 import (
    Base, engine, SessionLocal,
    Playlist, PlaylistTrack, PlaylistTemplate, GeneratedPlaylist, 
    TrackSimilarityCache, PlaylistRecommendation, UIState, AppPreference
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_new_tables():
    """Create all new tables from the v2 architecture"""
    logger.info("Creating new tables...")
    
    try:
        # Create all tables defined in the v2 models
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All new tables created successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error creating tables: {e}")
        return False

def add_enhanced_fields_to_existing_tables():
    """Add enhanced control fields to existing tables"""
    logger.info("Adding enhanced fields to existing tables...")
    
    db = SessionLocal()
    try:
        # Add fields to files table
        alter_queries = [
            # Playlist generation fields for files table
            "ALTER TABLE files ADD COLUMN IF NOT EXISTS is_favorite BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE files ADD COLUMN IF NOT EXISTS rating INTEGER;",
            "ALTER TABLE files ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';",
            "ALTER TABLE files ADD COLUMN IF NOT EXISTS notes TEXT;",
            "ALTER TABLE files ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE files ADD COLUMN IF NOT EXISTS custom_metadata JSONB DEFAULT '{}';",
            
            # Quality control fields for track_analysis_summary table
            "ALTER TABLE track_analysis_summary ADD COLUMN IF NOT EXISTS analysis_quality_score FLOAT;",
            "ALTER TABLE track_analysis_summary ADD COLUMN IF NOT EXISTS confidence_threshold FLOAT DEFAULT 0.7;",
            "ALTER TABLE track_analysis_summary ADD COLUMN IF NOT EXISTS manual_override BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE track_analysis_summary ADD COLUMN IF NOT EXISTS override_reason TEXT;",
        ]
        
        for query in alter_queries:
            try:
                db.execute(text(query))
                logger.info(f"✅ Executed: {query[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️  Query failed (may already exist): {query[:50]}... - {e}")
        
        db.commit()
        logger.info("✅ Enhanced fields added successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding enhanced fields: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_indexes():
    """Create performance indexes for the new architecture"""
    logger.info("Creating performance indexes...")
    
    db = SessionLocal()
    try:
        index_queries = [
            # Playlist generation indexes
            "CREATE INDEX IF NOT EXISTS idx_playlists_public ON playlists(is_public) WHERE is_public = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist_position ON playlist_tracks(playlist_id, position);",
            "CREATE INDEX IF NOT EXISTS idx_playlist_tracks_file_id ON playlist_tracks(file_id);",
            
            # Analysis indexes for playlist generation
            "CREATE INDEX IF NOT EXISTS idx_files_favorite ON files(is_favorite) WHERE is_favorite = TRUE;",
            "CREATE INDEX IF NOT EXISTS idx_files_rating ON files(rating) WHERE rating IS NOT NULL;",
            
            # Similarity and recommendations indexes
            "CREATE INDEX IF NOT EXISTS idx_track_similarity_source ON track_similarity_cache(source_file_id, similarity_score);",
            "CREATE INDEX IF NOT EXISTS idx_track_similarity_target ON track_similarity_cache(target_file_id, similarity_score);",
            "CREATE INDEX IF NOT EXISTS idx_playlist_recommendations_playlist ON playlist_recommendations(playlist_id, recommendation_score);",
        ]
        
        for query in index_queries:
            try:
                db.execute(text(query))
                logger.info(f"✅ Created index: {query[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️  Index creation failed (may already exist): {query[:50]}... - {e}")
        
        db.commit()
        logger.info("✅ Performance indexes created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating indexes: {e}")
        db.rollback()
        return False
    finally:
        db.close()



def create_system_playlist_templates():
    """Create default system playlist templates"""
    logger.info("Creating system playlist templates...")
    
    db = SessionLocal()
    try:
        # Check if templates already exist
        existing_templates = db.query(PlaylistTemplate).filter(PlaylistTemplate.is_system_template == True).count()
        if existing_templates > 0:
            logger.info("✅ System templates already exist")
            return True
        

        
        templates = [
            {
                "name": "High Energy Workout",
                "description": "High BPM tracks perfect for intense workouts",
                "template_type": "energy",
                "parameters": {
                    "min_bpm": 140,
                    "max_bpm": 200,
                    "energy_threshold": 0.8,
                    "target_duration": 3600  # 1 hour
                }
            },
            {
                "name": "Chill Evening",
                "description": "Relaxing tracks for evening wind-down",
                "template_type": "mood",
                "parameters": {
                    "mood": "calm",
                    "max_bpm": 90,
                    "energy_threshold": 0.3,
                    "target_duration": 1800  # 30 minutes
                }
            },
            {
                "name": "Party Mix",
                "description": "Danceable tracks for parties and celebrations",
                "template_type": "energy",
                "parameters": {
                    "min_bpm": 120,
                    "max_bpm": 140,
                    "danceability_threshold": 0.7,
                    "target_duration": 3600  # 1 hour
                }
            },
            {
                "name": "Focus Study",
                "description": "Instrumental tracks for concentration and study",
                "template_type": "custom",
                "parameters": {
                    "instrumental_only": True,
                    "max_vocal_presence": 0.1,
                    "energy_range": [0.2, 0.6],
                    "target_duration": 2700  # 45 minutes
                }
            }
        ]
        
        for template_data in templates:
            template = PlaylistTemplate(
                name=template_data["name"],
                description=template_data["description"],
                template_type=template_data["template_type"],
                parameters=template_data["parameters"],
                is_system_template=True,
                is_active=True
            )
            db.add(template)
        
        db.commit()
        logger.info(f"✅ Created {len(templates)} system playlist templates")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating system templates: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_migration():
    """Verify that all tables and fields were created correctly"""
    logger.info("Verifying migration...")
    
    db = SessionLocal()
    try:
        # Check if all new tables exist
        new_tables = [
            "playlists", "playlist_tracks", "playlist_templates", "generated_playlists",
            "track_similarity_cache", "playlist_recommendations", 
            "ui_state", "app_preferences"
        ]
        
        for table_name in new_tables:
            result = db.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"))
            exists = result.scalar()
            if exists:
                logger.info(f"✅ Table '{table_name}' exists")
            else:
                logger.error(f"❌ Table '{table_name}' missing")
                return False
        
        # Check if playlist generation fields were added
        enhanced_fields = [
            ("files", "is_favorite"),
            ("files", "rating"),
            ("track_analysis_summary", "analysis_quality_score"),
            ("track_analysis_summary", "manual_override")
        ]
        
        for table_name, column_name in enhanced_fields:
            result = db.execute(text(f"SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = '{table_name}' AND column_name = '{column_name}')"))
            exists = result.scalar()
            if exists:
                logger.info(f"✅ Field '{table_name}.{column_name}' exists")
            else:
                logger.error(f"❌ Field '{table_name}.{column_name}' missing")
                return False
        
        logger.info("✅ Migration verification completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error during verification: {e}")
        return False
    finally:
        db.close()

def main():
    """Main migration function"""
    logger.info("🚀 Starting database migration to v2 architecture...")
    
    # Step 1: Create new tables
    if not create_new_tables():
        logger.error("❌ Failed to create new tables")
        return False
    
    # Step 2: Add enhanced fields to existing tables
    if not add_enhanced_fields_to_existing_tables():
        logger.error("❌ Failed to add enhanced fields")
        return False
    
    # Step 3: Create performance indexes
    if not create_indexes():
        logger.error("❌ Failed to create indexes")
        return False
    

    
    # Step 4: Create system playlist templates
    if not create_system_playlist_templates():
        logger.error("❌ Failed to create system templates")
        return False
    
    # Step 5: Verify migration
    if not verify_migration():
        logger.error("❌ Migration verification failed")
        return False
    
    logger.info("🎉 Database migration to v2 architecture completed successfully!")
    logger.info("📋 Next steps:")
    logger.info("   1. Update your application to use the new database models")
    logger.info("   2. Implement the new API endpoints")
    logger.info("   3. Update the web UI to use the new features")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
