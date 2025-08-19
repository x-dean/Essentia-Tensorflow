#!/usr/bin/env python3
"""
Docker-based Analyzer Verification Script

This script runs the analyzer verification in the Docker container environment
where all dependencies (Essentia, TensorFlow, FAISS) are available.
"""

import sys
import os
import json
import time
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DockerAnalyzerVerification:
    """
    Docker-based verification for all analyzers.
    
    This class runs verification tests inside the Docker container
    where all dependencies are available.
    """
    
    def __init__(self):
        self.container_name = "playlist-app"
        self.test_results = {
            "docker_environment": {},
            "database_connection": {},
            "analyzer_availability": {},
            "individual_tests": {},
            "integration_tests": {},
            "end_to_end_tests": {}
        }
    
    def check_docker_environment(self) -> Dict[str, Any]:
        """Check if Docker environment is available"""
        logger.info("=== CHECKING DOCKER ENVIRONMENT ===")
        
        results = {
            "success": True,
            "docker_available": False,
            "container_running": False,
            "container_health": {},
            "errors": []
        }
        
        try:
            # Check if Docker is available
            try:
                subprocess.run(["docker", "--version"], check=True, capture_output=True)
                results["docker_available"] = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                results["errors"].append("Docker not available")
                results["success"] = False
                return results
            
            # Check if container is running
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Status}}"],
                    check=True, capture_output=True, text=True
                )
                if result.stdout.strip():
                    results["container_running"] = True
                    results["container_health"]["status"] = result.stdout.strip()
                else:
                    results["errors"].append(f"Container {self.container_name} not running")
                    results["success"] = False
            except subprocess.CalledProcessError as e:
                results["errors"].append(f"Failed to check container status: {e}")
                results["success"] = False
            
            # Check container logs for any errors
            try:
                result = subprocess.run(
                    ["docker", "logs", "--tail", "50", self.container_name],
                    check=True, capture_output=True, text=True
                )
                logs = result.stdout + result.stderr
                if "error" in logs.lower() or "exception" in logs.lower():
                    results["container_health"]["warnings"] = "Errors found in container logs"
                else:
                    results["container_health"]["logs_ok"] = True
            except subprocess.CalledProcessError as e:
                results["errors"].append(f"Failed to get container logs: {e}")
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Docker environment check failed: {e}")
        
        self.test_results["docker_environment"] = results
        return results
    
    def test_database_connection(self) -> Dict[str, Any]:
        """Test database connection from within container"""
        logger.info("=== TESTING DATABASE CONNECTION ===")
        
        results = {
            "success": True,
            "connection_ok": False,
            "tables_exist": {},
            "sample_data": {},
            "errors": []
        }
        
        try:
            # Run database connection test in container
            test_script = """
import sys
import os
sys.path.insert(0, '/app/src')

try:
    from playlist_app.models.database import get_db_session, close_db_session, File, FileStatus, AnalyzerStatus
    from playlist_app.models.database import EssentiaAnalysisStatus, TensorFlowAnalysisStatus, FAISSAnalysisStatus
    
    # Test connection
    db = get_db_session()
    
    # Check tables
    tables = {}
    for table in ['files', 'essentia_analysis_status', 'tensorflow_analysis_status', 'faiss_analysis_status']:
        try:
            result = db.execute(f"SELECT COUNT(*) FROM {table}")
            count = result.scalar()
            tables[table] = count
        except Exception as e:
            tables[table] = f"error: {str(e)}"
    
    # Get sample data
    sample_data = {}
    try:
        total_files = db.query(File).count()
        sample_data['total_files'] = total_files
        
        if total_files > 0:
            sample_file = db.query(File).first()
            sample_data['sample_file'] = {
                'id': sample_file.id,
                'file_path': sample_file.file_path,
                'status': sample_file.status.value if sample_file.status else None,
                'is_active': sample_file.is_active
            }
    except Exception as e:
        sample_data['error'] = str(e)
    
    close_db_session(db)
    
    print("SUCCESS")
    print(f"TABLES: {tables}")
    print(f"SAMPLE_DATA: {sample_data}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
"""
            
            # Write test script to temporary file
            test_file = "temp_db_test.py"
            with open(test_file, 'w') as f:
                f.write(test_script)
            
            # Run test in container
            result = subprocess.run(
                ["docker", "exec", self.container_name, "python", f"/app/{test_file}"],
                check=True, capture_output=True, text=True
            )
            
            # Parse results
            output = result.stdout
            if "SUCCESS" in output:
                results["connection_ok"] = True
                
                # Extract tables info
                if "TABLES:" in output:
                    tables_line = output.split("TABLES:")[1].split("SAMPLE_DATA:")[0].strip()
                    results["tables_exist"] = eval(tables_line)
                
                # Extract sample data
                if "SAMPLE_DATA:" in output:
                    sample_line = output.split("SAMPLE_DATA:")[1].strip()
                    results["sample_data"] = eval(sample_line)
            else:
                results["errors"].append(f"Database test failed: {output}")
                results["success"] = False
            
            # Cleanup
            os.remove(test_file)
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Database connection test failed: {e}")
            if e.stderr:
                results["errors"].append(f"Stderr: {e.stderr}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Database connection test failed: {e}")
        
        self.test_results["database_connection"] = results
        return results
    
    def test_analyzer_availability(self) -> Dict[str, Any]:
        """Test if all analyzers are available in the container"""
        logger.info("=== TESTING ANALYZER AVAILABILITY ===")
        
        results = {
            "success": True,
            "essentia_available": False,
            "tensorflow_available": False,
            "faiss_available": False,
            "analyzer_services": {},
            "errors": []
        }
        
        try:
            # Test script to check analyzer availability
            test_script = """
import sys
import os
sys.path.insert(0, '/app/src')

try:
    # Test Essentia
    try:
        import essentia
        import essentia.standard as ess
        essentia_available = True
        essentia_version = essentia.__version__
    except ImportError:
        essentia_available = False
        essentia_version = None
    
    # Test TensorFlow
    try:
        import tensorflow as tf
        tensorflow_available = True
        tensorflow_version = tf.__version__
    except ImportError:
        tensorflow_available = False
        tensorflow_version = None
    
    # Test FAISS
    try:
        import faiss
        faiss_available = True
        faiss_version = faiss.__version__
    except ImportError:
        faiss_available = False
        faiss_version = None
    
    # Test analyzer services
    services = {}
    try:
        from playlist_app.services.independent_essentia_service import IndependentEssentiaService
        services['essentia_service'] = 'available'
    except Exception as e:
        services['essentia_service'] = f'error: {str(e)}'
    
    try:
        from playlist_app.services.independent_tensorflow_service import IndependentTensorFlowService
        services['tensorflow_service'] = 'available'
    except Exception as e:
        services['tensorflow_service'] = f'error: {str(e)}'
    
    try:
        from playlist_app.services.independent_faiss_service import IndependentFAISSService
        services['faiss_service'] = 'available'
    except Exception as e:
        services['faiss_service'] = f'error: {str(e)}'
    
    print("SUCCESS")
    print(f"ESSENTIA: {essentia_available} ({essentia_version})")
    print(f"TENSORFLOW: {tensorflow_available} ({tensorflow_version})")
    print(f"FAISS: {faiss_available} ({faiss_version})")
    print(f"SERVICES: {services}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
"""
            
            # Write and run test
            test_file = "temp_analyzer_test.py"
            with open(test_file, 'w') as f:
                f.write(test_script)
            
            result = subprocess.run(
                ["docker", "exec", self.container_name, "python", f"/app/{test_file}"],
                check=True, capture_output=True, text=True
            )
            
            # Parse results
            output = result.stdout
            if "SUCCESS" in output:
                # Parse availability
                for line in output.split('\n'):
                    if line.startswith("ESSENTIA:"):
                        results["essentia_available"] = "True" in line
                    elif line.startswith("TENSORFLOW:"):
                        results["tensorflow_available"] = "True" in line
                    elif line.startswith("FAISS:"):
                        results["faiss_available"] = "True" in line
                    elif line.startswith("SERVICES:"):
                        services_line = line.split("SERVICES:")[1].strip()
                        results["analyzer_services"] = eval(services_line)
            else:
                results["errors"].append(f"Analyzer availability test failed: {output}")
                results["success"] = False
            
            # Cleanup
            os.remove(test_file)
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Analyzer availability test failed: {e}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Analyzer availability test failed: {e}")
        
        self.test_results["analyzer_availability"] = results
        return results
    
    def test_individual_analyzers(self) -> Dict[str, Any]:
        """Test each analyzer individually"""
        logger.info("=== TESTING INDIVIDUAL ANALYZERS ===")
        
        results = {
            "success": True,
            "essentia_test": {},
            "tensorflow_test": {},
            "faiss_test": {},
            "errors": []
        }
        
        try:
            # Test script for individual analyzers
            test_script = """
import sys
import os
sys.path.insert(0, '/app/src')

from playlist_app.models.database import get_db_session, close_db_session, File, AnalyzerStatus
from playlist_app.services.independent_essentia_service import IndependentEssentiaService
from playlist_app.services.independent_tensorflow_service import IndependentTensorFlowService
from playlist_app.services.independent_faiss_service import IndependentFAISSService

def test_analyzer(service_class, service_name):
    try:
        # Initialize service
        service = service_class()
        
        # Get database session
        db = get_db_session()
        
        # Get pending files
        pending_files = service.get_pending_files(db, limit=5)
        
        # Get stats
        stats = service.get_stats(db)
        
        close_db_session(db)
        
        return {
            'success': True,
            'pending_files_count': len(pending_files),
            'stats': stats
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Test each analyzer
essentia_result = test_analyzer(IndependentEssentiaService, 'essentia')
tensorflow_result = test_analyzer(IndependentTensorFlowService, 'tensorflow')
faiss_result = test_analyzer(IndependentFAISSService, 'faiss')

print("SUCCESS")
print(f"ESSENTIA_RESULT: {essentia_result}")
print(f"TENSORFLOW_RESULT: {tensorflow_result}")
print(f"FAISS_RESULT: {faiss_result}")
"""
            
            # Write and run test
            test_file = "temp_individual_test.py"
            with open(test_file, 'w') as f:
                f.write(test_script)
            
            result = subprocess.run(
                ["docker", "exec", self.container_name, "python", f"/app/{test_file}"],
                check=True, capture_output=True, text=True
            )
            
            # Parse results
            output = result.stdout
            if "SUCCESS" in output:
                for line in output.split('\n'):
                    if line.startswith("ESSENTIA_RESULT:"):
                        essentia_line = line.split("ESSENTIA_RESULT:")[1].strip()
                        results["essentia_test"] = eval(essentia_line)
                    elif line.startswith("TENSORFLOW_RESULT:"):
                        tensorflow_line = line.split("TENSORFLOW_RESULT:")[1].strip()
                        results["tensorflow_test"] = eval(tensorflow_line)
                    elif line.startswith("FAISS_RESULT:"):
                        faiss_line = line.split("FAISS_RESULT:")[1].strip()
                        results["faiss_test"] = eval(faiss_line)
            else:
                results["errors"].append(f"Individual analyzer test failed: {output}")
                results["success"] = False
            
            # Cleanup
            os.remove(test_file)
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Individual analyzer test failed: {e}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Individual analyzer test failed: {e}")
        
        self.test_results["individual_tests"] = results
        return results
    
    def test_integration(self) -> Dict[str, Any]:
        """Test integration between analyzers"""
        logger.info("=== TESTING INTEGRATION ===")
        
        results = {
            "success": True,
            "status_records": {},
            "cross_analyzer_dependencies": {},
            "errors": []
        }
        
        try:
            # Test script for integration
            test_script = """
import sys
import os
sys.path.insert(0, '/app/src')

from playlist_app.models.database import get_db_session, close_db_session, File, AnalyzerStatus
from playlist_app.models.database import EssentiaAnalysisStatus, TensorFlowAnalysisStatus, FAISSAnalysisStatus

try:
    db = get_db_session()
    
    # Check status records
    status_records = {}
    status_records['essentia_status_count'] = db.query(EssentiaAnalysisStatus).count()
    status_records['tensorflow_status_count'] = db.query(TensorFlowAnalysisStatus).count()
    status_records['faiss_status_count'] = db.query(FAISSAnalysisStatus).count()
    
    # Check cross-analyzer dependencies
    files_with_all_statuses = db.query(File).join(
        EssentiaAnalysisStatus, File.id == EssentiaAnalysisStatus.file_id
    ).join(
        TensorFlowAnalysisStatus, File.id == TensorFlowAnalysisStatus.file_id
    ).join(
        FAISSAnalysisStatus, File.id == FAISSAnalysisStatus.file_id
    ).count()
    
    files_analyzed_by_all = db.query(File).join(
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
    
    cross_analyzer = {
        'files_with_all_statuses': files_with_all_statuses,
        'files_analyzed_by_all': files_analyzed_by_all
    }
    
    close_db_session(db)
    
    print("SUCCESS")
    print(f"STATUS_RECORDS: {status_records}")
    print(f"CROSS_ANALYZER: {cross_analyzer}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
"""
            
            # Write and run test
            test_file = "temp_integration_test.py"
            with open(test_file, 'w') as f:
                f.write(test_script)
            
            result = subprocess.run(
                ["docker", "exec", self.container_name, "python", f"/app/{test_file}"],
                check=True, capture_output=True, text=True
            )
            
            # Parse results
            output = result.stdout
            if "SUCCESS" in output:
                for line in output.split('\n'):
                    if line.startswith("STATUS_RECORDS:"):
                        status_line = line.split("STATUS_RECORDS:")[1].strip()
                        results["status_records"] = eval(status_line)
                    elif line.startswith("CROSS_ANALYZER:"):
                        cross_line = line.split("CROSS_ANALYZER:")[1].strip()
                        results["cross_analyzer_dependencies"] = eval(cross_line)
            else:
                results["errors"].append(f"Integration test failed: {output}")
                results["success"] = False
            
            # Cleanup
            os.remove(test_file)
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Integration test failed: {e}")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Integration test failed: {e}")
        
        self.test_results["integration_tests"] = results
        return results
    
    def run_complete_verification(self) -> Dict[str, Any]:
        """Run complete verification"""
        logger.info("=== STARTING DOCKER-BASED ANALYZER VERIFICATION ===")
        
        start_time = time.time()
        
        # Run all tests
        self.check_docker_environment()
        self.test_database_connection()
        self.test_analyzer_availability()
        self.test_individual_analyzers()
        self.test_integration()
        
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
    
    def save_results(self, filename: str = None):
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"docker_analyzer_verification_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

def main():
    """Main function to run the Docker-based verification"""
    print("=== DOCKER-BASED ANALYZER VERIFICATION ===")
    print()
    
    # Create verification instance
    verifier = DockerAnalyzerVerification()
    
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
    
    print(f"\nResults saved to docker_analyzer_verification_results_*.json")
    print("\n=== VERIFICATION COMPLETED ===")

if __name__ == "__main__":
    main()
