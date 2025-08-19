#!/usr/bin/env python3

import sys
import os

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

from playlist_app.models.database import get_db_session, File, FileStatus
from playlist_app.services.independent_essentia_service import essentia_service

def debug_stats():
    db = get_db_session()
    try:
        # Check total files
        total_files = db.query(File).filter(File.is_active == True).count()
        print(f"Total active files: {total_files}")
        
        # Check Essentia stats directly
        essentia_stats = essentia_service.get_stats(db)
        print(f"Essentia stats: {essentia_stats}")
        
        # Check if there are any Essentia status records
        from playlist_app.models.database import EssentiaAnalysisStatus, AnalyzerStatus
        analyzed_count = db.query(EssentiaAnalysisStatus).filter(
            EssentiaAnalysisStatus.status == AnalyzerStatus.ANALYZED
        ).count()
        print(f"Essentia analyzed count: {analyzed_count}")
        
        pending_count = db.query(EssentiaAnalysisStatus).filter(
            EssentiaAnalysisStatus.status == AnalyzerStatus.PENDING
        ).count()
        print(f"Essentia pending count: {pending_count}")
        
        # Check if any status records exist at all
        total_status_records = db.query(EssentiaAnalysisStatus).count()
        print(f"Total Essentia status records: {total_status_records}")
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_stats()
