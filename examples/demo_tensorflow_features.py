#!/usr/bin/env python3
"""
TensorFlow Integration Features Demo

This script demonstrates the enhanced TensorFlow integration features:
- Configuration management
- Mood analysis algorithms
- MusicNN tag processing
- Emotional dimension calculations
- Integration capabilities
"""

import sys
import json
import numpy as np
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playlist_app.services.tensorflow_analyzer import TensorFlowConfig, TensorFlowAnalyzer

def demo_configuration():
    """Demonstrate configuration management"""
    print("=== Configuration Management ===")
    
    # Default configuration
    default_config = TensorFlowConfig()
    print("Default Configuration:")
    print(f"  Models Directory: {default_config.models_directory}")
    print(f"  Enable MusicNN: {default_config.enable_musicnn}")
    print(f"  Sample Rate: {default_config.sample_rate}")
    print(f"  MusicNN Input Frames: {default_config.musicnn_input_frames}")
    print(f"  MusicNN Input Mels: {default_config.musicnn_input_mels}")
    print(f"  Enable Mood Analysis: {default_config.enable_mood_analysis}")
    print(f"  Mood Confidence Threshold: {default_config.mood_confidence_threshold}")
    
    # Custom configuration
    custom_config = TensorFlowConfig(
        models_directory="custom_models",
        enable_musicnn=True,
        sample_rate=22050,
        mood_confidence_threshold=0.5
    )
    print("\nCustom Configuration:")
    print(f"  Models Directory: {custom_config.models_directory}")
    print(f"  Sample Rate: {custom_config.sample_rate}")
    print(f"  Mood Confidence Threshold: {custom_config.mood_confidence_threshold}")

def demo_mood_analysis():
    """Demonstrate mood analysis algorithms"""
    print("\n=== Mood Analysis Algorithms ===")
    
    # Create analyzer instance
    analyzer = TensorFlowAnalyzer()
    
    # Mock MusicNN predictions for different music types
    test_cases = [
        {
            "name": "Energetic Rock",
            "predictions": [0.9, 0.8, 0.7, 0.1, 0.2, 0.3, 0.8, 0.1, 0.9, 0.2],
            "tags": ["dance", "rock", "party", "chill", "ambient", "mellow", "catchy", "sad", "happy", "aggressive"]
        },
        {
            "name": "Calm Ambient",
            "predictions": [0.1, 0.2, 0.1, 0.9, 0.8, 0.7, 0.2, 0.1, 0.3, 0.1],
            "tags": ["dance", "rock", "party", "chill", "ambient", "mellow", "catchy", "sad", "happy", "aggressive"]
        },
        {
            "name": "Happy Pop",
            "predictions": [0.8, 0.6, 0.7, 0.3, 0.2, 0.4, 0.9, 0.1, 0.8, 0.2],
            "tags": ["dance", "rock", "party", "chill", "ambient", "mellow", "catchy", "sad", "happy", "aggressive"]
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{test_case['name']}:")
        
        # Calculate emotional dimensions
        valence = analyzer._calculate_valence(test_case["predictions"], test_case["tags"])
        arousal = analyzer._calculate_arousal(test_case["predictions"], test_case["tags"])
        energy = analyzer._calculate_energy_level(test_case["predictions"], test_case["tags"])
        
        print(f"  Valence (Positive/Negative): {valence:.3f}")
        print(f"  Arousal (High/Low Energy): {arousal:.3f}")
        print(f"  Energy Level: {energy:.3f}")
        
        # Determine mood characteristics
        if valence > 0.3:
            valence_desc = "Positive"
        elif valence < -0.3:
            valence_desc = "Negative"
        else:
            valence_desc = "Neutral"
        
        if arousal > 0.6:
            arousal_desc = "High Energy"
        else:
            arousal_desc = "Low Energy"
        
        print(f"  Mood: {valence_desc}, {arousal_desc}")

def demo_musicnn_processing():
    """Demonstrate MusicNN processing capabilities"""
    print("\n=== MusicNN Processing ===")
    
    analyzer = TensorFlowAnalyzer()
    
    # Mock MusicNN results
    mock_results = {
        "all_predictions": [
            0.85, 0.72, 0.68, 0.45, 0.38, 0.32, 0.28, 0.25, 0.22, 0.18,
            0.15, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01
        ] * 2 + [0.01] * 10,  # 50 total predictions
        "tag_names": [
            "rock", "pop", "alternative", "indie", "electronic", "female vocalists",
            "dance", "00s", "alternative rock", "jazz", "beautiful", "metal",
            "chillout", "male vocalists", "classic rock", "soul", "indie rock",
            "Mellow", "electronica", "80s", "folk", "90s", "chill", "instrumental",
            "punk", "oldies", "blues", "hard rock", "ambient", "acoustic",
            "experimental", "female vocalist", "guitar", "Hip-Hop", "70s", "party",
            "country", "easy listening", "sexy", "catchy", "funk", "electro",
            "heavy metal", "Progressive rock", "60s", "rnb", "indie pop", "sad",
            "House", "happy"
        ]
    }
    
    # Process results
    processed_results = analyzer._process_musicnn_predictions(np.array([mock_results["all_predictions"]]))
    
    print("Top Predictions:")
    for i, pred in enumerate(processed_results["top_predictions"][:10], 1):
        print(f"  {i:2d}. {pred['tag']:<20} {pred['confidence']:.3f}")
    
    print(f"\nStatistics:")
    stats = processed_results["statistics"]
    print(f"  Mean Confidence: {stats['mean_confidence']:.3f}")
    print(f"  Max Confidence: {stats['max_confidence']:.3f}")
    print(f"  High Confidence Count: {stats['high_confidence_count']}")
    
    # Extract mood analysis
    mood_results = analyzer._extract_mood_analysis(processed_results)
    
    print(f"\nMood Analysis:")
    print(f"  Primary Mood: {mood_results['primary_mood']}")
    print(f"  Mood Confidence: {mood_results['mood_confidence']:.3f}")
    
    print(f"\nDominant Moods:")
    for mood in mood_results["dominant_moods"][:5]:
        print(f"  • {mood['mood']:<15} {mood['confidence']:.3f}")
    
    print(f"\nEmotional Dimensions:")
    emotions = mood_results["emotions"]
    print(f"  Valence: {emotions['valence']:.3f}")
    print(f"  Arousal: {emotions['arousal']:.3f}")
    print(f"  Energy Level: {emotions['energy_level']:.3f}")

def demo_integration_capabilities():
    """Demonstrate integration capabilities"""
    print("\n=== Integration Capabilities ===")
    
    # Show how the system integrates with different components
    integration_points = [
        {
            "component": "Database Storage",
            "description": "TensorFlow results stored in dedicated columns",
            "fields": [
                "tensorflow_features (JSON)",
                "tensorflow_summary (JSON)", 
                "mood_analysis (JSON)",
                "primary_mood (VARCHAR)",
                "mood_confidence (FLOAT)"
            ]
        },
        {
            "component": "CLI Commands",
            "description": "Command-line interface for analysis",
            "commands": [
                "python scripts/master_cli.py tensorflow analyze --files track.mp3",
                "python scripts/master_cli.py audio-values analyze --files track.mp3"
            ]
        },
        {
            "component": "API Integration",
            "description": "RESTful API endpoints for programmatic access",
            "endpoints": [
                "POST /api/analyzer/analyze (with tensorflow=true)",
                "GET /api/analyzer/status (shows TensorFlow availability)"
            ]
        },
        {
            "component": "Modular Design",
            "description": "Independent enable/disable of components",
            "modules": [
                "Essentia (audio features)",
                "TensorFlow (ML predictions)", 
                "FAISS (vector search)"
            ]
        }
    ]
    
    for point in integration_points:
        print(f"\n{point['component']}:")
        print(f"  {point['description']}")
        
        if "fields" in point:
            print("  Database Fields:")
            for field in point["fields"]:
                print(f"    • {field}")
        
        if "commands" in point:
            print("  CLI Commands:")
            for cmd in point["commands"]:
                print(f"    • {cmd}")
        
        if "endpoints" in point:
            print("  API Endpoints:")
            for endpoint in point["endpoints"]:
                print(f"    • {endpoint}")
        
        if "modules" in point:
            print("  Modules:")
            for module in point["modules"]:
                print(f"    • {module}")

def demo_mood_categories():
    """Demonstrate mood categories and their characteristics"""
    print("\n=== Mood Categories ===")
    
    mood_categories = {
        "energetic": {
            "description": "High-energy, dynamic music",
            "associated_tags": ["dance", "party", "catchy", "rock", "metal", "hard rock", "heavy metal", "punk"],
            "characteristics": ["Fast tempo", "High intensity", "Upbeat rhythm"]
        },
        "calm": {
            "description": "Relaxing, peaceful music", 
            "associated_tags": ["chill", "chillout", "ambient", "Mellow", "easy listening", "beautiful"],
            "characteristics": ["Slow tempo", "Low intensity", "Smooth transitions"]
        },
        "happy": {
            "description": "Positive, uplifting music",
            "associated_tags": ["happy", "catchy", "party", "dance", "funk", "sexy"],
            "characteristics": ["Positive valence", "Upbeat mood", "Catchy melodies"]
        },
        "sad": {
            "description": "Melancholic, emotional music",
            "associated_tags": ["sad", "Mellow", "chill", "chillout"],
            "characteristics": ["Negative valence", "Slow tempo", "Emotional depth"]
        },
        "aggressive": {
            "description": "Intense, powerful music",
            "associated_tags": ["metal", "hard rock", "heavy metal", "punk", "rock"],
            "characteristics": ["High intensity", "Distorted sounds", "Strong rhythm"]
        },
        "peaceful": {
            "description": "Serene, tranquil music",
            "associated_tags": ["ambient", "chill", "chillout", "beautiful", "easy listening"],
            "characteristics": ["Low arousal", "Smooth textures", "Relaxing atmosphere"]
        }
    }
    
    for mood, info in mood_categories.items():
        print(f"\n{mood.title()}:")
        print(f"  Description: {info['description']}")
        print(f"  Associated Tags: {', '.join(info['associated_tags'][:4])}...")
        print(f"  Characteristics: {', '.join(info['characteristics'])}")

def main():
    """Main demonstration function"""
    print("🎵 TensorFlow Integration Features Demo")
    print("=" * 60)
    print("This demo shows the enhanced TensorFlow integration capabilities")
    print("without requiring actual audio files or TensorFlow installation.")
    print()
    
    try:
        demo_configuration()
        demo_mood_analysis()
        demo_musicnn_processing()
        demo_integration_capabilities()
        demo_mood_categories()
        
        print("\n" + "=" * 60)
        print("✅ Demo completed successfully!")
        print("\nTo test with actual audio files:")
        print("1. Install TensorFlow: pip install tensorflow")
        print("2. Ensure MusicNN models are in models/ directory")
        print("3. Run: python examples/tensorflow_mood_demo.py music/track.mp3")
        print("4. Or use CLI: python scripts/master_cli.py tensorflow analyze --files music/track.mp3")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
