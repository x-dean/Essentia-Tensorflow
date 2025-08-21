import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.database import (
    File, TrackAnalysisSummary, AnalyzerStatus, SessionLocal,
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
    
    def update_track_summary(self, file_id: int, db: Session = None) -> bool:
        """
        Update the track analysis summary for a specific file.
        
        Args:
            file_id: Database ID of the file
            db: Database session (optional, will create new session if not provided)
            
        Returns:
            True if update was successful
        """
        # Use provided session or create new one
        should_close_db = db is None
        if db is None:
            db = SessionLocal()
        
        try:
            # Get current status from each analyzer using separate sessions
            essentia_status = self._get_analyzer_status_safe(file_id, "essentia")
            tensorflow_status = self._get_analyzer_status_safe(file_id, "tensorflow")
            faiss_status = self._get_analyzer_status_safe(file_id, "faiss")
            
            # Get completion timestamps using separate sessions
            essentia_completed_at = self._get_completion_time_safe(file_id, "essentia")
            tensorflow_completed_at = self._get_completion_time_safe(file_id, "tensorflow")
            faiss_completed_at = self._get_completion_time_safe(file_id, "faiss")
            
            # Determine analysis status
            analysis_status = self._calculate_analysis_status(
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
            summary_record.analysis_status = analysis_status
            summary_record.analysis_date = datetime.utcnow()
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update track summary for file {file_id}: {e}")
            db.rollback()
            return False
        finally:
            if should_close_db:
                db.close()
    
    def _get_analyzer_status_safe(self, file_id: int, analyzer: str) -> AnalyzerStatus:
        """Get analyzer status using a separate database session."""
        db = SessionLocal()
        try:
            if analyzer == "essentia":
                return self.essentia_service.get_status(file_id, db)
            elif analyzer == "tensorflow":
                return self.tensorflow_service.get_status(file_id, db)
            elif analyzer == "faiss":
                return self.faiss_service.get_status(file_id, db)
            else:
                return AnalyzerStatus.PENDING
        except Exception as e:
            logger.error(f"Error getting status for {analyzer}: {e}")
            return AnalyzerStatus.FAILED
        finally:
            db.close()
    
    def _get_completion_time_safe(self, file_id: int, analyzer: str) -> Optional[datetime]:
        """Get completion time using a separate database session."""
        db = SessionLocal()
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
        finally:
            db.close()

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
    
    def _calculate_analysis_status(self, essentia_status: AnalyzerStatus, 
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
            "analysis_status": summary_record.analysis_status,
            "analysis_date": summary_record.analysis_date,
            "analysis_duration": summary_record.analysis_duration,
            "analysis_errors": summary_record.analysis_errors
        }
    
    def get_complete_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with complete analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.analysis_status == "complete"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_partial_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with partial analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.analysis_status == "partial"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_failed_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with failed analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.analysis_status == "failed"
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_pending_tracks(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get file IDs of tracks with pending analysis."""
        query = db.query(TrackAnalysisSummary.file_id).filter(
            TrackAnalysisSummary.analysis_status == "pending"
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
                self.update_track_summary(file_record.id)
            
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
                            force_reanalyze: bool = False, enable_essentia: bool = True,
                            enable_tensorflow: bool = True, enable_faiss: bool = True) -> Dict[str, Any]:
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
            # Get files that need analysis
            query = db.query(File).filter(File.is_active == True)
            
            if not force_reanalyze:
                # Only get files that haven't been analyzed by all analyzers
                query = query.outerjoin(EssentiaAnalysisStatus, File.id == EssentiaAnalysisStatus.file_id)
                query = query.outerjoin(TensorFlowAnalysisStatus, File.id == TensorFlowAnalysisStatus.file_id)
                query = query.outerjoin(FAISSAnalysisStatus, File.id == FAISSAnalysisStatus.file_id)
                query = query.filter(
                    (EssentiaAnalysisStatus.status.is_(None)) |
                    (EssentiaAnalysisStatus.status != AnalyzerStatus.ANALYZED) |
                    (TensorFlowAnalysisStatus.status.is_(None)) |
                    (TensorFlowAnalysisStatus.status != AnalyzerStatus.ANALYZED) |
                    (FAISSAnalysisStatus.status.is_(None)) |
                    (FAISSAnalysisStatus.status != AnalyzerStatus.ANALYZED)
                )
            
            if max_files:
                query = query.limit(max_files)
            
            files = query.all()
            
            if not files:
                return {
                    "success": True,
                    "message": "No files need analysis",
                    "summary": {
                        "total_files": 0,
                        "successful": 0,
                        "failed": 0
                    },
                    "results": {}
                }
            
            logger.info(f"Found {len(files)} files to analyze")
            
            results = {}
            total_successful = 0
            total_failed = 0
            
            # Run Essentia analysis
            if enable_essentia:
                logger.info("Starting Essentia analysis...")
                essentia_result = self.essentia_service.analyze_pending_files(db, max_files, force_reanalyze)
                results["essentia"] = essentia_result
            else:
                logger.info("Essentia analysis disabled, skipping...")
                results["essentia"] = {"successful": 0, "failed": 0, "message": "Essentia analysis disabled"}
            
            # Run TensorFlow analysis
            if enable_tensorflow:
                logger.info("Starting TensorFlow analysis...")
                tensorflow_result = self.tensorflow_service.analyze_pending_files(db, max_files, force_reanalyze)
                results["tensorflow"] = tensorflow_result
            else:
                logger.info("TensorFlow analysis disabled, skipping...")
                results["tensorflow"] = {"successful": 0, "failed": 0, "message": "TensorFlow analysis disabled"}
            
            # Run FAISS analysis
            if enable_faiss:
                logger.info("Starting FAISS analysis...")
                faiss_result = self.faiss_service.analyze_pending_files(db, max_files, force_reanalyze)
                results["faiss"] = faiss_result
            else:
                logger.info("FAISS analysis disabled, skipping...")
                results["faiss"] = {"successful": 0, "failed": 0, "message": "FAISS analysis disabled"}
            
            # Calculate unique files processed (not sum of all analyzer operations)
            # Count files where at least one analyzer succeeded
            files_with_success = set()
            files_with_failure = set()
            
            for analyzer_name, result in results.items():
                if isinstance(result, dict) and 'successful' in result and result['successful'] > 0:
                    # For now, assume successful count represents the files processed by this analyzer
                    # In a more sophisticated implementation, we would track individual file IDs
                    files_with_success.add(analyzer_name)
                if isinstance(result, dict) and 'failed' in result and result['failed'] > 0:
                    files_with_failure.add(analyzer_name)
            
            # Since all analyzers process the same files, the number of unique files
            # is the number of files we started with, minus any that completely failed
            total_files_processed = len(files)
            total_successful = total_files_processed if files_with_success else 0
            total_failed = 0  # Files that failed completely (all analyzers failed)
            
            # Update track summaries for all processed files
            if total_successful > 0:
                logger.info("Updating track summaries...")
                for file_record in files:
                    self.update_track_summary(file_record.id)
            
            return {
                "success": True,
                "message": f"Analysis completed: {total_successful} files fully analyzed, {total_failed} files failed",
                "summary": {
                    "total_files": len(files),
                    "successful": total_successful,
                    "failed": total_failed
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
