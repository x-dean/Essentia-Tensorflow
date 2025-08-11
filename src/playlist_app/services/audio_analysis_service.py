import logging
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import time

from ..models.database import File, AudioAnalysis
from .essentia_analyzer import essentia_analyzer, EssentiaConfig

logger = logging.getLogger(__name__)

class AudioAnalysisService:
    """
    Service for managing audio analysis operations with database integration.
    
    Handles analysis persistence, retrieval, and batch processing.
    """
    
    def __init__(self, config: Optional[EssentiaConfig] = None):
        self.analyzer = essentia_analyzer
        if config:
            self.analyzer.config = config
    
    def analyze_file(self, db: Session, file_path: str, include_tensorflow: bool = True, force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Analyze a single audio file and store results in database.
        
        Args:
            db: Database session
            file_path: Path to audio file
            include_tensorflow: Whether to include TensorFlow model analysis
            force_reanalyze: Whether to force re-analysis even if it exists
            
        Returns:
            Analysis results
        """
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
            analysis_results = self.analyzer.analyze_audio_file(file_path, include_tensorflow, category)
            
            # Store in database
            analysis_record = self._store_analysis_in_db(db, file_record.id, analysis_results)
            
            # Mark file as analyzed
            file_record.is_analyzed = True
            db.commit()
            
            logger.info(f"Analysis completed and stored for {file_path}")
            return analysis_results
            
        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {e}")
            db.rollback()
            raise
    
    def analyze_files_batch(self, db: Session, file_paths: List[str], 
                          include_tensorflow: bool = True) -> Dict[str, Any]:
        """
        Analyze multiple files in batch.
        
        Args:
            db: Database session
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
                analysis_result = self.analyze_file(db, file_path, include_tensorflow)
                results['analysis_results'].append({
                    'file_path': file_path,
                    'status': 'success',
                    'result': analysis_result
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
    
    def get_analysis(self, db: Session, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve analysis results for a file.
        
        Args:
            db: Database session
            file_path: Path to audio file
            
        Returns:
            Analysis results or None if not found
        """
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
    
    def get_analysis_summary(self, db: Session, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get a summary of analysis results for a file.
        
        Args:
            db: Database session
            file_path: Path to audio file
            
        Returns:
            Analysis summary or None if not found
        """
        try:
            analysis_results = self.get_analysis(db, file_path)
            if not analysis_results:
                return None
            
            return self.analyzer.get_analysis_summary(analysis_results)
            
        except Exception as e:
            logger.error(f"Failed to get analysis summary for {file_path}: {e}")
            return None
    
    def get_unanalyzed_files(self, db: Session, limit: Optional[int] = None) -> List[str]:
        """
        Get list of files that haven't been analyzed yet.
        
        Args:
            db: Database session
            limit: Maximum number of files to return
            
        Returns:
            List of file paths
        """
        try:
            query = db.query(File).filter(File.is_analyzed == False)
            if limit:
                query = query.limit(limit)
            
            files = query.all()
            return [file.file_path for file in files]
            
        except Exception as e:
            logger.error(f"Failed to get unanalyzed files: {e}")
            return []
    
    def get_analysis_statistics(self, db: Session) -> Dict[str, Any]:
        """
        Get statistics about analysis coverage.
        
        Args:
            db: Database session
            
        Returns:
            Analysis statistics
        """
        try:
            total_files = db.query(File).count()
            analyzed_files = db.query(File).filter(File.is_analyzed == True).count()
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
    
    def delete_analysis(self, db: Session, file_path: str) -> bool:
        """
        Delete analysis results for a file.
        
        Args:
            db: Database session
            file_path: Path to audio file
            
        Returns:
            True if successful, False otherwise
        """
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
            db.rollback()
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
                spectral_centroid_mean=basic_features.get('spectral_centroid_mean'),
                spectral_centroid_std=basic_features.get('spectral_centroid_std'),
                spectral_rolloff_mean=basic_features.get('spectral_rolloff_mean'),
                spectral_rolloff_std=basic_features.get('spectral_rolloff_std'),
                spectral_contrast_mean=basic_features.get('spectral_contrast_mean'),
                spectral_contrast_std=basic_features.get('spectral_contrast_std'),
                spectral_complexity_mean=basic_features.get('spectral_complexity_mean'),
                spectral_complexity_std=basic_features.get('spectral_complexity_std'),
                
                # MFCC features
                mfcc_mean=json.dumps(basic_features.get('mfcc_mean', [])),
                mfcc_bands_mean=json.dumps(basic_features.get('mfcc_bands_mean', [])),
                
                # Rhythm features
                tempo=rhythm_features.get('estimated_bpm') or rhythm_features.get('tempo'),
                tempo_confidence=rhythm_features.get('tempo_confidence', 0.0),
                rhythm_bpm=rhythm_features.get('estimated_bpm') or rhythm_features.get('rhythm_bpm'),
                rhythm_confidence=rhythm_features.get('rhythm_confidence', 0.0),
                beat_confidence=rhythm_features.get('beat_confidence', 0.0),
                beats=json.dumps(rhythm_features.get('beats', [])),
                rhythm_ticks=json.dumps(rhythm_features.get('rhythm_ticks', [])),
                rhythm_estimates=json.dumps(rhythm_features.get('rhythm_estimates', [])),
                onset_detections=json.dumps(rhythm_features.get('onset_detections', [])),
                
                # Harmonic features
                key=harmonic_features.get('key'),
                scale=harmonic_features.get('scale'),
                key_strength=harmonic_features.get('key_strength'),
                chords=json.dumps(harmonic_features.get('chords', [])),
                chord_strengths=json.dumps(harmonic_features.get('chord_strengths', [])),
                pitch_yin=json.dumps(harmonic_features.get('pitch_yin', [])),
                pitch_yin_confidence=json.dumps(harmonic_features.get('pitch_yin_confidence', [])),
                pitch_melodia=json.dumps(harmonic_features.get('pitch_melodia', [])),
                pitch_melodia_confidence=json.dumps(harmonic_features.get('pitch_melodia_confidence', [])),
                chromagram=json.dumps(harmonic_features.get('chromagram', [])),
                
                # TensorFlow features
                tensorflow_features=json.dumps(analysis_results.get('tensorflow_features', {})),
                
                # Complete analysis
                complete_analysis=json.dumps(analysis_results)
            )
            
            db.add(analysis_record)
            db.commit()
            
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
