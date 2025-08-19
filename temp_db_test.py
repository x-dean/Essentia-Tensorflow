
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
