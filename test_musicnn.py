#!/usr/bin/env python3
"""
Simple MusicNN Test Script
"""

import sys
import os
sys.path.insert(0, '/app/src')

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

try:
    from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig
    
    print("=== MusicNN Test ===")
    
    # Create configuration
    config = TensorFlowConfig()
    print(f"Models directory: {config.models_directory}")
    print(f"MusicNN enabled: {config.enable_musicnn}")
    print(f"Mood analysis enabled: {config.enable_mood_analysis}")
    
    # Create analyzer
    analyzer = TensorFlowAnalyzer(config)
    print("TensorFlow analyzer created successfully")
    
    # Test with a short audio file
    audio_file = "/music/Mark Ambor - Belong Together.mp3"
    print(f"Testing with: {audio_file}")
    
    # Run analysis
    result = analyzer.analyze_audio_file(audio_file)
    
    print("Analysis completed!")
    print(f"Result keys: {list(result.keys())}")
    
    if 'tensorflow_analysis' in result:
        print("TensorFlow analysis available!")
        musicnn = result['tensorflow_analysis'].get('musicnn', {})
        if 'top_predictions' in musicnn:
            print("\nTop MusicNN predictions:")
            for i, pred in enumerate(musicnn['top_predictions'][:5], 1):
                print(f"  {i}. {pred['tag']}: {pred['confidence']:.3f}")
    
    if 'mood_analysis' in result:
        print("\nMood analysis available!")
        mood = result['mood_analysis']
        print(f"Primary mood: {mood.get('primary_mood', 'N/A')}")
        print(f"Mood confidence: {mood.get('mood_confidence', 0):.3f}")
        
        if 'emotions' in mood:
            emotions = mood['emotions']
            print(f"Valence: {emotions.get('valence', 0):.3f}")
            print(f"Arousal: {emotions.get('arousal', 0):.3f}")
            print(f"Energy level: {emotions.get('energy_level', 0):.3f}")
    
    print("\nTest completed successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
