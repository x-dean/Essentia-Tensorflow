#!/usr/bin/env python3
"""
Playlist App CLI - Command Line Interface for Discovery System
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Dict
import json

from src.playlist_app.models.database import create_tables, SessionLocal
from src.playlist_app.services.discovery import DiscoveryService
from src.playlist_app.core.config import DiscoveryConfig
from src.playlist_app.core.config_loader import config_loader

class PlaylistCLI:
    """Command Line Interface for Playlist App Discovery System"""
    
    def __init__(self):
        self.db = None
        self.discovery_service = None
        
    def init_database(self):
        """Initialize database and discovery service"""
        try:
            create_tables()
            self.db = SessionLocal()
            self.discovery_service = DiscoveryService(self.db)
            return True
        except Exception as e:
            print(f"Error initializing database: {e}")
            return False
    
    def scan_files(self, verbose: bool = False):
        """Scan for files and display results"""
        if not self.init_database():
            return False
        
        try:
            if verbose:
                print("Scanning directories for audio files...")
                print(f"Search directories: {', '.join(self.discovery_service.search_directories)}")
                print(f"Supported extensions: {', '.join(self.discovery_service.supported_extensions)}")
                print()
            
            results = self.discovery_service.discover_files()
            
            print("Discovery Results:")
            print(f"  Added: {len(results['added'])} files")
            print(f"  Removed: {len(results['removed'])} files")
            print(f"  Unchanged: {len(results['unchanged'])} files")
            
            if results['added'] and verbose:
                print("\nAdded files:")
                for file_path in results['added']:
                    print(f"  + {Path(file_path).name}")
            
            if results['removed'] and verbose:
                print("\nRemoved files:")
                for file_path in results['removed']:
                    print(f"  - {Path(file_path).name}")
            
            return True
            
        except Exception as e:
            print(f"Error scanning files: {e}")
            return False
        finally:
            if self.db:
                self.db.close()
    
    def list_files(self, limit: int = 50, offset: int = 0, format: str = "table"):
        """List discovered files"""
        if not self.init_database():
            return False
        
        try:
            files = self.discovery_service.get_discovered_files(limit=limit, offset=offset)
            
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
        finally:
            if self.db:
                self.db.close()
    
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
        if not self.init_database():
            return False
        
        try:
            from src.playlist_app.models.database import File
            
            # Get statistics
            total_files = self.db.query(File).filter(File.is_active == True).count()
            analyzed_files = self.db.query(File).filter(File.is_active == True, File.is_analyzed == True).count()
            unanalyzed_files = total_files - analyzed_files
            
            # Get extension distribution
            extension_stats = {}
            files = self.db.query(File).filter(File.is_active == True).all()
            for file in files:
                ext = file.file_extension
                extension_stats[ext] = extension_stats.get(ext, 0) + 1
            
            stats = {
                "total_files": total_files,
                "analyzed_files": analyzed_files,
                "unanalyzed_files": unanalyzed_files,
                "extension_distribution": extension_stats
            }
            
            if format == "json":
                print(json.dumps(stats, indent=2))
            else:
                self._print_stats_table(stats)
            
            return True
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return False
        finally:
            if self.db:
                self.db.close()
    
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
        try:
            # Get all configurations
            discovery_config = config_loader.get_discovery_config()
            database_config = config_loader.get_database_config()
            logging_config = config_loader.get_logging_config()
            app_config = config_loader.get_app_settings()
            
            print("Playlist App Configuration:")
            print("=" * 50)
            
            # Discovery Configuration
            print("\n📁 Discovery Configuration:")
            print("-" * 30)
            print(f"Search Directories: {', '.join(discovery_config.get('search_directories', []))}")
            print(f"Supported Extensions: {', '.join(discovery_config.get('supported_extensions', []))}")
            print(f"Cache TTL:        {discovery_config.get('cache_settings', {}).get('ttl', 3600)} seconds")
            print(f"Batch Size:       {discovery_config.get('scan_settings', {}).get('batch_size', 100)}")
            print(f"Recursive Scan:   {discovery_config.get('scan_settings', {}).get('recursive', True)}")
            
            # Database Configuration
            print("\n🗄️ Database Configuration:")
            print("-" * 30)
            db_url = database_config.get('connection', {}).get('url', 'not configured')
            print(f"Database URL:     {db_url}")
            print(f"Pool Size:        {database_config.get('connection', {}).get('pool_size', 10)}")
            print(f"Max Overflow:     {database_config.get('connection', {}).get('max_overflow', 20)}")
            
            # Logging Configuration
            print("\n📝 Logging Configuration:")
            print("-" * 30)
            print(f"Log Level:        {logging_config.get('level', 'INFO')}")
            print(f"Console Enabled:  {logging_config.get('handlers', {}).get('console', {}).get('enabled', True)}")
            print(f"File Enabled:     {logging_config.get('handlers', {}).get('file', {}).get('enabled', True)}")
            
            # App Settings
            print("\n⚙️ Application Settings:")
            print("-" * 30)
            print(f"API Port:         {app_config.get('api', {}).get('port', 8000)}")
            print(f"Background Discovery: {app_config.get('discovery', {}).get('background_enabled', False)}")
            print(f"Discovery Interval: {app_config.get('discovery', {}).get('interval', 3600)} seconds")
            
            # Configuration Sources
            print("\n📋 Configuration Sources:")
            print("-" * 30)
            available_configs = config_loader.list_available_configs()
            if available_configs:
                print(f"Config Files:     {', '.join(available_configs)}")
            else:
                print("Config Files:     None (using environment variables)")
            print(f"Config Directory: {config_loader.config_dir}")
            
        except Exception as e:
            print(f"Error loading configuration: {e}")
            # Fallback to old method
            print("\n📁 Discovery Configuration (Fallback):")
            print("-" * 30)
            print(f"Database URL:     {DiscoveryConfig.DATABASE_URL}")
            print(f"Search Directories: {', '.join(DiscoveryConfig.SEARCH_DIRECTORIES)}")
            print(f"Supported Extensions: {', '.join(DiscoveryConfig.SUPPORTED_EXTENSIONS)}")
            print(f"Cache TTL:        {DiscoveryConfig.DISCOVERY_CACHE_TTL} seconds")
            print(f"Batch Size:       {DiscoveryConfig.DISCOVERY_BATCH_SIZE}")
            print(f"Log Level:        {DiscoveryConfig.LOG_LEVEL}")
    
    def validate_directories(self):
        """Validate search directories"""
        print("Validating search directories...")
        print()
        
        all_exist = True
        for directory in DiscoveryConfig.SEARCH_DIRECTORIES:
            if os.path.exists(directory):
                print(f"✓ {directory}")
            else:
                print(f"✗ {directory} (does not exist)")
                all_exist = False
        
        print()
        if all_exist:
            print("All search directories are valid.")
        else:
            print("Some search directories do not exist. Please check your configuration.")
        
        return all_exist

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
