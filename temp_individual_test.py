
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
