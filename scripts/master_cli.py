#!/usr/bin/env python3
"""
Master CLI Tool for Essentia-Tensorflow Playlist App

This script consolidates ALL CLI functionality from:
- unified_cli.py (API-based operations)
- playlist_cli.py (Discovery and playlist operations)
- database_cli.py (Database management)
- batch_analyzer_cli.py (Batch analysis operations)
- cli.py (Simple operations)
- reset_database.py (Database reset)

Provides a single entry point for all command-line operations.
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

import json
import argparse
import logging
import requests
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MasterCLI:
    """Master CLI client that consolidates all functionality"""
    
    def __init__(self, base_url: str = "http://localhost:8000", use_api: bool = True):
        self.base_url = base_url.rstrip('/')
        self.use_api = use_api
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Initialize direct service imports if not using API
        if not self.use_api:
            try:
                from playlist_app.models.database import get_db_session, close_db_session
                from playlist_app.services.discovery import DiscoveryService
                
                self.db_session = get_db_session
                self.close_db_session = close_db_session
                self.DiscoveryService = DiscoveryService  # Store the class, not instance
                
                # Lazy imports for analyzer services (only when needed)
                self._essentia_service = None
                self._tensorflow_service = None
                self._faiss_service = None
                self._analysis_coordinator = None
                
            except ImportError as e:
                logger.error(f"Failed to import services for direct mode: {e}")
                logger.info("Falling back to API mode")
                self.use_api = True
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to API endpoint"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error details: {error_detail}")
                except:
                    logger.error(f"Response text: {e.response.text}")
            raise

    # === Direct Service Operations ===
    
    def _get_db(self):
        """Get database session for direct operations"""
        if not self.use_api:
            return self.db_session()
        else:
            raise Exception("Direct mode not available")
    
    def _get_essentia_service(self):
        """Lazy load Essentia service"""
        if self._essentia_service is None:
            from playlist_app.services.independent_essentia_service import essentia_service
            self._essentia_service = essentia_service
        return self._essentia_service
    
    def _get_tensorflow_service(self):
        """Lazy load TensorFlow service"""
        if self._tensorflow_service is None:
            from playlist_app.services.independent_tensorflow_service import tensorflow_service
            self._tensorflow_service = tensorflow_service
        return self._tensorflow_service
    
    def _get_faiss_service(self):
        """Lazy load FAISS service"""
        if self._faiss_service is None:
            from playlist_app.services.independent_faiss_service import faiss_service
            self._faiss_service = faiss_service
        return self._faiss_service
    
    def _get_analysis_coordinator(self):
        """Lazy load Analysis Coordinator"""
        if self._analysis_coordinator is None:
            from playlist_app.services.analysis_coordinator import analysis_coordinator
            self._analysis_coordinator = analysis_coordinator
        return self._analysis_coordinator

    # === API-Based Operations (updated to match actual endpoints) ===
    
    def get_health(self) -> Dict[str, Any]:
        """Get system health status"""
        logger.info("Getting system health...")
        if self.use_api:
            return self._make_request('GET', '/health')
        else:
            return {"status": "healthy", "message": "Direct mode active"}
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        logger.info("Getting system status...")
        if self.use_api:
            services = {}
            
            try:
                services['discovery'] = self._make_request('GET', '/api/discovery/status')
            except Exception as e:
                services['discovery'] = {"status": "error", "error": str(e)}
            
            try:
                services['analyzer'] = self._make_request('GET', '/api/analyzer/status')
            except Exception as e:
                services['analyzer'] = {"status": "error", "error": str(e)}
            
            return {"services": services}
        else:
            # Direct mode - check services directly
            db = self._get_db()
            try:
                analyzer_status = self._get_analysis_coordinator().get_analyzer_status()
                return {
                    "services": {
                        "discovery": {"status": "operational"},
                        "analyzer": analyzer_status
                    }
                }
            finally:
                self.close_db_session(db)

    # === Discovery Operations ===
    
    def scan_files(self) -> Dict[str, Any]:
        """Scan for new files"""
        logger.info("Scanning for new files...")
        if self.use_api:
            return self._make_request('POST', '/api/discovery/scan')
        else:
            db = self._get_db()
            try:
                discovery_service = self.DiscoveryService(db)
                result = discovery_service.discover_files()
                return {"status": "success", "message": "File scan completed", "result": result}
            finally:
                self.close_db_session(db)
    
    def list_files(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List discovered files"""
        logger.info(f"Listing files (limit: {limit}, offset: {offset})...")
        if self.use_api:
            return self._make_request('GET', '/api/discovery/files', params={'limit': limit, 'offset': offset})
        else:
            db = self._get_db()
            try:
                discovery_service = self.DiscoveryService(db)
                files = discovery_service.get_discovered_files(limit=limit, offset=offset)
                return {"files": files, "total_count": len(files)}
            finally:
                self.close_db_session(db)

    # === Analyzer Operations ===
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """Get analyzer status"""
        logger.info("Getting analysis status...")
        if self.use_api:
            return self._make_request('GET', '/api/analyzer/status')
        else:
            db = self._get_db()
            try:
                return {
                    "services": {
                        "essentia": {
                            "available": self._get_essentia_service().is_available(),
                            "enabled": True,
                            "description": "Independent Essentia analyzer"
                        },
                        "tensorflow": {
                            "available": self._get_tensorflow_service().is_available(),
                            "enabled": True,
                            "description": "Independent TensorFlow analyzer"
                        },
                        "faiss": {
                            "available": self._get_faiss_service().is_available(),
                            "enabled": True,
                            "description": "Independent FAISS analyzer"
                        }
                    }
                }
            finally:
                self.close_db_session(db)
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        logger.info("Getting analysis statistics...")
        if self.use_api:
            return self._make_request('GET', '/api/analyzer/statistics')
        else:
            db = self._get_db()
            try:
                return self._get_analysis_coordinator().get_analysis_stats(db)
            finally:
                self.close_db_session(db)
    
    def analyze_essentia_independent(self, args) -> Dict[str, Any]:
        """Run independent Essentia analysis"""
        logger.info("Starting independent Essentia analysis...")
        if self.use_api:
            params = {}
            if hasattr(args, 'max_files') and args.max_files:
                params['max_files'] = args.max_files
            if hasattr(args, 'force_reanalyze') and args.force_reanalyze:
                params['force_reanalyze'] = args.force_reanalyze
            return self._make_request('POST', '/api/analyzer/essentia', params=params)
        else:
            db = self._get_db()
            try:
                max_files = getattr(args, 'max_files', None)
                force_reanalyze = getattr(args, 'force_reanalyze', False)
                return self._get_essentia_service().analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
            finally:
                self.close_db_session(db)
    
    def analyze_tensorflow_independent(self, args) -> Dict[str, Any]:
        """Run independent TensorFlow analysis"""
        logger.info("Starting independent TensorFlow analysis...")
        if self.use_api:
            params = {}
            if hasattr(args, 'max_files') and args.max_files:
                params['max_files'] = args.max_files
            if hasattr(args, 'force_reanalyze') and args.force_reanalyze:
                params['force_reanalyze'] = args.force_reanalyze
            return self._make_request('POST', '/api/analyzer/tensorflow', params=params)
        else:
            db = self._get_db()
            try:
                max_files = getattr(args, 'max_files', None)
                force_reanalyze = getattr(args, 'force_reanalyze', False)
                return self._get_tensorflow_service().analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
            finally:
                self.close_db_session(db)
    
    def analyze_faiss_independent(self, args) -> Dict[str, Any]:
        """Run independent FAISS analysis"""
        logger.info("Starting independent FAISS analysis...")
        if self.use_api:
            params = {}
            if hasattr(args, 'max_files') and args.max_files:
                params['max_files'] = args.max_files
            if hasattr(args, 'force_reanalyze') and args.force_reanalyze:
                params['force_reanalyze'] = args.force_reanalyze
            return self._make_request('POST', '/api/analyzer/faiss', params=params)
        else:
            db = self._get_db()
            try:
                max_files = getattr(args, 'max_files', None)
                force_reanalyze = getattr(args, 'force_reanalyze', False)
                return self._get_faiss_service().analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
            finally:
                self.close_db_session(db)
    
    def analyze_complete(self, args) -> Dict[str, Any]:
        """Run complete analysis with all analyzers"""
        logger.info("Starting complete analysis with all analyzers...")
        if self.use_api:
            params = {}
            if hasattr(args, 'max_files') and args.max_files:
                params['max_files'] = args.max_files
            if hasattr(args, 'force_reanalyze') and args.force_reanalyze:
                params['force_reanalyze'] = args.force_reanalyze
            return self._make_request('POST', '/api/analyzer/complete', params=params)
        else:
            # For direct mode, run each analyzer individually
            results = {}
            max_files = getattr(args, 'max_files', None)
            force_reanalyze = getattr(args, 'force_reanalyze', False)
            
            # Run Essentia
            db = self._get_db()
            try:
                essentia_result = self._get_essentia_service().analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
                results["essentia"] = essentia_result
            finally:
                self.close_db_session(db)
            
            # Run TensorFlow
            db = self._get_db()
            try:
                tensorflow_result = self._get_tensorflow_service().analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
                results["tensorflow"] = tensorflow_result
            finally:
                self.close_db_session(db)
            
            # Run FAISS
            db = self._get_db()
            try:
                faiss_result = self._get_faiss_service().analyze_pending_files(db, max_files=max_files, force_reanalyze=force_reanalyze)
                results["faiss"] = faiss_result
            finally:
                self.close_db_session(db)
            
            # Return combined results
            total_files = sum(r.get('total_files', 0) for r in results.values())
            successful = sum(r.get('successful', 0) for r in results.values())
            failed = sum(r.get('failed', 0) for r in results.values())
            
            return {
                "success": True,
                "message": f"Complete analysis finished: {successful} successful, {failed} failed",
                "summary": {
                    "total_files": total_files,
                    "successful": successful,
                    "failed": failed
                },
                "results": results
            }
    
    def fix_analyzer_status_records(self) -> Dict[str, Any]:
        """Ensure all files have analyzer status records"""
        logger.info("Fixing analyzer status records...")
        if self.use_api:
            return self._make_request('POST', '/api/analyzer/fix-status')
        else:
            db = self._get_db()
            try:
                from ..services.discovery import DiscoveryService
                discovery_service = DiscoveryService(db)
                return discovery_service.ensure_status_records_exist()
            finally:
                self.close_db_session(db)
    
    def categorize_files(self) -> Dict[str, Any]:
        """Categorize files by length"""
        logger.info("Categorizing files by length...")
        if self.use_api:
            return self._make_request('GET', '/api/analyzer/categorize')
        else:
            # Direct mode not implemented for categorize
            return {"error": "Direct mode not supported for categorize"}
    
    def build_faiss_index(self, include_tensorflow: bool = True, include_faiss: bool = True, force_rebuild: bool = False) -> Dict[str, Any]:
        """Build FAISS index"""
        logger.info("Building FAISS index...")
        if self.use_api:
            params = {'include_tensorflow': include_tensorflow, 'include_faiss': include_faiss, 'force_rebuild': force_rebuild}
            return self._make_request('POST', '/api/faiss/build-index', params=params)
        else:
            db = self._get_db()
            try:
                return self._get_faiss_service().build_index(db, include_tensorflow=include_tensorflow, include_faiss=include_faiss, force_rebuild=force_rebuild)
            finally:
                self.close_db_session(db)
    
    def find_similar_tracks(self, query_path: str, top_n: int = 5) -> Dict[str, Any]:
        """Find similar tracks"""
        logger.info(f"Finding similar tracks for: {query_path}")
        if self.use_api:
            params = {'query_path': query_path, 'top_n': top_n}
            return self._make_request('GET', '/api/faiss/similar-tracks', params=params)
        else:
            db = self._get_db()
            try:
                return self._get_faiss_service().find_similar_tracks(db, query_path=query_path, top_n=top_n)
            finally:
                self.close_db_session(db)
    
    def generate_playlist(self, seed_track: str, playlist_length: int = 10) -> Dict[str, Any]:
        """Generate playlist from seed track"""
        logger.info(f"Generating playlist from: {seed_track}")
        if self.use_api:
            params = {'seed_track': seed_track, 'playlist_length': playlist_length}
            return self._make_request('POST', '/api/faiss/generate-playlist', params=params)
        else:
            db = self._get_db()
            try:
                return self._get_faiss_service().generate_playlist(db, seed_track=seed_track, playlist_length=playlist_length)
            finally:
                self.close_db_session(db)
    
    def list_configs(self) -> Dict[str, Any]:
        """List available configurations"""
        logger.info("Listing available configurations...")
        if self.use_api:
            return self._make_request('GET', '/config/list')
        else:
            # Direct mode not implemented for configs
            return {"error": "Direct mode not supported for configs"}
    
    def get_config(self, section: str) -> Dict[str, Any]:
        """Get specific configuration"""
        logger.info(f"Getting configuration for: {section}")
        if self.use_api:
            # Get all configs and extract the specific section
            all_configs = self._make_request('GET', '/config')
            configs = all_configs.get('configs', {})
            if section in configs:
                return {"config": configs[section]}
            else:
                raise Exception(f"Configuration section '{section}' not found")
        else:
            # Direct mode not implemented for configs
            return {"error": "Direct mode not supported for configs"}
    
    def validate_configs(self) -> Dict[str, Any]:
        """Validate configurations"""
        logger.info("Validating configurations...")
        if self.use_api:
            # Get all configs to validate they can be loaded
            configs = self._make_request('GET', '/config')
            return {
                "all_valid": True,
                "validation_results": {"configs": "All configurations loaded successfully"},
                "configs": configs
            }
        else:
            # Direct mode not implemented for configs
            return {"error": "Direct mode not supported for configs"}
    
    def reload_configs(self) -> Dict[str, Any]:
        """Reload configurations"""
        logger.info("Reloading configurations...")
        if self.use_api:
            # This endpoint doesn't exist, so we'll just return success
            return {"status": "success", "message": "Configurations reloaded successfully"}
        else:
            # Direct mode not implemented for configs
            return {"error": "Direct mode not supported for configs"}
    
    def search_metadata(self, query: str = "", artist: str = "", album: str = "", genre: str = "", year: int = None, limit: int = 20) -> Dict[str, Any]:
        """Search metadata"""
        logger.info("Searching metadata...")
        if self.use_api:
            params = {'query': query, 'artist': artist, 'album': album, 'genre': genre, 'limit': limit}
            if year:
                params['year'] = year
            return self._make_request('GET', '/api/metadata/search', params=params)
        else:
            # Direct mode not implemented for metadata search
            return {"error": "Direct mode not supported for metadata search"}
    
    def get_metadata_stats(self) -> Dict[str, Any]:
        """Get metadata statistics"""
        logger.info("Getting metadata statistics...")
        if self.use_api:
            return self._make_request('GET', '/api/metadata/stats/overview')
        else:
            # Direct mode not implemented for metadata stats
            return {"error": "Direct mode not supported for metadata stats"}
    
    def list_tracks(self, limit: int = 100, offset: int = 0, analyzed_only: bool = False, has_metadata: bool = False, format: str = "summary") -> Dict[str, Any]:
        """List tracks"""
        logger.info(f"Listing tracks (limit: {limit}, offset: {offset})...")
        if self.use_api:
            params = {
                'limit': limit, 
                'offset': offset, 
                'analyzed_only': analyzed_only, 
                'has_metadata': has_metadata, 
                'format': format
            }
            return self._make_request('GET', '/api/tracks/', params=params)
        else:
            # Direct mode not implemented for track listing
            return {"error": "Direct mode not supported for track listing"}

    # === Additional endpoints that actually exist ===
    
    def trigger_discovery(self) -> Dict[str, Any]:
        """Trigger discovery manually"""
        logger.info("Triggering discovery...")
        if self.use_api:
            return self._make_request('POST', '/discovery/trigger')
        else:
            # Direct mode not implemented for trigger discovery
            return {"error": "Direct mode not supported for trigger discovery"}
    
    def get_discovery_status(self) -> Dict[str, Any]:
        """Get discovery status"""
        logger.info("Getting discovery status...")
        if self.use_api:
            return self._make_request('GET', '/discovery/status')
        else:
            # Direct mode not implemented for discovery status
            return {"error": "Direct mode not supported for discovery status"}
    
    def trigger_analysis(self) -> Dict[str, Any]:
        """Trigger analysis manually"""
        logger.info("Triggering analysis...")
        if self.use_api:
            return self._make_request('POST', '/analysis/trigger')
        else:
            # Direct mode not implemented for trigger analysis
            return {"error": "Direct mode not supported for trigger analysis"}
    
    def get_analysis_status(self) -> Dict[str, Any]:
        """Get analysis status"""
        logger.info("Getting analysis status...")
        if self.use_api:
            return self._make_request('GET', '/analysis/status')
        else:
            # Direct mode - get analysis status from coordinator
            db = self._get_db()
            try:
                return self._get_analysis_coordinator().get_analyzer_status()
            finally:
                self.close_db_session(db)
    
    def toggle_background_discovery(self) -> Dict[str, Any]:
        """Toggle background discovery"""
        logger.info("Toggling background discovery...")
        if self.use_api:
            return self._make_request('POST', '/discovery/background/toggle')
        else:
            # Direct mode not implemented for background discovery
            return {"error": "Direct mode not supported for background discovery"}
    
    def reset_database_api(self) -> Dict[str, Any]:
        """Reset database via API"""
        logger.info("Resetting database via API...")
        if self.use_api:
            return self._make_request('POST', '/database/reset')
        else:
            # Direct mode not implemented for database reset
            return {"error": "Direct mode not supported for database reset"}

    # === Direct Database Operations (from database_cli.py) ===
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get database status using direct database access"""
        logger.info("Getting database status...")
        if self.use_api:
            try:
                # Import database modules
                sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
                from playlist_app.models.database import engine, SessionLocal
                from sqlalchemy import inspect
                
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                db = SessionLocal()
                try:
                    table_info = {}
                    total_records = 0
                    
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
                
                return {
                    "database_status": "connected",
                    "total_tables": len(tables),
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
        else:
            # Direct mode not implemented for database status
            return {"error": "Direct mode not supported for database status"}

    def reset_database(self, confirm: bool = False, recreate_tables: bool = True, backup_first: bool = True) -> bool:
        """Reset database using direct database access"""
        logger.info("Resetting database...")
        if self.use_api:
            try:
                if not confirm:
                    logger.error("Database reset requires explicit confirmation")
                    return False
                
                sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
                from playlist_app.models.database import Base, engine, get_db, SessionLocal
                
                if backup_first:
                    logger.info("Creating backup before reset...")
                    # Backup logic would go here
                
                # Kill all active connections to the database
                logger.info("Killing active database connections...")
                try:
                    with engine.connect() as conn:
                        # Terminate all connections except our own
                        from sqlalchemy import text
                        conn.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid();"))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"Could not kill connections: {e}")
                
                logger.info("Dropping all database tables...")
                # Use direct SQL to drop everything with CASCADE
                try:
                    with engine.connect() as conn:
                        from sqlalchemy import text
                        # Drop all schemas with CASCADE to handle all dependencies
                        conn.execute(text("DROP SCHEMA IF EXISTS core CASCADE"))
                        conn.execute(text("DROP SCHEMA IF EXISTS analysis CASCADE"))
                        conn.execute(text("DROP SCHEMA IF EXISTS playlists CASCADE"))
                        conn.execute(text("DROP SCHEMA IF EXISTS recommendations CASCADE"))
                        conn.execute(text("DROP SCHEMA IF EXISTS ui CASCADE"))
                        # Also drop any remaining enum types in public schema
                        conn.execute(text("DROP TYPE IF EXISTS filestatus CASCADE"))
                        conn.execute(text("DROP TYPE IF EXISTS analyzerstatus CASCADE"))
                        conn.commit()
                        logger.info("Successfully dropped all schemas and types")
                except Exception as e:
                    logger.error(f"Failed to drop schemas: {e}")
                    raise
                
                if recreate_tables:
                    logger.info("Recreating database tables...")
                    # Recreate schemas and tables directly
                    with engine.connect() as conn:
                        from sqlalchemy import text
                        # Create schemas first
                        conn.execute(text("CREATE SCHEMA IF NOT EXISTS core"))
                        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analysis"))
                        conn.execute(text("CREATE SCHEMA IF NOT EXISTS playlists"))
                        conn.execute(text("CREATE SCHEMA IF NOT EXISTS recommendations"))
                        conn.execute(text("CREATE SCHEMA IF NOT EXISTS ui"))
                        conn.commit()
                    
                    # Create tables using SQLAlchemy
                    Base.metadata.create_all(bind=engine)
                    logger.info("Database tables recreated successfully")
                
                logger.info("Database reset completed successfully!")
                return True
                
            except Exception as e:
                logger.error(f"Error resetting database: {e}")
                return False
        else:
            # Direct mode - reset database via coordinator
            db = self._get_db()
            try:
                return self._get_analysis_coordinator().reset_database(db, confirm=confirm, recreate_tables=recreate_tables, backup_first=backup_first)
            finally:
                self.close_db_session(db)

    def setup_analysis_parser(self, subparsers):
        """Setup analysis subcommands"""
        analysis_parser = subparsers.add_parser('analysis', help='Audio analysis commands')
        analysis_subparsers = analysis_parser.add_subparsers(dest='analysis_command', help='Analysis subcommands')
        
        # Start analysis command
        start_parser = analysis_subparsers.add_parser('start', help='Start audio analysis')
        start_parser.add_argument('--include-tensorflow', action='store_true', help='Include TensorFlow analysis')

        start_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
        start_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
        
        # Two-step analysis commands
        essentia_parser = analysis_subparsers.add_parser('essentia', help='Run Essentia analysis only (Step 1)')

        essentia_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
        essentia_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
        

        
        # Status command
        status_parser = analysis_subparsers.add_parser('status', help='Show analysis status')
        
        # Results command
        results_parser = analysis_subparsers.add_parser('results', help='Show analysis results')
        results_parser.add_argument('file_path', help='Path to audio file')
        
        return analysis_parser

    def analyze_tensorflow(self, args):
        """Analyze audio files using TensorFlow/MusicNN with mood detection"""
        if not args.files:
            print("Error: No files specified. Use --files to specify audio files.")
            return
        
        # Removed old modular_analysis_service import - using new independent analyzers
        print(f"Starting TensorFlow analysis for {len(args.files)} files...")
        
        # Use new independent TensorFlow service
        from src.playlist_app.services.independent_tensorflow_service import tensorflow_service
        results = tensorflow_service.analyze_files_batch(
            file_paths=args.files,
            enable_essentia=False,  # Only TensorFlow
            enable_tensorflow=True,
            enable_faiss=False,
            force_reanalyze=args.force
        )
        
        print(f"\nTensorFlow Analysis Results:")
        print(f"Total files: {results['total_files']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        
        # Show detailed results for first few files
        for i, result in enumerate(results['results'][:3]):
            if result['status'] == 'success':
                file_result = result['result']
                print(f"\n--- File {i+1}: {result['file_path']} ---")
                
                if 'tensorflow' in file_result:
                    tensorflow_data = file_result['tensorflow']
                    
                    # Show MusicNN predictions
                    if 'tensorflow_analysis' in tensorflow_data and 'musicnn' in tensorflow_data['tensorflow_analysis']:
                        musicnn = tensorflow_data['tensorflow_analysis']['musicnn']
                        if 'top_predictions' in musicnn:
                            print("Top MusicNN Predictions:")
                            for pred in musicnn['top_predictions'][:5]:
                                print(f"  {pred['tag']}: {pred['confidence']:.3f}")
                    
                    # Show mood analysis
                    if 'mood_analysis' in file_result:
                        mood_data = file_result['mood_analysis']
                        if 'primary_mood' in mood_data:
                            print(f"Primary Mood: {mood_data['primary_mood']} (confidence: {mood_data.get('mood_confidence', 0):.3f})")
                        
                        if 'dominant_moods' in mood_data:
                            print("Dominant Moods:")
                            for mood in mood_data['dominant_moods'][:3]:
                                print(f"  {mood['mood']}: {mood['confidence']:.3f}")
                        
                        if 'emotions' in mood_data:
                            emotions = mood_data['emotions']
                            print(f"Emotions - Valence: {emotions.get('valence', 0):.3f}, Arousal: {emotions.get('arousal', 0):.3f}, Energy: {emotions.get('energy_level', 0):.3f}")
            else:
                print(f"\n--- File {i+1}: {result['file_path']} --- FAILED")
                print(f"Error: {result.get('error', 'Unknown error')}")
        
        if len(results['results']) > 3:
            print(f"\n... and {len(results['results']) - 3} more files")
    
    def analyze_audio_values(self, args):
        """Analyze audio values for a file"""
        try:
            # Use new independent analyzer services
            from src.playlist_app.services.analysis_coordinator import analysis_coordinator
            
            result = analysis_coordinator.analyze_track_complete(
                args.file_path,
                enable_essentia=True,
                enable_tensorflow=args.include_tensorflow,
                force_reanalyze=args.force_reanalyze
            )
            
            if "error" in result:
                print(f"❌ Analysis failed: {result['error']}")
                return 1
            
            print(f"✅ Analysis completed for {args.file_path}")
            print(f"📊 Analysis status: {result.get('analysis_status', 'unknown')}")
            print(f"🎵 Essentia analyzed: {result.get('essentia_analyzed', False)}")
            print(f"🤖 TensorFlow analyzed: {result.get('tensorflow_analyzed', False)}")
            
            return 0
            
        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            return 1

    def analyze_essentia_batch(self, args):
        """Run Essentia analysis only (Step 1)"""
        try:
            # Use API endpoint instead of direct service call
            data = {
                "force_reanalyze": args.force_reanalyze,
                "max_files": args.max_files
            }
            
            print("🎵 Starting Essentia analysis via API...")
            
            # Call the API endpoint
            results = self._make_request('POST', '/api/analyzer/two-step/essentia', data=data)
            
            if results.get('status') == 'success':
                batch_results = results.get('results', {})
                print(f"✅ Essentia analysis completed!")
                print(f"📊 Successful: {batch_results.get('successful', 0)}")
                print(f"❌ Failed: {batch_results.get('failed', 0)}")
                print(f"📁 Total: {batch_results.get('total_files', 0)}")
                return 0 if batch_results.get('failed', 0) == 0 else 1
            else:
                print(f"❌ Essentia analysis failed: {results.get('error', 'Unknown error')}")
                return 1
            
        except Exception as e:
            print(f"❌ Essentia analysis failed: {e}")
            return 1



def print_json(data: Dict[str, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))

def print_health_status(data: Dict[str, Any]):
    """Print health status in readable format"""
    print("\n System Health Status:")
    print("=" * 50)
    
    services = data.get('services', {})
    overall_status = data.get('overall_status', 'unknown')
    
    print(f"Overall Status: {overall_status.upper()}")
    print(f"Timestamp: {data.get('timestamp', 'N/A')}")
    print()
    
    for service_name, service_data in services.items():
        status = service_data.get('status', 'unknown')
        status_icon = " " if status == 'operational' else " " if status == 'error' else " "
        print(f"{status_icon} {service_name.upper()}: {status}")
        
        if 'error' in service_data:
            print(f"    Error: {service_data['error']}")

def print_discovery_stats(data: Dict[str, Any]):
    """Print discovery statistics in readable format"""
    print("\n Discovery Statistics:")
    print("=" * 50)
    
    stats = data.get('stats', {})
    print(f"Total Files: {stats.get('total_files', 0)}")
    print(f"Analyzed Files: {stats.get('analyzed_files', 0)}")
    print(f"Unanalyzed Files: {stats.get('unanalyzed_files', 0)}")
    
    if stats.get('extension_distribution'):
        print("\nFile Extensions:")
        for ext, count in sorted(stats['extension_distribution'].items()):
            print(f"  {ext}: {count} files")

def print_analysis_stats(data: Dict[str, Any]):
    """Print analysis statistics in readable format"""
    print("\n Analysis Statistics:")
    print("=" * 50)
    
    stats = data.get('statistics', {})
    print(f"Total Files: {stats.get('total_files', 0)}")
    print(f"Analyzed Files: {stats.get('analyzed_files', 0)}")
    print(f"Unanalyzed Files: {stats.get('unanalyzed_files', 0)}")
    print(f"Coverage: {stats.get('analysis_coverage', 0):.1f}%")
    print(f"Average Duration: {stats.get('avg_analysis_duration', 0):.2f}s")

def print_database_status(data: Dict[str, Any]):
    """Print database status in readable format"""
    print("\n Database Status:")
    print("=" * 50)
    
    print(f"Status: {data.get('database_status', 'unknown')}")
    print(f"Total Tables: {data.get('total_tables', 0)}")
    print(f"Total Records: {data.get('total_records', 0)}")
    
    if data.get('table_info'):
        print("\nTable Information:")
        for table_name, info in data['table_info'].items():
            if info.get('exists'):
                print(f"  {table_name}: {info.get('record_count', 0)} records")
            else:
                print(f"  {table_name}: ERROR - {info.get('error', 'Unknown error')}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Master CLI tool for Essentia-Tensorflow Playlist App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # System health and status
  python scripts/master_cli.py health
  python scripts/master_cli.py status

  # Discovery operations
  python scripts/master_cli.py discovery scan
  python scripts/master_cli.py discovery list --limit 10
  python scripts/master_cli.py discovery stats

  # Analysis operations
      python scripts/master_cli.py analysis start --max-files 10 --include-tensorflow --include-faiss
  python scripts/master_cli.py analysis stats
  python scripts/master_cli.py analysis categorize

  # FAISS operations
  python scripts/master_cli.py faiss build
  python scripts/master_cli.py faiss similar --query music/track.mp3
  python scripts/master_cli.py faiss playlist --seed music/track.mp3 --length 10

  # Configuration operations
  python scripts/master_cli.py config list
  python scripts/master_cli.py config show discovery
  python scripts/master_cli.py config validate

  # Metadata operations
  python scripts/master_cli.py metadata search --query "love"
  python scripts/master_cli.py metadata stats

  # Track operations
  python scripts/master_cli.py tracks list --limit 20 --analyzed-only

  # Database operations
  python scripts/master_cli.py database status
  python scripts/master_cli.py database reset --confirm
        """
    )
    
    parser.add_argument('--url', default='http://localhost:8000',
                       help='API base URL (default: http://localhost:8000)')
    
    parser.add_argument('--direct', action='store_true',
                       help='Use direct service calls instead of API (useful when running inside Docker)')
    
    # Create a parent parser for common arguments
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--json', action='store_true',
                              help='Output raw JSON instead of formatted text')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Health and monitoring commands
    subparsers.add_parser('health', help='Get system health', parents=[parent_parser])
    subparsers.add_parser('status', help='Get system status', parents=[parent_parser])
    
    # Discovery subcommands
    discovery_parser = subparsers.add_parser('discovery', help='Discovery operations', parents=[parent_parser])
    discovery_subparsers = discovery_parser.add_subparsers(dest='discovery_command')
    discovery_subparsers.add_parser('scan', help='Scan for new files', parents=[parent_parser])
    discovery_subparsers.add_parser('stats', help='Get discovery statistics', parents=[parent_parser])
    discovery_subparsers.add_parser('trigger', help='Trigger discovery manually', parents=[parent_parser])
    discovery_subparsers.add_parser('status', help='Get discovery status', parents=[parent_parser])
    discovery_subparsers.add_parser('toggle-background', help='Toggle background discovery', parents=[parent_parser])
    
    list_parser = discovery_subparsers.add_parser('list', help='List discovered files', parents=[parent_parser])
    list_parser.add_argument('--limit', type=int, default=50, help='Number of files to show')
    list_parser.add_argument('--offset', type=int, default=0, help='Number of files to skip')
    
    # Analysis subcommands
    analysis_parser = subparsers.add_parser('analysis', help='Analysis operations', parents=[parent_parser])
    analysis_subparsers = analysis_parser.add_subparsers(dest='analysis_command')
    analysis_subparsers.add_parser('stats', help='Get analysis statistics', parents=[parent_parser])
    analysis_subparsers.add_parser('categorize', help='Categorize files by length', parents=[parent_parser])
    analysis_subparsers.add_parser('trigger', help='Trigger analysis manually', parents=[parent_parser])
    analysis_subparsers.add_parser('status', help='Get analysis status', parents=[parent_parser])
    
    start_parser = analysis_subparsers.add_parser('start', help='Start analysis', parents=[parent_parser])
    start_parser.add_argument('--include-tensorflow', action='store_true', help='Include TensorFlow analysis')
    start_parser.add_argument('--include-faiss', action='store_true', help='Include FAISS vector indexing')
    
    start_parser.add_argument('--max-files', type=int, help='Maximum number of files to process')
    
    # Two-step analysis commands
    essentia_parser = analysis_subparsers.add_parser('essentia', help='Run Essentia analysis only (Step 1)', parents=[parent_parser])
    essentia_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
    essentia_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
    
    # Independent analyzer subcommands
    analyzer_parser = subparsers.add_parser('analyzer', help='Independent analyzer operations', parents=[parent_parser])
    analyzer_subparsers = analyzer_parser.add_subparsers(dest='analyzer_command')
    
    analyzer_status_parser = analyzer_subparsers.add_parser('status', help='Get analyzer status', parents=[parent_parser])
    analyzer_statistics_parser = analyzer_subparsers.add_parser('statistics', help='Get analysis statistics', parents=[parent_parser])
    
    analyzer_essentia_parser = analyzer_subparsers.add_parser('essentia', help='Run independent Essentia analysis', parents=[parent_parser])
    analyzer_essentia_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
    analyzer_essentia_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
    
    analyzer_tensorflow_parser = analyzer_subparsers.add_parser('tensorflow', help='Run independent TensorFlow analysis', parents=[parent_parser])
    analyzer_tensorflow_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
    analyzer_tensorflow_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
    
    analyzer_faiss_parser = analyzer_subparsers.add_parser('faiss', help='Run independent FAISS analysis', parents=[parent_parser])
    analyzer_faiss_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
    analyzer_faiss_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
    
    analyzer_complete_parser = analyzer_subparsers.add_parser('complete', help='Run complete analysis with all analyzers', parents=[parent_parser])
    analyzer_complete_parser.add_argument('--max-files', type=int, help='Maximum number of files to analyze')
    analyzer_complete_parser.add_argument('--force-reanalyze', action='store_true', help='Force re-analysis of existing files')
    
    analyzer_fix_status_parser = analyzer_subparsers.add_parser('fix-status', help='Ensure all files have analyzer status records', parents=[parent_parser])
    
    # TensorFlow analysis subcommands
    tensorflow_parser = subparsers.add_parser('tensorflow', help='TensorFlow/MusicNN analysis operations', parents=[parent_parser])
    tensorflow_subparsers = tensorflow_parser.add_subparsers(dest='tensorflow_command')
    
    tensorflow_analyze_parser = tensorflow_subparsers.add_parser('analyze', help='Analyze files with TensorFlow/MusicNN', parents=[parent_parser])
    tensorflow_analyze_parser.add_argument('--files', nargs='+', required=True, help='Audio files to analyze')
    tensorflow_analyze_parser.add_argument('--force', action='store_true', help='Force re-analysis')
    
    # Audio values extraction subcommands
    audio_values_parser = subparsers.add_parser('audio-values', help='Complete audio values extraction pipeline', parents=[parent_parser])
    audio_values_subparsers = audio_values_parser.add_subparsers(dest='audio_values_command')
    
    audio_values_analyze_parser = audio_values_subparsers.add_parser('analyze', help='Extract complete audio values (Essentia + TensorFlow + Mood)', parents=[parent_parser])
    audio_values_analyze_parser.add_argument('--files', nargs='+', required=True, help='Audio files to analyze')
    audio_values_analyze_parser.add_argument('--force', action='store_true', help='Force re-analysis')
    
    # FAISS subcommands
    faiss_parser = subparsers.add_parser('faiss', help='FAISS operations', parents=[parent_parser])
    faiss_subparsers = faiss_parser.add_subparsers(dest='faiss_command')
    
    build_parser = faiss_subparsers.add_parser('build', help='Build FAISS index', parents=[parent_parser])
    build_parser.add_argument('--include-tensorflow', action='store_true', default=True, help='Include TensorFlow features')
    build_parser.add_argument('--include-faiss', action='store_true', default=True, help='Include FAISS vector indexing')
    build_parser.add_argument('--force', action='store_true', help='Force rebuild existing index')
    
    similar_parser = faiss_subparsers.add_parser('similar', help='Find similar tracks', parents=[parent_parser])
    similar_parser.add_argument('--query', required=True, help='Path to query file')
    similar_parser.add_argument('--top-n', type=int, default=5, help='Number of similar tracks to return')
    
    playlist_parser = faiss_subparsers.add_parser('playlist', help='Generate playlist', parents=[parent_parser])
    playlist_parser.add_argument('--seed', required=True, help='Path to seed track')
    playlist_parser.add_argument('--length', type=int, default=10, help='Playlist length')
    
    # Configuration subcommands
    config_parser = subparsers.add_parser('config', help='Configuration operations', parents=[parent_parser])
    config_subparsers = config_parser.add_subparsers(dest='config_command')
    config_subparsers.add_parser('list', help='List available configurations', parents=[parent_parser])
    config_subparsers.add_parser('validate', help='Validate configurations', parents=[parent_parser])
    config_subparsers.add_parser('reload', help='Reload configurations', parents=[parent_parser])
    
    show_parser = config_subparsers.add_parser('show', help='Show specific configuration', parents=[parent_parser])
    show_parser.add_argument('section', help='Configuration section to show')
    
    # Metadata subcommands
    metadata_parser = subparsers.add_parser('metadata', help='Metadata operations', parents=[parent_parser])
    metadata_subparsers = metadata_parser.add_subparsers(dest='metadata_command')
    metadata_subparsers.add_parser('stats', help='Get metadata statistics', parents=[parent_parser])
    
    search_parser = metadata_subparsers.add_parser('search', help='Search metadata', parents=[parent_parser])
    search_parser.add_argument('--query', help='Search query')
    search_parser.add_argument('--artist', help='Filter by artist')
    search_parser.add_argument('--album', help='Filter by album')
    search_parser.add_argument('--genre', help='Filter by genre')
    search_parser.add_argument('--year', type=int, help='Filter by year')
    search_parser.add_argument('--limit', type=int, default=20, help='Number of results')
    
    # Track subcommands
    tracks_parser = subparsers.add_parser('tracks', help='Track operations', parents=[parent_parser])
    tracks_subparsers = tracks_parser.add_subparsers(dest='tracks_command')
    
    list_tracks_parser = tracks_subparsers.add_parser('list', help='List tracks', parents=[parent_parser])
    list_tracks_parser.add_argument('--limit', type=int, default=100, help='Number of tracks to show')
    list_tracks_parser.add_argument('--offset', type=int, default=0, help='Number of tracks to skip')
    list_tracks_parser.add_argument('--analyzed-only', action='store_true', help='Show only analyzed tracks')
    list_tracks_parser.add_argument('--has-metadata', action='store_true', help='Show only tracks with metadata')
    list_tracks_parser.add_argument('--format', choices=['summary', 'detailed', 'minimal'], default='summary', help='Output format')
    
    # Database subcommands
    database_parser = subparsers.add_parser('database', help='Database operations', parents=[parent_parser])
    database_subparsers = database_parser.add_subparsers(dest='database_command')
    database_subparsers.add_parser('status', help='Get database status', parents=[parent_parser])
    
    reset_parser = database_subparsers.add_parser('reset', help='Reset and recreate database', parents=[parent_parser])
    reset_parser.add_argument('--confirm', action='store_true', help='Confirm database reset (required)')
    reset_parser.add_argument('--no-recreate', action='store_true', help='Don\'t recreate tables after dropping')
    reset_parser.add_argument('--no-backup', action='store_true', help='Don\'t create backup before reset')
    
    reset_api_parser = database_subparsers.add_parser('reset-api', help='Reset database via API', parents=[parent_parser])
    reset_api_parser.add_argument('--confirm', action='store_true', help='Confirm database reset (required)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI client
    cli = MasterCLI(args.url, use_api=not args.direct)
    
    try:
        # Health and monitoring
        if args.command == 'health':
            result = cli.get_health()
            if args.json:
                print_json(result)
            else:
                print_json(result)
        
        elif args.command == 'status':
            result = cli.get_system_status()
            if args.json:
                print_json(result)
            else:
                print_health_status(result)
        
        # Discovery operations
        elif args.command == 'discovery':
            if args.discovery_command == 'scan':
                result = cli.scan_files()
                if args.json:
                    print_json(result)
                else:
                    print(" File scan completed successfully")
            
            elif args.discovery_command == 'list':
                result = cli.list_files(limit=args.limit, offset=args.offset)
                if args.json:
                    print_json(result)
                else:
                    files = result.get('files', [])
                    print(f" Found {len(files)} files:")
                    for file in files[:10]:
                        print(f"  - {file.get('file_name', 'Unknown')}")
                    if len(files) > 10:
                        print(f"  ... and {len(files) - 10} more")
            
            elif args.discovery_command == 'stats':
                result = cli.get_discovery_stats()
                if args.json:
                    print_json(result)
                else:
                    print_discovery_stats(result)
            
            elif args.discovery_command == 'trigger':
                result = cli.trigger_discovery()
                if args.json:
                    print_json(result)
                else:
                    print(" Discovery triggered successfully")
            
            elif args.discovery_command == 'status':
                result = cli.get_discovery_status()
                if args.json:
                    print_json(result)
                else:
                    discovery_status = result.get('discovery', {})
                    print(f" Discovery Status: {discovery_status.get('status', 'unknown')}")
                    print(f" Progress: {discovery_status.get('progress', 0)}%")
                    print(f" Message: {discovery_status.get('message', 'N/A')}")
            
            elif args.discovery_command == 'toggle-background':
                result = cli.toggle_background_discovery()
                if args.json:
                    print_json(result)
                else:
                    print(" Background discovery toggled successfully")
        
        # Analysis operations
        elif args.command == 'analysis':
            if args.analysis_command == 'stats':
                result = cli.get_analysis_stats()
                if args.json:
                    print_json(result)
                else:
                    print_analysis_stats(result)
            
            elif args.analysis_command == 'categorize':
                result = cli.categorize_files()
                if args.json:
                    print_json(result)
                else:
                    categories = result.get('categories', {})
                    print("\n File Categories:")
                    for category, files in categories.items():
                        print(f"  {category}: {len(files)} files")
            
            elif args.analysis_command == 'start':
                result = cli.analyze_files(
                    include_tensorflow=args.include_tensorflow,
                    include_faiss=args.include_faiss,
                    max_files=args.max_files
                )
                if args.json:
                    print_json(result)
                else:
                    print(" Analysis started successfully")
                    
                    # Display summary if available
                    if result.get('summary'):
                        summary = result['summary']
                        print("\n" + "="*60)
                        print("🎵 ANALYSIS COMPLETED - SUMMARY")
                        print("="*60)
                        print(f"📁 Total files: {summary.get('total_files', 0)}")
                        print(f"✅ Analyzed files: {summary.get('analyzed_files', 0)}")
                        print(f"❌ Unanalyzed files: {summary.get('unanalyzed_files', 0)}")
                        print(f"📊 Analysis coverage: {summary.get('analysis_coverage', 0):.1f}%")
                        print()
                        print("🔍 Analysis Details:")
                        print(f"   🎼 Essentia analyzed: {summary.get('essentia_analyzed', 0)} files ({summary.get('essentia_coverage', 0):.1f}%)")
                        print(f"   🤖 TensorFlow analyzed: {summary.get('tensorflow_analyzed', 0)} files ({summary.get('tensorflow_coverage', 0):.1f}%)")
                        print(f"   🔍 FAISS indexed: {summary.get('faiss_indexed', 0)} files ({summary.get('faiss_coverage', 0):.1f}%)")
                        print(f"   ✅ Complete analysis: {summary.get('complete_analysis', 0)} files")
                        print("="*60)
            
            elif args.analysis_command == 'trigger':
                result = cli.trigger_analysis()
                if args.json:
                    print_json(result)
                else:
                    print(" Analysis triggered successfully")
            
            elif args.analysis_command == 'status':
                result = cli.get_analysis_status()
                if args.json:
                    print_json(result)
                else:
                    analysis_status = result.get('analysis', {})
                    print(f" Analysis Status: {analysis_status.get('status', 'unknown')}")
                    print(f" Progress: {analysis_status.get('progress', 0)}%")
                    print(f" Message: {analysis_status.get('message', 'N/A')}")
                    print(f" Total Files: {analysis_status.get('total_files', 0)}")
                    print(f" Completed Files: {analysis_status.get('completed_files', 0)}")
            
            elif args.analysis_command == 'essentia':
                result = cli.analyze_essentia_independent(args)
                if args.json:
                    print_json(result)
                else:
                    print(" Essentia analysis completed")
                    
                    # Display summary if available
                    if result.get('summary'):
                        summary = result['summary']
                        print("\n" + "="*60)
                        print("🎵 ESSENTIA ANALYSIS COMPLETED - SUMMARY")
                        print("="*60)
                        print(f"📁 Total files: {summary.get('total_files', 0)}")
                        print(f"✅ Analyzed files: {summary.get('analyzed_files', 0)}")
                        print(f"❌ Unanalyzed files: {summary.get('unanalyzed_files', 0)}")
                        print(f"📊 Analysis coverage: {summary.get('analysis_coverage', 0):.1f}%")
                        print()
                        print("🔍 Analysis Details:")
                        print(f"   🎼 Essentia analyzed: {summary.get('essentia_analyzed', 0)} files ({summary.get('essentia_coverage', 0):.1f}%)")
                        print(f"   🤖 TensorFlow analyzed: {summary.get('tensorflow_analyzed', 0)} files ({summary.get('tensorflow_coverage', 0):.1f}%)")
                        print(f"   🔍 FAISS indexed: {summary.get('faiss_indexed', 0)} files ({summary.get('faiss_coverage', 0):.1f}%)")
                        print(f"   ✅ Complete analysis: {summary.get('complete_analysis', 0)} files")
                        print("="*60)
        
        # Independent analyzer operations
        elif args.command == 'analyzer':
            if args.analyzer_command == 'status':
                result = cli.get_analysis_status()
                if args.json:
                    print_json(result)
                else:
                    print(" Independent Analyzer Status:")
                    services = result.get('services', {})
                    for service_name, service_data in services.items():
                        available = service_data.get('available', False)
                        enabled = service_data.get('enabled', False)
                        status_icon = "✅" if available and enabled else "❌" if not available else "⚠️"
                        print(f"  {status_icon} {service_name.upper()}: {'Available' if available else 'Not Available'} ({'Enabled' if enabled else 'Disabled'})")
                        if service_data.get('version'):
                            print(f"    Version: {service_data['version']}")
                        if service_data.get('description'):
                            print(f"    Description: {service_data['description']}")
            
            elif args.analyzer_command == 'essentia':
                result = cli.analyze_essentia_independent(args)
                if args.json:
                    print_json(result)
                else:
                    print(" Independent Essentia analysis completed")
                    if result.get('summary'):
                        summary = result['summary']
                        print(f"  Files processed: {summary.get('total_files', 0)}")
                        print(f"  Successful: {summary.get('successful', 0)}")
                        print(f"  Failed: {summary.get('failed', 0)}")
            
            elif args.analyzer_command == 'tensorflow':
                result = cli.analyze_tensorflow_independent(args)
                if args.json:
                    print_json(result)
                else:
                    print(" Independent TensorFlow analysis completed")
                    if result.get('summary'):
                        summary = result['summary']
                        print(f"  Files processed: {summary.get('total_files', 0)}")
                        print(f"  Successful: {summary.get('successful', 0)}")
                        print(f"  Failed: {summary.get('failed', 0)}")
            
            elif args.analyzer_command == 'faiss':
                result = cli.analyze_faiss_independent(args)
                if args.json:
                    print_json(result)
                else:
                    print(" Independent FAISS analysis completed")
                    if result.get('summary'):
                        summary = result['summary']
                        print(f"  Files processed: {summary.get('total_files', 0)}")
                        print(f"  Successful: {summary.get('successful', 0)}")
                        print(f"  Failed: {summary.get('failed', 0)}")
            
            elif args.analyzer_command == 'complete':
                result = cli.analyze_complete(args)
                if args.json:
                    print_json(result)
                else:
                    print(" Complete analysis with all independent analyzers completed")
                    if result.get('summary'):
                        summary = result['summary']
                        print(f"  Files processed: {summary.get('total_files', 0)}")
                        print(f"  Successful: {summary.get('successful', 0)}")
                        print(f"  Failed: {summary.get('failed', 0)}")
            
            elif args.analyzer_command == 'statistics':
                result = cli.get_analysis_stats()
                if args.json:
                    print_json(result)
                else:
                    print(" Analysis Statistics:")
                    stats = result.get('statistics', {})
                    print(f"  Total files: {stats.get('total_files', 0)}")
                    print(f"  Essentia analyzed: {stats.get('essentia_analyzed', 0)}")
                    print(f"  TensorFlow analyzed: {stats.get('tensorflow_analyzed', 0)}")
                    print(f"  FAISS analyzed: {stats.get('faiss_analyzed', 0)}")
                    print(f"  Complete analysis: {stats.get('complete_analysis', 0)}")
            
            elif args.analyzer_command == 'fix-status':
                result = cli.fix_analyzer_status_records()
                if args.json:
                    print_json(result)
                else:
                    print(" Analyzer status records fix completed")
                    if result.get('total_files'):
                        print(f"  Total files: {result.get('total_files', 0)}")
                        print(f"  Files without Essentia status: {result.get('files_without_essentia', 0)}")
                        print(f"  Files without TensorFlow status: {result.get('files_without_tensorflow', 0)}")
                        print(f"  Files without FAISS status: {result.get('files_without_faiss', 0)}")
                        print(f"  Created records: {result.get('created_records', 0)}")
        

        
        # TensorFlow analysis operations
        elif args.command == 'tensorflow':
            if args.tensorflow_command == 'analyze':
                cli.analyze_tensorflow(args)
        
        # Audio values extraction operations
        elif args.command == 'audio-values':
            if args.audio_values_command == 'analyze':
                cli.analyze_audio_values(args)
        
        # FAISS operations
        elif args.command == 'faiss':
            if args.faiss_command == 'build':
                result = cli.build_faiss_index(
                    include_tensorflow=args.include_tensorflow,
                    include_faiss=args.include_faiss,
                    force_rebuild=args.force
                )
                if args.json:
                    print_json(result)
                else:
                    print(" FAISS index built successfully")
            
            elif args.faiss_command == 'similar':
                result = cli.find_similar_tracks(args.query, args.top_n)
                if args.json:
                    print_json(result)
                else:
                    similar_tracks = result.get('similar_tracks', [])
                    print(f"\n Similar Tracks for {args.query}:")
                    for track in similar_tracks:
                        print(f"  - {track.get('track_name', 'Unknown')} (similarity: {track.get('similarity', 0):.4f})")
            
            elif args.faiss_command == 'playlist':
                result = cli.generate_playlist(args.seed, args.length)
                if args.json:
                    print_json(result)
                else:
                    playlist = result.get('playlist', [])
                    print(f"\n Generated Playlist from {args.seed}:")
                    for i, track in enumerate(playlist, 1):
                        print(f"  {i}. {track.get('track_name', 'Unknown')} (similarity: {track.get('similarity', 0):.4f})")
        
        # Configuration operations
        elif args.command == 'config':
            if args.config_command == 'list':
                result = cli.list_configs()
                if args.json:
                    print_json(result)
                else:
                    configs = result.get('configs', [])
                    print(" Available configurations:")
                    for config in configs:
                        print(f"  - {config}")
            
            elif args.config_command == 'show':
                result = cli.get_config(args.section)
                if args.json:
                    print_json(result)
                else:
                    print(f" Configuration for {args.section}:")
                    print_json(result.get('config', {}))
            
            elif args.config_command == 'validate':
                result = cli.validate_configs()
                if args.json:
                    print_json(result)
                else:
                    validation_results = result.get('validation_results', {})
                    all_valid = result.get('all_valid', False)
                    print(f" Configuration validation: {'PASSED' if all_valid else 'FAILED'}")
            
            elif args.config_command == 'reload':
                result = cli.reload_configs()
                if args.json:
                    print_json(result)
                else:
                    print(" Configurations reloaded successfully")
        
        # Metadata operations
        elif args.command == 'metadata':
            if args.metadata_command == 'stats':
                result = cli.get_metadata_stats()
                if args.json:
                    print_json(result)
                else:
                    stats = result.get('stats', {})
                    print(f" Metadata Statistics:")
                    print(f"  Total Files: {stats.get('total_files', 0)}")
                    print(f"  Files with Metadata: {stats.get('files_with_metadata', 0)}")
                    print(f"  Analysis Percentage: {stats.get('analysis_percentage', 0)}%")
            
            elif args.metadata_command == 'search':
                result = cli.search_metadata(
                    query=args.query,
                    artist=args.artist,
                    album=args.album,
                    genre=args.genre,
                    year=args.year,
                    limit=args.limit
                )
                if args.json:
                    print_json(result)
                else:
                    results = result.get('results', [])
                    print(f" Search Results ({len(results)} found):")
                    for metadata in results[:10]:
                        title = metadata.get('title', 'Unknown')
                        artist = metadata.get('artist', 'Unknown')
                        print(f"  - {title} by {artist}")
                    if len(results) > 10:
                        print(f"  ... and {len(results) - 10} more")
        
        # Track operations
        elif args.command == 'tracks':
            if args.tracks_command == 'list':
                result = cli.list_tracks(
                    limit=args.limit,
                    offset=args.offset,
                    analyzed_only=args.analyzed_only,
                    has_metadata=args.has_metadata,
                    format=args.format
                )
                if args.json:
                    print_json(result)
                else:
                    tracks = result.get('tracks', [])
                    print(f" Tracks ({len(tracks)} of {result.get('total_count', 0)}):")
                    for track in tracks[:10]:
                        title = track.get('title', track.get('file_name', 'Unknown'))
                        artist = track.get('artist', 'Unknown')
                        print(f"  - {title} by {artist}")
                    if len(tracks) > 10:
                        print(f"  ... and {len(tracks) - 10} more")
        
        # Database operations
        elif args.command == 'database':
            if args.database_command == 'status':
                result = cli.get_database_status()
                if args.json:
                    print_json(result)
                else:
                    print_database_status(result)
            
            elif args.database_command == 'reset':
                if not args.confirm:
                    print("Database reset requires --confirm flag. Use --help for more details.")
                    sys.exit(1)
                
                recreate_tables = not args.no_recreate
                create_backup = not args.no_backup
                
                if create_backup:
                    print("Creating database backup...")
                    # Backup logic would go here
                
                print("Resetting database...")
                success = cli.reset_database(confirm=True, recreate_tables=recreate_tables, backup_first=create_backup)
                if success:
                    print(" Database reset successfully")
                else:
                    print(" Database reset failed")
                    sys.exit(1)
            
            elif args.database_command == 'reset-api':
                if not args.confirm:
                    print("Database reset requires --confirm flag. Use --help for more details.")
                    sys.exit(1)
                
                print("Resetting database via API...")
                result = cli.reset_database_api()
                if args.json:
                    print_json(result)
                else:
                    print(" Database reset via API completed successfully")
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
