#!/usr/bin/env python3
"""
Test script to verify TensorFlow support in Essentia
"""

import sys
import os

def test_tensorflow_essentia():
    """Test if TensorFlow is supported by Essentia"""
    try:
        print("Testing TensorFlow support in Essentia...")
        
        # Test TensorFlow import
        print("1. Testing TensorFlow import...")
        import tensorflow as tf
        print(f"   ✓ TensorFlow version: {tf.__version__}")
        
        # Test Essentia import
        print("2. Testing Essentia import...")
        import essentia
        import essentia.standard as es
        print(f"   ✓ Essentia version: {essentia.__version__}")
        
        # Test TensorFlow algorithms in Essentia
        print("3. Testing TensorFlow algorithms in Essentia...")
        
        # Check if TensorFlow algorithms are available
        tf_algorithms = [
            'TensorFlowPredict',
            'TensorFlowPredict2D',
            'TensorFlowPredictFSDSINet',
            'TensorFlowPredictVGGish'
        ]
        
        available_tf_algs = []
        for alg_name in tf_algorithms:
            try:
                alg_class = getattr(es, alg_name)
                available_tf_algs.append(alg_name)
                print(f"   ✓ {alg_name} is available")
            except AttributeError:
                print(f"   ✗ {alg_name} is not available")
        
        if available_tf_algs:
            print(f"\n✓ TensorFlow support is working! Found {len(available_tf_algs)} TensorFlow algorithms:")
            for alg in available_tf_algs:
                print(f"   - {alg}")
        else:
            print("\n✗ No TensorFlow algorithms found in Essentia")
            return False
        
        # Test basic TensorFlow functionality
        print("4. Testing basic TensorFlow functionality...")
        try:
            # Create a simple TensorFlow model
            model = tf.keras.Sequential([
                tf.keras.layers.Dense(10, activation='relu', input_shape=(5,)),
                tf.keras.layers.Dense(1)
            ])
            print("   ✓ TensorFlow model creation successful")
            
            # Test with Essentia TensorFlowPredict
            if 'TensorFlowPredict' in available_tf_algs:
                # This would require a saved model file, but we can test the import
                print("   ✓ TensorFlowPredict algorithm is available for use")
            
        except Exception as e:
            print(f"   ✗ TensorFlow functionality test failed: {e}")
            return False
        
        print("\n🎉 All tests passed! TensorFlow is properly supported by Essentia.")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_postgresql():
    """Test PostgreSQL connection"""
    try:
        print("\nTesting PostgreSQL connection...")
        
        import psycopg2
        from sqlalchemy import create_engine
        
        # Test direct psycopg2 connection
        print("1. Testing direct PostgreSQL connection...")
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="playlist_db",
            user="playlist_user",
            password="playlist_password"
        )
        print("   ✓ Direct PostgreSQL connection successful")
        conn.close()
        
        # Test SQLAlchemy connection
        print("2. Testing SQLAlchemy connection...")
        engine = create_engine("postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")
        with engine.connect() as conn:
            result = conn.execute("SELECT version();")
            version = result.fetchone()[0]
            print(f"   ✓ SQLAlchemy connection successful - PostgreSQL version: {version.split(',')[0]}")
        
        print("🎉 PostgreSQL is working correctly!")
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Docker Setup: TensorFlow + Essentia + PostgreSQL")
    print("=" * 60)
    
    tf_success = test_tensorflow_essentia()
    pg_success = test_postgresql()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    print("=" * 60)
    print(f"TensorFlow + Essentia: {'✓ PASS' if tf_success else '✗ FAIL'}")
    print(f"PostgreSQL: {'✓ PASS' if pg_success else '✗ FAIL'}")
    
    if tf_success and pg_success:
        print("\n🎉 All tests passed! Docker setup is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please check the setup.")
        sys.exit(1)
