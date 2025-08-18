#!/usr/bin/env python3
"""
Simple MusicNN Test with Mock Data
"""

import sys
import os
import numpy as np
sys.path.insert(0, '/app/src')

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig
    
    print("=== MusicNN Test with Mock Data ===")
    
    # Create configuration
    config = TensorFlowConfig()
    print(f"Models directory: {config.models_directory}")
    print(f"MusicNN enabled: {config.enable_musicnn}")
    
    # Create analyzer
    analyzer = TensorFlowAnalyzer(config)
    print("TensorFlow analyzer created successfully")
    
    # Test mood analysis with mock MusicNN results
    mock_musicnn_results = {
        "all_predictions": [0.8, 0.7, 0.6, 0.5, 0.4] * 10,  # 50 predictions
        "tag_names": ["rock", "pop", "jazz", "classical", "electronic"] * 10,
        "top_predictions": [
            {"tag": "rock", "confidence": 0.85, "index": 0},
            {"tag": "pop", "confidence": 0.72, "index": 1},
            {"tag": "dance", "confidence": 0.68, "index": 2},
            {"tag": "catchy", "confidence": 0.65, "index": 3},
            {"tag": "happy", "confidence": 0.62, "index": 4}
        ]
    }
    
    print("\nTesting mood analysis with mock data...")
    mood_results = analyzer._extract_mood_analysis(mock_musicnn_results)
    
    print("Mood analysis completed!")
    print(f"Primary mood: {mood_results.get('primary_mood', 'N/A')}")
    print(f"Mood confidence: {mood_results.get('mood_confidence', 0):.3f}")
    
    if 'emotions' in mood_results:
        emotions = mood_results['emotions']
        print(f"Valence: {emotions.get('valence', 0):.3f}")
        print(f"Arousal: {emotions.get('arousal', 0):.3f}")
        print(f"Energy level: {emotions.get('energy_level', 0):.3f}")
    
    if 'dominant_moods' in mood_results:
        print("\nDominant moods:")
        for mood in mood_results['dominant_moods'][:3]:
            print(f"  • {mood['mood']}: {mood['confidence']:.3f}")
    
    print("\nTest completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
