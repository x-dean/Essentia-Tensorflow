import logging
import time
import json
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from .base_analyzer_service import BaseAnalyzerService
from ..models.database_v2 import (
    File, EssentiaAnalysisStatus, EssentiaAnalysisResults,
    AnalyzerStatus, get_db, SessionLocal
)
from .essentia_analyzer import essentia_analyzer, safe_json_serialize

logger = logging.getLogger(__name__)

class IndependentEssentiaService(BaseAnalyzerService):
    """
    Independent Essentia analyzer service.
    
    Handles audio feature extraction using Essentia library
    with independent status tracking and result storage.
    """
    
    def __init__(self):
        super().__init__("essentia")
        self.analyzer = essentia_analyzer
    
    def analyze_file(self, file_path: str, db: Session) -> Dict[str, Any]:
        """
        Analyze a single file using Essentia.
        
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
            self.logger.info(f"Starting Essentia analysis for {file_path}")
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
                self.logger.info(f"Essentia analysis completed for {file_path} in {analysis_duration:.2f}s")
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
            self.logger.error(f"Essentia analysis failed for {file_path}: {e}")
            
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
        status_record = db.query(EssentiaAnalysisStatus).filter(
            EssentiaAnalysisStatus.file_id == file_id
        ).first()
        
        if status_record:
            return status_record.status
        else:
            # Create status record if it doesn't exist
            status_record = EssentiaAnalysisStatus(
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
        
        query = db.query(EssentiaAnalysisStatus.file_id).filter(
            EssentiaAnalysisStatus.status == AnalyzerStatus.PENDING
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def _ensure_status_records_exist(self, db: Session):
        """Ensure all active files have Essentia status records"""
        try:
            # Find files without Essentia status records
            files_without_status = db.query(File).filter(
                File.is_active == True,
                ~File.id.in_(db.query(EssentiaAnalysisStatus.file_id))
            ).all()
            
            if files_without_status:
                self.logger.info(f"Creating Essentia status records for {len(files_without_status)} files")
                
                for file in files_without_status:
                    status_record = EssentiaAnalysisStatus(
                        file_id=file.id,
                        status=AnalyzerStatus.PENDING
                    )
                    db.add(status_record)
                
                db.commit()
                self.logger.info(f"Created {len(files_without_status)} Essentia status records")
            
        except Exception as e:
            self.logger.error(f"Error ensuring Essentia status records exist: {e}")
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
            
            self.logger.info(f"Starting Essentia analysis for {len(file_ids)} files")
            
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
                "message": f"Essentia analysis completed: {successful} successful, {failed} failed",
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
            
            analyzed_count = db.query(EssentiaAnalysisStatus).filter(
                EssentiaAnalysisStatus.status == AnalyzerStatus.ANALYZED
            ).count()
            
            failed_count = db.query(EssentiaAnalysisStatus).filter(
                EssentiaAnalysisStatus.status == AnalyzerStatus.FAILED
            ).count()
            
            pending_count = db.query(EssentiaAnalysisStatus).filter(
                EssentiaAnalysisStatus.status == AnalyzerStatus.PENDING
            ).count()
            
            return {
                "total_files": total_files,
                "analyzed": analyzed_count,
                "failed": failed_count,
                "pending": pending_count,
                "coverage": (analyzed_count / total_files * 100) if total_files > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting Essentia stats: {e}")
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
            status_record = db.query(EssentiaAnalysisStatus).filter(
                EssentiaAnalysisStatus.file_id == file_id
            ).first()
            
            if not status_record:
                status_record = EssentiaAnalysisStatus(file_id=file_id)
                db.add(status_record)
            
            # Update status fields
            status_record.status = status
            status_record.last_attempt = datetime.utcnow()
            
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
                
                # Store detailed Essentia results
                rhythm_features = analysis_results.get("rhythm_features", {})
                harmonic_features = analysis_results.get("harmonic_features", {})
                danceability_features = analysis_results.get("danceability_features", {})
                basic_features = analysis_results.get("basic_features", {})
                spectral_features = analysis_results.get("spectral_features", {})
                mfcc_features = analysis_results.get("mfcc_features", {})
                
                # Get or create Essentia results record
                essentia_results = db.query(EssentiaAnalysisResults).filter(
                    EssentiaAnalysisResults.file_id == file_id
                ).first()
                
                if not essentia_results:
                    essentia_results = EssentiaAnalysisResults(file_id=file_id)
                    db.add(essentia_results)
                
                # Store rhythm analysis
                essentia_results.bpm = rhythm_features.get("bpm")
                essentia_results.rhythm_confidence = rhythm_features.get("rhythm_confidence")
                essentia_results.beat_loudness = rhythm_features.get("beat_loudness")
                essentia_results.beat_loudness_band_ratio = rhythm_features.get("beat_loudness_band_ratio")
                
                # Store harmonic analysis
                essentia_results.key = harmonic_features.get("key")
                essentia_results.scale = harmonic_features.get("scale")
                essentia_results.key_strength = harmonic_features.get("key_strength")
                essentia_results.key_scale_strength = harmonic_features.get("key_scale_strength")
                essentia_results.hpcp = harmonic_features.get("hpcp")
                
                # Store spectral analysis
                essentia_results.spectral_centroid = spectral_features.get("spectral_centroid")
                essentia_results.spectral_rolloff = spectral_features.get("spectral_rolloff")
                essentia_results.spectral_bandwidth = spectral_features.get("spectral_bandwidth")
                essentia_results.spectral_contrast = spectral_features.get("spectral_contrast")
                essentia_results.spectral_peaks = spectral_features.get("spectral_peaks")
                
                # Store basic features
                essentia_results.energy = basic_features.get("energy")
                essentia_results.loudness = basic_features.get("loudness")
                essentia_results.dynamic_complexity = basic_features.get("dynamic_complexity")
                essentia_results.zero_crossing_rate = basic_features.get("zero_crossing_rate")
                
                # Store danceability
                essentia_results.danceability = danceability_features.get("danceability")
                essentia_results.rhythm_strength = danceability_features.get("rhythm_strength")
                essentia_results.rhythm_regularity = danceability_features.get("rhythm_regularity")
                
                # Store MFCC features
                essentia_results.mfcc = mfcc_features.get("mfcc")
                
                # Store analysis metadata
                essentia_results.analysis_timestamp = datetime.utcnow()
                essentia_results.analysis_duration = analysis_duration
                essentia_results.analysis_version = "2.1"
                
                # Also store key summary features in TrackAnalysisSummary for compatibility
                from ..models.database_v2 import TrackAnalysisSummary
                track_summary = db.query(TrackAnalysisSummary).filter(
                    TrackAnalysisSummary.file_id == file_id
                ).first()
                
                if not track_summary:
                    track_summary = TrackAnalysisSummary(file_id=file_id)
                    db.add(track_summary)
                
                # Update with key Essentia results for quick access
                track_summary.bpm = essentia_results.bpm
                track_summary.key = essentia_results.key
                track_summary.scale = essentia_results.scale
                track_summary.energy = essentia_results.energy
                track_summary.danceability = essentia_results.danceability
                track_summary.loudness = essentia_results.loudness
                track_summary.dynamic_complexity = essentia_results.dynamic_complexity
                track_summary.rhythm_confidence = essentia_results.rhythm_confidence
                track_summary.key_strength = essentia_results.key_strength
                
                track_summary.analysis_status = "essentia_completed"
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
        query = db.query(EssentiaAnalysisStatus.file_id).filter(
            EssentiaAnalysisStatus.status == AnalyzerStatus.ANALYZED
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_failed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get list of file IDs that failed analysis."""
        query = db.query(EssentiaAnalysisStatus.file_id).filter(
            EssentiaAnalysisStatus.status == AnalyzerStatus.FAILED
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_files_by_status(self, db: Session, status: AnalyzerStatus, 
                           limit: Optional[int] = None) -> List[int]:
        """Get files with a specific status."""
        query = db.query(EssentiaAnalysisStatus.file_id).filter(
            EssentiaAnalysisStatus.status == status
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
        status_record = db.query(EssentiaAnalysisStatus).filter(
            EssentiaAnalysisStatus.file_id == file_id
        ).first()
        
        if not status_record or status_record.status != AnalyzerStatus.ANALYZED:
            return None
        
        # Get results from EssentiaAnalysisResults
        essentia_results = db.query(EssentiaAnalysisResults).filter(
            EssentiaAnalysisResults.file_id == file_id
        ).first()
        
        if not essentia_results:
            return None
        
        return {
            "analysis_timestamp": essentia_results.analysis_timestamp,
            "analysis_duration": essentia_results.analysis_duration,
            "analysis_version": essentia_results.analysis_version,
            
            # Rhythm analysis
            "bpm": essentia_results.bpm,
            "rhythm_confidence": essentia_results.rhythm_confidence,
            "beat_loudness": essentia_results.beat_loudness,
            "beat_loudness_band_ratio": essentia_results.beat_loudness_band_ratio,
            
            # Harmonic analysis
            "key": essentia_results.key,
            "scale": essentia_results.scale,
            "key_strength": essentia_results.key_strength,
            "key_scale_strength": essentia_results.key_scale_strength,
            "hpcp": essentia_results.hpcp,
            
            # Spectral analysis
            "spectral_centroid": essentia_results.spectral_centroid,
            "spectral_rolloff": essentia_results.spectral_rolloff,
            "spectral_bandwidth": essentia_results.spectral_bandwidth,
            "spectral_contrast": essentia_results.spectral_contrast,
            "spectral_peaks": essentia_results.spectral_peaks,
            
            # Basic features
            "energy": essentia_results.energy,
            "loudness": essentia_results.loudness,
            "dynamic_complexity": essentia_results.dynamic_complexity,
            "zero_crossing_rate": essentia_results.zero_crossing_rate,
            
            # Danceability
            "danceability": essentia_results.danceability,
            "rhythm_strength": essentia_results.rhythm_strength,
            "rhythm_regularity": essentia_results.rhythm_regularity,
            
            # MFCC features
            "mfcc": essentia_results.mfcc
        }
    
    def is_available(self) -> bool:
        """Check if Essentia analyzer is available."""
        try:
            # Test if essentia analyzer is working
            return hasattr(self.analyzer, 'analyze_audio_file')
        except Exception:
            return False
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration for Essentia analyzer."""
        config = super().get_configuration()
        config.update({
            "description": "Audio feature extraction using Essentia library",
            "features": [
                "Basic audio features (RMS, energy, loudness)",
                "Rhythm analysis (tempo, beat tracking)",
                "Harmonic analysis (key detection)",
                "Spectral features (MFCC, spectral centroid)",
                "Danceability analysis"
            ]
        })
        return config

# Create global instance
essentia_service = IndependentEssentiaService()
