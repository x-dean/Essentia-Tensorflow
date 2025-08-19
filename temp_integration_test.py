
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
