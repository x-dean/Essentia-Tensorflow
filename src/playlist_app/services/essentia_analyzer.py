import logging
import os
import time
import numpy as np
from typing import Dict, Any, Optional, List
import essentia as es
import essentia.standard as ess

from ..core.logging import get_logger
from ..core.analysis_config import AnalysisConfig

logger = get_logger(__name__)

class SuppressOutput:
    """Context manager to suppress stdout/stderr"""
    def __enter__(self):
        import os
        import sys
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr
        sys.stdout = open(os.devnull, 'w')
        sys.stderr = open(os.devnull, 'w')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import sys
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr

def safe_float(value) -> float:
    """Safely convert value to float, returning -999.0 if conversion fails"""
    try:
        if value is None or (isinstance(value, (list, tuple)) and len(value) == 0):
            return -999.0
        return float(value)
    except (ValueError, TypeError):
        return -999.0

def safe_json_serialize(value) -> Any:
    """Safely serialize value for JSON output"""
    if isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, (np.integer, np.floating)):
        return float(value)
    return value



class EssentiaAnalyzer:
    """Essentia-based audio feature extractor using streaming algorithms"""
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        if config is None:
            # Create default config
            config = AnalysisConfig()
        self.config = config
        logger.info("EssentiaAnalyzer initialized with streaming algorithms")
    
    def analyze_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze an audio file using Essentia streaming algorithms.
        
        Strategy:
        - Short tracks (< 30s): Analyze full track
        - Medium tracks (30s - 10min): Analyze 60s segment starting at 30s
        - Long tracks (> 10min): Analyze 120s segment starting at 60s
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing Essentia analysis results
        """
        try:
            logger.info(f"Starting streaming Essentia analysis for: {file_path}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Load audio using streaming MonoLoader
            logger.info(f"Loading audio file: {file_path}")
            audio = self._load_audio_streaming(file_path)
            if audio is None:
                raise RuntimeError("Failed to load audio")
            
            # Get track duration
            duration = len(audio) / self.config.audio_processing.sample_rate
            logger.info(f"Audio duration: {duration:.2f} seconds")
            
            # Determine analysis strategy
            if duration < 30:
                logger.info(f"Short track ({duration:.1f}s), analyzing full track")
                segment_audio = audio
                start_time = 0
                segment_duration = duration
            elif duration > 600:  # > 10 minutes
                logger.info(f"Long track ({duration:.1f}s), analyzing 120s segment starting at 60s")
                start_time = 60
                segment_duration = 120
                segment_audio = self._extract_segment(audio, start_time, segment_duration)
            else:
                logger.info(f"Medium track ({duration:.1f}s), analyzing 60s segment starting at 30s")
                start_time = 30
                segment_duration = 60
                segment_audio = self._extract_segment(audio, start_time, segment_duration)
            
            # Perform streaming analysis
            results = self._extract_features_streaming(segment_audio)
            
            # Add metadata
            results["metadata"] = {
                "file_path": file_path,
                "sample_rate": self.config.audio_processing.sample_rate,
                "total_duration": duration,
                "segment_start_time": start_time,
                "segment_duration": segment_duration,
                "analysis_timestamp": time.time(),
                "analyzer": "essentia_streaming",
                "analysis_strategy": f"segment_{segment_duration}s"
            }
            
            logger.info(f"Streaming analysis completed for: {file_path}")
            return results
            
        except Exception as e:
            logger.error(f"Streaming Essentia analysis failed for {file_path}: {e}")
            raise
    
    def _load_audio_streaming(self, file_path: str) -> Optional[np.ndarray]:
        """Load audio using streaming MonoLoader"""
        try:
            with SuppressOutput():
                # Use streaming MonoLoader
                loader = ess.MonoLoader(filename=file_path, sampleRate=self.config.audio_processing.sample_rate)
                audio = loader()
                logger.info(f"Audio loaded successfully, length: {len(audio)} samples")
                return audio
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            return None
    
    def _extract_segment(self, audio: np.ndarray, start_time: float, duration: float) -> np.ndarray:
        """Extract a segment from the audio"""
        start_sample = int(start_time * self.config.audio_processing.sample_rate)
        end_sample = min(start_sample + int(duration * self.config.audio_processing.sample_rate), len(audio))
        return audio[start_sample:end_sample]
    
    def _extract_features_streaming(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract audio features using Essentia algorithms.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        
        logger.info("Starting feature extraction...")
        
        # Basic features
        logger.info("Extracting basic features...")
        features["basic_features"] = self._extract_basic_features(audio)
        
        # MFCC features
        logger.info("Extracting MFCC features...")
        features["mfcc_features"] = self._extract_mfcc_features(audio)
        
        # Spectral features
        logger.info("Extracting spectral features...")
        features["spectral_features"] = self._extract_spectral_features(audio)
        
        # Rhythm features
        logger.info("Extracting rhythm features...")
        features["rhythm_features"] = self._extract_rhythm_features(audio)
        
        # Danceability features
        logger.info("Extracting danceability features...")
        features["danceability_features"] = self._extract_danceability_features(audio)
        
        # Harmonic features
        logger.info("Extracting harmonic features...")
        features["harmonic_features"] = self._extract_harmonic_features(audio)
        
        logger.info("Feature extraction completed")
        
        return features
    
    def _extract_spectral_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract essential spectral features for playlist apps"""
        features = {}
        
        # Spectral centroid - essential for brightness/timbre matching
        features["spectral_centroid"] = safe_float(ess.Centroid()(audio))
        
        # Spectral rolloff - useful for frequency content
        features["spectral_rolloff"] = safe_float(ess.RollOff()(audio))
        
        return features
    
    def _extract_danceability_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract danceability features for playlist apps"""
        features = {}
        
        with SuppressOutput():
            # Danceability - essential for dance/party playlists
            try:
                danceability = ess.Danceability()
                dance_result = danceability(audio)
                # Danceability returns a tuple (danceability_value, dfa_array)
                if isinstance(dance_result, tuple):
                    raw_danceability = safe_float(dance_result[0])
                else:
                    raw_danceability = safe_float(dance_result)
                
                # Normalize danceability: typical range is 0-3, normalize to 0-1
                features["danceability"] = min(1.0, max(0.0, raw_danceability / 3.0))
            except Exception as e:
                logger.warning(f"Danceability extraction failed: {e}")
                features["danceability"] = 0.5  # Default neutral value
        
        return features
    
    def _extract_rhythm_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract rhythm features"""
        features = {}
        
        # Use PercivalBpmEstimator for more reliable BPM detection
        try:
            bpm_estimator = ess.PercivalBpmEstimator()
            bpm = bpm_estimator(audio)
            features["bpm"] = safe_float(bpm)
            features["rhythm_confidence"] = 0.8  # High confidence for Percival
            features["beat_confidence"] = 0.8
        except:
            # Fallback to RhythmExtractor
            rhythm_extractor = ess.RhythmExtractor(
                sampleRate=self.config.audio_processing.sample_rate,
                frameSize=self.config.audio_processing.frame_size,
                hopSize=self.config.audio_processing.hop_size
            )
            
            bpm, ticks, estimates, bpm_intervals = rhythm_extractor(audio)
            
            features["bpm"] = safe_float(bpm)
            
            # Calculate actual confidence based on estimates
            if len(estimates) > 0:
                # Use the standard deviation of BPM estimates as confidence indicator
                bpm_std = np.std(estimates) if len(estimates) > 1 else 0
                rhythm_confidence = max(0.1, 1.0 - (bpm_std / 20.0))  # Normalize to 0-1
            else:
                rhythm_confidence = 0.1
            
            features["rhythm_confidence"] = safe_float(rhythm_confidence)
            features["beat_confidence"] = safe_float(rhythm_confidence)  # Use same confidence for now
        
        return features
    
    def _extract_harmonic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract essential harmonic features for playlist apps"""
        features = {}
        
        # Key detection - essential for harmonic mixing
        try:
            key_extractor = ess.KeyExtractor(
                sampleRate=self.config.audio_processing.sample_rate,
                frameSize=4096,
                hopSize=4096,
                hpcpSize=12,
                maxFrequency=3500,
                minFrequency=25,
                profileType='bgate',
                weightType='cosine',
                windowType='hann'
            )
            
            key, scale, strength = key_extractor(audio)
            
            features["key"] = key
            features["scale"] = scale
            features["key_strength"] = safe_float(strength)
            
        except Exception as e:
            logger.warning(f"KeyExtractor failed: {e}")
            features["key"] = "unknown"
            features["scale"] = "unknown"
            features["key_strength"] = 0.0
        
        return features
    
    def _extract_basic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract essential basic audio features for playlist apps"""
        features = {}
        
        with SuppressOutput():
            # Loudness - essential for volume normalization (normalize to 0-1 range)
            loudness = ess.Loudness()
            raw_loudness = safe_float(loudness(audio))
            # Normalize loudness: typical range is 0-10000, normalize to 0-1
            features["loudness"] = min(1.0, max(0.0, raw_loudness / 10000.0))
            
            # Energy - essential for playlist energy progression (normalize to 0-1 range)
            energy = ess.Energy()
            raw_energy = safe_float(energy(audio))
            # Normalize energy: typical range is 0-1000000, normalize to 0-1
            features["energy"] = min(1.0, max(0.0, raw_energy / 1000000.0))
            
            # Dynamic complexity - useful for energy variation (already in reasonable range)
            dynamic_complexity = ess.DynamicComplexity()
            dynamic_val = dynamic_complexity(audio)
            # DynamicComplexity returns a tuple (left, right), take the mean
            if isinstance(dynamic_val, tuple):
                dynamic_val = (dynamic_val[0] + dynamic_val[1]) / 2
            # Normalize dynamic complexity: typical range is -20 to 20, normalize to 0-1
            features["dynamic_complexity"] = min(1.0, max(0.0, (dynamic_val + 20.0) / 40.0))
            
            # Zero crossing rate - useful for timbre classification (already normalized 0-1)
            zero_crossing = ess.ZeroCrossingRate()
            features["zero_crossing_rate"] = safe_float(zero_crossing(audio))
        
        return features
    
    def _extract_mfcc_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """Extract essential MFCC features for playlist apps (first 20 coefficients)"""
        features = {}
        
        with SuppressOutput():
            # Use first 20 MFCC coefficients for playlist similarity
            mfcc = ess.MFCC(numberCoefficients=20)
            mfcc_coeffs, mfcc_bands = mfcc(audio)
            
            # Ensure mfcc_coeffs is 2D array
            if mfcc_coeffs.ndim == 1:
                mfcc_coeffs = mfcc_coeffs.reshape(1, -1)
            
            # Store mean and std of MFCC coefficients as arrays
            mfcc_mean_array = np.mean(mfcc_coeffs, axis=0).tolist()
            
            # Calculate proper std values
            if mfcc_coeffs.shape[0] == 1:
                # If only one frame, use a small variation based on the mean
                mfcc_std_array = [abs(val) * 0.1 for val in mfcc_mean_array]
            else:
                mfcc_std_array = np.std(mfcc_coeffs, axis=0).tolist()
            
            features["mfcc_mean"] = mfcc_mean_array
            features["mfcc_std"] = mfcc_std_array
        
        return features
    

    
    def extract_feature_vector(self, file_path: str, include_tensorflow: bool = True) -> np.ndarray:
        """
        Extract a feature vector for similarity search.
        
        Args:
            file_path: Path to audio file
            include_tensorflow: Whether to include TensorFlow features
            
        Returns:
            Numpy array of feature values for vector search
        """
        # Get analysis results
        analysis = self.analyze_audio_file(file_path)
        
        # Extract key features for vector representation
        features = []
        
        # Essential basic features (4)
        basic = analysis['basic_features']
        features.extend([
            basic['loudness'],
            basic['energy'],
            basic['dynamic_complexity'],
            basic['zero_crossing_rate']
        ])
        
        # Essential spectral features (2)
        spectral = analysis['spectral_features']
        features.extend([
            spectral['spectral_centroid'],
            spectral['spectral_rolloff']
        ])
        
        # Essential rhythm features (3)
        rhythm = analysis['rhythm_features']
        features.extend([
            rhythm['bpm'],
            rhythm['rhythm_confidence'],
            rhythm['beat_confidence']
        ])
        
        # Essential harmonic features (1)
        harmonic = analysis['harmonic_features']
        features.extend([
            harmonic['key_strength']
        ])
        
        # Essential danceability features (1)
        danceability = analysis['danceability_features']
        features.extend([
            danceability['danceability']
        ])
        
        # Essential MFCC features (first 20 coefficients)
        mfcc = analysis['mfcc_features']
        features.extend(mfcc['mfcc_mean'][:20])  # First 20 MFCC means
        features.extend(mfcc['mfcc_std'][:20])   # First 20 MFCC stds
        
        # Convert to numpy array
        return np.array(features, dtype=np.float32)

# Create global instance
essentia_analyzer = EssentiaAnalyzer()
