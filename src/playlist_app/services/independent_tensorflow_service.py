import logging
import time
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from .base_analyzer_service import BaseAnalyzerService
from ..models.database_v2 import (
    File, TensorFlowAnalysisStatus, TensorFlowAnalysisResults,
    AnalyzerStatus, get_db, SessionLocal
)
from .tensorflow_analyzer import tensorflow_analyzer

logger = logging.getLogger(__name__)

class IndependentTensorFlowService(BaseAnalyzerService):
    """
    Independent TensorFlow analyzer service.
    
    Handles machine learning classification using TensorFlow models
    with independent status tracking and result storage.
    """
    
    def __init__(self):
        super().__init__("tensorflow")
        self.analyzer = tensorflow_analyzer
    
    def analyze_file(self, file_path: str, db: Session) -> Dict[str, Any]:
        """
        Analyze a single file using TensorFlow.
        
        Args:
            file_path: Path to the audio file
            db: Database session
            
        Returns:
            Dictionary with analysis results and metadata
        """
        start_time = time.time()
        
        try:
            # Get file record
            file_record = db.query(File).filter(File.file_path == file_path).first()
            if not file_record:
                raise ValueError(f"File not found in database: {file_path}")
            
            file_id = file_record.id
            
            # Update status to analyzing
            self.update_status(file_id, AnalyzerStatus.ANALYZING, db)
            
            # Perform analysis
            self.logger.info(f"Starting TensorFlow analysis for {file_path}")
            analysis_results = self.analyzer.analyze_audio_file(file_path)
            
            # Calculate analysis duration
            analysis_duration = time.time() - start_time
            
            # Store results
            success = self.update_status(
                file_id, 
                AnalyzerStatus.ANALYZED, 
                db, 
                results={
                    "analysis_results": analysis_results,
                    "analysis_duration": analysis_duration
                }
            )
            
            if success:
                self.logger.info(f"TensorFlow analysis completed for {file_path} in {analysis_duration:.2f}s")
                return {
                    "success": True,
                    "file_path": file_path,
                    "file_id": file_id,
                    "analysis_duration": analysis_duration,
                    "results": analysis_results
                }
            else:
                raise Exception("Failed to store analysis results")
                
        except Exception as e:
            analysis_duration = time.time() - start_time
            self.logger.error(f"TensorFlow analysis failed for {file_path}: {e}")
            
            # Update status to failed
            if 'file_id' in locals():
                self.update_status(file_id, AnalyzerStatus.FAILED, db, error_message=str(e))
            
            return {
                "success": False,
                "file_path": file_path,
                "error": str(e),
                "analysis_duration": analysis_duration
            }
    
    def get_status(self, file_id: int, db: Session) -> AnalyzerStatus:
        """Get the current analysis status for a file."""
        status_record = db.query(TensorFlowAnalysisStatus).filter(
            TensorFlowAnalysisStatus.file_id == file_id
        ).first()
        
        if status_record:
            return status_record.status
        else:
            # Create status record if it doesn't exist
            status_record = TensorFlowAnalysisStatus(
                file_id=file_id,
                status=AnalyzerStatus.PENDING
            )
            db.add(status_record)
            db.commit()
            return AnalyzerStatus.PENDING
    
    def get_pending_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get list of file IDs that are pending analysis."""
        # First, ensure all files have status records
        self._ensure_status_records_exist(db)
        
        query = db.query(TensorFlowAnalysisStatus.file_id).filter(
            TensorFlowAnalysisStatus.status == AnalyzerStatus.PENDING
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def _ensure_status_records_exist(self, db: Session):
        """Ensure all active files have TensorFlow status records"""
        try:
            # Find files without TensorFlow status records
            files_without_status = db.query(File).filter(
                File.is_active == True,
                ~File.id.in_(db.query(TensorFlowAnalysisStatus.file_id))
            ).all()
            
            if files_without_status:
                self.logger.info(f"Creating TensorFlow status records for {len(files_without_status)} files")
                
                for file in files_without_status:
                    status_record = TensorFlowAnalysisStatus(
                        file_id=file.id,
                        status=AnalyzerStatus.PENDING
                    )
                    db.add(status_record)
                
                db.commit()
                self.logger.info(f"Created {len(files_without_status)} TensorFlow status records")
            
        except Exception as e:
            self.logger.error(f"Error ensuring TensorFlow status records exist: {e}")
            db.rollback()
    
    def analyze_pending_files(self, db: Session, max_files: Optional[int] = None, 
                            force_reanalyze: bool = False) -> Dict[str, Any]:
        """Analyze all pending files."""
        try:
            # Get pending files
            if force_reanalyze:
                # Get all files that need reanalysis
                query = db.query(File).filter(File.is_active == True)
                if max_files:
                    query = query.limit(max_files)
                files = query.all()
                file_ids = [f.id for f in files]
            else:
                file_ids = self.get_pending_files(db, max_files)
            
            if not file_ids:
                return {
                    "success": True,
                    "message": "No files to analyze",
                    "total_files": 0,
                    "successful": 0,
                    "failed": 0,
                    "results": []
                }
            
            self.logger.info(f"Starting TensorFlow analysis for {len(file_ids)} files")
            
            successful = 0
            failed = 0
            results = []
            
            for file_id in file_ids:
                try:
                    # Get file path
                    file_record = db.query(File).filter(File.id == file_id).first()
                    if not file_record:
                        self.logger.warning(f"File record not found for ID {file_id}")
                        failed += 1
                        continue
                    
                    # Analyze file
                    result = self.analyze_file(file_record.file_path, db)
                    
                    if result.get("success"):
                        successful += 1
                        results.append({
                            "file_path": file_record.file_path,
                            "status": "success",
                            "result": result
                        })
                    else:
                        failed += 1
                        results.append({
                            "file_path": file_record.file_path,
                            "status": "failed",
                            "error": result.get("error", "Unknown error")
                        })
                        
                except Exception as e:
                    self.logger.error(f"Error analyzing file ID {file_id}: {e}")
                    failed += 1
                    results.append({
                        "file_id": file_id,
                        "status": "failed",
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"TensorFlow analysis completed: {successful} successful, {failed} failed",
                "total_files": len(file_ids),
                "successful": successful,
                "failed": failed,
                "results": results
            }
            
        except Exception as e:
            self.logger.error(f"Error in analyze_pending_files: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_files": 0,
                "successful": 0,
                "failed": 0,
                "results": []
            }
    
    def get_stats(self, db: Session) -> Dict[str, Any]:
        """Get statistics for this analyzer."""
        try:
            # Count files by status
            total_files = db.query(File).filter(File.is_active == True).count()
            
            analyzed_count = db.query(TensorFlowAnalysisStatus).filter(
                TensorFlowAnalysisStatus.status == AnalyzerStatus.ANALYZED
            ).count()
            
            failed_count = db.query(TensorFlowAnalysisStatus).filter(
                TensorFlowAnalysisStatus.status == AnalyzerStatus.FAILED
            ).count()
            
            pending_count = db.query(TensorFlowAnalysisStatus).filter(
                TensorFlowAnalysisStatus.status == AnalyzerStatus.PENDING
            ).count()
            
            return {
                "total_files": total_files,
                "analyzed": analyzed_count,
                "failed": failed_count,
                "pending": pending_count,
                "coverage": (analyzed_count / total_files * 100) if total_files > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting TensorFlow stats: {e}")
            return {
                "total_files": 0,
                "analyzed": 0,
                "failed": 0,
                "pending": 0,
                "coverage": 0
            }
    
    def update_status(self, file_id: int, status: AnalyzerStatus, 
                     db: Session, results: Optional[Dict] = None, 
                     error_message: Optional[str] = None) -> bool:
        """Update the analysis status for a file."""
        try:
            # Get or create status record
            status_record = db.query(TensorFlowAnalysisStatus).filter(
                TensorFlowAnalysisStatus.file_id == file_id
            ).first()
            
            if not status_record:
                status_record = TensorFlowAnalysisStatus(file_id=file_id)
                db.add(status_record)
            
            # Update status fields
            status_record.status = status
            
            if status == AnalyzerStatus.ANALYZING:
                status_record.started_at = datetime.utcnow()
            elif status == AnalyzerStatus.ANALYZED:
                status_record.completed_at = datetime.utcnow()
                status_record.error_message = None
            elif status == AnalyzerStatus.FAILED:
                status_record.error_message = error_message
                status_record.retry_count += 1
            elif status == AnalyzerStatus.RETRY:
                status_record.error_message = error_message
                status_record.retry_count += 1
            
            # Store results if provided and status is ANALYZED
            if status == AnalyzerStatus.ANALYZED and results:
                analysis_results = results.get("analysis_results", {})
                analysis_duration = results.get("analysis_duration", 0)
                
                # Store detailed TensorFlow results
                tensorflow_analysis = analysis_results.get("tensorflow_analysis", {})
                mood_analysis = analysis_results.get("mood_analysis", {})
                genre_analysis = analysis_results.get("genre_analysis", {})
                
                # Get or create TensorFlow results record
                tf_results = db.query(TensorFlowAnalysisResults).filter(
                    TensorFlowAnalysisResults.file_id == file_id
                ).first()
                
                if not tf_results:
                    tf_results = TensorFlowAnalysisResults(file_id=file_id)
                    db.add(tf_results)
                
                # Store MusicNN predictions
                musicnn_results = tensorflow_analysis.get("musicnn", {})
                if musicnn_results and "error" not in musicnn_results:
                    tf_results.top_predictions = musicnn_results.get("top_predictions", [])
                    tf_results.all_predictions = musicnn_results.get("all_predictions", [])
                    tf_results.prediction_statistics = musicnn_results.get("statistics", {})
                
                # Store genre analysis
                if genre_analysis and "error" not in genre_analysis:
                    tf_results.genre_scores = genre_analysis.get("genre_scores", {})
                    
                    # Calculate dominant genres from scores
                    genre_scores = genre_analysis.get("genre_scores", {})
                    if genre_scores:
                        # Sort genres by score and get top 3
                        sorted_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)
                        tf_results.dominant_genres = [
                            {"genre": genre, "score": score} 
                            for genre, score in sorted_genres[:3] 
                            if score > 0.05  # Only include genres with significant scores
                        ]
                    else:
                        tf_results.dominant_genres = []
                
                # Store mood analysis
                if mood_analysis and "error" not in mood_analysis:
                    tf_results.mood_scores = mood_analysis.get("mood_scores", {})
                    
                    # Calculate dominant moods from scores
                    mood_scores = mood_analysis.get("mood_scores", {})
                    if mood_scores:
                        # Sort moods by score and get top 3
                        sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
                        tf_results.dominant_moods = [
                            {"mood": mood, "score": score} 
                            for mood, score in sorted_moods[:3] 
                            if score > 0.02  # Lower threshold for moods
                        ]
                    else:
                        tf_results.dominant_moods = []
                    
                    tf_results.emotion_dimensions = mood_analysis.get("emotions", {})
                
                # Store analysis metadata
                tf_results.model_used = "MusicNN"
                tf_results.analysis_timestamp = datetime.utcnow()
                tf_results.analysis_duration = analysis_duration
                
                # Also store primary mood in AudioMetadata for compatibility
                if mood_analysis and mood_analysis.get("primary_mood"):
                    from ..models.database_v2 import AudioMetadata
                    audio_metadata = db.query(AudioMetadata).filter(
                        AudioMetadata.file_id == file_id
                    ).first()
                    if audio_metadata:
                        audio_metadata.mood = mood_analysis.get("primary_mood")
                        audio_metadata.valence = mood_analysis.get("mood_confidence")
                
                # Update TrackAnalysisSummary with TensorFlow results
                from ..models.database_v2 import TrackAnalysisSummary
                track_summary = db.query(TrackAnalysisSummary).filter(
                    TrackAnalysisSummary.file_id == file_id
                ).first()
                
                if not track_summary:
                    track_summary = TrackAnalysisSummary(file_id=file_id)
                    db.add(track_summary)
                
                # Extract emotion dimensions from mood analysis if available
                if mood_analysis and mood_analysis.get("emotions"):
                    emotions = mood_analysis.get("emotions", {})
                    track_summary.tensorflow_valence = emotions.get("valence")
                    # Note: TensorFlow doesn't provide energy, BPM, key, scale, or danceability
                    # These should come from Essentia analysis
                
                # Extract other TensorFlow features from mood analysis
                if mood_analysis and mood_analysis.get("mood_scores"):
                    mood_scores = mood_analysis.get("mood_scores", {})
                    # Map mood scores to TensorFlow-style features
                    track_summary.tensorflow_acousticness = mood_scores.get("acoustic", 0.0)
                    track_summary.tensorflow_instrumentalness = mood_scores.get("instrumental", 0.0)
                    track_summary.tensorflow_speechiness = 1.0 - mood_scores.get("instrumental", 0.0)  # Inverse of instrumental
                    track_summary.tensorflow_liveness = mood_scores.get("energetic", 0.0)
                    # Note: TensorFlow doesn't provide danceability - this should come from Essentia
                
                # Update analysis status
                track_summary.analysis_status = "tensorflow_completed"
                track_summary.analysis_date = datetime.utcnow()
                track_summary.analysis_duration = analysis_duration
            
            db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update status for file {file_id}: {e}")
            db.rollback()
            return False
    
    def get_analyzed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get list of file IDs that have been successfully analyzed."""
        query = db.query(TensorFlowAnalysisStatus.file_id).filter(
            TensorFlowAnalysisStatus.status == AnalyzerStatus.ANALYZED
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_failed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get list of file IDs that failed analysis."""
        query = db.query(TensorFlowAnalysisStatus.file_id).filter(
            TensorFlowAnalysisStatus.status == AnalyzerStatus.FAILED
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_files_by_status(self, db: Session, status: AnalyzerStatus, 
                           limit: Optional[int] = None) -> List[int]:
        """Get files with a specific status."""
        query = db.query(TensorFlowAnalysisStatus.file_id).filter(
            TensorFlowAnalysisStatus.status == status
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_analysis_results(self, file_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get analysis results for a specific file.
        
        Args:
            file_id: Database ID of the file
            db: Database session
            
        Returns:
            Analysis results dictionary or None if not found
        """
        status_record = db.query(TensorFlowAnalysisStatus).filter(
            TensorFlowAnalysisStatus.file_id == file_id
        ).first()
        
        if not status_record or status_record.status != AnalyzerStatus.ANALYZED:
            return None
        
        # Get results from TensorFlowAnalysisResults
        tf_results = db.query(TensorFlowAnalysisResults).filter(
            TensorFlowAnalysisResults.file_id == file_id
        ).first()
        
        if not tf_results:
            return None
        
        return {
            "analysis_timestamp": tf_results.analysis_timestamp,
            "analysis_duration": tf_results.analysis_duration,
            "model_used": tf_results.model_used,
            
            # MusicNN predictions
            "top_predictions": tf_results.top_predictions,
            "all_predictions": tf_results.all_predictions,
            "prediction_statistics": tf_results.prediction_statistics,
            
            # Genre analysis
            "genre_scores": tf_results.genre_scores,
            "dominant_genres": tf_results.dominant_genres,
            
            # Mood analysis
            "mood_scores": tf_results.mood_scores,
            "dominant_moods": tf_results.dominant_moods,
            "emotion_dimensions": tf_results.emotion_dimensions
        }
    
    def is_available(self) -> bool:
        """Check if TensorFlow analyzer is available."""
        try:
            return self.analyzer.is_available()
        except Exception:
            return False
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration for TensorFlow analyzer."""
        config = super().get_configuration()
        config.update({
            "description": "Machine learning classification using TensorFlow models",
            "features": [
                "MusicNN model for music tag prediction",
                "Mood analysis and classification",
                "Genre prediction with confidence scores",
                "Mel-spectrogram feature extraction",
                "Streaming audio processing support"
            ],
            "models": self.analyzer.get_available_models() if hasattr(self.analyzer, 'get_available_models') else []
        })
        return config

# Create global instance
tensorflow_service = IndependentTensorFlowService()
