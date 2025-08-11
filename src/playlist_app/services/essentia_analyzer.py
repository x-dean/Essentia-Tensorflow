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
from dataclasses import dataclass
import warnings
from src.playlist_app.core.analysis_config import analysis_config_loader

# Suppress TensorFlow and Essentia logs using proper methods
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress INFO, WARNING, and ERROR logs
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"  # Disable oneDNN optimization messages
os.environ["TF_GPU_ALLOCATOR"] = "cpu"  # Force CPU allocation
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU

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

logger = logging.getLogger(__name__)

@dataclass
class EssentiaConfig:
    """Configuration for Essentia analysis"""
    # Load from config system instead of hardcoded values
    sample_rate: int = None
    channels: int = None
    frame_size: int = None
    hop_size: int = None
    window_type: str = None
    zero_padding: int = None
    chunk_duration: float = None
    min_frequency: float = None
    max_frequency: float = None
    n_mels: int = None
    n_mfcc: int = None
    n_spectral_peaks: int = None
    silence_threshold: float = None
    min_track_length: float = None
    max_track_length: float = None
    overlap_ratio: float = None

    def __post_init__(self):
        # Load configuration from the config system
        config = analysis_config_loader.get_config()
        if self.sample_rate is None:
            self.sample_rate = config.audio_processing.sample_rate
        if self.channels is None:
            self.channels = config.audio_processing.channels
        if self.frame_size is None:
            self.frame_size = config.audio_processing.frame_size
        if self.hop_size is None:
            self.hop_size = config.audio_processing.hop_size
        if self.window_type is None:
            self.window_type = config.audio_processing.window_type
        if self.zero_padding is None:
            self.zero_padding = config.audio_processing.zero_padding
        if self.chunk_duration is None:
            self.chunk_duration = config.track_analysis.chunk_duration
        if self.min_frequency is None:
            self.min_frequency = config.spectral_analysis.min_frequency
        if self.max_frequency is None:
            self.max_frequency = config.spectral_analysis.max_frequency
        if self.n_mels is None:
            self.n_mels = config.spectral_analysis.n_mels
        if self.n_mfcc is None:
            self.n_mfcc = config.spectral_analysis.n_mfcc
        if self.n_spectral_peaks is None:
            self.n_spectral_peaks = config.spectral_analysis.n_spectral_peaks
        if self.silence_threshold is None:
            self.silence_threshold = config.spectral_analysis.silence_threshold
        if self.min_track_length is None:
            self.min_track_length = config.track_analysis.min_track_length
        if self.max_track_length is None:
            self.max_track_length = config.track_analysis.max_track_length
        if self.overlap_ratio is None:
            self.overlap_ratio = config.track_analysis.overlap_ratio

class EssentiaAnalyzer:
    """
    Comprehensive audio analyzer using Essentia and TensorFlow models.
    
    Handles preprocessing, feature extraction, and model inference with proper
    error handling and performance optimizations.
    """
    
    def __init__(self, config: Optional[EssentiaConfig] = None):
        self.config = config or EssentiaConfig()
        self._initialize_algorithms()
        
    def _initialize_algorithms(self):
        """Initialize Essentia algorithms for reuse"""
        try:
            # Core audio processing
            self.loader = es.MonoLoader(
                sampleRate=self.config.sample_rate,
                downmix='mix'
            )
            
            # Spectral analysis
            self.windowing = es.Windowing(
                type=self.config.window_type,
                size=self.config.frame_size,
                zeroPadding=self.config.zero_padding
            )
            
            self.spectrum = es.Spectrum(size=self.config.frame_size)
            
            # MFCC
            self.mfcc = es.MFCC(
                numberCoefficients=self.config.n_mfcc,
                sampleRate=self.config.sample_rate
            )
            
            # Mel spectrogram
            self.mel_bands = es.MelBands(
                numberBands=self.config.n_mels,
                sampleRate=self.config.sample_rate,
                lowFrequencyBound=self.config.min_frequency,
                highFrequencyBound=self.config.max_frequency
            )
            
            # Spectral peaks
            self.spectral_peaks = es.SpectralPeaks(
                maxPeaks=self.config.n_spectral_peaks,
                magnitudeThreshold=0.0,
                minFrequency=self.config.min_frequency,
                maxFrequency=self.config.max_frequency
            )
            
            # Pitch analysis
            self.pitch_yin = es.PitchYin()
            self.pitch_melodia = es.PitchMelodia()
            
            # Rhythm analysis
            self.beat_tracker = es.BeatTrackerDegara()
            self.tempo_tap = es.TempoTap()
            self.rhythm_extractor = es.RhythmExtractor2013()
            
            # Harmonic analysis
            self.chromagram = es.Chromagram()
            self.key_extractor = es.KeyExtractor()
            self.chords_detection = es.ChordsDetection()
            
            # Energy and loudness
            self.rms = es.RMS()
            self.energy = es.Energy()
            self.loudness = es.Loudness()
            
            # Onset detection
            self.onset_detector = es.OnsetDetection()
            
            # Spectral analysis algorithms - using correct algorithm names
            self.spectral_contrast = es.SpectralContrast()
            self.spectral_complexity = es.SpectralComplexity()
            
            # TensorFlow models (optional)
            self._initialize_tensorflow_models()
            
            logger.info("Essentia algorithms initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Essentia algorithms: {e}")
            raise
    
    def _initialize_tensorflow_models(self):
        """Initialize TensorFlow models if available"""
        self.tensorflow_models = {}
        
        try:
            # Try to initialize TensorFlow models
            model_configs = {
                'musicnn': {
                    'class': es.TensorflowInputMusiCNN,
                    'description': 'Music analysis with CNN'
                },
                'tempo_cnn': {
                    'class': es.TensorflowInputTempoCNN,
                    'description': 'Tempo estimation'
                },
                'vggish': {
                    'class': es.TensorflowInputVGGish,
                    'description': 'Audio feature extraction'
                },
                'fsdsinet': {
                    'class': es.TensorflowInputFSDSINet,
                    'description': 'Sound event detection'
                }
            }
            
            for model_name, config in model_configs.items():
                try:
                    model_class = config['class']
                    self.tensorflow_models[model_name] = model_class()
                    logger.info(f"TensorFlow model '{model_name}' initialized: {config['description']}")
                except Exception as e:
                    logger.warning(f"Failed to initialize TensorFlow model '{model_name}': {e}")
                    
        except Exception as e:
            logger.warning(f"TensorFlow models not available: {e}")
    
    def _get_audio_duration(self, file_path: str) -> float:
        """
        Get audio duration using FFmpeg without loading the entire file.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        try:
            import subprocess
            
            # Use FFmpeg to get duration
            cmd = [
                'ffprobe', 
                '-v', 'quiet', 
                '-show_entries', 'format=duration', 
                '-of', 'csv=p=0', 
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            
            return duration
            
        except Exception as e:
            logger.error(f"Failed to get duration for {file_path}: {e}")
            raise
    
    def _load_audio_chunk(self, file_path: str, start_time: float, end_time: float) -> Tuple[np.ndarray, int]:
        """
        Load a specific audio chunk using FFmpeg streaming.
        
        Args:
            file_path: Path to audio file
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            import subprocess
            import tempfile
            import os
            
            # Calculate chunk duration
            chunk_duration = end_time - start_time
            
            # Create temporary file for the chunk
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Use FFmpeg to extract the chunk
                cmd = [
                    'ffmpeg',
                    '-i', str(file_path),
                    '-ss', str(start_time),
                    '-t', str(chunk_duration),
                    '-acodec', 'pcm_s16le',
                    '-ar', str(self.config.sample_rate),
                    '-ac', '1',
                    '-y',  # Overwrite output file
                    temp_path
                ]
                
                # Run FFmpeg command
                result = subprocess.run(cmd, capture_output=True, check=True)
                
                # Load the chunk using Essentia
                loader = es.MonoLoader(filename=temp_path)
                audio = loader()
                
                return audio, self.config.sample_rate
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Failed to load audio chunk {start_time}-{end_time}s from {file_path}: {e}")
            raise
    
    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """
        Load and preprocess audio file using FFmpeg for streaming.
        
        Args:
            file_path: Path to audio file
            
        Returns:
            Tuple of (audio_data, sample_rate)
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            # Use Essentia's MonoLoader with FFmpeg backend for streaming
            # This avoids loading entire file into memory
            with SuppressOutput():
                loader = es.MonoLoader(filename=str(file_path))
                audio = loader()
            
            # Get sample rate from loader
            sr = self.config.sample_rate
            
            # Check audio length
            duration = len(audio) / sr
            if duration < self.config.min_track_length:
                raise ValueError(f"Audio too short: {duration:.2f}s < {self.config.min_track_length}s")
            if duration > self.config.max_track_length:
                logger.warning(f"Audio very long: {duration:.2f}s > {self.config.max_track_length}s")
            
            logger.info(f"Loaded audio: {file_path.name}, duration: {duration:.2f}s, sample_rate: {sr}Hz")
            return audio, sr
            
        except Exception as e:
            logger.error(f"Failed to load audio {file_path}: {e}")
            raise
    
    def compute_mel_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """
        Compute mel spectrogram for TensorFlow models.
        
        Args:
            audio: Audio data
            
        Returns:
            Mel spectrogram as numpy array
        """
        try:
            # Frame the audio
            frames = es.FrameGenerator(
                audio,
                frameSize=self.config.frame_size,
                hopSize=self.config.hop_size
            )
            
            mel_spectrogram = []
            
            for frame in frames:
                # Apply windowing
                windowed_frame = self.windowing(frame)
                
                # Compute spectrum
                spectrum = self.spectrum(windowed_frame)
                
                # Compute mel bands
                mel_bands = self.mel_bands(spectrum)
                
                mel_spectrogram.append(mel_bands)
            
            mel_spectrogram = np.array(mel_spectrogram)
            
            # Apply log scaling
            mel_spectrogram = np.log(mel_spectrogram + 1e-6)
            
            return mel_spectrogram
            
        except Exception as e:
            logger.error(f"Failed to compute mel spectrogram: {e}")
            raise
    
    def extract_basic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract basic audio features using Essentia.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of basic features
        """
        try:
            features = {}
            
            # Duration
            features['duration'] = len(audio) / self.config.sample_rate
            
            # RMS and Energy
            with SuppressOutput():
                features['rms'] = float(self.rms(audio))
                features['energy'] = float(self.energy(audio))
                features['loudness'] = float(self.loudness(audio))
            
            # Basic spectral features using available algorithms
            frames = es.FrameGenerator(
                audio,
                frameSize=self.config.frame_size,
                hopSize=self.config.hop_size
            )
            
            # Spectral analysis using available Essentia algorithms
            spectral_contrasts = []
            spectral_complexities = []
            
            for frame in frames:
                with SuppressOutput():
                    windowed_frame = self.windowing(frame)
                    spectrum = self.spectrum(windowed_frame)
                    
                    # Spectral contrast
                    contrast = self.spectral_contrast(spectrum)
                    spectral_contrasts.append(contrast)
                    
                    # Spectral complexity
                    complexity = self.spectral_complexity(spectrum)
                    spectral_complexities.append(complexity)
            
            # Aggregate spectral features
            features['spectral_contrast_mean'] = float(np.mean(spectral_contrasts))
            features['spectral_contrast_std'] = float(np.std(spectral_contrasts))
            features['spectral_complexity_mean'] = float(np.mean(spectral_complexities))
            features['spectral_complexity_std'] = float(np.std(spectral_complexities))
            
            # MFCC features
            mfcc_values, mfcc_bands = self.mfcc(audio)
            features['mfcc_mean'] = mfcc_values.tolist()
            features['mfcc_bands_mean'] = mfcc_bands.tolist()
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract basic features: {e}")
            # Return standardized out-of-range fallback values
            return {
                'duration': -999.0,
                'rms': -999.0,
                'energy': -999.0,
                'loudness': -999.0,
                'spectral_contrast_mean': -999.0,
                'spectral_contrast_std': -999.0,
                'spectral_complexity_mean': -999.0,
                'spectral_complexity_std': -999.0,
                'mfcc_mean': [-999.0] * 40,
                'mfcc_bands_mean': [-999.0] * 40
            }
    
    def _extract_simple_rhythm_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract simple rhythm features that won't hang.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of simple rhythm features
        """
        try:
            features = {}
            
            # Simple tempo estimation using RMS energy
            try:
                # Calculate RMS energy over time
                frame_size = int(0.1 * self.config.sample_rate)  # 100ms frames
                hop_size = frame_size // 2
                
                rms_values = []
                for i in range(0, len(audio) - frame_size, hop_size):
                    frame = audio[i:i + frame_size]
                    rms = float(self.rms(frame))
                    rms_values.append(rms)
                
                # Simple tempo estimation based on energy peaks
                if len(rms_values) > 10:
                    # Find peaks in RMS energy
                    peaks = []
                    for i in range(1, len(rms_values) - 1):
                        if rms_values[i] > rms_values[i-1] and rms_values[i] > rms_values[i+1]:
                            peaks.append(i)
                    
                    if len(peaks) > 1:
                        # Calculate average time between peaks
                        peak_times = [p * hop_size / self.config.sample_rate for p in peaks]
                        intervals = [peak_times[i+1] - peak_times[i] for i in range(len(peak_times)-1)]
                        avg_interval = sum(intervals) / len(intervals)
                        
                        if avg_interval > 0:
                            estimated_bpm = 60.0 / avg_interval
                            features['estimated_bpm'] = min(max(estimated_bpm, 60), 200)  # Clamp to reasonable range
                        else:
                            features['estimated_bpm'] = -999.0
                    else:
                        features['estimated_bpm'] = -999.0
                else:
                    features['estimated_bpm'] = -999.0
                    
            except Exception as e:
                logger.warning(f"Simple tempo estimation failed: {e}")
                features['estimated_bpm'] = -999.0
            
            # Energy-based rhythm features
            features['energy_variance'] = float(np.var(audio))
            features['energy_mean'] = float(np.mean(np.abs(audio)))
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract simple rhythm features: {e}")
            return {'estimated_bpm': -999.0, 'energy_variance': -999.0, 'energy_mean': -999.0}
    
    def _extract_simple_harmonic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract simple harmonic features that won't hang.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of simple harmonic features
        """
        try:
            features = {}
            
            # Simple spectral analysis for harmonic content
            try:
                # Use a smaller frame size for faster processing
                frame_size = 1024
                hop_size = 512
                
                frames = es.FrameGenerator(
                    audio,
                    frameSize=frame_size,
                    hopSize=hop_size
                )
                
                # Calculate spectral centroid and rolloff for harmonic analysis
                centroids = []
                rolloffs = []
                
                for frame in frames:
                    windowed_frame = self.windowing(frame)
                    spectrum = self.spectrum(windowed_frame)
                    
                    # Simple spectral centroid calculation
                    freqs = np.linspace(0, self.config.sample_rate/2, len(spectrum))
                    centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
                    centroids.append(centroid)
                    
                    # Simple spectral rolloff calculation
                    cumsum = np.cumsum(spectrum)
                    threshold = 0.85 * cumsum[-1]
                    rolloff_idx = np.where(cumsum >= threshold)[0]
                    if len(rolloff_idx) > 0:
                        rolloff = freqs[rolloff_idx[0]]
                    else:
                        rolloff = freqs[-1]
                    rolloffs.append(rolloff)
                
                features['spectral_centroid_mean'] = float(np.mean(centroids))
                features['spectral_centroid_std'] = float(np.std(centroids))
                features['spectral_rolloff_mean'] = float(np.mean(rolloffs))
                features['spectral_rolloff_std'] = float(np.std(rolloffs))
                
            except Exception as e:
                logger.warning(f"Spectral analysis failed: {e}")
                features['spectral_centroid_mean'] = -999.0
                features['spectral_centroid_std'] = -999.0
                features['spectral_rolloff_mean'] = -999.0
                features['spectral_rolloff_std'] = -999.0
            
            # Simple key estimation based on spectral content
            try:
                # Use a small segment for key detection
                segment_length = min(len(audio), int(10 * self.config.sample_rate))  # 10 seconds max
                segment = audio[:segment_length]
                
                key, scale, strength = self.key_extractor(segment)
                features['key'] = key
                features['scale'] = scale
                features['key_strength'] = float(strength)
                
            except Exception as e:
                logger.warning(f"Key detection failed: {e}")
                features['key'] = 'unknown'
                features['scale'] = 'unknown'
                features['key_strength'] = -999.0
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract simple harmonic features: {e}")
            return {
                'spectral_centroid_mean': -999.0,
                'spectral_centroid_std': -999.0,
                'spectral_rolloff_mean': -999.0,
                'spectral_rolloff_std': -999.0,
                'key': 'unknown',
                'scale': 'unknown',
                'key_strength': -999.0
            }
    
    def apply_tensorflow_models(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Apply TensorFlow models to audio.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of TensorFlow model outputs
        """
        try:
            results = {}
            
            if not self.tensorflow_models:
                logger.warning("No TensorFlow models available")
                return results
            
            # Compute mel spectrogram for models
            mel_spectrogram = self.compute_mel_spectrogram(audio)
            
            for model_name, model in self.tensorflow_models.items():
                try:
                    # Reshape input for model
                    if model_name == 'musicnn':
                        # MusiCNN expects (n_mels, time, channels)
                        input_data = mel_spectrogram.T.reshape(1, self.config.n_mels, -1, 1)
                    elif model_name == 'tempo_cnn':
                        # TempoCNN expects similar format
                        input_data = mel_spectrogram.T.reshape(1, self.config.n_mels, -1, 1)
                    elif model_name == 'vggish':
                        # VGGish expects (batch, time, mel_bands)
                        input_data = mel_spectrogram.reshape(1, -1, self.config.n_mels)
                    else:
                        # Default reshaping
                        input_data = mel_spectrogram.reshape(1, -1, self.config.n_mels)
                    
                    # Apply model
                    output = model(input_data)
                    results[model_name] = output.tolist()
                    
                    logger.info(f"Applied TensorFlow model '{model_name}' successfully")
                    
                except Exception as e:
                    logger.warning(f"Failed to apply TensorFlow model '{model_name}': {e}")
                    results[model_name] = [-999.0]  # Out-of-range fallback
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to apply TensorFlow models: {e}")
            return {'error': 'tensorflow_failed', 'models': {}}  # Out-of-range fallback
    
    def analyze_audio_file(self, file_path: str, include_tensorflow: bool = False, category: str = 'normal') -> Dict[str, Any]:
        """
        Analyze an audio file using Essentia with smart segmentation based on track length.
        
        Args:
            file_path: Path to the audio file
            include_tensorflow: Whether to include TensorFlow model analysis (disabled by default for performance)
            category: Track length category ('normal', 'long', 'very_long') - affects analysis strategy
        
        Returns:
            Dictionary containing all analysis results
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting analysis of {file_path} (category: {category})")
            
            # Get file duration first using FFmpeg
            duration = self._get_audio_duration(file_path)
            logger.info(f"Audio duration: {duration:.2f}s")
            
            # Determine analysis strategy based on track length
            if duration <= 300:  # 0-5 minutes: analyze key segments
                analysis_strategy = 'key_segments'
                segments = self._get_key_segments(duration, strategy='short')
                logger.info(f"Using key segments strategy: {len(segments)} segments")
                
            elif duration <= 600:  # 5-10 minutes: analyze beginning, middle, end
                analysis_strategy = 'three_point'
                segments = self._get_key_segments(duration, strategy='medium')
                logger.info(f"Using three-point strategy: {len(segments)} segments")
                
            else:  # 10+ minutes: analyze strategic points
                analysis_strategy = 'strategic_points'
                segments = self._get_key_segments(duration, strategy='long')
                logger.info(f"Using strategic points strategy: {len(segments)} segments")
            
            # Analyze selected segments using FFmpeg streaming
            all_results = []
            
            for i, (start_time_seg, end_time_seg) in enumerate(segments):
                logger.info(f"Processing segment {i+1}/{len(segments)} ({start_time_seg:.1f}s - {end_time_seg:.1f}s)")
                
                try:
                    # Load only this segment using FFmpeg streaming
                    segment_audio, sample_rate = self._load_audio_chunk(file_path, start_time_seg, end_time_seg)
                    
                    # Basic features for this segment
                    basic_features = self.extract_basic_features(segment_audio)
                    
                    # Simple rhythm features (avoid complex algorithms that can hang)
                    rhythm_features = self._extract_simple_rhythm_features(segment_audio)
                    
                    # Simple harmonic features
                    harmonic_features = self._extract_simple_harmonic_features(segment_audio)
                    
                    segment_result = {
                        'segment_index': i,
                        'start_time': start_time_seg,
                        'end_time': end_time_seg,
                        'segment_duration': end_time_seg - start_time_seg,
                        'basic_features': basic_features,
                        'rhythm_features': rhythm_features,
                        'harmonic_features': harmonic_features
                    }
                    
                    all_results.append(segment_result)
                    logger.info(f"Segment {i+1} completed successfully")
                    
                except Exception as e:
                    logger.warning(f"Segment {i+1} failed: {e}")
                    # Add empty result for failed segment
                    all_results.append({
                        'segment_index': i,
                        'start_time': start_time_seg,
                        'end_time': end_time_seg,
                        'error': str(e)
                    })
            
            # Aggregate results across segments
            results = self._aggregate_segment_results(all_results)
            
            # Add metadata
            results['metadata'] = {
                'file_path': file_path,
                'duration': duration,
                'sample_rate': sample_rate,
                'category': category,
                'analysis_strategy': analysis_strategy,
                'num_segments': len(segments),
                'segments_analyzed': len([r for r in all_results if 'error' not in r]),
                'analysis_duration': time.time() - start_time
            }
            
            logger.info(f"Analysis completed in {time.time() - start_time:.2f}s using {analysis_strategy}")
            return results
            
        except Exception as e:
            logger.error(f"Analysis failed for {file_path}: {e}")
            raise
    
    def _analyze_full_track(self, audio: np.ndarray, sample_rate: int, include_tensorflow: bool) -> Dict[str, Any]:
        """Analyze the full track (for normal length tracks)"""
        results = {}
        
        # Extract all features from the full track
        results['basic_features'] = self.extract_basic_features(audio)
        results['rhythm_features'] = self.extract_rhythm_features(audio)
        results['harmonic_features'] = self.extract_harmonic_features(audio)
        
        if include_tensorflow:
            results['tensorflow_features'] = self.apply_tensorflow_models(audio)
        
        return results
    
    def _analyze_chunked(self, audio: np.ndarray, sample_rate: int, include_tensorflow: bool) -> Dict[str, Any]:
        """Analyze track in chunks (for long tracks)"""
        chunk_duration = self.config.chunk_duration
        overlap_ratio = self.config.overlap_ratio
        
        # Calculate chunk parameters
        chunk_samples = int(chunk_duration * sample_rate)
        hop_samples = int(chunk_samples * (1 - overlap_ratio))
        
        # Extract chunks
        chunks = []
        chunk_times = []
        
        for start_sample in range(0, len(audio) - chunk_samples, hop_samples):
            end_sample = start_sample + chunk_samples
            chunk = audio[start_sample:end_sample]
            chunks.append(chunk)
            chunk_times.append({
                'start': start_sample / sample_rate,
                'end': end_sample / sample_rate,
                'duration': chunk_duration
            })
        
        logger.info(f"Analyzing {len(chunks)} chunks for long track")
        
        # Analyze each chunk
        chunk_results = []
        for i, (chunk, chunk_info) in enumerate(zip(chunks, chunk_times)):
            try:
                chunk_result = self.analyze_audio_chunk(chunk, chunk_info)
                chunk_results.append(chunk_result)
                logger.debug(f"Chunk {i+1}/{len(chunks)} analyzed successfully")
            except Exception as e:
                logger.warning(f"Chunk {i+1} analysis failed: {e}")
                chunk_results.append({
                    'chunk_info': chunk_info,
                    'error': str(e)
                })
        
        # Aggregate results across chunks
        results = self._aggregate_chunk_results(chunk_results)
        
        # Add chunk metadata
        results['chunk_analysis'] = {
            'total_chunks': len(chunks),
            'chunk_duration': chunk_duration,
            'overlap_ratio': overlap_ratio,
            'chunk_results': chunk_results
        }
        
        return results
    
    def _analyze_segmented(self, audio: np.ndarray, sample_rate: int, include_tensorflow: bool) -> Dict[str, Any]:
        """Analyze selected segments (for very long tracks)"""
        # For very long tracks, analyze key segments:
        # 1. Beginning (first 2 minutes)
        # 2. Middle (2 minutes from center)
        # 3. End (last 2 minutes)
        
        segment_duration = 120.0  # 2 minutes
        segment_samples = int(segment_duration * sample_rate)
        
        segments = []
        segment_times = []
        
        # Beginning segment
        if len(audio) > segment_samples:
            beginning = audio[:segment_samples]
            segments.append(beginning)
            segment_times.append({
                'type': 'beginning',
                'start': 0,
                'end': segment_duration,
                'duration': segment_duration
            })
        
        # Middle segment
        middle_start = len(audio) // 2 - segment_samples // 2
        if middle_start >= 0 and middle_start + segment_samples <= len(audio):
            middle = audio[middle_start:middle_start + segment_samples]
            segments.append(middle)
            segment_times.append({
                'type': 'middle',
                'start': middle_start / sample_rate,
                'end': (middle_start + segment_samples) / sample_rate,
                'duration': segment_duration
            })
        
        # End segment
        if len(audio) > segment_samples:
            end = audio[-segment_samples:]
            segments.append(end)
            segment_times.append({
                'type': 'end',
                'start': (len(audio) - segment_samples) / sample_rate,
                'end': len(audio) / sample_rate,
                'duration': segment_duration
            })
        
        logger.info(f"Analyzing {len(segments)} key segments for very long track")
        
        # Analyze each segment
        segment_results = []
        for i, (segment, segment_info) in enumerate(zip(segments, segment_times)):
            try:
                segment_result = self.analyze_audio_chunk(segment, segment_info)
                segment_results.append(segment_result)
                logger.debug(f"Segment {segment_info['type']} analyzed successfully")
            except Exception as e:
                logger.warning(f"Segment {segment_info['type']} analysis failed: {e}")
                segment_results.append({
                    'segment_info': segment_info,
                    'error': str(e)
                })
        
        # Aggregate results across segments
        results = self._aggregate_chunk_results(segment_results)
        
        # Add segment metadata
        results['segment_analysis'] = {
            'total_segments': len(segments),
            'segment_duration': segment_duration,
            'segment_results': segment_results
        }
        
        return results
    
    def _get_key_segments(self, duration: float, strategy: str = 'short') -> List[Tuple[float, float]]:
        """
        Get key segments to analyze based on track length strategy.
        
        Args:
            duration: Track duration in seconds
            strategy: Analysis strategy ('short', 'medium', 'long')
            
        Returns:
            List of (start_time, end_time) tuples for segments to analyze
        """
        segments = []
        
        if strategy == 'short':  # 0-5 minutes: analyze key parts
            # For short tracks, analyze beginning, middle, and end
            if duration <= 60:  # Very short: analyze first 30s
                segments = [(0, min(30, duration))]
            elif duration <= 180:  # Short: analyze beginning and end
                segments = [
                    (0, 30),  # First 30s
                    (duration - 30, duration)  # Last 30s
                ]
            else:  # Medium short: analyze beginning, middle, end
                segments = [
                    (0, 30),  # First 30s
                    (duration / 2 - 15, duration / 2 + 15),  # Middle 30s
                    (duration - 30, duration)  # Last 30s
                ]
                
        elif strategy == 'medium':  # 5-10 minutes: analyze strategic points
            # Analyze beginning, 1/4, 1/2, 3/4, and end
            segments = [
                (0, 30),  # First 30s
                (duration * 0.25 - 15, duration * 0.25 + 15),  # 1/4 point
                (duration * 0.5 - 15, duration * 0.5 + 15),  # Middle
                (duration * 0.75 - 15, duration * 0.75 + 15),  # 3/4 point
                (duration - 30, duration)  # Last 30s
            ]
            
        elif strategy == 'long':  # 10+ minutes: analyze key moments
            # Analyze beginning, key points, and end
            segments = [
                (0, 30),  # First 30s
                (duration * 0.2 - 15, duration * 0.2 + 15),  # 20% point
                (duration * 0.4 - 15, duration * 0.4 + 15),  # 40% point
                (duration * 0.6 - 15, duration * 0.6 + 15),  # 60% point
                (duration * 0.8 - 15, duration * 0.8 + 15),  # 80% point
                (duration - 30, duration)  # Last 30s
            ]
        
        # Ensure segments are within track bounds and have minimum duration
        valid_segments = []
        for start, end in segments:
            start = max(0, start)
            end = min(duration, end)
            if end - start >= 10:  # Minimum 10s segment
                valid_segments.append((start, end))
        
        return valid_segments
    
    def _aggregate_segment_results(self, segment_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from multiple segments into a single result.
        
        Args:
            segment_results: List of segment analysis results
            
        Returns:
            Aggregated analysis results
        """
        if not segment_results:
            return {}
        
        # Separate successful and failed segments
        successful_segments = [r for r in segment_results if 'error' not in r]
        failed_segments = [r for r in segment_results if 'error' in r]
        
        if not successful_segments:
            logger.warning("No successful segments to aggregate")
            return {}
        
        # Aggregate basic features
        basic_features_list = [r['basic_features'] for r in successful_segments]
        aggregated_basic = self._average_features(basic_features_list)
        
        # Aggregate rhythm features
        rhythm_features_list = [r['rhythm_features'] for r in successful_segments]
        aggregated_rhythm = self._average_rhythm_features(rhythm_features_list)
        
        # Aggregate harmonic features
        harmonic_features_list = [r['harmonic_features'] for r in successful_segments]
        aggregated_harmonic = self._aggregate_harmonic_features(harmonic_features_list)
        
        # Combine results
        results = {
            'basic_features': aggregated_basic,
            'rhythm_features': aggregated_rhythm,
            'harmonic_features': aggregated_harmonic,
            'tensorflow_features': {},  # Disabled for performance
            'segment_analysis': {
                'total_segments': len(segment_results),
                'successful_segments': len(successful_segments),
                'failed_segments': len(failed_segments),
                'segments_analyzed': [f"{r['start_time']:.1f}s-{r['end_time']:.1f}s" for r in successful_segments],
                'segment_results': segment_results
            }
        }
        
        return results
    
    def _aggregate_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple chunks/segments"""
        if not chunk_results:
            return {}
        
        # Initialize aggregated results
        aggregated = {
            'basic_features': {},
            'rhythm_features': {},
            'harmonic_features': {},
            'tensorflow_features': {}
        }
        
        # Collect all successful results
        successful_results = [r for r in chunk_results if 'error' not in r]
        
        if not successful_results:
            logger.warning("No successful chunk results to aggregate")
            return aggregated
        
        # Aggregate basic features (average numerical values)
        if successful_results and 'basic_features' in successful_results[0]:
            basic_features = [r['basic_features'] for r in successful_results]
            aggregated['basic_features'] = self._average_features(basic_features)
        
        # Aggregate rhythm features (weighted average for tempo, etc.)
        if successful_results and 'rhythm_features' in successful_results[0]:
            rhythm_features = [r['rhythm_features'] for r in successful_results]
            aggregated['rhythm_features'] = self._average_rhythm_features(rhythm_features)
        
        # Aggregate harmonic features (most common key, average chord complexity)
        if successful_results and 'harmonic_features' in successful_results[0]:
            harmonic_features = [r['harmonic_features'] for r in successful_results]
            aggregated['harmonic_features'] = self._aggregate_harmonic_features(harmonic_features)
        
        # Aggregate TensorFlow features (average embeddings)
        if successful_results and 'tensorflow_features' in successful_results[0]:
            tensorflow_features = [r['tensorflow_features'] for r in successful_results]
            aggregated['tensorflow_features'] = self._average_tensorflow_features(tensorflow_features)
        
        return aggregated
    
    def _average_features(self, features_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average numerical features across chunks"""
        if not features_list:
            return {}
        
        averaged = {}
        
        # Get all keys from all feature dictionaries
        all_keys = set()
        for features in features_list:
            all_keys.update(features.keys())
        
        for key in all_keys:
            values = []
            for features in features_list:
                if key in features and isinstance(features[key], (int, float)):
                    values.append(features[key])
            
            if values:
                averaged[key] = sum(values) / len(values)
        
        return averaged
    
    def _average_rhythm_features(self, rhythm_features_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average rhythm features with special handling for tempo"""
        if not rhythm_features_list:
            return {}
        
        averaged = {}
        
        # Average tempo (weighted by confidence if available)
        tempos = []
        for features in rhythm_features_list:
            if 'tempo' in features and features['tempo'] > 0:
                tempos.append(features['tempo'])
        
        if tempos:
            averaged['tempo'] = sum(tempos) / len(tempos)
        
        # Average other numerical features
        other_features = self._average_features(rhythm_features_list)
        averaged.update(other_features)
        
        return averaged
    
    def _aggregate_harmonic_features(self, harmonic_features_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate harmonic features (most common key, average complexity)"""
        if not harmonic_features_list:
            return {}
        
        aggregated = {}
        
        # Find most common key
        keys = []
        for features in harmonic_features_list:
            if 'key' in features and features['key']:
                keys.append(features['key'])
        
        if keys:
            # Simple approach: use the first key (could be improved with voting)
            aggregated['key'] = keys[0]
            aggregated['scale'] = next((f.get('scale', '') for f in harmonic_features_list if f.get('key') == keys[0]), '')
        
        # Average numerical features
        other_features = self._average_features(harmonic_features_list)
        aggregated.update(other_features)
        
        return aggregated
    
    def _average_tensorflow_features(self, tensorflow_features_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Average TensorFlow model outputs"""
        if not tensorflow_features_list:
            return {}
        
        averaged = {}
        
        # Average embeddings and probabilities
        for features in tensorflow_features_list:
            for model_name, model_output in features.items():
                if model_name not in averaged:
                    averaged[model_name] = {}
                
                for output_name, output_value in model_output.items():
                    if isinstance(output_value, (list, np.ndarray)):
                        # Average arrays/embeddings
                        if output_name not in averaged[model_name]:
                            averaged[model_name][output_name] = []
                        
                        averaged[model_name][output_name].append(output_value)
        
        # Calculate averages for arrays
        for model_name in averaged:
            for output_name in averaged[model_name]:
                if isinstance(averaged[model_name][output_name], list):
                    arrays = averaged[model_name][output_name]
                    if arrays:
                        averaged[model_name][output_name] = np.mean(arrays, axis=0)
        
        return averaged
    
    def analyze_audio_chunk(self, audio: np.ndarray, chunk_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a chunk of audio (for long tracks).
        
        Args:
            audio: Audio chunk data
            chunk_info: Information about the chunk
            
        Returns:
            Analysis results for the chunk
        """
        try:
            results = {
                'chunk_info': chunk_info,
                'duration': len(audio) / self.config.sample_rate
            }
            
            # Basic features for chunk
            basic_features = self.extract_basic_features(audio)
            results['basic_features'] = basic_features
            
            # Rhythm features for chunk
            rhythm_features = self.extract_rhythm_features(audio)
            results['rhythm_features'] = rhythm_features
            
            # Harmonic features for chunk
            harmonic_features = self.extract_harmonic_features(audio)
            results['harmonic_features'] = harmonic_features
            
            return results
            
        except Exception as e:
            logger.error(f"Chunk analysis failed: {e}")
            raise
    
    def get_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a summary of analysis results.
        
        Args:
            results: Complete analysis results
            
        Returns:
            Summary of key features
        """
        try:
            summary = {
                'file_path': results.get('file_path'),
                'duration': results.get('duration'),
                'sample_rate': results.get('sample_rate'),
                'analysis_duration': results.get('analysis_duration'),
                'key_features': {}
            }
            
            # Basic features summary
            basic = results.get('basic_features', {})
            if basic:
                summary['key_features']['rms'] = basic.get('rms')
                summary['key_features']['energy'] = basic.get('energy')
                summary['key_features']['loudness'] = basic.get('loudness')
                summary['key_features']['spectral_contrast_mean'] = basic.get('spectral_contrast_mean')
                summary['key_features']['spectral_complexity_mean'] = basic.get('spectral_complexity_mean')
            
            # Rhythm features summary
            rhythm = results.get('rhythm_features', {})
            if rhythm:
                summary['key_features']['tempo'] = rhythm.get('tempo')
                summary['key_features']['rhythm_bpm'] = rhythm.get('rhythm_bpm')
                summary['key_features']['beat_confidence'] = rhythm.get('beat_confidence')
            
            # Harmonic features summary
            harmonic = results.get('harmonic_features', {})
            if harmonic:
                summary['key_features']['key'] = harmonic.get('key')
                summary['key_features']['scale'] = harmonic.get('scale')
                summary['key_features']['key_strength'] = harmonic.get('key_strength')
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to create analysis summary: {e}")
            raise

# Global instance
essentia_analyzer = EssentiaAnalyzer()
