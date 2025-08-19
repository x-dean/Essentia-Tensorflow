
import sys
import os
sys.path.insert(0, '/app/src')

try:
    # Test Essentia
    try:
        import essentia
        import essentia.standard as ess
        essentia_available = True
        essentia_version = essentia.__version__
    except ImportError:
        essentia_available = False
        essentia_version = None
    
    # Test TensorFlow
    try:
        import tensorflow as tf
        tensorflow_available = True
        tensorflow_version = tf.__version__
    except ImportError:
        tensorflow_available = False
        tensorflow_version = None
    
    # Test FAISS
    try:
        import faiss
        faiss_available = True
        faiss_version = faiss.__version__
    except ImportError:
        faiss_available = False
        faiss_version = None
    
    # Test analyzer services
    services = {}
    try:
        from playlist_app.services.independent_essentia_service import IndependentEssentiaService
        services['essentia_service'] = 'available'
    except Exception as e:
        services['essentia_service'] = f'error: {str(e)}'
    
    try:
        from playlist_app.services.independent_tensorflow_service import IndependentTensorFlowService
        services['tensorflow_service'] = 'available'
    except Exception as e:
        services['tensorflow_service'] = f'error: {str(e)}'
    
    try:
        from playlist_app.services.independent_faiss_service import IndependentFAISSService
        services['faiss_service'] = 'available'
    except Exception as e:
        services['faiss_service'] = f'error: {str(e)}'
    
    print("SUCCESS")
    print(f"ESSENTIA: {essentia_available} ({essentia_version})")
    print(f"TENSORFLOW: {tensorflow_available} ({tensorflow_version})")
    print(f"FAISS: {faiss_available} ({faiss_version})")
    print(f"SERVICES: {services}")
    
except Exception as e:
    print(f"ERROR: {str(e)}")
    sys.exit(1)
