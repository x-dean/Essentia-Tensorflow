import logging
import time
import json
import hashlib
import numpy as np
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime

from .base_analyzer_service import BaseAnalyzerService
from ..models.database_v2 import (
    File, FAISSAnalysisStatus, FAISSAnalysisResults,
    AnalyzerStatus, get_db, SessionLocal
)
from .essentia_analyzer import essentia_analyzer

logger = logging.getLogger(__name__)

class IndependentFAISSService(BaseAnalyzerService):
    """
    Independent FAISS analyzer service.
    
    Handles vector indexing and similarity search using FAISS
    with independent status tracking and result storage.
    """
    
    def __init__(self):
        super().__init__("faiss")
        self.essentia_analyzer = essentia_analyzer
        
        # FAISS availability check
        try:
            import faiss
            self.FAISS_AVAILABLE = True
            logger.info("FAISS is available for vector indexing")
        except ImportError:
            self.FAISS_AVAILABLE = False
            logger.warning("FAISS not available. Install with: pip install faiss-cpu or faiss-gpu")
    
    def analyze_file(self, file_path: str, db: Session, include_tensorflow: bool = True) -> Dict[str, Any]:
        """
        Analyze a single file using FAISS vector indexing.
        
        Args:
            file_path: Path to the audio file
            db: Database session
            include_tensorflow: Whether to include TensorFlow features in vector
            
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
            self.logger.info(f"Starting FAISS analysis for {file_path}")
            
            # Extract feature vector
            feature_vector = self.essentia_analyzer.extract_feature_vector(
                file_path, 
                include_tensorflow=include_tensorflow
            )
            
            # Calculate vector hash for change detection
            vector_hash = hashlib.md5(feature_vector.tobytes()).hexdigest()
            
            # Calculate analysis duration
            analysis_duration = time.time() - start_time
            
            # Store results
            success = self.update_status(
                file_id, 
                AnalyzerStatus.ANALYZED, 
                db, 
                results={
                    "feature_vector": feature_vector,
                    "vector_hash": vector_hash,
                    "include_tensorflow": include_tensorflow,
                    "analysis_duration": analysis_duration
                }
            )
            
            if success:
                self.logger.info(f"FAISS analysis completed for {file_path} in {analysis_duration:.2f}s")
                return {
                    "success": True,
                    "file_path": file_path,
                    "file_id": file_id,
                    "analysis_duration": analysis_duration,
                    "vector_dimension": len(feature_vector),
                    "vector_hash": vector_hash,
                    "include_tensorflow": include_tensorflow
                }
            else:
                raise Exception("Failed to store analysis results")
                
        except Exception as e:
            analysis_duration = time.time() - start_time
            self.logger.error(f"FAISS analysis failed for {file_path}: {e}")
            
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
        status_record = db.query(FAISSAnalysisStatus).filter(
            FAISSAnalysisStatus.file_id == file_id
        ).first()
        
        if status_record:
            return status_record.status
        else:
            # Create status record if it doesn't exist
            status_record = FAISSAnalysisStatus(
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
        
        query = db.query(FAISSAnalysisStatus.file_id).filter(
            FAISSAnalysisStatus.status == AnalyzerStatus.PENDING
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def _ensure_status_records_exist(self, db: Session):
        """Ensure all active files have FAISS status records"""
        try:
            # Find files without FAISS status records
            files_without_status = db.query(File).filter(
                File.is_active == True,
                ~File.id.in_(db.query(FAISSAnalysisStatus.file_id))
            ).all()
            
            if files_without_status:
                self.logger.info(f"Creating FAISS status records for {len(files_without_status)} files")
                
                for file in files_without_status:
                    status_record = FAISSAnalysisStatus(
                        file_id=file.id,
                        status=AnalyzerStatus.PENDING
                    )
                    db.add(status_record)
                
                db.commit()
                self.logger.info(f"Created {len(files_without_status)} FAISS status records")
            
        except Exception as e:
            self.logger.error(f"Error ensuring FAISS status records exist: {e}")
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
            
            self.logger.info(f"Starting FAISS analysis for {len(file_ids)} files")
            
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
                "message": f"FAISS analysis completed: {successful} successful, {failed} failed",
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
            
            analyzed_count = db.query(FAISSAnalysisStatus).filter(
                FAISSAnalysisStatus.status == AnalyzerStatus.ANALYZED
            ).count()
            
            failed_count = db.query(FAISSAnalysisStatus).filter(
                FAISSAnalysisStatus.status == AnalyzerStatus.FAILED
            ).count()
            
            pending_count = db.query(FAISSAnalysisStatus).filter(
                FAISSAnalysisStatus.status == AnalyzerStatus.PENDING
            ).count()
            
            return {
                "total_files": total_files,
                "analyzed": analyzed_count,
                "failed": failed_count,
                "pending": pending_count,
                "coverage": (analyzed_count / total_files * 100) if total_files > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting FAISS stats: {e}")
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
            status_record = db.query(FAISSAnalysisStatus).filter(
                FAISSAnalysisStatus.file_id == file_id
            ).first()
            
            if not status_record:
                status_record = FAISSAnalysisStatus(file_id=file_id)
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
                feature_vector = results.get("feature_vector")
                vector_hash = results.get("vector_hash")
                include_tensorflow = results.get("include_tensorflow", True)
                analysis_duration = results.get("analysis_duration", 0)
                
                # Store detailed FAISS results
                faiss_results = db.query(FAISSAnalysisResults).filter(
                    FAISSAnalysisResults.file_id == file_id
                ).first()
                
                if not faiss_results:
                    faiss_results = FAISSAnalysisResults(file_id=file_id)
                    db.add(faiss_results)
                
                # Store vector data
                faiss_results.vector_data = feature_vector.tolist() if feature_vector is not None else None
                faiss_results.vector_dimension = len(feature_vector) if feature_vector is not None else 0
                faiss_results.vector_hash = vector_hash
                
                # Store analysis configuration
                faiss_results.includes_tensorflow = include_tensorflow
                faiss_results.is_normalized = True  # Default
                faiss_results.feature_weights = {"essentia": 0.6, "tensorflow": 0.4}  # Default weights
                
                # Store analysis metadata
                faiss_results.analysis_timestamp = datetime.utcnow()
                faiss_results.analysis_duration = analysis_duration
                faiss_results.analysis_version = "1.0"
            
            db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update status for file {file_id}: {e}")
            db.rollback()
            return False
    
    def get_analyzed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get list of file IDs that have been successfully analyzed."""
        query = db.query(FAISSAnalysisStatus.file_id).filter(
            FAISSAnalysisStatus.status == AnalyzerStatus.ANALYZED
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_failed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """Get list of file IDs that failed analysis."""
        query = db.query(FAISSAnalysisStatus.file_id).filter(
            FAISSAnalysisStatus.status == AnalyzerStatus.FAILED
        )
        
        if limit:
            query = query.limit(limit)
        
        return [row[0] for row in query.all()]
    
    def get_files_by_status(self, db: Session, status: AnalyzerStatus, 
                           limit: Optional[int] = None) -> List[int]:
        """Get files with a specific status."""
        query = db.query(FAISSAnalysisStatus.file_id).filter(
            FAISSAnalysisStatus.status == status
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
        status_record = db.query(FAISSAnalysisStatus).filter(
            FAISSAnalysisStatus.file_id == file_id
        ).first()
        
        if not status_record or status_record.status != AnalyzerStatus.ANALYZED:
            return None
        
        # Get results from FAISSAnalysisResults
        faiss_results = db.query(FAISSAnalysisResults).filter(
            FAISSAnalysisResults.file_id == file_id
        ).first()
        
        if not faiss_results:
            return None
        
        return {
            "analysis_timestamp": faiss_results.analysis_timestamp,
            "analysis_duration": faiss_results.analysis_duration,
            "analysis_version": faiss_results.analysis_version,
            
            # Vector data
            "vector_data": faiss_results.vector_data,
            "vector_dimension": faiss_results.vector_dimension,
            "vector_hash": faiss_results.vector_hash,
            
            # Index information
            "index_type": faiss_results.index_type,
            "index_position": faiss_results.index_position,
            "similarity_score": faiss_results.similarity_score,
            
            # Analysis configuration
            "includes_tensorflow": faiss_results.includes_tensorflow,
            "is_normalized": faiss_results.is_normalized,
            "feature_weights": faiss_results.feature_weights
        }
    
    def get_feature_vector(self, file_id: int, db: Session) -> Optional[np.ndarray]:
        """
        Get the feature vector for a specific file.
        
        Args:
            file_id: Database ID of the file
            db: Database session
            
        Returns:
            Feature vector as numpy array or None if not found
        """
        faiss_results = db.query(FAISSAnalysisResults).filter(
            FAISSAnalysisResults.file_id == file_id
        ).first()
        
        if faiss_results and faiss_results.vector_data:
            return np.array(faiss_results.vector_data, dtype=np.float32)
        return None
    
    def find_similar_tracks(self, query_file_id: int, db: Session, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar tracks using FAISS index.
        
        Args:
            query_file_id: Database ID of the query file
            db: Database session
            top_n: Number of similar tracks to return
            
        Returns:
            List of similar track dictionaries with similarity scores
        """
        try:
            # Get query vector
            query_vector = self.get_feature_vector(query_file_id, db)
            if query_vector is None:
                raise ValueError(f"No feature vector found for file {query_file_id}")
            
            # Get all analyzed files
            analyzed_file_ids = self.get_analyzed_files(db)
            if not analyzed_file_ids:
                return []
            
            # Calculate similarities (simple cosine similarity for now)
            similarities = []
            for file_id in analyzed_file_ids:
                if file_id == query_file_id:
                    continue
                
                target_vector = self.get_feature_vector(file_id, db)
                if target_vector is not None:
                    # Cosine similarity
                    similarity = np.dot(query_vector, target_vector) / (
                        np.linalg.norm(query_vector) * np.linalg.norm(target_vector)
                    )
                    similarities.append({
                        "file_id": file_id,
                        "similarity_score": float(similarity)
                    })
            
            # Sort by similarity and return top_n
            similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
            return similarities[:top_n]
            
        except Exception as e:
            self.logger.error(f"Error finding similar tracks: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if FAISS analyzer is available."""
        return self.FAISS_AVAILABLE
    
    def get_configuration(self) -> Dict[str, Any]:
        """Get current configuration for FAISS analyzer."""
        config = super().get_configuration()
        config.update({
            "description": "Vector similarity search using FAISS",
            "features": [
                "Feature vector extraction and indexing",
                "Similarity search and matching",
                "Vector persistence and management",
                "Integration with Essentia and TensorFlow features",
                "High-performance similarity search"
            ],
            "faiss_available": self.FAISS_AVAILABLE
        })
        return config

# Create global instance
faiss_service = IndependentFAISSService()
