#!/usr/bin/env python3
"""
Test script for backup and restore functionality
"""

import os
import sys
import tempfile
import zipfile
import shutil
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from playlist_app.core.config_loader import config_loader
from playlist_app.core.config_manager import config_manager

def test_backup():
    """Test backup functionality"""
    print("Testing backup functionality...")
    
    try:
        # Create a backup
        backup_path = config_loader.create_backup()
        print(f"Backup created at: {backup_path}")
        
        # Check if backup files exist
        backup_files = list(backup_path.glob("*.json"))
        print(f"Backup contains {len(backup_files)} files:")
        for file in backup_files:
            print(f"  - {file.name}")
        
        return backup_path
    except Exception as e:
        print(f"Backup failed: {e}")
        return None

def test_zip_creation(backup_path):
    """Test ZIP file creation"""
    print("\nTesting ZIP creation...")
    
    try:
        # Create a temporary ZIP file
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_zip:
            zip_path = Path(tmp_zip.name)
        
        # Create ZIP from backup
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in backup_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(backup_path)
                    zipf.write(file_path, arcname)
                    print(f"Added to ZIP: {arcname}")
        
        print(f"ZIP file created: {zip_path}")
        print(f"ZIP file size: {zip_path.stat().st_size} bytes")
        
        return zip_path
    except Exception as e:
        print(f"ZIP creation failed: {e}")
        return None

def test_restore(zip_path):
    """Test restore functionality"""
    print("\nTesting restore functionality...")
    
    try:
        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            extract_dir = temp_path / "extracted"
            extract_dir.mkdir(exist_ok=True)
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            print(f"ZIP extracted to: {extract_dir}")
            
            # List extracted files
            extracted_files = list(extract_dir.rglob("*.json"))
            print(f"Extracted {len(extracted_files)} files:")
            for file in extracted_files:
                print(f"  - {file.relative_to(extract_dir)}")
            
            # Find config backup directory
            config_backup_dir = None
            for item in extract_dir.iterdir():
                if item.is_dir() and item.name.startswith("config_backup"):
                    config_backup_dir = item
                    break
            
            if not config_backup_dir:
                if any(extract_dir.glob("*.json")):
                    config_backup_dir = extract_dir
            
            if config_backup_dir:
                print(f"Found config backup directory: {config_backup_dir}")
                return True
            else:
                print("No valid config backup directory found")
                return False
                
    except Exception as e:
        print(f"Restore test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Starting backup and restore tests...")
    
    # Test backup
    backup_path = test_backup()
    if not backup_path:
        print("Backup test failed, exiting")
        return
    
    # Test ZIP creation
    zip_path = test_zip_creation(backup_path)
    if not zip_path:
        print("ZIP creation test failed, exiting")
        return
    
    # Test restore
    restore_success = test_restore(zip_path)
    
    # Cleanup
    try:
        if zip_path and zip_path.exists():
            zip_path.unlink()
            print(f"\nCleaned up: {zip_path}")
    except Exception as e:
        print(f"Cleanup failed: {e}")
    
    print(f"\nTest results:")
    print(f"  Backup: {'PASS' if backup_path else 'FAIL'}")
    print(f"  ZIP Creation: {'PASS' if zip_path else 'FAIL'}")
    print(f"  Restore: {'PASS' if restore_success else 'FAIL'}")

if __name__ == "__main__":
    main()
