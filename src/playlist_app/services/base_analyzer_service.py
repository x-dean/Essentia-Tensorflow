import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from datetime import datetime
import enum

from ..models.database_v2 import AnalyzerStatus

logger = logging.getLogger(__name__)

class BaseAnalyzerService(ABC):
    """
    Base class for all independent analyzer services.
    
    Each analyzer should inherit from this class and implement
    the required methods for independent operation.
    """
    
    def __init__(self, analyzer_name: str):
        self.analyzer_name = analyzer_name
        self.logger = logging.getLogger(f"{__name__}.{analyzer_name}")
    
    @abstractmethod
    def analyze_file(self, file_path: str, db: Session) -> Dict[str, Any]:
        """
        Analyze a single file and return results.
        
        Args:
            file_path: Path to the audio file
            db: Database session
            
        Returns:
            Dictionary with analysis results and metadata
        """
        pass
    
    @abstractmethod
    def get_status(self, file_id: int, db: Session) -> AnalyzerStatus:
        """
        Get the current analysis status for a file.
        
        Args:
            file_id: Database ID of the file
            db: Database session
            
        Returns:
            Current analyzer status
        """
        pass
    
    @abstractmethod
    def get_pending_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """
        Get list of file IDs that are pending analysis.
        
        Args:
            db: Database session
            limit: Maximum number of files to return
            
        Returns:
            List of file IDs pending analysis
        """
        pass
    
    @abstractmethod
    def update_status(self, file_id: int, status: AnalyzerStatus, 
                     db: Session, results: Optional[Dict] = None, 
                     error_message: Optional[str] = None) -> bool:
        """
        Update the analysis status for a file.
        
        Args:
            file_id: Database ID of the file
            status: New status to set
            db: Database session
            results: Analysis results to store (if status is ANALYZED)
            error_message: Error message (if status is FAILED)
            
        Returns:
            True if update was successful
        """
        pass
    
    @abstractmethod
    def get_analyzed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """
        Get list of file IDs that have been successfully analyzed.
        
        Args:
            db: Database session
            limit: Maximum number of files to return
            
        Returns:
            List of file IDs that have been analyzed
        """
        pass
    
    @abstractmethod
    def get_failed_files(self, db: Session, limit: Optional[int] = None) -> List[int]:
        """
        Get list of file IDs that failed analysis.
        
        Args:
            db: Database session
            limit: Maximum number of files to return
            
        Returns:
            List of file IDs that failed analysis
        """
        pass
    
    def mark_for_retry(self, file_id: int, db: Session, error_message: Optional[str] = None) -> bool:
        """
        Mark a file for retry analysis.
        
        Args:
            file_id: Database ID of the file
            db: Database session
            error_message: Optional error message to store
            
        Returns:
            True if marked for retry successfully
        """
        return self.update_status(file_id, AnalyzerStatus.RETRY, db, error_message=error_message)
    
    def get_stats(self, db: Session) -> Dict[str, Any]:
        """
        Get statistics about this analyzer's performance.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Get counts for each status
            pending_count = len(self.get_pending_files(db))
            analyzed_count = len(self.get_analyzed_files(db))
            failed_count = len(self.get_failed_files(db))
            
            # Get retry count
            retry_count = len(self.get_files_by_status(db, AnalyzerStatus.RETRY))
            
            total = pending_count + analyzed_count + failed_count + retry_count
            
            return {
                "analyzer_name": self.analyzer_name,
                "total_files": total,
                "pending": pending_count,
                "analyzed": analyzed_count,
                "failed": failed_count,
                "retry": retry_count,
                "success_rate": (analyzed_count / total * 100) if total > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Error getting stats: {e}")
            return {
                "analyzer_name": self.analyzer_name,
                "error": str(e)
            }
    
    @abstractmethod
    def get_files_by_status(self, db: Session, status: AnalyzerStatus, 
                           limit: Optional[int] = None) -> List[int]:
        """
        Get files with a specific status.
        
        Args:
            db: Database session
            status: Status to filter by
            limit: Maximum number of files to return
            
        Returns:
            List of file IDs with the specified status
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if this analyzer is available for use.
        
        Returns:
            True if analyzer is available
        """
        return True
    
    def get_configuration(self) -> Dict[str, Any]:
        """
        Get current configuration for this analyzer.
        
        Returns:
            Dictionary with configuration
        """
        return {
            "analyzer_name": self.analyzer_name,
            "available": self.is_available()
        }
