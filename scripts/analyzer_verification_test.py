#!/usr/bin/env python3
"""
Simple Analyzer Verification Test

This script uses the existing CLI to test each analyzer independently.
It provides a comprehensive verification of the analyzer system.
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

class SimpleAnalyzerVerification:
    """
    Simple verification using CLI commands.
    
    This class tests analyzers using the existing CLI interface.
    """
    
    def __init__(self):
        self.cli_script = "scripts/master_cli.py"
        self.test_results = {
            "cli_availability": {},
            "analyzer_status": {},
            "essentia_test": {},
            "tensorflow_test": {},
            "faiss_test": {},
            "integration_test": {},
            "database_info": {}
        }
    
    def test_cli_availability(self) -> Dict[str, Any]:
        """Test if CLI is available and working"""
        logger.info("=== TESTING CLI AVAILABILITY ===")
        
        results = {
            "success": True,
            "cli_exists": False,
            "cli_executable": False,
            "help_works": False,
            "errors": []
        }
        
        try:
            # Check if CLI script exists
            if os.path.exists(self.cli_script):
                results["cli_exists"] = True
            else:
                results["errors"].append(f"CLI script not found: {self.cli_script}")
                results["success"] = False
                return results
            
            # Test CLI help
            try:
                result = subprocess.run(
                    [sys.executable, self.cli_script, "--help"],
                    check=True, capture_output=True, text=True, timeout=30
                )
                results["cli_executable"] = True
                results["help_works"] = True
                logger.info("CLI help command works")
            except subprocess.CalledProcessError as e:
                results["errors"].append(f"CLI help failed: {e}")
                results["success"] = False
            except subprocess.TimeoutExpired:
                results["errors"].append("CLI help timed out")
                results["success"] = False
            
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"CLI availability test failed: {e}")
        
        self.test_results["cli_availability"] = results
        return results
    
    def test_analyzer_status(self) -> Dict[str, Any]:
        """Test analyzer status endpoint"""
        logger.info("=== TESTING ANALYZER STATUS ===")
        
        results = {
            "success": True,
            "status_response": {},
            "services_available": {},
            "errors": []
        }
        
        try:
            # Test analyzer status
            result = subprocess.run(
                [sys.executable, self.cli_script, "analyzer", "status"],
                check=True, capture_output=True, text=True, timeout=30
            )
            
            # Parse the output
            output = result.stdout
            if "operational" in output.lower() or "status" in output.lower() or "success" in output.lower():
                results["status_response"]["operational"] = True
                
                # Extract service information
                if "essentia" in output.lower():
                    results["services_available"]["essentia"] = True
                if "tensorflow" in output.lower():
                    results["services_available"]["tensorflow"] = True
                if "faiss" in output.lower():
                    results["services_available"]["faiss"] = True
                
                logger.info("Analyzer status check successful")
            else:
                results["errors"].append("Analyzer status not operational")
                results["success"] = False
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Analyzer status test failed: {e}")
            if e.stderr:
                results["errors"].append(f"Stderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append("Analyzer status test timed out")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Analyzer status test failed: {e}")
        
        self.test_results["analyzer_status"] = results
        return results
    
    def test_essentia_analyzer(self) -> Dict[str, Any]:
        """Test Essentia analyzer"""
        logger.info("=== TESTING ESSENTIA ANALYZER ===")
        
        results = {
            "success": True,
            "pending_files": {},
            "analysis_result": {},
            "errors": []
        }
        
        try:
            # First, check pending files
            result = subprocess.run(
                [sys.executable, self.cli_script, "analyzer", "essentia", "--max-files", "5"],
                check=True, capture_output=True, text=True, timeout=60
            )
            
            output = result.stdout
            if "success" in output.lower() or "no files to analyze" in output.lower() or "analysis completed" in output.lower():
                results["analysis_result"]["success"] = True
                
                # Extract statistics
                if "total_files" in output:
                    # Try to extract numbers
                    lines = output.split('\n')
                    for line in lines:
                        if "total_files" in line:
                            results["pending_files"]["total"] = line.strip()
                        elif "successful" in line:
                            results["pending_files"]["successful"] = line.strip()
                        elif "failed" in line:
                            results["pending_files"]["failed"] = line.strip()
                
                logger.info("Essentia analysis test successful")
            else:
                results["errors"].append("Essentia analysis failed")
                results["success"] = False
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Essentia test failed: {e}")
            if e.stderr:
                results["errors"].append(f"Stderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append("Essentia test timed out")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Essentia test failed: {e}")
        
        self.test_results["essentia_test"] = results
        return results
    
    def test_tensorflow_analyzer(self) -> Dict[str, Any]:
        """Test TensorFlow analyzer"""
        logger.info("=== TESTING TENSORFLOW ANALYZER ===")
        
        results = {
            "success": True,
            "pending_files": {},
            "analysis_result": {},
            "errors": []
        }
        
        try:
            # Test TensorFlow analysis
            result = subprocess.run(
                [sys.executable, self.cli_script, "analyzer", "tensorflow", "--max-files", "5"],
                check=True, capture_output=True, text=True, timeout=60
            )
            
            output = result.stdout
            if "success" in output.lower() or "no files to analyze" in output.lower() or "analysis completed" in output.lower():
                results["analysis_result"]["success"] = True
                
                # Extract statistics
                lines = output.split('\n')
                for line in lines:
                    if "total_files" in line:
                        results["pending_files"]["total"] = line.strip()
                    elif "successful" in line:
                        results["pending_files"]["successful"] = line.strip()
                    elif "failed" in line:
                        results["pending_files"]["failed"] = line.strip()
                
                logger.info("TensorFlow analysis test successful")
            else:
                results["errors"].append("TensorFlow analysis failed")
                results["success"] = False
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"TensorFlow test failed: {e}")
            if e.stderr:
                results["errors"].append(f"Stderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append("TensorFlow test timed out")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"TensorFlow test failed: {e}")
        
        self.test_results["tensorflow_test"] = results
        return results
    
    def test_faiss_analyzer(self) -> Dict[str, Any]:
        """Test FAISS analyzer"""
        logger.info("=== TESTING FAISS ANALYZER ===")
        
        results = {
            "success": True,
            "pending_files": {},
            "analysis_result": {},
            "errors": []
        }
        
        try:
            # Test FAISS analysis
            result = subprocess.run(
                [sys.executable, self.cli_script, "analyzer", "faiss", "--max-files", "5"],
                check=True, capture_output=True, text=True, timeout=60
            )
            
            output = result.stdout
            if "success" in output.lower() or "no files to analyze" in output.lower() or "analysis completed" in output.lower():
                results["analysis_result"]["success"] = True
                
                # Extract statistics
                lines = output.split('\n')
                for line in lines:
                    if "total_files" in line:
                        results["pending_files"]["total"] = line.strip()
                    elif "successful" in line:
                        results["pending_files"]["successful"] = line.strip()
                    elif "failed" in line:
                        results["pending_files"]["failed"] = line.strip()
                
                logger.info("FAISS analysis test successful")
            else:
                results["errors"].append("FAISS analysis failed")
                results["success"] = False
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"FAISS test failed: {e}")
            if e.stderr:
                results["errors"].append(f"Stderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append("FAISS test timed out")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"FAISS test failed: {e}")
        
        self.test_results["faiss_test"] = results
        return results
    
    def test_integration(self) -> Dict[str, Any]:
        """Test integration between analyzers"""
        logger.info("=== TESTING INTEGRATION ===")
        
        results = {
            "success": True,
            "all_analyzers": {},
            "statistics": {},
            "errors": []
        }
        
        try:
            # Test all analyzers together
            result = subprocess.run(
                [sys.executable, self.cli_script, "analyzer", "complete", "--max-files", "3"],
                check=True, capture_output=True, text=True, timeout=120
            )
            
            output = result.stdout
            if "success" in output.lower() or "no files to analyze" in output.lower() or "analysis completed" in output.lower():
                results["all_analyzers"]["success"] = True
                
                # Extract statistics for each analyzer
                lines = output.split('\n')
                current_analyzer = None
                for line in lines:
                    if "essentia" in line.lower():
                        current_analyzer = "essentia"
                    elif "tensorflow" in line.lower():
                        current_analyzer = "tensorflow"
                    elif "faiss" in line.lower():
                        current_analyzer = "faiss"
                    elif "total_files" in line and current_analyzer:
                        results["statistics"][current_analyzer] = line.strip()
                
                logger.info("Integration test successful")
            else:
                results["errors"].append("Integration test failed")
                results["success"] = False
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Integration test failed: {e}")
            if e.stderr:
                results["errors"].append(f"Stderr: {e.stderr}")
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append("Integration test timed out")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Integration test failed: {e}")
        
        self.test_results["integration_test"] = results
        return results
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        logger.info("=== GETTING DATABASE INFO ===")
        
        results = {
            "success": True,
            "file_count": {},
            "analyzer_stats": {},
            "errors": []
        }
        
        try:
            # Get file count
            result = subprocess.run(
                [sys.executable, self.cli_script, "tracks", "list", "--limit", "1"],
                check=True, capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout
            if "total" in output.lower():
                results["file_count"]["response"] = "Files found"
            else:
                results["file_count"]["response"] = "No files or error"
            
            # Get analyzer statistics
            result = subprocess.run(
                [sys.executable, self.cli_script, "analyzer", "statistics"],
                check=True, capture_output=True, text=True, timeout=30
            )
            
            output = result.stdout
            if "essentia" in output.lower() or "tensorflow" in output.lower() or "faiss" in output.lower():
                results["analyzer_stats"]["response"] = "Statistics available"
            else:
                results["analyzer_stats"]["response"] = "No statistics or error"
            
            logger.info("Database info retrieval successful")
            
        except subprocess.CalledProcessError as e:
            results["success"] = False
            results["errors"].append(f"Database info failed: {e}")
        except subprocess.TimeoutExpired:
            results["success"] = False
            results["errors"].append("Database info timed out")
        except Exception as e:
            results["success"] = False
            results["errors"].append(f"Database info failed: {e}")
        
        self.test_results["database_info"] = results
        return results
    
    def run_complete_verification(self) -> Dict[str, Any]:
        """Run complete verification"""
        logger.info("=== STARTING SIMPLE ANALYZER VERIFICATION ===")
        
        start_time = time.time()
        
        # Run all tests
        self.test_cli_availability()
        self.test_analyzer_status()
        self.test_essentia_analyzer()
        self.test_tensorflow_analyzer()
        self.test_faiss_analyzer()
        self.test_integration()
        self.get_database_info()
        
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
            filename = f"simple_analyzer_verification_results_{timestamp}.json"
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.test_results, f, indent=2, default=str)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

def main():
    """Main function to run the simple verification"""
    print("=== SIMPLE ANALYZER VERIFICATION ===")
    print()
    
    # Create verification instance
    verifier = SimpleAnalyzerVerification()
    
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
    
    print(f"\nResults saved to simple_analyzer_verification_results_*.json")
    print("\n=== VERIFICATION COMPLETED ===")

if __name__ == "__main__":
    main()
