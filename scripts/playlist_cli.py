#!/usr/bin/env python3
"""
Playlist App CLI - Command Line Interface for Discovery System
"""

import argparse
import sys
import os
import requests
from pathlib import Path
from typing import List, Dict
import json

# API base URL
API_BASE_URL = "http://localhost:8000"

class PlaylistCLI:
    """Command Line Interface for Playlist App Discovery System"""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        
    def _make_request(self, method: str, endpoint: str, **kwargs):
        """Make HTTP request to API"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    def scan_files(self, verbose: bool = False):
        """Scan for files and display results"""
        try:
            if verbose:
                print("Scanning directories for audio files...")
                print()
            
            response = self._make_request("POST", "/api/discovery/scan")
            if not response:
                return False
            
            results = response.get('results', {})
            
            print("Discovery Results:")
            print(f"  Added: {len(results.get('added_files', []))} files")
            print(f"  Removed: {len(results.get('removed_files', []))} files")
            print(f"  Unchanged: {results.get('unchanged_count', 0)} files")
            
            if results.get('added_files') and verbose:
                print("\nAdded files:")
                for file_path in results['added_files'][:10]:  # Show first 10
                    print(f"  + {Path(file_path).name}")
                if len(results['added_files']) > 10:
                    print(f"  ... and {len(results['added_files']) - 10} more files")
            
            if results.get('removed_files') and verbose:
                print("\nRemoved files:")
                for file_path in results['removed_files']:
                    print(f"  - {Path(file_path).name}")
            
            return True
            
        except Exception as e:
            print(f"Error scanning files: {e}")
            return False
    
    def list_files(self, limit: int = 50, offset: int = 0, format: str = "table"):
        """List discovered files"""
        try:
            response = self._make_request("GET", f"/api/discovery/files?limit={limit}&offset={offset}")
            if not response:
                return False
            
            files = response.get('files', [])
            
            if format == "json":
                print(json.dumps({
                    "files": files,
                    "count": len(files),
                    "limit": limit,
                    "offset": offset
                }, indent=2))
            else:
                self._print_files_table(files)
            
            return True
            
        except Exception as e:
            print(f"Error listing files: {e}")
            return False
    
    def _print_files_table(self, files: List[Dict]):
        """Print files in table format"""
        if not files:
            print("No files found.")
            return
        
        # Calculate column widths
        max_name = max(len(f['file_name']) for f in files) + 2
        max_ext = max(len(f['file_extension']) for f in files) + 2
        max_size = max(len(self._format_size(f['file_size'])) for f in files) + 2
        
        # Print header
        header = f"{'Name':<{max_name}} {'Ext':<{max_ext}} {'Size':<{max_size}} {'Status':<10}"
        print(header)
        print("-" * len(header))
        
        # Print files
        for file in files:
            status = "Analyzed" if file['is_analyzed'] else "Pending"
            size = self._format_size(file['file_size'])
            print(f"{file['file_name']:<{max_name}} {file['file_extension']:<{max_ext}} {size:<{max_size}} {status:<10}")
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f}TB"
    
    def show_stats(self, format: str = "table"):
        """Show discovery statistics"""
        try:
            response = self._make_request("GET", "/api/discovery/stats")
            if not response:
                return False
            
            stats = response.get('stats', {})
            
            if format == "json":
                print(json.dumps(stats, indent=2))
            else:
                self._print_stats_table(stats)
            
            return True
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return False
    
    def _print_stats_table(self, stats: Dict):
        """Print statistics in table format"""
        print("Discovery Statistics:")
        print("=" * 30)
        print(f"Total Files:      {stats['total_files']}")
        print(f"Analyzed Files:   {stats['analyzed_files']}")
        print(f"Pending Analysis: {stats['unanalyzed_files']}")
        
        if stats['extension_distribution']:
            print("\nFile Extensions:")
            print("-" * 20)
            for ext, count in sorted(stats['extension_distribution'].items()):
                print(f"{ext:<8} {count:>6} files")
    
    def show_config(self):
        """Show current configuration"""
        print("Playlist App Configuration:")
        print("=" * 50)
        print("Configuration is managed through the API server.")
        print("Use the API endpoints to view and modify configuration.")
        print(f"API Base URL: {self.base_url}")
        print("\nAvailable API endpoints:")
        print("- GET /api/discovery/config - Discovery configuration")
        print("- GET /api/discovery/stats - Discovery statistics")
        print("- GET /api/metadata/stats/overview - Metadata statistics")
    
    def validate_directories(self):
        """Validate search directories"""
        print("Validating search directories...")
        print("This feature requires API access to check configuration.")
        print("Please use the API endpoints to validate directories.")
        print(f"API Base URL: {self.base_url}")
        return True
    
    def re_discover_files(self, verbose: bool = False):
        """Re-discover all files and extract metadata"""
        try:
            if verbose:
                print("Re-discovering all files and extracting metadata...")
                print("This will clear existing data and re-process all files.")
                print()
            
            response = self._make_request("POST", "/api/discovery/re-discover")
            if not response:
                return False
            
            results = response.get('results', {})
            
            print("Re-discovery Results:")
            print(f"  Added: {results.get('added_count', 0)} files")
            print(f"  Removed: {results.get('removed_count', 0)} files")
            print(f"  Unchanged: {results.get('unchanged_count', 0)} files")
            
            if verbose and results.get('added_files'):
                print("\nProcessed files (with metadata extraction):")
                for file_path in results['added_files'][:10]:  # Show first 10
                    print(f"  ✓ {Path(file_path).name}")
                if len(results['added_files']) > 10:
                    print(f"  ... and {len(results['added_files']) - 10} more files")
            
            return True
            
        except Exception as e:
            print(f"Error re-discovering files: {e}")
            return False
    
    def show_metadata_stats(self, format: str = "table"):
        """Show metadata statistics"""
        try:
            response = self._make_request("GET", "/api/metadata/stats/overview")
            if not response:
                return False
            
            stats = response.get('stats', {})
            
            if format == "json":
                print(json.dumps(stats, indent=2))
            else:
                self._print_metadata_stats_table(stats)
            
            return True
            
        except Exception as e:
            print(f"Error getting metadata statistics: {e}")
            return False
    
    def _print_metadata_stats_table(self, stats: Dict):
        """Print metadata statistics in table format"""
        print("Metadata Statistics:")
        print("=" * 30)
        print(f"Total Files:           {stats['total_files']}")
        print(f"Files with Metadata:   {stats['files_with_metadata']}")
        print(f"Analysis Percentage:   {stats['analysis_percentage']}%")
        
        if stats['top_genres']:
            print("\nTop Genres:")
            print("-" * 20)
            for genre_info in stats['top_genres']:
                print(f"{genre_info['genre']:<20} {genre_info['count']:>6} files")
        
        if stats['top_years']:
            print("\nTop Years:")
            print("-" * 20)
            for year_info in stats['top_years']:
                print(f"{year_info['year']:<20} {year_info['count']:>6} files")
    
    def show_file_metadata(self, file_id: int, format: str = "table"):
        """Show metadata for a specific file"""
        try:
            response = self._make_request("GET", f"/api/metadata/{file_id}")
            if not response:
                return False
            
            if format == "json":
                print(json.dumps(response, indent=2, default=str))
            else:
                # For table format, we need to get file info separately
                file_response = self._make_request("GET", f"/api/discovery/files?limit=1000")
                if file_response:
                    files = file_response.get('files', [])
                    file_record = next((f for f in files if f['id'] == file_id), None)
                    if file_record:
                        self._print_file_metadata_table(file_record, response.get('metadata'))
                    else:
                        print(f"File with ID {file_id} not found.")
                        return False
                else:
                    print(f"Could not retrieve file information.")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error getting file metadata: {e}")
            return False
    
    def _print_file_metadata_table(self, file_record, metadata):
        """Print file metadata in table format"""
        print(f"File: {file_record['file_name']}")
        print(f"Path: {file_record['file_path']}")
        print(f"Size: {self._format_size(file_record['file_size'])}")
        print(f"Extension: {file_record['file_extension']}")
        print()
        
        if metadata:
            print("Metadata:")
            print("=" * 30)
            
            # Core metadata
            core_fields = [
                ('Title', metadata.get('title')),
                ('Artist', metadata.get('artist')),
                ('Album', metadata.get('album')),
                ('Track Number', metadata.get('track_number')),
                ('Year', metadata.get('year')),
                ('Genre', metadata.get('genre')),
                ('Album Artist', metadata.get('album_artist')),
                ('Composer', metadata.get('composer')),
                ('Duration', f"{metadata.get('duration', 0):.2f}s" if metadata.get('duration') else None),
                ('BPM', metadata.get('bpm')),
                ('Key', metadata.get('key'))
            ]
            
            for label, value in core_fields:
                if value is not None:
                    print(f"{label:<15}: {value}")
            
            # Technical metadata
            tech_fields = [
                ('Bitrate', f"{metadata.get('bitrate')} kbps" if metadata.get('bitrate') else None),
                ('Sample Rate', f"{metadata.get('sample_rate')} Hz" if metadata.get('sample_rate') else None),
                ('Channels', metadata.get('channels')),
                ('ISRC', metadata.get('isrc')),
                ('Comment', metadata.get('comment'))
            ]
            
            print("\nTechnical Information:")
            print("-" * 30)
            for label, value in tech_fields:
                if value is not None:
                    print(f"{label:<15}: {value}")
        else:
            print("No metadata found for this file.")
            print("Metadata is automatically extracted during discovery.")
    
    def enrich_genres(self, limit: int = 10, format: str = "table"):
        """Enrich genre information for files with 'Other' or missing genres"""
        try:
            # Get files with 'Other' or missing genres
            response = self._make_request("GET", f"/api/metadata/search?genre=Other&limit={limit}")
            if not response:
                return False
            
            results = response.get('results', [])
            total_count = response.get('total_count', 0)
            
            if format == "json":
                print(json.dumps({
                    "files_to_enrich": results,
                    "total_count": total_count,
                    "limit": limit,
                    "note": "Use POST /api/metadata/enrich-genres to enrich these files"
                }, indent=2, default=str))
            else:
                self._print_genre_enrichment_results(results, total_count, limit)
            
            return True
            
        except Exception as e:
            print(f"Error getting files for genre enrichment: {e}")
            return False
    
    def _print_genre_enrichment_results(self, results, total_count, limit):
        """Print genre enrichment results in table format"""
        print(f"Files with 'Other' Genre ({len(results)} of {total_count}):")
        print("=" * 80)
        
        if not results:
            print("No files with 'Other' genre found.")
            return
        
        # Print header
        header = f"{'Title':<30} {'Artist':<20} {'Album':<20} {'Current Genre':<12}"
        print(header)
        print("-" * len(header))
        
        # Print results
        for metadata in results:
            title = (metadata.get('title') or "Unknown")[:29]
            artist = (metadata.get('artist') or "Unknown")[:19]
            album = (metadata.get('album') or "Unknown")[:19]
            genre = (metadata.get('genre') or "")[:11]
            
            print(f"{title:<30} {artist:<20} {album:<20} {genre:<12}")
        
        print(f"\nUse 'enrich-genres' command to list files that need genre enrichment.")
        print("Genre enrichment happens automatically during file discovery using:")
        print("- MusicBrainz (free, no API key required)")
        print("- Last.fm (requires API key)")
        print("- Discogs (requires API key)")
        print("\nConfigure API keys in config/app_settings.json and run 're-discover' to enrich genres.")
    

    
    def search_metadata(self, query: str = "", artist: str = "", album: str = "", 
                       genre: str = "", year: int = None, limit: int = 20, format: str = "table"):
        """Search metadata"""
        try:
            # Build query parameters
            params = []
            if query:
                params.append(f"query={query}")
            if artist:
                params.append(f"artist={artist}")
            if album:
                params.append(f"album={album}")
            if genre:
                params.append(f"genre={genre}")
            if year is not None:
                params.append(f"year={year}")
            if limit:
                params.append(f"limit={limit}")
            
            query_string = "&".join(params)
            endpoint = f"/api/metadata/search?{query_string}"
            
            response = self._make_request("GET", endpoint)
            if not response:
                return False
            
            if format == "json":
                print(json.dumps(response, indent=2, default=str))
            else:
                results = response.get('results', [])
                total_count = response.get('total_count', 0)
                self._print_metadata_search_results(results, total_count, limit)
            
            return True
            
        except Exception as e:
            print(f"Error searching metadata: {e}")
            return False
    
    def _print_metadata_search_results(self, results, total_count, limit):
        """Print metadata search results in table format"""
        print(f"Search Results ({len(results)} of {total_count}):")
        print("=" * 80)
        
        if not results:
            print("No results found.")
            return
        
        # Print header
        header = f"{'Title':<30} {'Artist':<20} {'Album':<20} {'Year':<6} {'Genre':<12}"
        print(header)
        print("-" * len(header))
        
        # Print results
        for metadata in results:
            title = (metadata.get('title') or "Unknown")[:29]
            artist = (metadata.get('artist') or "Unknown")[:19]
            album = (metadata.get('album') or "Unknown")[:19]
            year = str(metadata.get('year') or "")[:5]
            genre = (metadata.get('genre') or "")[:11]
            
            print(f"{title:<30} {artist:<20} {album:<20} {year:<6} {genre:<12}")
    
    def categorize_files(self, format: str = "table"):
        """Categorize files by length"""
        try:
            response = self._make_request("GET", "/api/analyzer/categorize")
            if not response:
                return False
            
            categories = response.get('categories', {})
            
            if format == "json":
                print(json.dumps(categories, indent=2))
            else:
                self._print_categories_table(categories)
            
            return True
            
        except Exception as e:
            print(f"Error categorizing files: {e}")
            return False
    
    def _print_categories_table(self, categories: Dict):
        """Print categories in table format"""
        print("\nFile Length Categories:")
        print("-" * 60)
        print(f"{'Category':<15} {'Count':<10} {'Description':<35}")
        print("-" * 60)
        
        total_files = 0
        for category, files in categories.items():
            count = len(files)
            total_files += count
            
            if category == 'normal':
                description = "0-5 minutes"
            elif category == 'long':
                description = "5-10 minutes"
            elif category == 'very_long':
                description = "10+ minutes"
            else:
                description = "Unknown duration"
            
            print(f"{category:<15} {count:<10} {description:<35}")
        
        print("-" * 60)
        print(f"{'Total':<15} {total_files:<10}")
        print()
    
    def analyze_batches(self, category: str = None, batch_size: int = 50, verbose: bool = False):
        """Create batches of files by category for later processing"""
        try:
            params = {'batch_size': batch_size}
            if category:
                params['category'] = category
            
            if verbose:
                print(f"Creating batches by category (batch_size: {batch_size})")
                if category:
                    print(f"Category: {category}")
                print()
            
            response = self._make_request("POST", "/api/analyzer/analyze-batches", json=params)
            if not response:
                return False
            
            results = response.get('results', {})
            
            if verbose:
                print("Batch Creation Results:")
                print(f"  Total batches created: {results.get('total_batches', 0)}")
                print(f"  Total files in batches: {results.get('total_files', 0)}")
                print(f"  Message: {results.get('message', '')}")
                
                batch_results = results.get('batch_results', [])
                if batch_results:
                    print("\nBatch Details:")
                    for i, batch in enumerate(batch_results, 1):
                        print(f"  Batch {i}: {batch['category']} - {batch['batch_size']} files")
            else:
                print(f"Batch creation complete: {results.get('total_batches', 0)} batches created with {results.get('total_files', 0)} files")
            
            return True
            
        except Exception as e:
            print(f"Error creating batches: {e}")
            return False
    
    def show_length_stats(self, format: str = "table"):
        """Show length statistics"""
        try:
            response = self._make_request("GET", "/api/analyzer/length-stats")
            if not response:
                return False
            
            stats = response.get('stats', {})
            
            if format == "json":
                print(json.dumps(stats, indent=2))
            else:
                self._print_length_stats_table(stats)
            
            return True
            
        except Exception as e:
            print(f"Error getting length statistics: {e}")
            return False
    
    def _print_length_stats_table(self, stats: Dict):
        """Print length statistics in table format"""
        print("\nLength Statistics:")
        print("-" * 60)
        print(f"{'Metric':<25} {'Value':<35}")
        print("-" * 60)
        
        print(f"{'Total files':<25} {stats.get('total_files', 0):<35}")
        print(f"{'Analyzed files':<25} {stats.get('analyzed_files', 0):<35}")
        
        print("\nCategory Counts:")
        category_counts = stats.get('category_counts', {})
        for category, count in category_counts.items():
            print(f"  {category}: {count}")
        
        duration_ranges = stats.get('duration_ranges', {})
        if duration_ranges.get('min_duration') is not None:
            print(f"\nDuration Ranges:")
            print(f"  Min duration: {duration_ranges['min_duration']} seconds")
            print(f"  Max duration: {duration_ranges['max_duration']} seconds")
            print(f"  Avg duration: {duration_ranges['avg_duration']:.2f} seconds")
        
        print()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Playlist App CLI - Discovery System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scan                    # Scan for new files
  %(prog)s scan --verbose          # Scan with detailed output
  %(prog)s list                    # List discovered files
  %(prog)s list --limit 10         # List first 10 files
  %(prog)s list --format json      # Output as JSON
  %(prog)s stats                   # Show statistics
  %(prog)s config                  # Show configuration
  %(prog)s validate                # Validate search directories
  %(prog)s re-discover             # Re-discover all files and extract metadata
  %(prog)s metadata-stats          # Show metadata statistics
  %(prog)s show-metadata 123       # Show metadata for file ID 123
  %(prog)s search --query "love"   # Search for songs with "love" in title/artist/album
  %(prog)s search --artist "Coldplay" --year 2020  # Search by artist and year
  %(prog)s enrich-genres --limit 5  # Enrich genre information for 5 files using MusicBrainz
  %(prog)s categorize               # Categorize files by length
  %(prog)s analyze-batches         # Analyze files in batches by category
  %(prog)s analyze-batches --category long  # Analyze only long tracks
  %(prog)s length-stats            # Show length statistics
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for new files')
    scan_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List discovered files')
    list_parser.add_argument('--limit', '-l', type=int, default=50, help='Number of files to show (default: 50)')
    list_parser.add_argument('--offset', '-o', type=int, default=0, help='Number of files to skip (default: 0)')
    list_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show discovery statistics')
    stats_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Config command
    subparsers.add_parser('config', help='Show current configuration')
    
    # Validate command
    subparsers.add_parser('validate', help='Validate search directories')
    
    # Re-discover command
    re_discover_parser = subparsers.add_parser('re-discover', help='Re-discover all files and extract metadata')
    re_discover_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Metadata stats command
    metadata_stats_parser = subparsers.add_parser('metadata-stats', help='Show metadata statistics')
    metadata_stats_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Show file metadata command
    show_metadata_parser = subparsers.add_parser('show-metadata', help='Show metadata for a specific file')
    show_metadata_parser.add_argument('file_id', type=int, help='File ID to show metadata for')
    show_metadata_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Search metadata command
    search_parser = subparsers.add_parser('search', help='Search metadata')
    search_parser.add_argument('--query', '-q', type=str, help='Search query (title, artist, album)')
    search_parser.add_argument('--artist', '-a', type=str, help='Filter by artist')
    search_parser.add_argument('--album', '-l', type=str, help='Filter by album')
    search_parser.add_argument('--genre', '-g', type=str, help='Filter by genre')
    search_parser.add_argument('--year', '-y', type=int, help='Filter by year')
    search_parser.add_argument('--limit', '-n', type=int, default=20, help='Number of results to show (default: 20)')
    search_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Enrich genres command
    enrich_parser = subparsers.add_parser('enrich-genres', help='List files with missing/generic genres for enrichment')
    enrich_parser.add_argument('--limit', '-n', type=int, default=10, help='Number of files to process (default: 10)')
    enrich_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Categorize files command
    categorize_parser = subparsers.add_parser('categorize', help='Categorize files by length')
    categorize_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    
    # Analyze batches command
    analyze_parser = subparsers.add_parser('analyze-batches', help='Analyze files in batches by category')
    analyze_parser.add_argument('--category', '-c', type=str, choices=['normal', 'long', 'very_long'], help='Specific category to analyze')
    analyze_parser.add_argument('--batch-size', '-b', type=int, default=50, help='Batch size (default: 50)')
    analyze_parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    
    # Length stats command
    length_stats_parser = subparsers.add_parser('length-stats', help='Show length statistics')
    length_stats_parser.add_argument('--format', '-f', choices=['table', 'json'], default='table', help='Output format (default: table)')
    

    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    cli = PlaylistCLI()
    
    try:
        if args.command == 'scan':
            success = cli.scan_files(verbose=args.verbose)
        elif args.command == 'list':
            success = cli.list_files(limit=args.limit, offset=args.offset, format=args.format)
        elif args.command == 'stats':
            success = cli.show_stats(format=args.format)
        elif args.command == 'config':
            cli.show_config()
            success = True
        elif args.command == 'validate':
            success = cli.validate_directories()
        elif args.command == 're-discover':
            success = cli.re_discover_files(verbose=args.verbose)
        elif args.command == 'metadata-stats':
            success = cli.show_metadata_stats(format=args.format)
        elif args.command == 'show-metadata':
            success = cli.show_file_metadata(file_id=args.file_id, format=args.format)
        elif args.command == 'search':
            success = cli.search_metadata(
                query=args.query,
                artist=args.artist,
                album=args.album,
                genre=args.genre,
                year=args.year,
                limit=args.limit,
                format=args.format
            )
        elif args.command == 'enrich-genres':
            success = cli.enrich_genres(limit=args.limit, format=args.format)
        elif args.command == 'categorize':
            success = cli.categorize_files(format=args.format)
        elif args.command == 'analyze-batches':
            success = cli.analyze_batches(category=args.category, batch_size=args.batch_size, verbose=args.verbose)
        elif args.command == 'length-stats':
            success = cli.show_length_stats(format=args.format)
        else:
            print(f"Unknown command: {args.command}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
