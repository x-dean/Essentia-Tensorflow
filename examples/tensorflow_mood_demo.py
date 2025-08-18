#!/usr/bin/env python3
"""
TensorFlow MusicNN and Mood Analysis Demo

This script demonstrates the enhanced TensorFlow analysis capabilities:
- MusicNN model predictions for music tags
- Mood and emotion analysis
- Integration with the audio values extraction pipeline
"""

import sys
import os
import json
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playlist_app.services.tensorflow_analyzer import tensorflow_analyzer
from playlist_app.services.modular_analysis_service import modular_analysis_service

def demo_tensorflow_analysis(audio_file: str):
    """Demonstrate TensorFlow analysis on a single audio file"""
    print(f"=== TensorFlow Analysis Demo ===")
    print(f"Analyzing: {audio_file}")
    print()
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        return
    
    # Check if TensorFlow is available
    if not tensorflow_analyzer.is_available():
        print("Error: TensorFlow analysis not available")
        print("Make sure TensorFlow is installed and MusicNN model is present")
        return
    
    try:
        # Run TensorFlow analysis
        print("Running TensorFlow/MusicNN analysis...")
        results = tensorflow_analyzer.analyze_audio_file(audio_file)
        
        # Display results
        print("\n=== Analysis Results ===")
        
        # MusicNN predictions
        if "tensorflow_analysis" in results and "musicnn" in results["tensorflow_analysis"]:
            musicnn_results = results["tensorflow_analysis"]["musicnn"]
            
            if "top_predictions" in musicnn_results:
                print("\n🎵 Top MusicNN Predictions:")
                for i, pred in enumerate(musicnn_results["top_predictions"][:10], 1):
                    print(f"  {i:2d}. {pred['tag']:<20} {pred['confidence']:.3f}")
            
            if "statistics" in musicnn_results:
                stats = musicnn_results["statistics"]
                print(f"\n📊 Statistics:")
                print(f"  Mean Confidence: {stats.get('mean_confidence', 0):.3f}")
                print(f"  Max Confidence: {stats.get('max_confidence', 0):.3f}")
                print(f"  High Confidence Tags: {stats.get('high_confidence_count', 0)}")
        
        # Mood analysis
        if "mood_analysis" in results:
            mood_data = results["mood_analysis"]
            
            if "primary_mood" in mood_data:
                print(f"\n😊 Mood Analysis:")
                print(f"  Primary Mood: {mood_data['primary_mood']}")
                print(f"  Confidence: {mood_data.get('mood_confidence', 0):.3f}")
            
            if "dominant_moods" in mood_data:
                print(f"\n🎭 Dominant Moods:")
                for mood in mood_data["dominant_moods"][:5]:
                    print(f"  • {mood['mood']:<15} {mood['confidence']:.3f}")
            
            if "emotions" in mood_data:
                emotions = mood_data["emotions"]
                print(f"\n🧠 Emotional Dimensions:")
                print(f"  Valence (Positive/Negative): {emotions.get('valence', 0):.3f}")
                print(f"  Arousal (High/Low Energy): {emotions.get('arousal', 0):.3f}")
                print(f"  Energy Level: {emotions.get('energy_level', 0):.3f}")
            
            if "mood_scores" in mood_data:
                print(f"\n📈 All Mood Scores:")
                mood_scores = mood_data["mood_scores"]
                sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
                for mood, score in sorted_moods[:8]:
                    print(f"  {mood:<15} {score:.3f}")
        
        print(f"\n✅ Analysis completed successfully!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

def demo_complete_pipeline(audio_file: str):
    """Demonstrate the complete audio values extraction pipeline"""
    print(f"\n=== Complete Audio Values Extraction Pipeline ===")
    print(f"Analyzing: {audio_file}")
    print("This includes Essentia features + TensorFlow/MusicNN + Mood analysis")
    print()
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found: {audio_file}")
        return
    
    try:
        # Run complete analysis
        print("Running complete audio values extraction...")
        results = modular_analysis_service.analyze_file(
            file_path=audio_file,
            enable_essentia=True,
            enable_tensorflow=True,
            enable_faiss=False,
            force_reanalyze=True
        )
        
        # Display comprehensive results
        print("\n=== Complete Analysis Results ===")
        
        # Essentia features
        if "essentia" in results:
            essentia_data = results["essentia"]
            
            print("\n🎼 Essentia Audio Features:")
            
            if "rhythm_features" in essentia_data:
                rhythm = essentia_data["rhythm_features"]
                print(f"  Tempo: {rhythm.get('bpm', 'N/A')} BPM")
                print(f"  Rhythm Confidence: {rhythm.get('rhythm_confidence', 'N/A'):.3f}")
            
            if "harmonic_features" in essentia_data:
                harmonic = essentia_data["harmonic_features"]
                print(f"  Key: {harmonic.get('key', 'N/A')} {harmonic.get('scale', 'N/A')}")
                print(f"  Key Strength: {harmonic.get('key_strength', 'N/A'):.3f}")
            
            if "danceability_features" in essentia_data:
                dance = essentia_data["danceability_features"]
                print(f"  Danceability: {dance.get('danceability', 'N/A'):.3f}")
            
            if "basic_features" in essentia_data:
                basic = essentia_data["basic_features"]
                print(f"  Loudness: {basic.get('loudness', 'N/A'):.3f}")
                print(f"  Energy: {basic.get('energy', 'N/A'):.3f}")
        
        # TensorFlow predictions
        if "tensorflow" in results:
            tensorflow_data = results["tensorflow"]
            
            if "tensorflow_analysis" in tensorflow_data and "musicnn" in tensorflow_data["tensorflow_analysis"]:
                musicnn = tensorflow_data["tensorflow_analysis"]["musicnn"]
                
                print(f"\n🤖 TensorFlow/MusicNN Predictions:")
                if "top_predictions" in musicnn:
                    for i, pred in enumerate(musicnn["top_predictions"][:5], 1):
                        print(f"  {i}. {pred['tag']:<20} {pred['confidence']:.3f}")
        
        # Mood analysis
        if "mood_analysis" in results:
            mood_data = results["mood_analysis"]
            
            print(f"\n😊 Mood Analysis:")
            if "primary_mood" in mood_data:
                print(f"  Primary Mood: {mood_data['primary_mood']}")
                print(f"  Confidence: {mood_data.get('mood_confidence', 0):.3f}")
            
            if "emotions" in mood_data:
                emotions = mood_data["emotions"]
                print(f"  Valence: {emotions.get('valence', 0):.3f}")
                print(f"  Arousal: {emotions.get('arousal', 0):.3f}")
                print(f"  Energy: {emotions.get('energy_level', 0):.3f}")
        
        print(f"\n✅ Complete analysis pipeline finished!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main demo function"""
    if len(sys.argv) < 2:
        print("Usage: python examples/tensorflow_mood_demo.py <audio_file>")
        print("Example: python examples/tensorflow_mood_demo.py music/test1.mp3")
        return
    
    audio_file = sys.argv[1]
    
    # Demo 1: TensorFlow analysis only
    demo_tensorflow_analysis(audio_file)
    
    # Demo 2: Complete pipeline
    demo_complete_pipeline(audio_file)
    
    print(f"\n🎉 Demo completed! Check the results above.")

if __name__ == "__main__":
    main()
