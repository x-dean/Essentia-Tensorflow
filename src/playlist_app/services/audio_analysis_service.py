import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import time
from contextlib import contextmanager

from sqlalchemy.orm import Session
from ..models.database import File, AudioAnalysis, AudioMetadata, get_db_session, close_db_session, FileStatus
from ..core.logging import get_logger
from .essentia_analyzer import essentia_analyzer, safe_json_serialize
from ..core.analysis_config import AnalysisConfig
from .faiss_service import faiss_service

logger = logging.getLogger(__name__)

class AudioAnalysisService:
    """
    Service for managing audio analysis operations with database integration.
    
    Handles analysis persistence, retrieval, and batch processing.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.analyzer = essentia_analyzer
        if config:
            self.analyzer.config = config
    
    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions with proper error handling and retry logic"""
        # Get retry settings from configuration
        try:
            from ..core.config_loader import config_loader
            db_config = config_loader.get_database_config()
            retry_settings = db_config.get("retry_settings", {})
            max_retries = retry_settings.get("max_retries", 3)
            retry_delay = retry_settings.get("initial_delay", 1)
            backoff_multiplier = retry_settings.get("backoff_multiplier", 2)
            max_delay = retry_settings.get("max_delay", 30)
        except Exception:
            # Fallback to hardcoded values
            max_retries = 3
            retry_delay = 1
            backoff_multiplier = 2
            max_delay = 30
        
        delay = retry_delay
        for attempt in range(max_retries):
            db = get_db_session()
            try:
                yield db
                break  # Success, exit retry loop
            except Exception as e:
                close_db_session(db)
                
                # Check if it's a connection-related error
                if "server closed the connection" in str(e) or "PGRES_TUPLES_OK" in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"Database connection error (attempt {attempt + 1}/{max_retries}): {e}")
                        import time
                        time.sleep(delay)
                        delay = min(delay * backoff_multiplier, max_delay)  # Exponential backoff with cap
                        continue
                    else:
                        logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                        raise
                else:
                    # Non-connection error, don't retry
                    raise
            finally:
                if attempt == max_retries - 1:
                    close_db_session(db)
    
    def analyze_file(self, file_path: str, include_tensorflow: bool = True, force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Analyze a single audio file and store results in database.
        
        Args:
            file_path: Path to audio file
            include_tensorflow: Whether to include TensorFlow model analysis
            force_reanalyze: Whether to force re-analysis even if it exists
            
        Returns:
            Analysis results
        """
        with self._get_db_session() as db:
            try:
                # Check if file exists in database
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    raise ValueError(f"File not found in database: {file_path}")
                
                # Check if analysis already exists
                existing_analysis = db.query(AudioAnalysis).filter(
                    AudioAnalysis.file_id == file_record.id
                ).first()
                
                if existing_analysis and not force_reanalyze:
                    logger.info(f"Analysis already exists for {file_path}, returning existing results")
                    return self._load_analysis_from_db(existing_analysis)
                
                # If force re-analyze, delete existing analysis
                if existing_analysis and force_reanalyze:
                    logger.info(f"Force re-analyzing {file_path}, deleting existing analysis")
                    db.delete(existing_analysis)
                    db.commit()
                
                # Determine track category based on duration
                category = self._get_track_category(db, file_record)
                logger.info(f"Track category determined: {category}")
                
                # Perform analysis with category-specific strategy
                logger.info(f"Starting analysis for {file_path} (category: {category})")
                analysis_results = self.analyzer.analyze_audio_file(file_path)
                
                # Store in database
                analysis_record = self._store_analysis_in_db(db, file_record.id, analysis_results)
                
                # Mark file as analyzed
                file_record.has_audio_analysis = True
                file_record.is_analyzed = True
                file_record.status = FileStatus.ANALYZED
                db.commit()
                
                # Add to FAISS index for similarity search (in separate session) if enabled
                try:
                    from ..core.analysis_config import analysis_config_loader
                    config = analysis_config_loader.get_config()
                    
                    if config.algorithms.enable_faiss:
                        with self._get_db_session() as faiss_db:
                            faiss_result = faiss_service.add_track_to_index(faiss_db, file_path, include_tensorflow)
                            if faiss_result.get("success"):
                                logger.info(f"Track added to FAISS index: {file_path}")
                            else:
                                logger.warning(f"Failed to add track to FAISS index: {faiss_result.get('error')}")
                    else:
                        logger.info(f"FAISS indexing skipped for {file_path} (disabled in configuration)")
                except Exception as e:
                    logger.warning(f"FAISS indexing failed for {file_path}: {e}")
                
                logger.info(f"Analysis completed and stored for {file_path}")
                return safe_json_serialize(analysis_results)
                
            except Exception as e:
                logger.error(f"Analysis failed for {file_path}: {e}")
                # Mark file as failed
                try:
                    file_record = db.query(File).filter(File.file_path == file_path).first()
                    if file_record:
                        file_record.status = FileStatus.FAILED
                        db.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update file status to FAILED: {db_error}")
                raise
    
    def analyze_files_batch(self, file_paths: List[str], 
                          include_tensorflow: bool = True) -> Dict[str, Any]:
        """
        Analyze multiple files in batch.
        
        Args:
            file_paths: List of file paths to analyze
            include_tensorflow: Whether to include TensorFlow model analysis
            
        Returns:
            Batch analysis results
        """
        results = {
            'total_files': len(file_paths),
            'successful': 0,
            'failed': 0,
            'errors': [],
            'analysis_results': []
        }
        
        for file_path in file_paths:
            try:
                analysis_result = self.analyze_file(file_path, include_tensorflow)
                results['analysis_results'].append({
                    'file_path': file_path,
                    'status': 'success',
                    'result': safe_json_serialize(analysis_result)
                })
                results['successful'] += 1
                
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
        
        logger.info(f"Batch analysis completed: {results['successful']} successful, {results['failed']} failed")
        return results
    
    def get_analysis(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis results for a file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Analysis results or None if not found
        """
        with self._get_db_session() as db:
            try:
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    return None
                
                analysis_record = db.query(AudioAnalysis).filter(
                    AudioAnalysis.file_id == file_record.id
                ).first()
                
                if not analysis_record:
                    return None
                
                return self._load_analysis_from_db(analysis_record)
                
            except Exception as e:
                logger.error(f"Failed to retrieve analysis for {file_path}: {e}")
                return None
    
    def get_analysis_summary(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of analysis results for a file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Analysis summary or None if not found
        """
        try:
            analysis_results = self.get_analysis(file_path)
            if not analysis_results:
                return None
            
            return self.analyzer.get_analysis_summary(analysis_results)
            
        except Exception as e:
            logger.error(f"Failed to get analysis summary for {file_path}: {e}")
            return None
    
    def get_unanalyzed_files(self, limit: Optional[int] = None) -> List[str]:
        """
        Get list of files that haven't been analyzed yet.
        
        Args:
            limit: Maximum number of files to return
            
        Returns:
            List of file paths
        """
        with self._get_db_session() as db:
            try:
                query = db.query(File).filter(File.is_analyzed == False)
                if limit:
                    query = query.limit(limit)
                
                files = query.all()
                return [file.file_path for file in files]
                
            except Exception as e:
                logger.error(f"Failed to get unanalyzed files: {e}")
                return []
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about analysis coverage.
        
        Returns:
            Analysis statistics
        """
        with self._get_db_session() as db:
            try:
                total_files = db.query(File).count()
                analyzed_files = db.query(File).filter(File.has_audio_analysis == True).count()
                unanalyzed_files = total_files - analyzed_files
                
                # Get analysis duration statistics
                analysis_durations = db.query(AudioAnalysis.analysis_duration).all()
                avg_analysis_duration = 0
                if analysis_durations:
                    durations = [d[0] for d in analysis_durations if d[0] is not None]
                    if durations:
                        avg_analysis_duration = sum(durations) / len(durations)
                
                # Get tempo statistics
                tempos = db.query(AudioAnalysis.tempo).filter(AudioAnalysis.tempo.isnot(None)).all()
                tempo_stats = {}
                if tempos:
                    tempo_values = [t[0] for t in tempos]
                    tempo_stats = {
                        'min': min(tempo_values),
                        'max': max(tempo_values),
                        'avg': sum(tempo_values) / len(tempo_values)
                    }
                
                return {
                    'total_files': total_files,
                    'analyzed_files': analyzed_files,
                    'unanalyzed_files': unanalyzed_files,
                    'analysis_coverage': (analyzed_files / total_files * 100) if total_files > 0 else 0,
                    'avg_analysis_duration': avg_analysis_duration,
                    'tempo_statistics': tempo_stats
                }
                
            except Exception as e:
                logger.error(f"Failed to get analysis statistics: {e}")
                return {}
    
    def build_faiss_index(self, include_tensorflow: bool = True, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build FAISS index from analyzed tracks in database.
        
        Args:
            include_tensorflow: Whether to include MusiCNN features
            force_rebuild: Whether to force rebuild existing index
            
        Returns:
            Build results
        """
        with self._get_db_session() as db:
            return faiss_service.build_index_from_database(db, include_tensorflow, force_rebuild)
    
    def find_similar_tracks(self, query_path: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Find similar tracks using FAISS index.
        
        Args:
            query_path: Path to query audio file
            top_n: Number of similar tracks to return
            
        Returns:
            List of (track_path, similarity_score) tuples
        """
        with self._get_db_session() as db:
            return faiss_service.find_similar_tracks(db, query_path, top_n)
    
    def get_faiss_statistics(self) -> Dict[str, Any]:
        """
        Get FAISS index statistics.
        
        Returns:
            FAISS index statistics
        """
        with self._get_db_session() as db:
            return faiss_service.get_index_statistics(db)
    
    def delete_analysis(self, file_path: str) -> bool:
        """
        Delete analysis results for a file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            True if successful, False otherwise
        """
        with self._get_db_session() as db:
            try:
                file_record = db.query(File).filter(File.file_path == file_path).first()
                if not file_record:
                    return False
                
                analysis_record = db.query(AudioAnalysis).filter(
                    AudioAnalysis.file_id == file_record.id
                ).first()
                
                if analysis_record:
                    db.delete(analysis_record)
                    file_record.is_analyzed = False
                    db.commit()
                    logger.info(f"Analysis deleted for {file_path}")
                    return True
                
                return False
                
            except Exception as e:
                logger.error(f"Failed to delete analysis for {file_path}: {e}")
                return False
    
    def _store_analysis_in_db(self, db: Session, file_id: int, analysis_results: Dict[str, Any]) -> AudioAnalysis:
        """
        Store analysis results in database.
        
        Args:
            db: Database session
            file_id: File ID
            analysis_results: Analysis results from Essentia
            
        Returns:
            AudioAnalysis record
        """
        try:
            # Extract basic features
            basic_features = analysis_results.get('basic_features', {})
            rhythm_features = analysis_results.get('rhythm_features', {})
            harmonic_features = analysis_results.get('harmonic_features', {})
            
            # Debug logging
            logger.info(f"Storing analysis - Tempo: {rhythm_features.get('tempo')}, Tempo confidence: {rhythm_features.get('tempo_confidence')}")
            logger.info(f"Will set rhythm_bpm to: {rhythm_features.get('tempo')}, rhythm_confidence to: {rhythm_features.get('tempo_confidence', 0.0)}")
            
            # Create analysis record
            analysis_record = AudioAnalysis(
                file_id=file_id,
                analysis_timestamp=datetime.fromtimestamp(analysis_results.get('analysis_timestamp', time.time())),
                analysis_duration=analysis_results.get('analysis_duration', 0.0),
                sample_rate=analysis_results.get('sample_rate'),
                duration=analysis_results.get('duration'),
                
                # Basic features
                rms=basic_features.get('rms'),
                energy=basic_features.get('energy'),
                loudness=basic_features.get('loudness'),
                
                # Rhythm features
                tempo=rhythm_features.get('tempo'),
                tempo_confidence=rhythm_features.get('tempo_confidence', 0.0),
                tempo_methods_used=rhythm_features.get('tempo_methods_used', 0),
                
                # Harmonic features
                key=harmonic_features.get('key'),
                scale=harmonic_features.get('scale'),
                key_strength=harmonic_features.get('key_strength'),
                dominant_chroma=harmonic_features.get('dominant_chroma'),
                dominant_chroma_strength=harmonic_features.get('dominant_chroma_strength'),
                
                # TensorFlow features
                tensorflow_features=json.dumps(safe_json_serialize(analysis_results.get('tensorflow_features', {}))),
                
                # Complete analysis
                complete_analysis=json.dumps(safe_json_serialize(analysis_results))
            )
            
            db.add(analysis_record)
            
            # Debug logging after creating record
            logger.info(f"Created analysis record - Tempo: {analysis_record.tempo}, Tempo confidence: {analysis_record.tempo_confidence}, Tempo methods: {analysis_record.tempo_methods_used}")
            
            # Update metadata with analysis results
            metadata_record = db.query(AudioMetadata).filter(AudioMetadata.file_id == file_id).first()
            if metadata_record:
                # Extract values from the correct locations in the analysis results
                complete_analysis = analysis_results.get('complete_analysis', {})
                rhythm_features_complete = complete_analysis.get('rhythm_features', {})
                harmonic_features_complete = complete_analysis.get('harmonic_features', {})
                
                # Update BPM from rhythm analysis
                bpm_value = None
                if rhythm_features.get('tempo') and rhythm_features['tempo'] != -999.0:
                    bpm_value = float(rhythm_features['tempo'])
                elif rhythm_features_complete.get('tempo') and rhythm_features_complete['tempo'] != -999.0:
                    bpm_value = float(rhythm_features_complete['tempo'])
                
                if bpm_value and bpm_value > 0:
                    metadata_record.bpm = bpm_value
                    logger.info(f"Updated BPM to {bpm_value} for file {file_id}")
                
                # Update key from harmonic analysis (try multiple sources)
                key_value = None
                if harmonic_features_complete.get('key') and harmonic_features_complete['key'] != 'unknown':
                    key_value = harmonic_features_complete['key']
                elif harmonic_features.get('key') and harmonic_features['key'] != 'unknown':
                    key_value = harmonic_features['key']
                
                if key_value:
                    metadata_record.key = key_value
                    logger.info(f"Updated key to {key_value} for file {file_id}")
                
                # Update duration if not already set
                if not metadata_record.duration and analysis_results.get('duration'):
                    metadata_record.duration = float(analysis_results['duration'])
            
            db.commit()
            
            # Debug logging after commit
            logger.info(f"After commit - Tempo: {analysis_record.tempo}, Tempo confidence: {analysis_record.tempo_confidence}, Tempo methods: {analysis_record.tempo_methods_used}")
            
            return analysis_record
            
        except Exception as e:
            logger.error(f"Failed to store analysis in database: {e}")
            raise
    
    def _load_analysis_from_db(self, analysis_record: AudioAnalysis) -> Dict[str, Any]:
        """
        Load analysis results from database record.
        
        Args:
            analysis_record: AudioAnalysis database record
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Load complete analysis if available
            if analysis_record.complete_analysis:
                return json.loads(analysis_record.complete_analysis)
            
            # Reconstruct from individual fields
            results = {
                'file_path': analysis_record.file.file_path,
                'sample_rate': analysis_record.sample_rate,
                'duration': analysis_record.duration,
                'analysis_timestamp': analysis_record.analysis_timestamp.timestamp(),
                'analysis_duration': analysis_record.analysis_duration,
                
                'basic_features': {
                    'rms': analysis_record.rms,
                    'energy': analysis_record.energy,
                    'loudness': analysis_record.loudness,
                    'spectral_centroid_mean': analysis_record.spectral_centroid_mean,
                    'spectral_centroid_std': analysis_record.spectral_centroid_std,
                    'spectral_rolloff_mean': analysis_record.spectral_rolloff_mean,
                    'spectral_rolloff_std': analysis_record.spectral_rolloff_std,
                    'spectral_contrast_mean': analysis_record.spectral_contrast_mean,
                    'spectral_contrast_std': analysis_record.spectral_contrast_std,
                    'spectral_complexity_mean': analysis_record.spectral_complexity_mean,
                    'spectral_complexity_std': analysis_record.spectral_complexity_std,
                    'mfcc_mean': json.loads(analysis_record.mfcc_mean) if analysis_record.mfcc_mean else [],
                    'mfcc_bands_mean': json.loads(analysis_record.mfcc_bands_mean) if analysis_record.mfcc_bands_mean else []
                },
                
                'rhythm_features': {
                    'tempo': analysis_record.tempo,
                    'tempo_confidence': analysis_record.tempo_confidence,
                    'rhythm_bpm': analysis_record.rhythm_bpm,
                    'rhythm_confidence': analysis_record.rhythm_confidence,
                    'beat_confidence': analysis_record.beat_confidence,
                    'beats': json.loads(analysis_record.beats) if analysis_record.beats else [],
                    'rhythm_ticks': json.loads(analysis_record.rhythm_ticks) if analysis_record.rhythm_ticks else [],
                    'rhythm_estimates': json.loads(analysis_record.rhythm_estimates) if analysis_record.rhythm_estimates else [],
                    'onset_detections': json.loads(analysis_record.onset_detections) if analysis_record.onset_detections else []
                },
                
                'harmonic_features': {
                    'key': analysis_record.key,
                    'scale': analysis_record.scale,
                    'key_strength': analysis_record.key_strength,
                    'chords': json.loads(analysis_record.chords) if analysis_record.chords else [],
                    'chord_strengths': json.loads(analysis_record.chord_strengths) if analysis_record.chord_strengths else [],
                    'pitch_yin': json.loads(analysis_record.pitch_yin) if analysis_record.pitch_yin else [],
                    'pitch_yin_confidence': json.loads(analysis_record.pitch_yin_confidence) if analysis_record.pitch_yin_confidence else [],
                    'pitch_melodia': json.loads(analysis_record.pitch_melodia) if analysis_record.pitch_melodia else [],
                    'pitch_melodia_confidence': json.loads(analysis_record.pitch_melodia_confidence) if analysis_record.pitch_melodia_confidence else [],
                    'chromagram': json.loads(analysis_record.chromagram) if analysis_record.chromagram else []
                },
                
                'tensorflow_features': json.loads(analysis_record.tensorflow_features) if analysis_record.tensorflow_features else {}
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to load analysis from database: {e}")
            raise

    def _get_track_category(self, db: Session, file_record: File) -> str:
        """Determine the track category based on duration"""
        try:
            # Import here to avoid circular imports
            from .analyzer_manager import analyzer_manager
            
            # Get metadata to find duration
            from ..models.database import AudioMetadata
            metadata = db.query(AudioMetadata).filter(AudioMetadata.file_id == file_record.id).first()
            
            if metadata and metadata.duration:
                category = analyzer_manager.get_track_length_category(metadata.duration)
                logger.info(f"Track duration: {metadata.duration}s, category: {category}")
                return category
            else:
                logger.warning(f"No duration metadata found for {file_record.file_path}, using 'normal' category")
                return 'normal'
                
        except Exception as e:
            logger.warning(f"Error determining track category: {e}, using 'normal' category")
            return 'normal'

# Global instance
audio_analysis_service = AudioAnalysisService()
