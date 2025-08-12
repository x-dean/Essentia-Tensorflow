import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.database import File, AudioMetadata
from ..core.config_loader import config_loader
from .metadata import AudioMetadataAnalyzer
from .audio_analysis_service import audio_analysis_service
from .essentia_analyzer import safe_json_serialize

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
                unanalyzed_files = db.query(File).filter(File.has_audio_analysis == False).all()
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
    
    def analyze_category_batch(self, file_paths: List[str], db: Session, include_tensorflow: bool = True) -> Dict[str, any]:
        """Process a batch of files from the same length category using Essentia analysis"""
        results = {
            'total_files': len(file_paths),
            'processed': 0,
            'failed': 0,
            'category': 'unknown',
            'batch_info': {
                'file_paths': file_paths,
                'batch_size': len(file_paths)
            },
            'analysis_results': [],
            'errors': []
        }
        
        logger.info(f"Processing batch of {len(file_paths)} files with Essentia analysis")
        
        # Determine category based on first file (assuming all files in batch are same category)
        if file_paths:
            try:
                first_file_record = db.query(File).filter(File.file_path == file_paths[0]).first()
                if first_file_record:
                    metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == first_file_record.id).first()
                    if metadata and metadata.duration:
                        results['category'] = self.get_track_length_category(metadata.duration)
            except Exception as e:
                logger.warning(f"Could not determine category for batch: {e}")
        
        # Process each file in the batch
        for file_path in file_paths:
            try:
                logger.info(f"Analyzing file: {file_path}")
                
                # Perform Essentia analysis
                analysis_result = audio_analysis_service.analyze_file(
                    file_path, 
                    include_tensorflow
                )
                
                results['analysis_results'].append({
                    'file_path': file_path,
                    'status': 'success',
                    'result': safe_json_serialize(analysis_result)
                })
                results['processed'] += 1
                
                logger.info(f"Successfully analyzed: {file_path}")
                
            except Exception as e:
                error_msg = f"Analysis failed for {file_path}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                results['failed'] += 1
                results['analysis_results'].append({
                    'file_path': file_path,
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.info(f"Batch processing complete: {results['processed']} successful, {results['failed']} failed")
        return results
    
    def analyze_batches_by_category(self, db: Session, category: str = None, batch_size: int = 50, 
                                  include_tensorflow: bool = True) -> Dict[str, any]:
        """Analyze all batches for a specific category or all categories"""
        try:
            # Get batches
            batches = self.get_analysis_batches(db, batch_size, include_analyzed=False)
            
            # Filter by category if specified
            if category:
                if category not in batches:
                    raise ValueError(f"Category '{category}' not found")
                batches = {category: batches[category]}
            
            # Process batches
            all_results = {
                'total_batches': 0,
                'total_files': 0,
                'total_processed': 0,
                'total_failed': 0,
                'category_results': {},
                'errors': []
            }
            
            for category_name, category_batches in batches.items():
                category_results = {
                    'batches': [],
                    'total_files': 0,
                    'processed': 0,
                    'failed': 0
                }
                
                for batch in category_batches:
                    if batch:  # Only process non-empty batches
                        batch_result = self.analyze_category_batch(batch, db, include_tensorflow)
                        category_results['batches'].append(batch_result)
                        category_results['total_files'] += batch_result['total_files']
                        category_results['processed'] += batch_result['processed']
                        category_results['failed'] += batch_result['failed']
                        
                        all_results['total_batches'] += 1
                        all_results['total_files'] += batch_result['total_files']
                        all_results['total_processed'] += batch_result['processed']
                        all_results['total_failed'] += batch_result['failed']
                        
                        # Collect errors
                        all_results['errors'].extend(batch_result['errors'])
                
                all_results['category_results'][category_name] = category_results
            
            logger.info(f"Category analysis complete: {all_results['total_processed']} files processed, {all_results['total_failed']} failed")
            return all_results
            
        except Exception as e:
            logger.error(f"Category analysis failed: {e}")
            raise
    
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
