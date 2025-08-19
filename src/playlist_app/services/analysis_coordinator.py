import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.database import (
    File, TrackAnalysisSummary, AnalyzerStatus, get_db_session, close_db_session,
    EssentiaAnalysisStatus, TensorFlowAnalysisStatus, FAISSAnalysisStatus
)
from .independent_essentia_service import essentia_service
from .independent_tensorflow_service import tensorflow_service
from .independent_faiss_service import faiss_service

logger = logging.getLogger(__name__)

class AnalysisCoordinator:
    """
    Coordinates between independent analyzers and manages the track analysis summary.
    
    This service:
    - Updates the track analysis summary table
    - Provides overall analysis status
    - Coordinates analysis workflows
    - Manages dependencies between analyzers
    """
    
    def __init__(self):
        self.essentia_service = essentia_service
        self.tensorflow_service = tensorflow_service
        self.faiss_service = faiss_service
    
    def update_track_summary(self, file_id: int, db: Session) -> bool:
        """
        Update the track analysis summary for a specific file.
        
        Args:
            file_id: Database ID of the file
            db: Database session
            
        Returns:
            True if update was successful
        """
        try:
            # Get current status from each analyzer
            essentia_status = self.essentia_service.get_status(file_id, db)
            tensorflow_status = self.tensorflow_service.get_status(file_id, db)
            faiss_status = self.faiss_service.get_status(file_id, db)
            
            # Get completion timestamps
            essentia_completed_at = self._get_completion_time(file_id, "essentia", db)
            tensorflow_completed_at = self._get_completion_time(file_id, "tensorflow", db)
            faiss_completed_at = self._get_completion_time(file_id, "faiss", db)
            
            # Determine overall status
            overall_status = self._calculate_overall_status(
                essentia_status, tensorflow_status, faiss_status
            )
            
            # Get or create summary record
            summary_record = db.query(TrackAnalysisSummary).filter(
                TrackAnalysisSummary.file_id == file_id
            ).first()
            
            if not summary_record:
                summary_record = TrackAnalysisSummary(file_id=file_id)
                db.add(summary_record)
            
            # Update summary fields
            summary_record.essentia_status = essentia_status
            summary_record.tensorflow_status = tensorflow_status
            summary_record.faiss_status = faiss_status
            summary_record.essentia_completed_at = essentia_completed_at
            summary_record.tensorflow_completed_at = tensorflow_completed_at
            summary_record.faiss_completed_at = faiss_completed_at
            summary_record.overall_status = overall_status
            summary_record.last_updated = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update track summary for file {file_id}: {e}")
            db.rollback()
            return False
    
    def _get_completion_time(self, file_id: int, analyzer: str, db: Session) -> Optional[datetime]:
        """Get completion time for a specific analyzer."""
        try:
            if analyzer == "essentia":
                status_record = db.query(EssentiaAnalysisStatus).filter(
                    EssentiaAnalysisStatus.file_id == file_id
                ).first()
            elif analyzer == "tensorflow":
                status_record = db.query(TensorFlowAnalysisStatus).filter(
                    TensorFlowAnalysisStatus.file_id == file_id
                ).first()
            elif analyzer == "faiss":
                status_record = db.query(FAISSAnalysisStatus).filter(
                    FAISSAnalysisStatus.file_id == file_id
                ).first()
            else:
                return None
            
            return status_record.completed_at if status_record else None
            
        except Exception as e:
            logger.error(f"Error getting completion time for {analyzer}: {e}")
            return None
    
    def _calculate_overall_status(self, essentia_status: AnalyzerStatus, 
                                tensorflow_status: AnalyzerStatus, 
                                faiss_status: AnalyzerStatus) -> str:
        """
        Calculate overall analysis status based on individual analyzer statuses.
        
        Returns:
            "complete" - All analyzers completed successfully
            "partial" - Some analyzers completed, some failed or pending
            "failed" - All analyzers failed
            "pending" - All analyzers pending
        """
        # Count statuses
        analyzed_count = sum(1 for status in [essentia_status, tensorflow_status, faiss_status] 
                           if status == AnalyzerStatus.ANALYZED)
        failed_count = sum(1 for status in [essentia_status, tensorflow_status, faiss_status] 
                          if status == AnalyzerStatus.FAILED)
        pending_count = sum(1 for status in [essentia_status, tensorflow_status, faiss_status] 
                           if status == AnalyzerStatus.PENDING)
        
        if analyzed_count == 3:
            return "complete"
        elif failed_count == 3:
            return "failed"
        elif pending_count == 3:
            return "pending"
        else:
            return "partial"
    
    def get_track_summary(self, file_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """
        Get the analysis summary for a specific track.
        
        Args:
            file_id: Database ID of the file
            db: Database session
            
        Returns:
            Summary dictionary or None if not found
        """
        summary_record = db.query(TrackAnalysisSummary).filter(
            TrackAnalysisSummary.file_id == file_id
        ).first()
        
        if not summary_record:
            return None
        
        return {
            "file_id": summary_record.file_id,
            "essentia_status": summary_record.essentia_status.value if summary_record.essentia_status else None,
            "tensorflow_status": summary_record.tensorflow_status.value if summary_record.tensorflow_status else None,
            "faiss_status": summary_record.faiss_status.value if summary_record.faiss_status else None,
            "essentia_completed_at": summary_record.essentia_completed_at,
            "tensorflow_completed_at": summary_record.tensorflow_completed_at,
            "faiss_completed_at": summary_record.faiss_completed_at,
            "overall_status": summary_record.overall_status,
            "last_updated": summary_record.last_updated
        }
    
    def get_complete_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with complete analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.overall_status == "complete"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_partial_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with partial analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.overall_status == "partial"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_failed_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with failed analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.overall_status == "failed"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_pending_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with pending analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.overall_status == "pending"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_analysis_stats(self, db: Session) -> Dict[str, Any]:
        """
        Get overall analysis statistics.
        
        Returns:
            Dictionary with analysis statistics
        """
        try:
            # Get counts for each overall status
            complete_count = len(self.get_complete_tracks(db))
            partial_count = len(self.get_partial_tracks(db))
            failed_count = len(self.get_failed_tracks(db))
            pending_count = len(self.get_pending_tracks(db))
            
            # Get individual analyzer stats
            essentia_stats = self.essentia_service.get_stats(db)
            tensorflow_stats = self.tensorflow_service.get_stats(db)
            faiss_stats = self.faiss_service.get_stats(db)
            
            total = complete_count + partial_count + failed_count + pending_count
            
            return {
                "overall": {
                    "total_tracks": total,
                    "complete": complete_count,
                    "partial": partial_count,
                    "failed": failed_count,
                    "pending": pending_count,
                    "completion_rate": (complete_count / total * 100) if total > 0 else 0
                },
                "analyzers": {
                    "essentia": essentia_stats,
                    "tensorflow": tensorflow_stats,
                    "faiss": faiss_stats
                }
            }
        except Exception as e:
            logger.error(f"Error getting analysis stats: {e}")
            return {"error": str(e)}
    
    def analyze_track_complete(self, file_path: str, db: Session, 
                             enable_essentia: bool = True,
                             enable_tensorflow: bool = True,
                             enable_faiss: bool = True) -> Dict[str, Any]:
        """
        Analyze a track with all enabled analyzers.
        
        Args:
            file_path: Path to the audio file
            db: Database session
            enable_essentia: Whether to run Essentia analysis
            enable_tensorflow: Whether to run TensorFlow analysis
            enable_faiss: Whether to run FAISS analysis
            
        Returns:
            Dictionary with analysis results
        """
        results = {
            "file_path": file_path,
            "essentia": None,
            "tensorflow": None,
            "faiss": None,
            "overall_success": False
        }
        
        try:
            # Run Essentia analysis if enabled
            if enable_essentia and self.essentia_service.is_available():
                results["essentia"] = self.essentia_service.analyze_file(file_path, db)
            
            # Run TensorFlow analysis if enabled
            if enable_tensorflow and self.tensorflow_service.is_available():
                results["tensorflow"] = self.tensorflow_service.analyze_file(file_path, db)
            
            # Run FAISS analysis if enabled
            if enable_faiss and self.faiss_service.is_available():
                results["faiss"] = self.faiss_service.analyze_file(file_path, db)
            
            # Update track summary
            file_record = db.query(File).filter(File.file_path == file_path).first()
            if file_record:
                self.update_track_summary(file_record.id, db)
            
            # Determine overall success
            success_count = sum(1 for result in [results["essentia"], results["tensorflow"], results["faiss"]] 
                              if result and result.get("success", False))
            enabled_count = sum([enable_essentia, enable_tensorflow, enable_faiss])
            
            results["overall_success"] = success_count > 0
            
            return results
            
        except Exception as e:
            logger.error(f"Error in complete track analysis: {e}")
            results["error"] = str(e)
            return results
    
    def get_analyzer_status(self) -> Dict[str, Any]:
        """
        Get status of all analyzers.
        
        Returns:
            Dictionary with analyzer status information
        """
        return {
            "essentia": {
                "available": self.essentia_service.is_available(),
                "config": self.essentia_service.get_configuration()
            },
            "tensorflow": {
                "available": self.tensorflow_service.is_available(),
                "config": self.tensorflow_service.get_configuration()
            },
            "faiss": {
                "available": self.faiss_service.is_available(),
                "config": self.faiss_service.get_configuration()
            }
        }
    
    def analyze_pending_files(self, db: Session, max_files: Optional[int] = None, 
                            force_reanalyze: bool = False) -> Dict[str, Any]:
        """
        Analyze all pending files using all analyzers.
        
        Args:
            db: Database session
            max_files: Maximum number of files to analyze
            force_reanalyze: Whether to force reanalysis of existing files
            
        Returns:
            Dictionary with analysis results
        """
        try:
            results = {}
            
            # Run Essentia analysis
            logger.info("Starting Essentia analysis...")
            essentia_result = self.essentia_service.analyze_pending_files(db, max_files, force_reanalyze)
            results["essentia"] = essentia_result
            
            # Run TensorFlow analysis
            logger.info("Starting TensorFlow analysis...")
            tensorflow_result = self.tensorflow_service.analyze_pending_files(db, max_files, force_reanalyze)
            results["tensorflow"] = tensorflow_result
            
            # Run FAISS analysis
            logger.info("Starting FAISS analysis...")
            faiss_result = self.faiss_service.analyze_pending_files(db, max_files, force_reanalyze)
            results["faiss"] = faiss_result
            
            # Calculate combined statistics
            total_files = sum(r.get('total_files', 0) for r in results.values())
            successful = sum(r.get('successful', 0) for r in results.values())
            failed = sum(r.get('failed', 0) for r in results.values())
            
            # Update track summaries for all processed files
            if successful > 0:
                logger.info("Updating track summaries...")
                for analyzer_result in results.values():
                    if analyzer_result.get('results'):
                        for result in analyzer_result['results']:
                            if result.get('file_path'):
                                file_record = db.query(File).filter(File.file_path == result['file_path']).first()
                                if file_record:
                                    self.update_track_summary(file_record.id, db)
            
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
            
        except Exception as e:
            logger.error(f"Error in analyze_pending_files: {e}")
            return {
                "success": False,
                "error": str(e),
                "summary": {
                    "total_files": 0,
                    "successful": 0,
                    "failed": 0
                },
                "results": {}
            }

# Create global instance
analysis_coordinator = AnalysisCoordinator()
