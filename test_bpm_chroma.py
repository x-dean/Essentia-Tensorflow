#!/usr/bin/env python3
"""
Test script to verify BPM and chroma fixes
"""

import sys
import os
import numpy as np
import tempfile
import soundfile as sf

# Add src to path
sys.path.insert(0, 'src')

def test_bpm_and_chroma():
    """Test BPM and chroma analysis with better audio signals"""
    print("🧪 Testing BPM and Chroma Analysis...")
    
    try:
        from playlist_app.services.essentia_analyzer import EssentiaAnalyzer
        
        analyzer = EssentiaAnalyzer()
        
        # Test 1: Create a rhythmic audio signal (120 BPM)
        print("✅ Test 1: Rhythmic audio (120 BPM)")
        sample_rate = 44100
        duration = 10.0  # 10 seconds for better rhythm analysis
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create a rhythmic signal with clear beats
        # 120 BPM = 0.5 seconds per beat
        beat_freq = 2.0  # 2 Hz = 120 BPM
        audio = np.sin(2 * np.pi * 440 * t) * np.sin(2 * np.pi * beat_freq * t)
        audio = audio.astype(np.float32)
        
        # Normalize
        audio = audio / np.max(np.abs(audio))
        
        rhythm_features = analyzer.extract_rhythm_features(audio)
        print(f"   - Tempo: {rhythm_features.get('tempo', 'N/A')}")
        print(f"   - Rhythm BPM: {rhythm_features.get('rhythm_bpm', 'N/A')}")
        print(f"   - Estimated BPM: {rhythm_features.get('estimated_bpm', 'N/A')}")
        print(f"   - Tempo confidence: {rhythm_features.get('tempo_confidence', 'N/A')}")
        
        # Test 2: Create a harmonic audio signal (A major chord)
        print("✅ Test 2: Harmonic audio (A major)")
        # A major chord: A (440Hz), C# (554Hz), E (659Hz)
        harmonic_audio = (
            np.sin(2 * np.pi * 440 * t) +  # A
            0.7 * np.sin(2 * np.pi * 554 * t) +  # C#
            0.5 * np.sin(2 * np.pi * 659 * t)  # E
        )
        harmonic_audio = harmonic_audio.astype(np.float32)
        harmonic_audio = harmonic_audio / np.max(np.abs(harmonic_audio))
        
        harmonic_features = analyzer.extract_harmonic_features(harmonic_audio)
        print(f"   - Dominant chroma: {harmonic_features.get('dominant_chroma', 'N/A')}")
        print(f"   - Chroma strength: {harmonic_features.get('dominant_chroma_strength', 'N/A')}")
        print(f"   - Key: {harmonic_features.get('key', 'N/A')}")
        print(f"   - Scale: {harmonic_features.get('scale', 'N/A')}")
        
        # Test 3: Test with a longer audio file for better analysis
        print("✅ Test 3: Long audio file analysis")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            sf.write(tmp_file.name, harmonic_audio, sample_rate)
            tmp_path = tmp_file.name
        
        try:
            results = analyzer.analyze_audio_file(tmp_path, include_tensorflow=False)
            
            # Extract rhythm and harmonic results
            if 'rhythm' in results:
                rhythm_result = results['rhythm']
                print(f"   - Full analysis tempo: {rhythm_result.get('tempo', 'N/A')}")
                print(f"   - Full analysis BPM: {rhythm_result.get('rhythm_bpm', 'N/A')}")
            
            if 'harmonic' in results:
                harmonic_result = results['harmonic']
                print(f"   - Full analysis chroma: {harmonic_result.get('dominant_chroma', 'N/A')}")
                print(f"   - Full analysis key: {harmonic_result.get('key', 'N/A')}")
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        print("✅ BPM and Chroma analysis completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bpm_and_chroma()
    sys.exit(0 if success else 1)
