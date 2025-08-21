import os
import hashlib
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from ..models.database import File, DiscoveryCache, get_db, FileStatus, EssentiaAnalysisStatus, TensorFlowAnalysisStatus, FAISSAnalysisStatus, AnalyzerStatus
from ..core.config import DiscoveryConfig
from ..core.logging import get_logger
from .metadata import audio_metadata_analyzer

logger = get_logger(__name__)

class DiscoveryService:
    """Service for discovering and tracking audio files"""
    
    def __init__(self, db_session: Session, 
                 search_directories: List[str] = None,
                 supported_extensions: List[str] = None):
        self.db = db_session
        self.search_directories = search_directories or DiscoveryConfig.get_search_directories()
        self.supported_extensions = supported_extensions or DiscoveryConfig.get_supported_extensions()
        
    def calculate_file_hash(self, file_name: str, file_size: int) -> str:
        """Calculate hash from filename + filesize"""
        hash_input = f"{file_name}_{file_size}".encode('utf-8')
        hash_algorithm = DiscoveryConfig.get_hash_algorithm()
        
        if hash_algorithm == "md5":
            return hashlib.md5(hash_input).hexdigest()
        elif hash_algorithm == "sha1":
            return hashlib.sha1(hash_input).hexdigest()
        elif hash_algorithm == "sha256":
            return hashlib.sha256(hash_input).hexdigest()
        else:
            # Default to MD5 if unknown algorithm
            return hashlib.md5(hash_input).hexdigest()
    
    def get_file_info(self, file_path: str) -> Dict:
        """Get file information"""
        try:
            path = Path(file_path)
            if not path.exists():
                return None
                
            stat = path.stat()
            file_name = path.name
            file_size = stat.st_size
            file_extension = path.suffix.lower()
            
            # Check if extension is supported
            if file_extension not in self.supported_extensions:
                return None
                
            file_hash = self.calculate_file_hash(file_name, file_size)
            
            return {
                "file_path": str(file_path),
                "file_name": file_name,
                "file_size": file_size,
                "file_hash": file_hash,
                "file_extension": file_extension,
                "last_modified": datetime.fromtimestamp(stat.st_mtime)
            }
        except Exception as e:
            logger.error(f"Error getting file info for {file_path}: {e}")
            return None
    
    def get_cached_file_info(self, file_path: str) -> Dict:
        """Get file info from cache if available"""
        cache_entry = self.db.query(DiscoveryCache).filter(
            DiscoveryCache.file_path == file_path
        ).first()
        
        if cache_entry:
            # Check if file still exists and size matches
            try:
                current_size = Path(file_path).stat().st_size
                if current_size == cache_entry.file_size:
                    return {
                        "file_path": cache_entry.file_path,
                        "file_name": Path(file_path).name,
                        "file_size": cache_entry.file_size,
                        "file_hash": cache_entry.file_hash,
                        "file_extension": Path(file_path).suffix.lower(),
                        "last_modified": cache_entry.last_checked
                    }
            except (OSError, FileNotFoundError):
                # File no longer exists, remove from cache
                self.db.delete(cache_entry)
                self.db.commit()
                
        return None
    
    def update_cache(self, file_info: Dict):
        """Update or create cache entry"""
        cache_entry = self.db.query(DiscoveryCache).filter(
            DiscoveryCache.file_path == file_info["file_path"]
        ).first()
        
        if cache_entry:
            cache_entry.file_size = file_info["file_size"]
            cache_entry.file_hash = file_info["file_hash"]
            cache_entry.last_checked = datetime.utcnow()
        else:
            cache_entry = DiscoveryCache(
                file_path=file_info["file_path"],
                file_size=file_info["file_size"],
                file_hash=file_info["file_hash"],
                last_checked=datetime.utcnow()
            )
            self.db.add(cache_entry)
        
        self.db.commit()
    
    def discover_files(self) -> Dict[str, List[str]]:
        """Discover files in search directories"""
        results = {
            "added": [],
            "removed": [],
            "unchanged": []
        }
        
        logger.info(f"Starting file discovery - Search directories: {self.search_directories}, Supported extensions: {self.supported_extensions}")
        
        # Get all currently tracked files
        tracked_files = set()
        for file_record in self.db.query(File).filter(File.is_active == True).all():
            tracked_files.add(file_record.file_path)
        
        logger.debug(f"Found {len(tracked_files)} currently tracked files")
        
        # Discover current files
        current_files = set()
        discovered_files = []
        
        for search_dir in self.search_directories:
            if not os.path.exists(search_dir):
                logger.warning(f"Search directory does not exist: {search_dir}")
                continue
                
            logger.info(f"Scanning directory: {search_dir}")
            
            for root, dirs, files in os.walk(search_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check cache first
                    cached_info = self.get_cached_file_info(file_path)
                    if cached_info:
                        current_files.add(file_path)
                        discovered_files.append(cached_info)
                        results["unchanged"].append(file_path)
                        continue
                    
                    # Get fresh file info
                    file_info = self.get_file_info(file_path)
                    if file_info:
                        current_files.add(file_path)
                        discovered_files.append(file_info)
                        
                        # Update cache
                        self.update_cache(file_info)
        
        # Find added and removed files
        added_files = current_files - tracked_files
        removed_files = tracked_files - current_files
        
        logger.debug(f"Found {len(added_files)} new files and {len(removed_files)} removed files")
        
        # Process added files
        for file_path in added_files:
            file_info = next((f for f in discovered_files if f["file_path"] == file_path), None)
            if file_info:
                self.add_file_to_db(file_info)
                results["added"].append(file_path)
        
        # Process removed files
        for file_path in removed_files:
            self.remove_file_from_db(file_path)
            results["removed"].append(file_path)
        
        logger.info(f"Discovery complete - Added: {len(results['added'])}, Removed: {len(results['removed'])}, Unchanged: {len(results['unchanged'])}, Total processed: {len(current_files)}")
        return results
    
    def add_file_to_db(self, file_info: Dict):
        """Add new file to database and extract metadata"""
        try:
            # Check if file already exists
            existing_file = self.db.query(File).filter(
                File.file_path == file_info["file_path"]
            ).first()
            
            if existing_file:
                logger.info(f"File already exists: {file_info['file_name']}")
                return
            
            # Create new file record
            new_file = File(
                file_path=file_info["file_path"],
                file_name=file_info["file_name"],
                file_size=file_info["file_size"],
                file_extension=file_info["file_extension"],
                is_active=True
            )
            
            self.db.add(new_file)
            self.db.commit()
            logger.info(f"Added file to database: {file_info['file_name']}")
            
            # Extract metadata immediately after adding file
            try:
                logger.info(f"Extracting metadata for: {file_info['file_name']}")
                metadata = audio_metadata_analyzer.analyze_file(file_info["file_path"], self.db)
                if metadata:
                    logger.info(f"Successfully extracted metadata for: {file_info['file_name']}")
                else:
                    logger.warning(f"No metadata extracted for: {file_info['file_name']}")
            except Exception as metadata_error:
                logger.error(f"Error extracting metadata for {file_info['file_name']}: {metadata_error}")
            
        except Exception as e:
            logger.error(f"Error adding file to database: {e}")
            self.db.rollback()
    
    def remove_file_from_db(self, file_path: str):
        """Remove file from database and trigger playlist cleanup"""
        try:
            file_record = self.db.query(File).filter(
                File.file_path == file_path
            ).first()
            
            if file_record:
                # Mark as inactive instead of deleting to preserve history
                file_record.is_active = False
                self.db.commit()
                logger.info(f"Removed file from database: {file_path}")
                
                # TODO: Trigger playlist cleanup to remove this file from playlists
                # This will be implemented when playlist system is added
                
        except Exception as e:
            logger.error(f"Error removing file from database: {e}")
            self.db.rollback()
    
    def get_discovered_files(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get list of discovered files"""
        files = self.db.query(File).filter(
            File.is_active == True
        ).offset(offset).limit(limit).all()
        
        return [
            {
                "id": file.id,
                "file_path": file.file_path,
                "file_name": file.file_name,
                "file_size": file.file_size,
                "file_extension": file.file_extension,
                "discovered_at": file.discovered_at.isoformat(),
                "status": file.status.value if file.status else "unknown"
            }
            for file in files
        ]
    
    def get_file_by_hash(self, file_hash: str) -> Dict:
        """Get file by hash"""
        file = self.db.query(File).filter(
            File.file_hash == file_hash,
            File.is_active == True
        ).first()
        
        if file:
            return {
                "id": file.id,
                "file_path": file.file_path,
                "file_name": file.file_name,
                "file_size": file.file_size,
                "file_extension": file.file_extension,
                "discovered_at": file.discovered_at.isoformat(),
                "status": file.status.value if file.status else "unknown"
            }
        return None
    
    def ensure_status_records_exist(self) -> Dict[str, int]:
        """Ensure all active files have analyzer status records"""
        try:
            logger.info("Checking for files without analyzer status records...")
            
            # Get all active files
            active_files = self.db.query(File).filter(File.is_active == True).all()
            
            # Check which files don't have status records
            files_without_essentia = []
            files_without_tensorflow = []
            files_without_faiss = []
            
            for file in active_files:
                # Check Essentia status
                essentia_status = self.db.query(EssentiaAnalysisStatus).filter(
                    EssentiaAnalysisStatus.file_id == file.id
                ).first()
                if not essentia_status:
                    files_without_essentia.append(file.id)
                
                # Check TensorFlow status
                tensorflow_status = self.db.query(TensorFlowAnalysisStatus).filter(
                    TensorFlowAnalysisStatus.file_id == file.id
                ).first()
                if not tensorflow_status:
                    files_without_tensorflow.append(file.id)
                
                # Check FAISS status
                faiss_status = self.db.query(FAISSAnalysisStatus).filter(
                    FAISSAnalysisStatus.file_id == file.id
                ).first()
                if not faiss_status:
                    files_without_faiss.append(file.id)
            
            # Create missing status records
            created_count = 0
            
            for file_id in files_without_essentia:
                essentia_status = EssentiaAnalysisStatus(
                    file_id=file_id,
                    status=AnalyzerStatus.PENDING
                )
                self.db.add(essentia_status)
                created_count += 1
            
            for file_id in files_without_tensorflow:
                tensorflow_status = TensorFlowAnalysisStatus(
                    file_id=file_id,
                    status=AnalyzerStatus.PENDING
                )
                self.db.add(tensorflow_status)
                created_count += 1
            
            for file_id in files_without_faiss:
                faiss_status = FAISSAnalysisStatus(
                    file_id=file_id,
                    status=AnalyzerStatus.PENDING
                )
                self.db.add(faiss_status)
                created_count += 1
            
            if created_count > 0:
                self.db.commit()
                logger.info(f"Created {created_count} missing analyzer status records")
            else:
                logger.info("All files already have analyzer status records")
            
            return {
                "total_files": len(active_files),
                "files_without_essentia": len(files_without_essentia),
                "files_without_tensorflow": len(files_without_tensorflow),
                "files_without_faiss": len(files_without_faiss),
                "created_records": created_count
            }
            
        except Exception as e:
            logger.error(f"Error ensuring status records exist: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def re_discover_files(self) -> Dict[str, List[str]]:
        """Re-discover all files (useful for initial setup or after file changes)"""
        try:
            logger.info("Starting re-discovery of all files...")
            
            # Clear all existing files and metadata
            from ..models.database import AudioMetadata
            
            # Delete all metadata first (due to foreign key constraint)
            self.db.query(AudioMetadata).delete()
            
            # Delete all files
            self.db.query(File).delete()
            
            self.db.commit()
            logger.info("Cleared all existing files and metadata")
            
            # Run normal discovery (this will add all files as new)
            results = self.discover_files()
            
            logger.info(f"Re-discovery complete - Added: {len(results['added'])}, Removed: {len(results['removed'])}, Unchanged: {len(results['unchanged'])}")
            return results
            
        except Exception as e:
            logger.error(f"Error in re-discovery: {e}")
            self.db.rollback()
            return {"added": [], "removed": [], "unchanged": []}
