import logging
import numpy as np
import essentia.standard as es
import essentia
import soundfile as sf
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import time
import os
import sys
import subprocess
from dataclasses import dataclass
import warnings
from ..core.analysis_config import analysis_config_loader

logger = logging.getLogger(__name__)

# Suppress Essentia logs
try:
    import essentia
    essentia.log.infoActive = False      # Disable INFO messages
    essentia.log.warningActive = False   # Disable WARNING messages
    # Keep ERROR active for critical issues
except ImportError:
    pass

# Suppress other library logs
os.environ["LIBROSA_LOG_LEVEL"] = "WARNING"
os.environ["PYTHONWARNINGS"] = "ignore"

# Redirect stdout/stderr for Essentia operations
class SuppressOutput:
    def __enter__(self):
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

def safe_float(value: Any) -> float:
    """
    Convert value to a JSON-safe float, handling inf, -inf, and NaN values.
    
    Args:
        value: The value to convert
        
    Returns:
        JSON-safe float value
    """
    if value is None:
        return -999.0  # Use standardized fallback value
    
    try:
        float_val = float(value)
        if np.isnan(float_val) or np.isinf(float_val):
            return -999.0  # Use standardized fallback value
        return float_val
    except (ValueError, TypeError):
        return -999.0  # Use standardized fallback value

def safe_json_serialize(obj: Any) -> Any:
    """
    Safely serialize objects for JSON storage, handling numpy types and special values.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON-serializable object
    """
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return safe_float(obj)
    elif isinstance(obj, dict):
        return {k: safe_json_serialize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif obj is None:
        return None
    else:
        return obj

@dataclass
class EssentiaConfig:
    """Configuration for Essentia analysis"""
    sample_rate: int = 44100
    channels: int = 1
    frame_size: int = 2048
    hop_size: int = 1024
    window_type: str = "hann"
    zero_padding: int = 0
    min_frequency: float = 20.0
    max_frequency: float = 8000.0
    n_mels: int = 96
    n_mfcc: int = 40
    n_spectral_peaks: int = 100
    silence_threshold: float = -60.0
    min_track_length: float = 1.0
    max_track_length: float = 600.0
    chunk_duration: float = 30.0
    overlap_ratio: float = 0.5

class EssentiaAnalyzer:
    """
    Pure Essentia audio analysis module.
    
    This module handles only Essentia-based audio feature extraction,
    without any TensorFlow or machine learning dependencies.
    """
    
    def __init__(self, config: Optional[EssentiaConfig] = None):
        self.config = config or EssentiaConfig()
        self._load_config()
    
    def _load_config(self):
        """Load configuration from analysis config"""
        try:
            config = analysis_config_loader.get_config()
            
            # Update config with loaded values
            self.config.sample_rate = config.audio_processing.sample_rate
            self.config.channels = config.audio_processing.channels
            self.config.frame_size = config.audio_processing.frame_size
            self.config.hop_size = config.audio_processing.hop_size
            self.config.window_type = config.audio_processing.window_type
            self.config.zero_padding = config.audio_processing.zero_padding
            
            self.config.min_frequency = config.spectral_analysis.min_frequency
            self.config.max_frequency = config.spectral_analysis.max_frequency
            self.config.n_mels = config.spectral_analysis.n_mels
            self.config.n_mfcc = config.spectral_analysis.n_mfcc
            self.config.n_spectral_peaks = config.spectral_analysis.n_spectral_peaks
            self.config.silence_threshold = config.spectral_analysis.silence_threshold
            
            self.config.min_track_length = config.track_analysis.min_track_length
            self.config.max_track_length = config.track_analysis.max_track_length
            self.config.chunk_duration = config.track_analysis.chunk_duration
            self.config.overlap_ratio = config.track_analysis.overlap_ratio
                
        except Exception as e:
            logger.warning(f"Failed to load Essentia configuration: {e}, using defaults")
    
    def analyze_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze an audio file using Essentia only.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing Essentia analysis results
        """
        try:
            logger.info(f"Starting Essentia analysis for: {file_path}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Load audio with Essentia
            with SuppressOutput():
                audio = es.MonoLoader(filename=file_path, sampleRate=self.config.sample_rate)()
            
            if len(audio) == 0:
                raise ValueError(f"Empty audio file: {file_path}")
            
            # Perform analysis
            results = self._extract_features(audio)
            
            # Add metadata
            results["metadata"] = {
                "file_path": file_path,
                "sample_rate": self.config.sample_rate,
                "duration": len(audio) / self.config.sample_rate,
                "analysis_timestamp": time.time(),
                "analyzer": "essentia"
            }
            
            logger.info(f"Essentia analysis completed for: {file_path}")
            return results
            
        except Exception as e:
            logger.error(f"Essentia analysis failed for {file_path}: {e}")
            # Return fallback results instead of raising
            return self._get_fallback_results(file_path, str(e))
    
    def _get_fallback_results(self, file_path: str, error: str) -> Dict[str, Any]:
        """Return fallback results when analysis fails"""
        return {
            "metadata": {
                "file_path": file_path,
                "analysis_timestamp": time.time(),
                "analyzer": "essentia",
                "error": error
            },
            "basic_features": {
                "loudness": -999.0,
                "dynamic_complexity": -999.0,
                "spectral_complexity": -999.0
            },
            "spectral_features": {
                "spectral_centroid": -999.0,
                "spectral_rolloff": -999.0,
                "spectral_bandwidth": -999.0,
                "spectral_flatness": -999.0
            },
            "rhythm_features": {
                "bpm": -999.0,
                "rhythm_confidence": -999.0,
                "beat_confidence": -999.0
            },
            "harmonic_features": {
                "key": "unknown",
                "scale": "unknown",
                "key_strength": -999.0,
                "chords": [],
                "chord_strength": -999.0
            },
            "mfcc_features": {
                "mfcc_mean": [-999.0] * self.config.n_mfcc,
                "mfcc_std": [-999.0] * self.config.n_mfcc
            }
        }
    
    def _extract_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract audio features using Essentia algorithms.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        
        try:
            with SuppressOutput():
                # Basic audio features
                features["basic_features"] = self._extract_basic_features(audio)
                
                # Spectral features
                features["spectral_features"] = self._extract_spectral_features(audio)
                
                # Rhythm features
                features["rhythm_features"] = self._extract_rhythm_features(audio)
                
                # Harmonic features
                features["harmonic_features"] = self._extract_harmonic_features(audio)
                
                # MFCC features
                features["mfcc_features"] = self._extract_mfcc_features(audio)
                
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            # Return basic features if advanced extraction fails
            features["basic_features"] = self._extract_basic_features(audio)
            features["spectral_features"] = self._get_spectral_fallback()
            features["rhythm_features"] = self._get_rhythm_fallback()
            features["harmonic_features"] = self._get_harmonic_fallback()
            features["mfcc_features"] = self._get_mfcc_fallback()
        
        return features
    
    def _extract_basic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract basic audio features"""
        features = {}
        
        try:
            with SuppressOutput():
                # Loudness
                loudness = es.Loudness()
                features["loudness"] = safe_float(loudness(audio))
                
                # Dynamic complexity
                dynamic_complexity = es.DynamicComplexity()
                features["dynamic_complexity"] = safe_float(dynamic_complexity(audio))
                
                # Spectral complexity
                spectral_complexity = es.SpectralComplexity()
                features["spectral_complexity"] = safe_float(spectral_complexity(audio))
                
        except Exception as e:
            logger.warning(f"Basic feature extraction failed: {e}")
            features.update({
                "loudness": -999.0,
                "dynamic_complexity": -999.0,
                "spectral_complexity": -999.0
            })
        
        return features
    
    def _extract_spectral_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract spectral features"""
        features = {}
        
        try:
            with SuppressOutput():
                # Use SpectralCentroid algorithm correctly
                spectral_centroid = es.SpectralCentroid()
                features["spectral_centroid"] = safe_float(spectral_centroid(audio))
                
                # Spectral rolloff
                spectral_rolloff = es.SpectralRolloff()
                features["spectral_rolloff"] = safe_float(spectral_rolloff(audio))
                
                # Spectral bandwidth
                spectral_bandwidth = es.SpectralBandwidth()
                features["spectral_bandwidth"] = safe_float(spectral_bandwidth(audio))
                
                # Spectral flatness
                spectral_flatness = es.SpectralFlatness()
                features["spectral_flatness"] = safe_float(spectral_flatness(audio))
                
        except Exception as e:
            logger.warning(f"Spectral feature extraction failed: {e}")
            features.update(self._get_spectral_fallback())
        
        return features
    
    def _get_spectral_fallback(self) -> Dict[str, Any]:
        """Get fallback values for spectral features"""
        return {
            "spectral_centroid": -999.0,
            "spectral_rolloff": -999.0,
            "spectral_bandwidth": -999.0,
            "spectral_flatness": -999.0
        }
    
    def _extract_rhythm_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract rhythm features"""
        features = {}
        
        try:
            with SuppressOutput():
                # Rhythm extractor
                rhythm_extractor = es.RhythmExtractor2013()
                bpm, ticks, confidence, estimates, bpm_intervals = rhythm_extractor(audio)
                
                features["bpm"] = safe_float(bpm)
                features["rhythm_confidence"] = safe_float(confidence)
                
                # Beat tracker
                beat_tracker = es.BeatTrackerMultiFeature()
                ticks, confidence = beat_tracker(audio)
                features["beat_confidence"] = safe_float(confidence)
                
        except Exception as e:
            logger.warning(f"Rhythm feature extraction failed: {e}")
            features.update(self._get_rhythm_fallback())
        
        return features
    
    def _get_rhythm_fallback(self) -> Dict[str, Any]:
        """Get fallback values for rhythm features"""
        return {
            "bpm": -999.0,
            "rhythm_confidence": -999.0,
            "beat_confidence": -999.0
        }
    
    def _extract_harmonic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract harmonic features"""
        features = {}
        
        try:
            with SuppressOutput():
                # Key detection
                key_detector = es.Key()
                key, scale, strength = key_detector(audio)
                
                features["key"] = key
                features["scale"] = scale
                features["key_strength"] = safe_float(strength)
                
                # Chords detection
                chord_detector = es.ChordsDetection()
                chords, strength = chord_detector(audio)
                features["chords"] = chords
                features["chord_strength"] = safe_float(strength)
                
        except Exception as e:
            logger.warning(f"Harmonic feature extraction failed: {e}")
            features.update(self._get_harmonic_fallback())
        
        return features
    
    def _get_harmonic_fallback(self) -> Dict[str, Any]:
        """Get fallback values for harmonic features"""
        return {
            "key": "unknown",
            "scale": "unknown",
            "key_strength": -999.0,
            "chords": [],
            "chord_strength": -999.0
        }
    
    def _extract_mfcc_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract MFCC features"""
        features = {}
        
        try:
            with SuppressOutput():
                # MFCC
                mfcc = es.MFCC(numberCoefficients=self.config.n_mfcc)
                mfcc_coeffs, mfcc_bands = mfcc(audio)
                
                # Store mean and std of MFCC coefficients
                features["mfcc_mean"] = safe_json_serialize(np.mean(mfcc_coeffs, axis=0))
                features["mfcc_std"] = safe_json_serialize(np.std(mfcc_coeffs, axis=0))
                
        except Exception as e:
            logger.warning(f"MFCC feature extraction failed: {e}")
            features.update(self._get_mfcc_fallback())
        
        return features
    
    def _get_mfcc_fallback(self) -> Dict[str, Any]:
        """Get fallback values for MFCC features"""
        return {
            "mfcc_mean": [-999.0] * self.config.n_mfcc,
            "mfcc_std": [-999.0] * self.config.n_mfcc
        }

# Global instance
essentia_analyzer = EssentiaAnalyzer()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python essentia_analyzer.py <audiofile> [command]")
        print("Commands:")
        print("  analyze - Analyze single file")
        print("  library <dir> - Build library from directory")
        print("  search <query> <top_n> - Search for similar tracks")
        print("  stats - Show library statistics")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    analyzer = EssentiaAnalyzer()
    
    command = sys.argv[2] if len(sys.argv) > 2 else "analyze"
    
    if command == "analyze":
        # Analyze single file
        results = analyzer.analyze_audio_file(str(file_path))
        print(json.dumps(results, indent=2))
        
    elif command == "library" and len(sys.argv) > 3:
        # Build library from directory
        import glob
        music_dir = sys.argv[3]
        audio_files = []
        for ext in ['*.mp3', '*.wav', '*.flac', '*.m4a']:
            audio_files.extend(glob.glob(os.path.join(music_dir, '**', ext), recursive=True))
        
        print(f"Found {len(audio_files)} audio files")
        analyzer.add_multiple_to_library(audio_files[:10])  # Limit to first 10 for demo
        
        # Save index
        analyzer.save_index("music_library")
        
        # Show stats
        stats = analyzer.get_library_stats()
        print(json.dumps(stats, indent=2))
        
    elif command == "search" and len(sys.argv) > 3:
        # Search for similar tracks
        top_n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        
        # Load index if exists
        if os.path.exists("music_library.faiss"):
            analyzer.load_index("music_library")
        
        results = analyzer.find_similar(str(file_path), top_n=top_n)
        print(json.dumps(results, indent=2))
        
    elif command == "stats":
        # Show library statistics
        stats = analyzer.get_library_stats()
        print(json.dumps(stats, indent=2))
        
    else:
        # Default: analyze single file
        results = analyzer.analyze_audio_file(str(file_path))
        print(json.dumps(results, indent=2))
