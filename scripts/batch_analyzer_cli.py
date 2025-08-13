#!/usr/bin/env python3
"""
CLI tool for batch audio analysis using the FastAPI endpoints.

This script provides command-line access to all analyzer functionality
including categorization, batch processing, and statistics.
"""

import sys
import os
import json
import time
import argparse
import logging
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BatchAnalyzerCLI:
    """CLI client for batch audio analysis"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to API endpoint"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error details: {error_detail}")
                except:
                    logger.error(f"Response text: {e.response.text}")
            raise
    
    def categorize_files(self) -> Dict[str, Any]:
        """Get file categorization by length"""
        logger.info("Getting file categorization...")
        return self._make_request('GET', '/api/analyzer/categorize')
    
    def get_length_statistics(self) -> Dict[str, Any]:
        """Get length statistics"""
        logger.info("Getting length statistics...")
        return self._make_request('GET', '/api/analyzer/length-stats')
    
    def get_categories(self) -> Dict[str, Any]:
        """Get available length categories"""
        logger.info("Getting available categories...")
        return self._make_request('GET', '/api/analyzer/categories')
    
    def analyze_file(self, file_path: str, include_tensorflow: bool = True) -> Dict[str, Any]:
        """Analyze a single file"""
        logger.info(f"Analyzing file: {file_path}")
        data = {
            'file_path': file_path,
            'include_tensorflow': include_tensorflow
        }
        return self._make_request('POST', '/api/analyzer/analyze-file', data)
    
    def analyze_files_batch(self, file_paths: List[str], include_tensorflow: bool = True) -> Dict[str, Any]:
        """Analyze multiple files in batch"""
        logger.info(f"Analyzing {len(file_paths)} files in batch...")
        data = {
            'file_paths': file_paths,
            'include_tensorflow': include_tensorflow
        }
        return self._make_request('POST', '/api/analyzer/analyze-files', data)
    
    def analyze_all_batches(self, include_tensorflow: bool = True) -> Dict[str, Any]:
        """Analyze all batches automatically using existing length-based categorization"""
        logger.info("Analyzing all batches automatically...")
        params = f'?include_tensorflow={str(include_tensorflow).lower()}'
        return self._make_request('POST', f'/api/analyzer/analyze-batches{params}')
    
    def analyze_category(self, category: str, include_tensorflow: bool = True) -> Dict[str, Any]:
        """Analyze files by category using existing batches"""
        logger.info(f"Analyzing category: {category}")
        params = f'?include_tensorflow={str(include_tensorflow).lower()}'
        return self._make_request('POST', f'/api/analyzer/analyze-category/{category}{params}')
    
    def get_analysis(self, file_path: str) -> Dict[str, Any]:
        """Get analysis results for a file"""
        logger.info(f"Getting analysis for: {file_path}")
        endpoint = f'/api/analyzer/analysis/{file_path}'
        return self._make_request('GET', endpoint)
    
    def get_analysis_summary(self, file_path: str) -> Dict[str, Any]:
        """Get analysis summary for a file"""
        logger.info(f"Getting analysis summary for: {file_path}")
        endpoint = f'/api/analyzer/analysis-summary/{file_path}'
        return self._make_request('GET', endpoint)
    
    def get_unanalyzed_files(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Get list of unanalyzed files"""
        logger.info("Getting unanalyzed files...")
        params = f'?limit={limit}' if limit else ''
        return self._make_request('GET', f'/api/analyzer/unanalyzed-files{params}')
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        logger.info("Getting analysis statistics...")
        return self._make_request('GET', '/api/analyzer/statistics')
    
    def delete_analysis(self, file_path: str) -> Dict[str, Any]:
        """Delete analysis results for a file"""
        logger.info(f"Deleting analysis for: {file_path}")
        endpoint = f'/api/analyzer/analysis/{file_path}'
        return self._make_request('DELETE', endpoint)

def print_json(data: Dict[str, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))

def print_categorization_results(data: Dict[str, Any]):
    """Print categorization results in a readable format"""
    print("\n File Categorization Results:")
    print("=" * 50)
    
    categories = data.get('categories', {})
    total_files = data.get('total_files', 0)
    
    print(f"Total files: {total_files}")
    print()
    
    for category, files in categories.items():
        count = len(files)
        percentage = (count / total_files * 100) if total_files > 0 else 0
        print(f"{category.upper():<12}: {count:>4} files ({percentage:>5.1f}%)")
        
        if files and len(files) <= 5:
            for file_path in files[:3]:
                print(f"  └─ {file_path}")
            if len(files) > 3:
                print(f"  └─ ... and {len(files) - 3} more")

def print_batch_results(data: Dict[str, Any]):
    """Print batch analysis results in a readable format"""
    print("\n Batch Analysis Results:")
    print("=" * 50)
    
    results = data.get('results', {})
    total_files = results.get('total_files', 0)
    total_processed = results.get('total_processed', 0)
    total_failed = results.get('total_failed', 0)
    
    print(f"Total files: {total_files}")
    print(f"Successfully processed: {total_processed}")
    print(f"Failed: {total_failed}")
    print(f"Success rate: {(total_processed/total_files*100):.1f}%" if total_files > 0 else "N/A")
    
    # Show batch details
    batch_results = results.get('batch_results', [])
    if batch_results:
        print("\nBatch Details:")
        for i, batch in enumerate(batch_results, 1):
            category = batch.get('category', 'unknown')
            batch_size = batch.get('batch_size', 0)
            result = batch.get('result', {})
            processed = result.get('processed', 0)
            failed = result.get('failed', 0)
            
            print(f"  Batch {i} ({category}): {processed}/{batch_size} successful, {failed} failed")

def print_statistics(data: Dict[str, Any]):
    """Print statistics in a readable format"""
    print("\n Analysis Statistics:")
    print("=" * 50)
    
    stats = data.get('statistics', {})
    total_files = stats.get('total_files', 0)
    analyzed_files = stats.get('analyzed_files', 0)
    unanalyzed_files = stats.get('unanalyzed_files', 0)
    coverage = stats.get('analysis_coverage', 0)
    avg_duration = stats.get('avg_analysis_duration', 0)
    
    print(f"Total files: {total_files}")
    print(f"Analyzed: {analyzed_files}")
    print(f"Unanalyzed: {unanalyzed_files}")
    print(f"Coverage: {coverage:.1f}%")
    print(f"Average analysis duration: {avg_duration:.2f}s")
    
    # Tempo statistics
    tempo_stats = stats.get('tempo_statistics', {})
    if tempo_stats:
        print(f"\nTempo Statistics:")
        print(f"  Range: {tempo_stats.get('min', 0):.1f} - {tempo_stats.get('max', 0):.1f} BPM")
        print(f"  Average: {tempo_stats.get('avg', 0):.1f} BPM")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="CLI tool for batch audio analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get file categorization
  python batch_analyzer_cli.py categorize

  # Analyze all batches automatically
  python batch_analyzer_cli.py analyze-all

  # Analyze specific category
  python batch_analyzer_cli.py analyze-category normal

  # Analyze specific files
  python batch_analyzer_cli.py analyze-files music/track1.mp3 music/track2.mp3

  # Get statistics
  python batch_analyzer_cli.py statistics
        """
    )
    
    parser.add_argument('--url', default='http://localhost:8000',
                       help='API base URL (default: http://localhost:8000)')
    parser.add_argument('--no-tensorflow', action='store_true',
                       help='Disable TensorFlow model analysis')
    parser.add_argument('--json', action='store_true',
                       help='Output raw JSON instead of formatted text')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Categorize command
    subparsers.add_parser('categorize', help='Get file categorization by length')
    
    # Statistics commands
    subparsers.add_parser('length-stats', help='Get length statistics')
    subparsers.add_parser('categories', help='Get available categories')
    subparsers.add_parser('statistics', help='Get analysis statistics')
    
    # Analysis commands
    analyze_file_parser = subparsers.add_parser('analyze-file', help='Analyze a single file')
    analyze_file_parser.add_argument('file_path', help='Path to audio file')
    
    analyze_files_parser = subparsers.add_parser('analyze-files', help='Analyze multiple files')
    analyze_files_parser.add_argument('file_paths', nargs='+', help='Paths to audio files')
    
    analyze_all_parser = subparsers.add_parser('analyze-all', help='Analyze all batches automatically')
    
    analyze_category_parser = subparsers.add_parser('analyze-category', help='Analyze files by category')
    analyze_category_parser.add_argument('category', choices=['normal', 'long', 'very_long'],
                                       help='Category to analyze')
    
    # Get commands
    get_analysis_parser = subparsers.add_parser('get-analysis', help='Get analysis results')
    get_analysis_parser.add_argument('file_path', help='Path to audio file')
    
    get_summary_parser = subparsers.add_parser('get-summary', help='Get analysis summary')
    get_summary_parser.add_argument('file_path', help='Path to audio file')
    
    unanalyzed_parser = subparsers.add_parser('unanalyzed', help='Get unanalyzed files')
    unanalyzed_parser.add_argument('--limit', type=int, help='Maximum number of files to return')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete-analysis', help='Delete analysis results')
    delete_parser.add_argument('file_path', help='Path to audio file')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize CLI client
    cli = BatchAnalyzerCLI(args.url)
    include_tensorflow = not args.no_tensorflow
    
    try:
        if args.command == 'categorize':
            result = cli.categorize_files()
            if args.json:
                print_json(result)
            else:
                print_categorization_results(result)
        
        elif args.command == 'length-stats':
            result = cli.get_length_statistics()
            if args.json:
                print_json(result)
            else:
                print_json(result.get('stats', {}))
        
        elif args.command == 'categories':
            result = cli.get_categories()
            if args.json:
                print_json(result)
            else:
                print_json(result.get('categories', {}))
        
        elif args.command == 'statistics':
            result = cli.get_statistics()
            if args.json:
                print_json(result)
            else:
                print_statistics(result)
        
        elif args.command == 'analyze-file':
            result = cli.analyze_file(args.file_path, include_tensorflow)
            if args.json:
                print_json(result)
            else:
                print(f" Analysis completed for: {args.file_path}")
                print(f"Duration: {result.get('result', {}).get('duration', 'N/A')} seconds")
        
        elif args.command == 'analyze-files':
            result = cli.analyze_files_batch(args.file_paths, include_tensorflow)
            if args.json:
                print_json(result)
            else:
                print(f" Batch analysis completed for {len(args.file_paths)} files")
                print(f"Successful: {result.get('result', {}).get('successful', 0)}")
                print(f"Failed: {result.get('result', {}).get('failed', 0)}")
        
        elif args.command == 'analyze-all':
            result = cli.analyze_all_batches(include_tensorflow)
            if args.json:
                print_json(result)
            else:
                print_batch_results(result)
        
        elif args.command == 'analyze-category':
            result = cli.analyze_category(args.category, include_tensorflow)
            if args.json:
                print_json(result)
            else:
                print_batch_results(result)
        
        elif args.command == 'get-analysis':
            result = cli.get_analysis(args.file_path)
            if args.json:
                print_json(result)
            else:
                analysis = result.get('result', {})
                print(f" Analysis for: {args.file_path}")
                print(f"Duration: {analysis.get('duration', 'N/A')} seconds")
                print(f"Tempo: {analysis.get('rhythm_features', {}).get('tempo', 'N/A')} BPM")
                print(f"Key: {analysis.get('harmonic_features', {}).get('key', 'N/A')} {analysis.get('harmonic_features', {}).get('scale', '')}")
        
        elif args.command == 'get-summary':
            result = cli.get_analysis_summary(args.file_path)
            if args.json:
                print_json(result)
            else:
                summary = result.get('result', {})
                print(f" Summary for: {args.file_path}")
                key_features = summary.get('key_features', {})
                print(f"Tempo: {key_features.get('tempo', 'N/A')} BPM")
                print(f"Key: {key_features.get('key', 'N/A')} {key_features.get('scale', '')}")
                print(f"RMS: {key_features.get('rms', 'N/A')}")
                print(f"Loudness: {key_features.get('loudness', 'N/A')}")
        
        elif args.command == 'unanalyzed':
            result = cli.get_unanalyzed_files(args.limit)
            if args.json:
                print_json(result)
            else:
                files = result.get('files', [])
                count = result.get('count', 0)
                print(f" Unanalyzed files: {count}")
                for file_path in files[:10]:  # Show first 10
                    print(f"  └─ {file_path}")
                if len(files) > 10:
                    print(f"  └─ ... and {len(files) - 10} more")
        
        elif args.command == 'delete-analysis':
            result = cli.delete_analysis(args.file_path)
            if args.json:
                print_json(result)
            else:
                print(f"️ Analysis deleted for: {args.file_path}")
        
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
