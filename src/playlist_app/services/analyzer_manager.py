import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.database import File, AudioMetadata
from ..core.config_loader import config_loader
from .metadata import AudioMetadataAnalyzer

logger = logging.getLogger(__name__)

class AnalyzerManager:
    """Manager for categorizing audio files based on length and creating analysis batches"""
    
    def __init__(self):
        self.metadata_analyzer = AudioMetadataAnalyzer()
        self.length_categories = self._load_length_categories()
        
    def _load_length_categories(self) -> Dict[str, Tuple[int, int]]:
        """Load length category thresholds from config"""
        config = config_loader.get_discovery_config()
        categories_config = config.get('length_categories', {})
        
        # Default thresholds in seconds
        default_categories = {
            'normal': (0, 300),      # 0-5 minutes
            'long': (300, 600),      # 5-10 minutes
            'very_long': (600, None) # 10+ minutes
        }
        
        # Override with config if available
        if categories_config:
            for category_name, category_config in categories_config.items():
                min_duration = category_config.get('min_duration', 0)
                max_duration = category_config.get('max_duration')
                default_categories[category_name] = (min_duration, max_duration)
        
        return default_categories
    
    def get_track_length_category(self, duration_seconds: int) -> str:
        """Determine the length category for a track based on duration"""
        if duration_seconds is None:
            return 'unknown'
            
        for category, (min_duration, max_duration) in self.length_categories.items():
            if max_duration is None:
                if duration_seconds >= min_duration:
                    return category
            else:
                if min_duration <= duration_seconds < max_duration:
                    return category
                    
        return 'unknown'
    
    def categorize_files_by_length(self, db: Session, file_paths: List[str] = None, include_analyzed: bool = False) -> Dict[str, List[str]]:
        """Categorize files by their length into batches"""
        categorized_files = {
            'normal': [],
            'long': [],
            'very_long': [],
            'unknown': []
        }
        
        # Get files to categorize
        if file_paths:
            files_to_process = file_paths
        else:
            if include_analyzed:
                # Get all files from database
                all_files = db.query(File).all()
                files_to_process = [file.file_path for file in all_files]
            else:
                # Get all unanalyzed files from database
                unanalyzed_files = db.query(File).filter(File.is_analyzed == False).all()
                files_to_process = [file.file_path for file in unanalyzed_files]
        
        logger.info(f"Categorizing {len(files_to_process)} files by length")
        
        for file_path in files_to_process:
            try:
                # Check if metadata already exists
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    logger.warning(f"File record not found: {file_path}")
                    categorized_files['unknown'].append(file_path)
                    continue
                
                # Check if metadata exists and has duration
                metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == file_record.id).first()
                if metadata and metadata.duration:
                    category = self.get_track_length_category(metadata.duration)
                    categorized_files[category].append(file_path)
                else:
                    # For files without duration, put them in unknown category
                    # We'll analyze them later when needed
                    categorized_files['unknown'].append(file_path)
                        
            except Exception as e:
                logger.error(f"Error categorizing file {file_path}: {e}")
                categorized_files['unknown'].append(file_path)
        
        # Log categorization results
        for category, files in categorized_files.items():
            logger.info(f"Category '{category}': {len(files)} files")
            
        return categorized_files
    
    def get_analysis_batches(self, db: Session, batch_size: int = 50, include_analyzed: bool = True) -> Dict[str, List[List[str]]]:
        """Create analysis batches based on length categories"""
        categorized_files = self.categorize_files_by_length(db, include_analyzed=include_analyzed)
        
        batches = {}
        for category, files in categorized_files.items():
            category_batches = []
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                category_batches.append(batch)
            batches[category] = category_batches
            
        return batches
    
    def analyze_category_batch(self, file_paths: List[str], db: Session) -> Dict[str, any]:
        """Process a batch of files from the same length category (no metadata analysis)"""
        results = {
            'total_files': len(file_paths),
            'processed': len(file_paths),
            'category': 'unknown',
            'batch_info': {
                'file_paths': file_paths,
                'batch_size': len(file_paths)
            }
        }
        
        logger.info(f"Processing batch of {len(file_paths)} files")
        
        # For now, just return the batch information
        # Metadata analysis will be handled separately by the discovery system
        logger.info(f"Batch processing complete: {len(file_paths)} files ready for processing")
        return results
    
    def get_length_statistics(self, db: Session) -> Dict[str, any]:
        """Get statistics about file lengths in the database"""
        stats = {
            'total_files': 0,
            'analyzed_files': 0,
            'category_counts': {
                'normal': 0,
                'long': 0,
                'very_long': 0,
                'unknown': 0
            },
            'duration_ranges': {
                'min_duration': None,
                'max_duration': None,
                'avg_duration': None
            }
        }
        
        # Get all files with metadata
        files_with_metadata = db.query(File, AudioMetadata).join(
            AudioMetadata, File.id == AudioMetadata.file_id
        ).filter(AudioMetadata.duration.isnot(None)).all()
        
        stats['total_files'] = db.query(File).count()
        stats['analyzed_files'] = len(files_with_metadata)
        
        durations = []
        for file_record, metadata in files_with_metadata:
            if metadata.duration:
                durations.append(metadata.duration)
                category = self.get_track_length_category(metadata.duration)
                if category in stats['category_counts']:
                    stats['category_counts'][category] += 1
        
        if durations:
            stats['duration_ranges']['min_duration'] = min(durations)
            stats['duration_ranges']['max_duration'] = max(durations)
            stats['duration_ranges']['avg_duration'] = sum(durations) / len(durations)
        
        return stats

# Global instance
analyzer_manager = AnalyzerManager()
