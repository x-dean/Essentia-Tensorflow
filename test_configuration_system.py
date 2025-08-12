#!/usr/bin/env python3
"""
Comprehensive test script for the configuration system improvements
Tests all phases: Phase 1 (basic config), Phase 2 (advanced config), Phase 3 (monitoring/validation)
"""

import json
import time
import requests
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

class ConfigurationSystemTester:
    """Test the complete configuration system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def test_phase1_basic_configuration(self):
        """Test Phase 1: Basic configuration improvements"""
        print("\n🔧 Testing Phase 1: Basic Configuration")
        print("=" * 50)
        
        # Test 1: API timeouts configuration
        try:
            response = requests.get(f"{self.base_url}/api/config/api-timeouts")
            if response.status_code == 200:
                timeouts = response.json()
                self.log_test("API Timeouts Configuration", True, 
                            f"Default: {timeouts['timeouts']['default']}s, Analysis: {timeouts['timeouts']['analysis']}s")
            else:
                self.log_test("API Timeouts Configuration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("API Timeouts Configuration", False, str(e))
        
        # Test 2: Database retry settings
        try:
            response = requests.get(f"{self.base_url}/api/config/database")
            if response.status_code == 200:
                db_config = response.json()
                retry_settings = db_config['config'].get('retry_settings', {})
                self.log_test("Database Retry Settings", True, 
                            f"Max retries: {retry_settings.get('max_retries', 'N/A')}")
            else:
                self.log_test("Database Retry Settings", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Database Retry Settings", False, str(e))
        
        # Test 3: Discovery configuration
        try:
            response = requests.get(f"{self.base_url}/api/config/discovery")
            if response.status_code == 200:
                discovery_config = response.json()
                extensions = discovery_config['config'].get('supported_extensions', [])
                self.log_test("Discovery Configuration", True, 
                            f"Supported extensions: {len(extensions)} types")
            else:
                self.log_test("Discovery Configuration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Discovery Configuration", False, str(e))
        
        # Test 4: Logging suppression
        try:
            response = requests.get(f"{self.base_url}/api/config/logging")
            if response.status_code == 200:
                logging_config = response.json()
                suppression = logging_config['config'].get('suppression', {})
                self.log_test("Logging Suppression", True, 
                            f"TensorFlow: {suppression.get('tensorflow', 'N/A')}, Essentia: {suppression.get('essentia', 'N/A')}")
            else:
                self.log_test("Logging Suppression", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Logging Suppression", False, str(e))
    
    def test_phase2_advanced_configuration(self):
        """Test Phase 2: Advanced configuration improvements"""
        print("\n🚀 Testing Phase 2: Advanced Configuration")
        print("=" * 50)
        
        # Test 1: Analysis configuration
        try:
            response = requests.get(f"{self.base_url}/api/config/analysis")
            if response.status_code == 200:
                analysis_config = response.json()
                tf_optimizations = analysis_config['config'].get('performance', {}).get('tensorflow_optimizations', {})
                vector_analysis = analysis_config['config'].get('vector_analysis', {})
                self.log_test("Analysis Configuration", True, 
                            f"TF optimizations: {len(tf_optimizations)} settings, Vector analysis: {len(vector_analysis)} settings")
            else:
                self.log_test("Analysis Configuration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Analysis Configuration", False, str(e))
        
        # Test 2: External API configuration
        try:
            response = requests.get(f"{self.base_url}/api/config/app")
            if response.status_code == 200:
                app_config = response.json()
                external_apis = app_config['config'].get('external_apis', {})
                api_count = len(external_apis)
                self.log_test("External API Configuration", True, 
                            f"Configured APIs: {api_count} (MusicBrainz, LastFM, Discogs)")
            else:
                self.log_test("External API Configuration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("External API Configuration", False, str(e))
        
        # Test 3: FAISS configuration
        try:
            response = requests.get(f"{self.base_url}/api/config/app")
            if response.status_code == 200:
                app_config = response.json()
                faiss_config = app_config['config'].get('faiss', {})
                self.log_test("FAISS Configuration", True, 
                            f"Index name: {faiss_config.get('index_name', 'N/A')}, Vector dimension: {faiss_config.get('vector_dimension', 'N/A')}")
            else:
                self.log_test("FAISS Configuration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("FAISS Configuration", False, str(e))
    
    def test_phase3_monitoring_validation(self):
        """Test Phase 3: Monitoring and validation features"""
        print("\n📊 Testing Phase 3: Monitoring & Validation")
        print("=" * 50)
        
        # Test 1: Configuration validation
        try:
            response = requests.get(f"{self.base_url}/api/config/validate")
            if response.status_code == 200:
                validation = response.json()
                all_valid = validation.get('all_valid', False)
                validation_results = validation.get('validation_results', {})
                self.log_test("Configuration Validation", all_valid, 
                            f"All valid: {all_valid}, Configs tested: {len(validation_results)}")
            else:
                self.log_test("Configuration Validation", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Configuration Validation", False, str(e))
        
        # Test 2: Configuration health monitoring
        try:
            response = requests.get(f"{self.base_url}/api/config/monitor/health")
            if response.status_code == 200:
                health = response.json()
                health_data = health.get('health', {})
                status = health_data.get('status', 'unknown')
                self.log_test("Configuration Health Monitoring", True, 
                            f"Status: {status}, Success rate: {health_data.get('overall_success_rate', 0):.1f}%")
            else:
                self.log_test("Configuration Health Monitoring", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Configuration Health Monitoring", False, str(e))
        
        # Test 3: Configuration metrics
        try:
            response = requests.get(f"{self.base_url}/api/config/monitor/metrics")
            if response.status_code == 200:
                metrics = response.json()
                metrics_data = metrics.get('metrics', {})
                config_count = len(metrics_data)
                self.log_test("Configuration Metrics", True, 
                            f"Monitored configs: {config_count}")
            else:
                self.log_test("Configuration Metrics", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Configuration Metrics", False, str(e))
        
        # Test 4: Configuration change history
        try:
            response = requests.get(f"{self.base_url}/api/config/monitor/history?hours=1")
            if response.status_code == 200:
                history = response.json()
                history_count = history.get('count', 0)
                self.log_test("Configuration Change History", True, 
                            f"Changes in last hour: {history_count}")
            else:
                self.log_test("Configuration Change History", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Configuration Change History", False, str(e))
        
        # Test 5: Configuration schemas
        try:
            response = requests.get(f"{self.base_url}/api/config/schemas")
            if response.status_code == 200:
                schemas = response.json()
                available_schemas = schemas.get('available_schemas', [])
                self.log_test("Configuration Schemas", True, 
                            f"Available schemas: {len(available_schemas)} ({', '.join(available_schemas)})")
            else:
                self.log_test("Configuration Schemas", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Configuration Schemas", False, str(e))
    
    def test_configuration_files(self):
        """Test configuration file structure and content"""
        print("\n📁 Testing Configuration Files")
        print("=" * 50)
        
        config_dir = Path("config")
        if not config_dir.exists():
            self.log_test("Configuration Directory", False, "config/ directory not found")
            return
        
        # Test 1: app_settings.json
        app_settings_file = config_dir / "app_settings.json"
        if app_settings_file.exists():
            try:
                with open(app_settings_file, 'r') as f:
                    app_settings = json.load(f)
                
                # Check for Phase 1 features
                api_timeouts = app_settings.get('api', {}).get('timeouts', {})
                discovery_settings = app_settings.get('discovery', {})
                faiss_settings = app_settings.get('faiss', {})
                external_apis = app_settings.get('external_apis', {})
                
                phase1_features = [
                    ('API Timeouts', bool(api_timeouts)),
                    ('Discovery Settings', bool(discovery_settings)),
                    ('FAISS Settings', bool(faiss_settings)),
                    ('External APIs', bool(external_apis))
                ]
                
                all_phase1 = all(feature[1] for feature in phase1_features)
                self.log_test("app_settings.json Phase 1", all_phase1, 
                            f"Features: {[f[0] for f in phase1_features if f[1]]}")
                
                # Check for Phase 2 features
                phase2_features = []
                for api_name, api_config in external_apis.items():
                    if isinstance(api_config, dict):
                        has_retry = 'retry_settings' in api_config
                        has_cache = 'cache_settings' in api_config
                        phase2_features.extend([f"{api_name} Retry", has_retry])
                        phase2_features.extend([f"{api_name} Cache", has_cache])
                
                phase2_count = sum(1 for i in range(1, len(phase2_features), 2) if phase2_features[i])
                self.log_test("app_settings.json Phase 2", phase2_count > 0, 
                            f"Advanced features: {phase2_count}")
                
            except Exception as e:
                self.log_test("app_settings.json", False, str(e))
        else:
            self.log_test("app_settings.json", False, "File not found")
        
        # Test 2: database.json
        database_file = config_dir / "database.json"
        if database_file.exists():
            try:
                with open(database_file, 'r') as f:
                    database_config = json.load(f)
                
                retry_settings = database_config.get('retry_settings', {})
                has_retry = bool(retry_settings)
                self.log_test("database.json Phase 1", has_retry, 
                            f"Retry settings: {len(retry_settings)} parameters")
                
            except Exception as e:
                self.log_test("database.json", False, str(e))
        else:
            self.log_test("database.json", False, "File not found")
        
        # Test 3: logging.json
        logging_file = config_dir / "logging.json"
        if logging_file.exists():
            try:
                with open(logging_file, 'r') as f:
                    logging_config = json.load(f)
                
                suppression = logging_config.get('suppression', {})
                has_suppression = bool(suppression)
                self.log_test("logging.json Phase 1", has_suppression, 
                            f"Suppression settings: {len(suppression)} libraries")
                
            except Exception as e:
                self.log_test("logging.json", False, str(e))
        else:
            self.log_test("logging.json", False, "File not found")
        
        # Test 4: analysis_config.json
        analysis_file = config_dir / "analysis_config.json"
        if analysis_file.exists():
            try:
                with open(analysis_file, 'r') as f:
                    analysis_config = json.load(f)
                
                # Check for Phase 2 features
                tf_optimizations = analysis_config.get('performance', {}).get('tensorflow_optimizations', {})
                vector_analysis = analysis_config.get('vector_analysis', {})
                
                phase2_features = [
                    ('TensorFlow Optimizations', bool(tf_optimizations)),
                    ('Vector Analysis', bool(vector_analysis))
                ]
                
                all_phase2 = all(feature[1] for feature in phase2_features)
                self.log_test("analysis_config.json Phase 2", all_phase2, 
                            f"Features: {[f[0] for f in phase2_features if f[1]]}")
                
            except Exception as e:
                self.log_test("analysis_config.json", False, str(e))
        else:
            self.log_test("analysis_config.json", False, "File not found")
    
    def test_service_integration(self):
        """Test service integration with new configuration"""
        print("\n🔗 Testing Service Integration")
        print("=" * 50)
        
        # Test 1: Discovery service with new config
        try:
            response = requests.get(f"{self.base_url}/api/discovery/status")
            if response.status_code == 200:
                status = response.json()
                self.log_test("Discovery Service Integration", True, 
                            f"Status: {status.get('status', 'unknown')}")
            else:
                self.log_test("Discovery Service Integration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Discovery Service Integration", False, str(e))
        
        # Test 2: Analysis service with new config
        try:
            response = requests.get(f"{self.base_url}/api/analyzer/status")
            if response.status_code == 200:
                status = response.json()
                self.log_test("Analysis Service Integration", True, 
                            f"Status: {status.get('status', 'unknown')}")
            else:
                self.log_test("Analysis Service Integration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("Analysis Service Integration", False, str(e))
        
        # Test 3: FAISS service with new config
        try:
            response = requests.get(f"{self.base_url}/api/faiss/status")
            if response.status_code == 200:
                status = response.json()
                self.log_test("FAISS Service Integration", True, 
                            f"Status: {status.get('status', 'unknown')}")
            else:
                self.log_test("FAISS Service Integration", False, f"Status: {response.status_code}")
        except Exception as e:
            self.log_test("FAISS Service Integration", False, str(e))
    
    def run_all_tests(self):
        """Run all configuration system tests"""
        print("🧪 Configuration System Test Suite")
        print("=" * 60)
        print(f"Testing against: {self.base_url}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test all phases
        self.test_phase1_basic_configuration()
        self.test_phase2_advanced_configuration()
        self.test_phase3_monitoring_validation()
        self.test_configuration_files()
        self.test_service_integration()
        
        # Summary
        print("\n📋 Test Summary")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['details']}")
        
        return passed_tests == total_tests

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the configuration system")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--output", help="Output results to JSON file")
    
    args = parser.parse_args()
    
    tester = ConfigurationSystemTester(args.url)
    success = tester.run_all_tests()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "base_url": args.url,
                "success": success,
                "results": tester.test_results
            }, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
