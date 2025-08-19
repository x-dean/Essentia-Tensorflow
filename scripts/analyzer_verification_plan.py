#!/usr/bin/env python3
"""
Comprehensive Analyzer Verification Plan and Testing Script

This script verifies each analyzer independently and tests their database integration.
It provides a complete testing framework for the modular analysis system.

Testing Plan:
1. Database Schema Verification
2. Individual Analyzer Testing
3. Database Integration Testing
4. Control Value Verification
5. End-to-End Workflow Testing
"""

import sys
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(os.path.dirname(current_dir), 'src')
sys.path.insert(0, src_path)

from sqlalchemy.orm import Session
from playlist_app.models.database import (
    get_db_session, close_db_session, File, FileStatus, AnalyzerStatus,
    EssentiaAnalysisStatus, TensorFlowAnalysisStatus, FAISSAnalysisStatus,
    EssentiaAnalysisResults, TensorFlowAnalysisResults, FAISSAnalysisResults,
    TrackAnalysisSummary
)
from playlist_app.services.independent_essentia_service import IndependentEssentiaService
from playlist_app.services.independent_tensorflow_service import IndependentTensorFlowService
from playlist_app.services.independent_faiss_service import IndependentFAISSService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalyzerVerificationPlan:
    """
    Comprehensive verification plan for all analyzers.
    
    This class provides methods to:
    1. Verify database schema and control values
    2. Test each analyzer independently
    3. Verify database integration
    4. Test end-to-end workflows
    """
    
    def __init__(self):
        self.db = None
        self.essentia_service = IndependentEssentiaService()
        self.tensorflow_service = IndependentTensorFlowService()
        self.faiss_service = IndependentFAISSService()
        
        # Test results storage
        self.test_results = {
            "database_schema": {},
            "essentia_analyzer": {},
            "tensorflow_analyzer": {},
            "faiss_analyzer": {},
            "integration_tests": {},
            "control_values": {},
            "end_to_end": {}
        }
    
    def setup_database(self):
        """Setup database connection"""
        try:
            self.db = get_db_session()
            logger.info("Database connection established")
            return True
        except Exception as e:
            logger.error(f"Failed to setup database: {e}")
            return False
    
    def cleanup_database(self):
        """Cleanup database connection"""
        if self.db:
            close_db_session(self.db)
            logger.info("Database connection closed")
    
    def verify_database_schema(self) -> Dict[str, Any]:
        """
        Verify database schema and control values.
        
        Checks:
        - All required tables exist
        - Status enums are properly defined
        - Control values are accessible
        """
        logger.info("=== VERIFYING DATABASE SCHEMA ===")
        
        results = {
            "success": True,
            "tables": {},
            "enums": {},
            "control_values": {},
            "errors": []
        }
        
        try:
            # Check if tables exist by querying them
            tables_to_check = [
                "files", "essentia_analysis_status", "tensorflow_analysis_status", 
                "faiss_analysis_status", "essentia_analysis_results", 
                "tensorflow_analysis_results", "faiss_analysis_results",
                "track_analysis_summary", "faiss_index_metadata"
            ]
            
            for table in tables_to_check:
                try:
                    # Try to query the table
                    self.db.execute(f"SELECT 1 FROM {table} LIMIT 1")
                    results["tables"][table] = "exists"
                except Exception as e:
                    results["tables"][table] = f"missing: {e}"
                    results["errors"].append(f"Table {table} not accessible: {e}")
            
            # Verify enums
            try:
                # Check FileStatus enum
                file_statuses = [status.value for status in FileStatus]
                results["enums"]["FileStatus"] = file_statuses
                
                # Check AnalyzerStatus enum
                analyzer_statuses = [status.value for status in AnalyzerStatus]
                results["enums"]["AnalyzerStatus"] = analyzer_statuses
                
            except Exception as e:
                results["enums"]["error"] = str(e)
                results["errors"].append(f"Enum verification failed: {e}")
            
            # Check control values
            try:
                # Get sample files to understand control values
                sample_files = self.db.query(File).limit(5).all()
                results["control_values"]["sample_files_count"] = len(sample_files)
                
                if sample_files:
                    sample_file = sample_files[0]
                    results["control_values"]["file_fields"] = {
                        "status": sample_file.status.value if sample_file.status else None,
                        "has_metadata": sample_file.has_metadata,
                        "is_active": sample_file.is_active
                    }
                
                # Check analyzer status records
                essentia_status_count = self.db.query(EssentiaAnalysisStatus).count()
                tensorflow_status_count = self.db.query(TensorFlowAnalysisStatus).count()
                faiss_status_count = self.db.query(FAISSAnalysisStatus).count()
                
                results["control_values"]["analyzer_status_counts"] = {
                    "essentia": essentia_status_count,
                    "tensorflow": tensorflow_status_count,
                    "faiss": faiss_status_count
                }
                
            except Exception as e:
                results["control_values"]["error"] = str(e)
                results["errors"].append(f"Control values check failed: {e}")
            
            if results["errors"]:
                results["success"] = False
                logger.error(f"Database schema verification failed: {results['errors']}")
            else:
                logger.info("Database schema verification completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Schema verification failed: {e}")
            logger.error(f"Database schema verification failed: {e}")
        
        self.test_results["database_schema"] = results
        return results
    
    def verify_control_values(self) -> Dict[str, Any]:
        """
        Verify control values that trigger analyzer execution.
        
        Control values checked:
        - File status (DISCOVERED, HAS_METADATA, FAILED)
        - Analyzer status (PENDING, ANALYZING, ANALYZED, FAILED, RETRY)
        - File.is_active flag
        - File.has_metadata flag
        """
        logger.info("=== VERIFYING CONTROL VALUES ===")
        
        results = {
            "success": True,
            "file_statuses": {},
            "analyzer_statuses": {},
            "trigger_conditions": {},
            "errors": []
        }
        
        try:
            # Check file status distribution
            file_status_counts = {}
            for status in FileStatus:
                count = self.db.query(File).filter(File.status == status).count()
                file_status_counts[status.value] = count
            results["file_statuses"] = file_status_counts
            
            # Check analyzer status distribution
            analyzer_status_counts = {}
            for status in AnalyzerStatus:
                # Essentia
                essentia_count = self.db.query(EssentiaAnalysisStatus).filter(
                    EssentiaAnalysisStatus.status == status
                ).count()
                
                # TensorFlow
                tensorflow_count = self.db.query(TensorFlowAnalysisStatus).filter(
                    TensorFlowAnalysisStatus.status == status
                ).count()
                
                # FAISS
                faiss_count = self.db.query(FAISSAnalysisStatus).filter(
                    FAISSAnalysisStatus.status == status
                ).count()
                
                analyzer_status_counts[status.value] = {
                    "essentia": essentia_count,
                    "tensorflow": tensorflow_count,
                    "faiss": faiss_count
                }
            results["analyzer_statuses"] = analyzer_status_counts
            
            # Check trigger conditions
            # Files that should trigger analysis
            pending_files = self.db.query(File).filter(
                File.is_active == True,
                File.status == FileStatus.DISCOVERED
            ).count()
            
            files_with_metadata = self.db.query(File).filter(
                File.is_active == True,
                File.has_metadata == True
            ).count()
            
            results["trigger_conditions"] = {
                "files_ready_for_analysis": pending_files,
                "files_with_metadata": files_with_metadata,
                "active_files": self.db.query(File).filter(File.is_active == True).count(),
                "total_files": self.db.query(File).count()
            }
            
            # Check if status records exist for files
            files_without_status = self.db.query(File).filter(
                File.is_active == True,
                ~File.id.in_(
                    self.db.query(EssentiaAnalysisStatus.file_id)
                )
            ).count()
            
            results["trigger_conditions"]["files_without_essentia_status"] = files_without_status
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Control values verification failed: {e}")
            logger.error(f"Control values verification failed: {e}")
        
        self.test_results["control_values"] = results
        return results
    
    def test_essentia_analyzer(self) -> Dict[str, Any]:
        """
        Test Essentia analyzer independently.
        
        Tests:
        - Service initialization
        - Pending files detection
        - Single file analysis
        - Batch analysis
        - Database integration
        """
        logger.info("=== TESTING ESSENTIA ANALYZER ===")
        
        results = {
            "success": True,
            "service_initialization": {},
            "pending_files_detection": {},
            "single_file_analysis": {},
            "batch_analysis": {},
            "database_integration": {},
            "errors": []
        }
        
        try:
            # Test service initialization
            try:
                self.essentia_service = IndependentEssentiaService()
                results["service_initialization"]["success"] = True
                results["service_initialization"]["message"] = "Service initialized successfully"
            except Exception as e:
                results["service_initialization"]["success"] = False
                results["service_initialization"]["error"] = str(e)
                results["errors"].append(f"Service initialization failed: {e}")
            
            # Test pending files detection
            try:
                pending_files = self.essentia_service.get_pending_files(self.db, limit=10)
                results["pending_files_detection"]["count"] = len(pending_files)
                results["pending_files_detection"]["file_ids"] = pending_files[:5]  # First 5
                results["pending_files_detection"]["success"] = True
            except Exception as e:
                results["pending_files_detection"]["success"] = False
                results["pending_files_detection"]["error"] = str(e)
                results["errors"].append(f"Pending files detection failed: {e}")
            
            # Test single file analysis (if files exist)
            if pending_files:
                try:
                    test_file_id = pending_files[0]
                    test_file = self.db.query(File).filter(File.id == test_file_id).first()
                    
                    if test_file and os.path.exists(test_file.file_path):
                        analysis_result = self.essentia_service.analyze_file(test_file.file_path, self.db)
                        results["single_file_analysis"]["success"] = analysis_result.get("success", False)
                        results["single_file_analysis"]["result"] = analysis_result
                    else:
                        results["single_file_analysis"]["success"] = False
                        results["single_file_analysis"]["error"] = "Test file not found or doesn't exist"
                except Exception as e:
                    results["single_file_analysis"]["success"] = False
                    results["single_file_analysis"]["error"] = str(e)
                    results["errors"].append(f"Single file analysis failed: {e}")
            
            # Test batch analysis
            try:
                batch_result = self.essentia_service.analyze_pending_files(self.db, max_files=2)
                results["batch_analysis"]["success"] = batch_result.get("success", False)
                results["batch_analysis"]["result"] = batch_result
            except Exception as e:
                results["batch_analysis"]["success"] = False
                results["batch_analysis"]["error"] = str(e)
                results["errors"].append(f"Batch analysis failed: {e}")
            
            # Test database integration
            try:
                stats = self.essentia_service.get_stats(self.db)
                results["database_integration"]["success"] = True
                results["database_integration"]["stats"] = stats
            except Exception as e:
                results["database_integration"]["success"] = False
                results["database_integration"]["error"] = str(e)
                results["errors"].append(f"Database integration failed: {e}")
            
            if results["errors"]:
                results["success"] = False
                logger.error(f"Essentia analyzer test failed: {results['errors']}")
            else:
                logger.info("Essentia analyzer test completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Essentia analyzer test failed: {e}")
            logger.error(f"Essentia analyzer test failed: {e}")
        
        self.test_results["essentia_analyzer"] = results
        return results
    
    def test_tensorflow_analyzer(self) -> Dict[str, Any]:
        """
        Test TensorFlow analyzer independently.
        
        Tests:
        - Service initialization
        - Pending files detection
        - Single file analysis
        - Batch analysis
        - Database integration
        """
        logger.info("=== TESTING TENSORFLOW ANALYZER ===")
        
        results = {
            "success": True,
            "service_initialization": {},
            "pending_files_detection": {},
            "single_file_analysis": {},
            "batch_analysis": {},
            "database_integration": {},
            "errors": []
        }
        
        try:
            # Test service initialization
            try:
                self.tensorflow_service = IndependentTensorFlowService()
                results["service_initialization"]["success"] = True
                results["service_initialization"]["message"] = "Service initialized successfully"
            except Exception as e:
                results["service_initialization"]["success"] = False
                results["service_initialization"]["error"] = str(e)
                results["errors"].append(f"Service initialization failed: {e}")
            
            # Test pending files detection
            try:
                pending_files = self.tensorflow_service.get_pending_files(self.db, limit=10)
                results["pending_files_detection"]["count"] = len(pending_files)
                results["pending_files_detection"]["file_ids"] = pending_files[:5]  # First 5
                results["pending_files_detection"]["success"] = True
            except Exception as e:
                results["pending_files_detection"]["success"] = False
                results["pending_files_detection"]["error"] = str(e)
                results["errors"].append(f"Pending files detection failed: {e}")
            
            # Test single file analysis (if files exist)
            if pending_files:
                try:
                    test_file_id = pending_files[0]
                    test_file = self.db.query(File).filter(File.id == test_file_id).first()
                    
                    if test_file and os.path.exists(test_file.file_path):
                        analysis_result = self.tensorflow_service.analyze_file(test_file.file_path, self.db)
                        results["single_file_analysis"]["success"] = analysis_result.get("success", False)
                        results["single_file_analysis"]["result"] = analysis_result
                    else:
                        results["single_file_analysis"]["success"] = False
                        results["single_file_analysis"]["error"] = "Test file not found or doesn't exist"
                except Exception as e:
                    results["single_file_analysis"]["success"] = False
                    results["single_file_analysis"]["error"] = str(e)
                    results["errors"].append(f"Single file analysis failed: {e}")
            
            # Test batch analysis
            try:
                batch_result = self.tensorflow_service.analyze_pending_files(self.db, max_files=2)
                results["batch_analysis"]["success"] = batch_result.get("success", False)
                results["batch_analysis"]["result"] = batch_result
            except Exception as e:
                results["batch_analysis"]["success"] = False
                results["batch_analysis"]["error"] = str(e)
                results["errors"].append(f"Batch analysis failed: {e}")
            
            # Test database integration
            try:
                stats = self.tensorflow_service.get_stats(self.db)
                results["database_integration"]["success"] = True
                results["database_integration"]["stats"] = stats
            except Exception as e:
                results["database_integration"]["success"] = False
                results["database_integration"]["error"] = str(e)
                results["errors"].append(f"Database integration failed: {e}")
            
            if results["errors"]:
                results["success"] = False
                logger.error(f"TensorFlow analyzer test failed: {results['errors']}")
            else:
                logger.info("TensorFlow analyzer test completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"TensorFlow analyzer test failed: {e}")
            logger.error(f"TensorFlow analyzer test failed: {e}")
        
        self.test_results["tensorflow_analyzer"] = results
        return results
    
    def test_faiss_analyzer(self) -> Dict[str, Any]:
        """
        Test FAISS analyzer independently.
        
        Tests:
        - Service initialization
        - Pending files detection
        - Single file analysis
        - Batch analysis
        - Database integration
        """
        logger.info("=== TESTING FAISS ANALYZER ===")
        
        results = {
            "success": True,
            "service_initialization": {},
            "pending_files_detection": {},
            "single_file_analysis": {},
            "batch_analysis": {},
            "database_integration": {},
            "errors": []
        }
        
        try:
            # Test service initialization
            try:
                self.faiss_service = IndependentFAISSService()
                results["service_initialization"]["success"] = True
                results["service_initialization"]["message"] = "Service initialized successfully"
            except Exception as e:
                results["service_initialization"]["success"] = False
                results["service_initialization"]["error"] = str(e)
                results["errors"].append(f"Service initialization failed: {e}")
            
            # Test pending files detection
            try:
                pending_files = self.faiss_service.get_pending_files(self.db, limit=10)
                results["pending_files_detection"]["count"] = len(pending_files)
                results["pending_files_detection"]["file_ids"] = pending_files[:5]  # First 5
                results["pending_files_detection"]["success"] = True
            except Exception as e:
                results["pending_files_detection"]["success"] = False
                results["pending_files_detection"]["error"] = str(e)
                results["errors"].append(f"Pending files detection failed: {e}")
            
            # Test single file analysis (if files exist)
            if pending_files:
                try:
                    test_file_id = pending_files[0]
                    test_file = self.db.query(File).filter(File.id == test_file_id).first()
                    
                    if test_file and os.path.exists(test_file.file_path):
                        analysis_result = self.faiss_service.analyze_file(test_file.file_path, self.db)
                        results["single_file_analysis"]["success"] = analysis_result.get("success", False)
                        results["single_file_analysis"]["result"] = analysis_result
                    else:
                        results["single_file_analysis"]["success"] = False
                        results["single_file_analysis"]["error"] = "Test file not found or doesn't exist"
                except Exception as e:
                    results["single_file_analysis"]["success"] = False
                    results["single_file_analysis"]["error"] = str(e)
                    results["errors"].append(f"Single file analysis failed: {e}")
            
            # Test batch analysis
            try:
                batch_result = self.faiss_service.analyze_pending_files(self.db, max_files=2)
                results["batch_analysis"]["success"] = batch_result.get("success", False)
                results["batch_analysis"]["result"] = batch_result
            except Exception as e:
                results["batch_analysis"]["success"] = False
                results["batch_analysis"]["error"] = str(e)
                results["errors"].append(f"Batch analysis failed: {e}")
            
            # Test database integration
            try:
                stats = self.faiss_service.get_stats(self.db)
                results["database_integration"]["success"] = True
                results["database_integration"]["stats"] = stats
            except Exception as e:
                results["database_integration"]["success"] = False
                results["database_integration"]["error"] = str(e)
                results["errors"].append(f"Database integration failed: {e}")
            
            if results["errors"]:
                results["success"] = False
                logger.error(f"FAISS analyzer test failed: {results['errors']}")
            else:
                logger.info("FAISS analyzer test completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"FAISS analyzer test failed: {e}")
            logger.error(f"FAISS analyzer test failed: {e}")
        
        self.test_results["faiss_analyzer"] = results
        return results
    
    def test_integration(self) -> Dict[str, Any]:
        """
        Test integration between analyzers and database.
        
        Tests:
        - Status record creation
        - Result storage
        - Status updates
        - Cross-analyzer dependencies
        """
        logger.info("=== TESTING INTEGRATION ===")
        
        results = {
            "success": True,
            "status_record_creation": {},
            "result_storage": {},
            "status_updates": {},
            "cross_analyzer_dependencies": {},
            "errors": []
        }
        
        try:
            # Test status record creation
            try:
                # Check if status records are created for files
                files_with_essentia_status = self.db.query(File).join(
                    EssentiaAnalysisStatus, File.id == EssentiaAnalysisStatus.file_id
                ).count()
                
                files_with_tensorflow_status = self.db.query(File).join(
                    TensorFlowAnalysisStatus, File.id == TensorFlowAnalysisStatus.file_id
                ).count()
                
                files_with_faiss_status = self.db.query(File).join(
                    FAISSAnalysisStatus, File.id == FAISSAnalysisStatus.file_id
                ).count()
                
                results["status_record_creation"] = {
                    "files_with_essentia_status": files_with_essentia_status,
                    "files_with_tensorflow_status": files_with_tensorflow_status,
                    "files_with_faiss_status": files_with_faiss_status,
                    "success": True
                }
            except Exception as e:
                results["status_record_creation"]["success"] = False
                results["status_record_creation"]["error"] = str(e)
                results["errors"].append(f"Status record creation test failed: {e}")
            
            # Test result storage
            try:
                essentia_results_count = self.db.query(EssentiaAnalysisResults).count()
                tensorflow_results_count = self.db.query(TensorFlowAnalysisResults).count()
                faiss_results_count = self.db.query(FAISSAnalysisResults).count()
                
                results["result_storage"] = {
                    "essentia_results": essentia_results_count,
                    "tensorflow_results": tensorflow_results_count,
                    "faiss_results": faiss_results_count,
                    "success": True
                }
            except Exception as e:
                results["result_storage"]["success"] = False
                results["result_storage"]["error"] = str(e)
                results["errors"].append(f"Result storage test failed: {e}")
            
            # Test status updates
            try:
                # Check status transitions
                analyzed_essentia = self.db.query(EssentiaAnalysisStatus).filter(
                    EssentiaAnalysisStatus.status == AnalyzerStatus.ANALYZED
                ).count()
                
                analyzed_tensorflow = self.db.query(TensorFlowAnalysisStatus).filter(
                    TensorFlowAnalysisStatus.status == AnalyzerStatus.ANALYZED
                ).count()
                
                analyzed_faiss = self.db.query(FAISSAnalysisStatus).filter(
                    FAISSAnalysisStatus.status == AnalyzerStatus.ANALYZED
                ).count()
                
                results["status_updates"] = {
                    "analyzed_essentia": analyzed_essentia,
                    "analyzed_tensorflow": analyzed_tensorflow,
                    "analyzed_faiss": analyzed_faiss,
                    "success": True
                }
            except Exception as e:
                results["status_updates"]["success"] = False
                results["status_updates"]["error"] = str(e)
                results["errors"].append(f"Status updates test failed: {e}")
            
            # Test cross-analyzer dependencies
            try:
                # Check if files analyzed by all analyzers
                files_analyzed_by_all = self.db.query(File).join(
                    EssentiaAnalysisStatus, File.id == EssentiaAnalysisStatus.file_id
                ).join(
                    TensorFlowAnalysisStatus, File.id == TensorFlowAnalysisStatus.file_id
                ).join(
                    FAISSAnalysisStatus, File.id == FAISSAnalysisStatus.file_id
                ).filter(
                    EssentiaAnalysisStatus.status == AnalyzerStatus.ANALYZED,
                    TensorFlowAnalysisStatus.status == AnalyzerStatus.ANALYZED,
                    FAISSAnalysisStatus.status == AnalyzerStatus.ANALYZED
                ).count()
                
                results["cross_analyzer_dependencies"] = {
                    "files_analyzed_by_all": files_analyzed_by_all,
                    "success": True
                }
            except Exception as e:
                results["cross_analyzer_dependencies"]["success"] = False
                results["cross_analyzer_dependencies"]["error"] = str(e)
                results["errors"].append(f"Cross-analyzer dependencies test failed: {e}")
            
            if results["errors"]:
                results["success"] = False
                logger.error(f"Integration test failed: {results['errors']}")
            else:
                logger.info("Integration test completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Integration test failed: {e}")
            logger.error(f"Integration test failed: {e}")
        
        self.test_results["integration_tests"] = results
        return results
    
    def test_end_to_end_workflow(self) -> Dict[str, Any]:
        """
        Test complete end-to-end workflow.
        
        Tests:
        - File discovery to analysis completion
        - All analyzers working together
        - Database consistency
        """
        logger.info("=== TESTING END-TO-END WORKFLOW ===")
        
        results = {
            "success": True,
            "workflow_steps": {},
            "database_consistency": {},
            "analyzer_coordination": {},
            "errors": []
        }
        
        try:
            # Test workflow steps
            try:
                # Step 1: Check file discovery
                total_files = self.db.query(File).count()
                active_files = self.db.query(File).filter(File.is_active == True).count()
                
                # Step 2: Check analysis progress
                analyzed_files = self.db.query(File).join(
                    EssentiaAnalysisStatus, File.id == EssentiaAnalysisStatus.file_id
                ).filter(
                    EssentiaAnalysisStatus.status == AnalyzerStatus.ANALYZED
                ).count()
                
                results["workflow_steps"] = {
                    "total_files": total_files,
                    "active_files": active_files,
                    "analyzed_files": analyzed_files,
                    "analysis_progress": f"{(analyzed_files/active_files*100):.1f}%" if active_files > 0 else "0%",
                    "success": True
                }
            except Exception as e:
                results["workflow_steps"]["success"] = False
                results["workflow_steps"]["error"] = str(e)
                results["errors"].append(f"Workflow steps test failed: {e}")
            
            # Test database consistency
            try:
                # Check for orphaned records
                orphaned_essentia = self.db.query(EssentiaAnalysisStatus).filter(
                    ~EssentiaAnalysisStatus.file_id.in_(self.db.query(File.id))
                ).count()
                
                orphaned_tensorflow = self.db.query(TensorFlowAnalysisStatus).filter(
                    ~TensorFlowAnalysisStatus.file_id.in_(self.db.query(File.id))
                ).count()
                
                orphaned_faiss = self.db.query(FAISSAnalysisStatus).filter(
                    ~FAISSAnalysisStatus.file_id.in_(self.db.query(File.id))
                ).count()
                
                results["database_consistency"] = {
                    "orphaned_essentia_records": orphaned_essentia,
                    "orphaned_tensorflow_records": orphaned_tensorflow,
                    "orphaned_faiss_records": orphaned_faiss,
                    "consistency_ok": (orphaned_essentia == 0 and orphaned_tensorflow == 0 and orphaned_faiss == 0),
                    "success": True
                }
            except Exception as e:
                results["database_consistency"]["success"] = False
                results["database_consistency"]["error"] = str(e)
                results["errors"].append(f"Database consistency test failed: {e}")
            
            # Test analyzer coordination
            try:
                # Check if analyzers are coordinated properly
                files_with_all_statuses = self.db.query(File).join(
                    EssentiaAnalysisStatus, File.id == EssentiaAnalysisStatus.file_id
                ).join(
                    TensorFlowAnalysisStatus, File.id == TensorFlowAnalysisStatus.file_id
                ).join(
                    FAISSAnalysisStatus, File.id == FAISSAnalysisStatus.file_id
                ).count()
                
                results["analyzer_coordination"] = {
                    "files_with_all_statuses": files_with_all_statuses,
                    "coordination_ok": files_with_all_statuses > 0,
                    "success": True
                }
            except Exception as e:
                results["analyzer_coordination"]["success"] = False
                results["analyzer_coordination"]["error"] = str(e)
                results["errors"].append(f"Analyzer coordination test failed: {e}")
            
            if results["errors"]:
                results["success"] = False
                logger.error(f"End-to-end workflow test failed: {results['errors']}")
            else:
                logger.info("End-to-end workflow test completed successfully")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"End-to-end workflow test failed: {e}")
            logger.error(f"End-to-end workflow test failed: {e}")
        
        self.test_results["end_to_end"] = results
        return results
    
    def run_complete_verification(self) -> Dict[str, Any]:
        """
        Run complete verification of all analyzers and systems.
        
        Returns:
            Complete test results summary
        """
        logger.info("=== STARTING COMPLETE ANALYZER VERIFICATION ===")
        
        start_time = time.time()
        
        # Setup
        if not self.setup_database():
            return {"success": False, "error": "Failed to setup database"}
        
        try:
            # Run all tests
            self.verify_database_schema()
            self.verify_control_values()
            self.test_essentia_analyzer()
            self.test_tensorflow_analyzer()
            self.test_faiss_analyzer()
            self.test_integration()
            self.test_end_to_end_workflow()
            
            # Generate summary
            total_tests = len(self.test_results)
            successful_tests = sum(1 for result in self.test_results.values() if result.get("success", False))
            
            summary = {
                "success": successful_tests == total_tests,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "failed_tests": total_tests - successful_tests,
                "execution_time": time.time() - start_time,
                "timestamp": datetime.now().isoformat(),
                "detailed_results": self.test_results
            }
            
            logger.info(f"=== VERIFICATION COMPLETED ===")
            logger.info(f"Total tests: {total_tests}")
            logger.info(f"Successful: {successful_tests}")
            logger.info(f"Failed: {total_tests - successful_tests}")
            logger.info(f"Execution time: {summary['execution_time']:.2f}s")
            
            return summary
            
        finally:
            self.cleanup_database()
    
    def save_results(self, filename: str = None):
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analyzer_verification_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

def main():
    """Main function to run the verification plan"""
    print("=== ESSENTIA-TENSORFLOW ANALYZER VERIFICATION PLAN ===")
    print()
    
    # Create verification plan
    verifier = AnalyzerVerificationPlan()
    
    # Run complete verification
    results = verifier.run_complete_verification()
    
    # Print summary
    print("\n=== VERIFICATION SUMMARY ===")
    print(f"Overall Success: {'✓' if results['success'] else '✗'}")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Successful: {results['successful_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Execution Time: {results['execution_time']:.2f}s")
    
    # Print detailed results
    print("\n=== DETAILED RESULTS ===")
    for test_name, test_result in results['detailed_results'].items():
        status = "✓" if test_result.get("success", False) else "✗"
        print(f"{status} {test_name.upper()}")
        
        if not test_result.get("success", False) and test_result.get("errors"):
            for error in test_result["errors"][:3]:  # Show first 3 errors
                print(f"  - {error}")
    
    # Save results
    verifier.save_results()
    
    print(f"\nResults saved to analyzer_verification_results_*.json")
    print("\n=== VERIFICATION COMPLETED ===")

if __name__ == "__main__":
    main()
