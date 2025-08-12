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

# FAISS for efficient vector similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Apply TensorFlow optimizations based on configuration
def apply_tensorflow_optimizations():
    """Apply TensorFlow optimizations from configuration"""
    try:
        from ..core.analysis_config import analysis_config_loader
        config = analysis_config_loader.get_config()
        tf_config = config.get("performance", {}).get("tensorflow_optimizations", {})
        
        # Apply optimizations
        if not tf_config.get("enable_onednn", False):
            os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
        
        os.environ["TF_GPU_ALLOCATOR"] = tf_config.get("gpu_allocator", "cpu")
        os.environ["CUDA_VISIBLE_DEVICES"] = tf_config.get("cuda_visible_devices", "-1")
        
        # Memory growth
        if tf_config.get("memory_growth", True):
            os.environ["TF_FORCE_GPU_ALLOW_GROWTH"] = "true"
        
        # Mixed precision
        if tf_config.get("mixed_precision", False):
            os.environ["TF_ENABLE_AUTO_MIXED_PRECISION"] = "1"
        
    except Exception as e:
        # Fallback to default settings
        os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
        os.environ["TF_GPU_ALLOCATOR"] = "cpu"
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Apply optimizations
apply_tensorflow_optimizations()

# Suppress TensorFlow logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress INFO, WARNING, and ERROR logs

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

# Log FAISS availability
if FAISS_AVAILABLE:
    logger.info("FAISS is available for vector indexing")
else:
    logger.warning("FAISS not available. Install with: pip install faiss-cpu or faiss-gpu")

def safe_float(value: Any) -> float:
    """
    Convert value to a JSON-safe float, handling inf, -inf, and NaN values.
    
    Args:
        value: The value to convert
        
    Returns:
        JSON-safe float value
    """
    # Get fallback value from configuration
    try:
        from ..core.analysis_config import analysis_config_loader
        config = analysis_config_loader.get_config()
        fallback_value = config.get("quality", {}).get("fallback_values", {}).get("default_float", -999.0)
    except Exception:
        fallback_value = -999.0
    
    if value is None:
        return fallback_value
    
    try:
        float_val = float(value)
        if np.isnan(float_val) or np.isinf(float_val):
            return fallback_value
        return float_val
    except (ValueError, TypeError):
        return fallback_value

def safe_json_serialize(obj: Any) -> Any:
    """
    Recursively convert numpy arrays and handle non-JSON-serializable values.
    
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
        return {key: safe_json_serialize(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_serialize(item) for item in obj]
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        if isinstance(obj, float):
            return safe_float(obj)
        return obj
    else:
        return str(obj)

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
        # Load configuration from the config system with error handling
        try:
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
        except Exception as e:
            logger.warning(f"Failed to load config, using defaults: {e}")
            # Set sensible defaults if config loading fails
            self.sample_rate = self.sample_rate or 44100
            self.channels = self.channels or 1
            self.frame_size = self.frame_size or 2048
            self.hop_size = self.hop_size or 1024
            self.window_type = self.window_type or "hann"
            self.zero_padding = self.zero_padding or 0
            self.chunk_duration = self.chunk_duration or 30.0
            self.min_frequency = self.min_frequency or 20.0
            self.max_frequency = self.max_frequency or 8000.0
            self.n_mels = self.n_mels or 96
            self.n_mfcc = self.n_mfcc or 40
            self.n_spectral_peaks = self.n_spectral_peaks or 100
            self.silence_threshold = self.silence_threshold or -60.0
            self.min_track_length = self.min_track_length or 1.0
            self.max_track_length = self.max_track_length or 600.0
            self.overlap_ratio = self.overlap_ratio or 0.5

class EssentiaAnalyzer:
    """
    Comprehensive audio analyzer using Essentia and TensorFlow models.
    
    Handles preprocessing, feature extraction, and model inference with proper
    error handling and performance optimizations.
    """
    
    def __init__(self, config: Optional[EssentiaConfig] = None):
        self.config = config or EssentiaConfig()
        self.track_library: List[Tuple[str, np.ndarray]] = []  # (track_path, vector)
        self.track_paths: List[str] = []  # List of track paths for indexing
        self.faiss_index = None  # FAISS index for similarity search
        self.vector_dimension = None  # Dimension of feature vectors
        self._initialize_algorithms()
        self._initialize_faiss_index()
        
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
        self.musicnn_models = {}
        
        # Initialize MusiCNN models for genre and mood
        self._load_musicnn_models()
        
        try:
            # Try to initialize other TensorFlow models
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
    
    def _load_musicnn_models(self):
        """Load MusiCNN models from local filesystem"""
        try:
            # Define model paths - try multiple possible locations
            possible_model_paths = [
                'models/msd-musicnn-1.pb',
                '/app/models/msd-musicnn-1.pb',
                'src/playlist_app/models/msd-musicnn-1.pb'
            ]
            possible_json_paths = [
                'models/msd-musicnn-1.json',
                '/app/models/msd-musicnn-1.json',
                'src/playlist_app/models/msd-musicnn-1.json'
            ]
            
            # Find the first existing model path
            model_path = None
            for path in possible_model_paths:
                if os.path.exists(path):
                    model_path = path
                    break
            
            # Find the first existing JSON path
            json_path = None
            for path in possible_json_paths:
                if os.path.exists(path):
                    json_path = path
                    break
            
            # Check if model exists
            if os.path.exists(model_path):
                try:
                    # Load the model
                    self.musicnn_models['musicnn'] = es.TensorflowPredictMusiCNN(
                        graphFilename=model_path,
                        output="model/Sigmoid"
                    )
                    
                    # Load labels from JSON if available
                    if os.path.exists(json_path):
                        import json
                        with open(json_path, 'r') as f:
                            model_info = json.load(f)
                        
                        # Extract labels from JSON
                        if 'classes' in model_info:
                            self.musicnn_models['labels'] = model_info['classes']
                            logger.info(f"MusiCNN model loaded successfully with {len(model_info['classes'])} labels")
                        else:
                            logger.warning("No 'classes' found in model JSON")
                    else:
                        logger.info("Model JSON file not found, using model without labels")
                    
                    logger.info(f"MusiCNN model loaded successfully from {model_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to load MusiCNN model: {e}")
            else:
                logger.info(f"MusiCNN model file not found at {model_path}")
            
            if not self.musicnn_models:
                logger.info("No MusiCNN models found, using basic analysis only")
                
        except Exception as e:
            logger.warning(f"Failed to load MusiCNN models: {e}")
    
    def _initialize_faiss_index(self):
        """Initialize FAISS index for efficient similarity search"""
        if not FAISS_AVAILABLE:
            logger.warning("FAISS not available, using basic similarity search")
            return
        
        try:
            # We'll initialize the index when we add the first vector
            # For now, just set up the configuration
            self.faiss_index = None
            self.vector_dimension = None
            logger.info("FAISS index ready for initialization")
        except Exception as e:
            logger.warning(f"Failed to initialize FAISS index: {e}")
    
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
                loader = es.MonoLoader(
                    filename=str(file_path),
                    sampleRate=self.config.sample_rate
                )
                audio = loader()
            
            # Get sample rate from config
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
            
            # Normalize audio to prevent extreme values
            if len(audio) > 0:
                audio_normalized = audio / (np.max(np.abs(audio)) + 1e-8)
            else:
                audio_normalized = audio
            
            # RMS, Energy, and Loudness - calculate frame by frame and average
            frames = es.FrameGenerator(
                audio_normalized,
                frameSize=self.config.frame_size,
                hopSize=self.config.hop_size
            )
            
            rms_values = []
            energy_values = []
            loudness_values = []
            
            for frame in frames:
                with SuppressOutput():
                    # Ensure frame is not empty
                    if len(frame) > 0:
                        rms_values.append(float(self.rms(frame)))
                        energy_values.append(float(self.energy(frame)))
                        loudness_values.append(float(self.loudness(frame)))
            
            # Calculate averages with proper bounds checking
            if rms_values:
                features['rms'] = safe_float(np.mean(rms_values))
            else:
                features['rms'] = 0.0
                
            if energy_values:
                features['energy'] = safe_float(np.mean(energy_values))
            else:
                features['energy'] = 0.0
                
            if loudness_values:
                features['loudness'] = safe_float(np.mean(loudness_values))
            else:
                features['loudness'] = -60.0  # Default quiet level
            
            # Basic spectral features using available algorithms
            # Use normalized audio for spectral analysis
            frames_spectral = es.FrameGenerator(
                audio_normalized,
                frameSize=self.config.frame_size,
                hopSize=self.config.hop_size
            )
            
            # Spectral analysis using available Essentia algorithms
            spectral_contrasts = []
            spectral_complexities = []
            
            for frame in frames_spectral:
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
            features['spectral_contrast_mean'] = safe_float(np.mean(spectral_contrasts))
            features['spectral_contrast_std'] = safe_float(np.std(spectral_contrasts))
            features['spectral_complexity_mean'] = safe_float(np.mean(spectral_complexities))
            features['spectral_complexity_std'] = safe_float(np.std(spectral_complexities))
            
            # MFCC features
            mfcc_values, mfcc_bands = self.mfcc(audio)
            features['mfcc_mean'] = safe_json_serialize(mfcc_values)
            features['mfcc_bands_mean'] = safe_json_serialize(mfcc_bands)
            
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
    
    def _extract_essential_basic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract only essential basic features for playlist generation.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of essential basic features
        """
        try:
            features = {}
            
            # Duration
            features['duration'] = len(audio) / self.config.sample_rate
            
            # Simple energy and loudness calculation
            features['energy'] = safe_float(np.mean(audio ** 2))
            features['loudness'] = safe_float(20 * np.log10(np.mean(np.abs(audio)) + 1e-8))
            
            # Simple RMS
            features['rms'] = safe_float(np.sqrt(np.mean(audio ** 2)))
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract essential basic features: {e}")
            return {
                'duration': -999.0,
                'energy': -999.0,
                'loudness': -999.0,
                'rms': -999.0
            }
    
    def _extract_essential_rhythm_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract only essential rhythm features (BPM) for playlist generation.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of essential rhythm features
        """
        try:
            features = {}
            
            # Normalize audio for better analysis
            if len(audio) > 0:
                audio_max = np.max(np.abs(audio))
                if audio_max > 0:
                    audio = audio / audio_max
            
            # Use multiple tempo estimation methods for different fields
            tempo_estimates = []
            rhythm_bpm_values = []
            
            # Method 1: RhythmExtractor2013 (for rhythm_bpm)
            try:
                with SuppressOutput():
                    rhythm_extractor = es.RhythmExtractor2013(
                        maxTempo=208,
                        minTempo=40,
                        method='multifeature'
                    )
                    
                    rhythm_bpm, rhythm_ticks, rhythm_confidence, rhythm_estimates, rhythm_bpm_intervals = rhythm_extractor(audio)
                    
                    if rhythm_bpm > 0 and rhythm_confidence > 0.1:
                        rhythm_bpm_values.append((rhythm_bpm, rhythm_confidence))
                        tempo_estimates.append((rhythm_bpm, rhythm_confidence))
                        logger.info(f"BPM extracted: {rhythm_bpm:.1f} (confidence: {rhythm_confidence:.3f})")
                    else:
                        logger.warning(f"BPM extraction failed: BPM={rhythm_bpm}, confidence={rhythm_confidence}")
            except Exception as e:
                logger.warning(f"RhythmExtractor2013 failed: {e}")
            
            # Method 2: TempoTap (for general tempo)
            try:
                with SuppressOutput():
                    tempo_tap_bpm, tempo_tap_confidence = self.tempo_tap(audio)
                    
                    if isinstance(tempo_tap_bpm, (int, float)) and tempo_tap_bpm > 0 and tempo_tap_confidence > 0.1:
                        tempo_estimates.append((tempo_tap_bpm, tempo_tap_confidence))
                        logger.debug(f"TempoTap: {tempo_tap_bpm:.1f} BPM (confidence: {tempo_tap_confidence:.3f})")
            except Exception as e:
                logger.debug(f"TempoTap failed: {e}")
            
            # Method 3: BeatTracker + BPM calculation (for bpm)
            try:
                with SuppressOutput():
                    beat_result = self.beat_tracker(audio)
                    
                    if isinstance(beat_result, tuple) and len(beat_result) >= 2:
                        beats = beat_result[0]
                        confidence = beat_result[1] if len(beat_result) > 1 else 0.0
                        
                        if isinstance(beats, np.ndarray) and beats.size > 2:
                            # Calculate BPM from beat intervals
                            beat_intervals = np.diff(beats)
                            if len(beat_intervals) > 0:
                                avg_interval = np.mean(beat_intervals)
                                if avg_interval > 0:
                                    beat_bpm = 60.0 / avg_interval
                                    if 40 <= beat_bpm <= 208:  # Reasonable BPM range
                                        tempo_estimates.append((beat_bpm, confidence))
                                        logger.debug(f"BeatTracker: {beat_bpm:.1f} BPM (confidence: {confidence:.3f})")
            except Exception as e:
                logger.debug(f"BeatTracker BPM calculation failed: {e}")
            
            # Use the best tempo estimate (highest confidence)
            if tempo_estimates:
                # Sort by confidence and use the best
                tempo_estimates.sort(key=lambda x: x[1], reverse=True)
                best_bpm, best_confidence = tempo_estimates[0]
                
                features['tempo'] = safe_float(best_bpm)
                features['tempo_confidence'] = safe_float(best_confidence)
                features['tempo_methods_used'] = len(tempo_estimates)
                
                logger.info(f"Tempo extracted: {best_bpm:.1f} BPM (confidence: {best_confidence:.3f}, methods: {len(tempo_estimates)})")
            else:
                features['tempo'] = -999.0
                features['tempo_confidence'] = -999.0
                features['tempo_methods_used'] = 0
                logger.warning("All tempo estimation methods failed")
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract essential rhythm features: {e}")
            return {'tempo': -999.0, 'tempo_confidence': -999.0, 'tempo_methods_used': 0}
    
    def _extract_essential_harmonic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract only essential harmonic features (key) for playlist generation.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of essential harmonic features
        """
        try:
            features = {}
            
            # Use only key detection (most useful for playlist generation)
            try:
                with SuppressOutput():
                    key, scale, strength = self.key_extractor(audio)
                    features['key'] = key
                    features['scale'] = scale
                    features['key_strength'] = safe_float(strength)
                    logger.info(f"Key extracted: {key} {scale} (strength: {strength:.3f})")
                    
            except Exception as e:
                logger.warning(f"Key detection failed: {e}")
                features['key'] = 'unknown'
                features['scale'] = 'unknown'
                features['key_strength'] = -999.0
            
            # Add chroma analysis for dominant chroma detection
            try:
                with SuppressOutput():
                    # For short audio, use spectral peaks to estimate dominant frequency
                    # and map to chroma
                    frequencies, magnitudes = self.spectral_peaks(audio)
                    if len(frequencies) > 0:
                        # Find the strongest frequency
                        strongest_idx = np.argmax(magnitudes)
                        dominant_freq = frequencies[strongest_idx]
                        
                        # Map frequency to chroma
                        chroma_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                        if dominant_freq > 0:
                            # Convert frequency to note number (A4 = 440Hz = note 69)
                            note_num = 12 * np.log2(dominant_freq / 440.0) + 69
                            chroma_idx = int(round(note_num)) % 12
                            features['dominant_chroma'] = chroma_names[chroma_idx]
                            features['dominant_chroma_strength'] = safe_float(magnitudes[strongest_idx])
                            
                            logger.debug(f"Spectral analysis: dominant chroma {features['dominant_chroma']} from {dominant_freq:.1f}Hz")
            except Exception as e:
                logger.warning(f"Chroma analysis failed: {e}")
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract essential harmonic features: {e}")
            return {
                'key': 'unknown',
                'scale': 'unknown',
                'key_strength': -999.0
            }
    
    def _extract_simple_rhythm_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract rhythm features using Essentia's tempo estimation algorithms.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of rhythm features
        """
        try:
            features = {}
            
            # Debug audio properties
            logger.debug(f"Audio shape: {audio.shape}, dtype: {audio.dtype}")
            logger.debug(f"Audio range: {np.min(audio):.6f} to {np.max(audio):.6f}")
            logger.debug(f"Audio mean: {np.mean(audio):.6f}, std: {np.std(audio):.6f}")
            logger.debug(f"Audio length: {len(audio)} samples, duration: {len(audio)/self.config.sample_rate:.2f}s")
            
            # Normalize audio for better analysis
            if len(audio) > 0:
                audio_max = np.max(np.abs(audio))
                if audio_max > 0:
                    audio = audio / audio_max
                    logger.debug(f"Audio normalized, new range: {np.min(audio):.6f} to {np.max(audio):.6f}")
            
            # Use multiple tempo estimation methods for different fields
            tempo_estimates = []
            rhythm_bpm_values = []
            
            # Method 1: RhythmExtractor2013 (for rhythm_bpm)
            try:
                with SuppressOutput():
                    rhythm_extractor = es.RhythmExtractor2013(
                        maxTempo=208,
                        minTempo=40,
                        method='multifeature'
                    )
                    
                    rhythm_bpm, rhythm_ticks, rhythm_confidence, rhythm_estimates, rhythm_bpm_intervals = rhythm_extractor(audio)
                    
                    if rhythm_bpm > 0 and rhythm_confidence > 0.1:
                        rhythm_bpm_values.append((rhythm_bpm, rhythm_confidence))
                        tempo_estimates.append((rhythm_bpm, rhythm_confidence))
                        
                        # Store rhythm-specific data
                        features['rhythm_ticks'] = safe_json_serialize(rhythm_ticks)
                        features['rhythm_estimates'] = safe_json_serialize(rhythm_estimates)
                        features['rhythm_bpm_intervals'] = safe_json_serialize(rhythm_bpm_intervals)
                        
                        logger.debug(f"RhythmExtractor2013: {rhythm_bpm:.1f} BPM (confidence: {rhythm_confidence:.3f})")
            except Exception as e:
                logger.debug(f"RhythmExtractor2013 failed: {e}")
            
            # Method 2: TempoTap (for general tempo)
            try:
                with SuppressOutput():
                    tempo_tap_bpm, tempo_tap_confidence = self.tempo_tap(audio)
                    
                    if isinstance(tempo_tap_bpm, (int, float)) and tempo_tap_bpm > 0 and tempo_tap_confidence > 0.1:
                        tempo_estimates.append((tempo_tap_bpm, tempo_tap_confidence))
                        logger.debug(f"TempoTap: {tempo_tap_bpm:.1f} BPM (confidence: {tempo_tap_confidence:.3f})")
            except Exception as e:
                logger.debug(f"TempoTap failed: {e}")
            
            # Method 3: BeatTracker + BPM calculation (for bpm)
            try:
                with SuppressOutput():
                    beat_result = self.beat_tracker(audio)
                    
                    if isinstance(beat_result, tuple) and len(beat_result) >= 2:
                        beats = beat_result[0]
                        confidence = beat_result[1] if len(beat_result) > 1 else 0.0
                        
                        if isinstance(beats, np.ndarray) and beats.size > 2:
                            # Calculate BPM from beat intervals
                            beat_intervals = np.diff(beats)
                            if len(beat_intervals) > 0:
                                avg_interval = np.mean(beat_intervals)
                                if avg_interval > 0:
                                    beat_bpm = 60.0 / avg_interval
                                    if 40 <= beat_bpm <= 208:  # Reasonable BPM range
                                        tempo_estimates.append((beat_bpm, confidence))
                                        logger.debug(f"BeatTracker: {beat_bpm:.1f} BPM (confidence: {confidence:.3f})")
            except Exception as e:
                logger.debug(f"BeatTracker BPM calculation failed: {e}")
            
            # Assign different BPM values based on method
            if tempo_estimates:
                # Sort by confidence
                tempo_estimates.sort(key=lambda x: x[1], reverse=True)
                
                # Use highest confidence for overall tempo
                best_bpm, best_confidence = tempo_estimates[0]
                features['tempo'] = safe_float(best_bpm)
                features['tempo_confidence'] = safe_float(best_confidence)
                

                
                # Use the best tempo estimate (highest confidence)
                features['tempo_methods_used'] = len(tempo_estimates)
                
                logger.info(f"Tempo extracted: {best_bpm:.1f} BPM (confidence: {best_confidence:.3f}, methods: {len(tempo_estimates)})")
            else:
                features['tempo'] = -999.0
                features['tempo_confidence'] = -999.0
                features['tempo_methods_used'] = 0
                logger.warning("All tempo estimation methods failed")
            
            # Energy-based rhythm features
            features['energy_variance'] = safe_float(np.var(audio))
            features['energy_mean'] = safe_float(np.mean(np.abs(audio)))
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract rhythm features: {e}")
            return {'tempo': -999.0, 'tempo_confidence': -999.0, 'tempo_methods_used': 0, 'energy_variance': -999.0, 'energy_mean': -999.0}
    
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
                
                features['spectral_centroid_mean'] = safe_float(np.mean(centroids))
                features['spectral_centroid_std'] = safe_float(np.std(centroids))
                features['spectral_rolloff_mean'] = safe_float(np.mean(rolloffs))
                features['spectral_rolloff_std'] = safe_float(np.std(rolloffs))
                
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
                features['key_strength'] = safe_float(strength)
                
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
    
    def extract_rhythm_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract comprehensive rhythm features using Essentia algorithms.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of rhythm features
        """
        try:
            features = {}
            
            # Get configuration to check which algorithms are enabled
            try:
                config = analysis_config_loader.get_config()
                # Handle different possible configuration structures
                if hasattr(config, 'algorithms'):
                    enable_complex_rhythm = config.algorithms.enable_complex_rhythm
                    enable_beat_tracking = config.algorithms.enable_beat_tracking
                    enable_tempo_tap = config.algorithms.enable_tempo_tap
                    enable_rhythm_extractor = config.algorithms.enable_rhythm_extractor
                elif hasattr(config, 'essentia') and hasattr(config.essentia, 'algorithms'):
                    try:
                        enable_complex_rhythm = config.essentia.algorithms.enable_complex_rhythm
                        enable_beat_tracking = config.essentia.algorithms.enable_beat_tracking
                        enable_tempo_tap = config.essentia.algorithms.enable_tempo_tap
                        enable_rhythm_extractor = config.essentia.algorithms.enable_rhythm_extractor
                    except AttributeError:
                        # Fallback to defaults if essentia structure is invalid
                        enable_complex_rhythm = True
                        enable_beat_tracking = True
                        enable_tempo_tap = True
                        enable_rhythm_extractor = True
                else:
                    # Default to enabled if config structure is different
                    enable_complex_rhythm = True
                    enable_beat_tracking = True
                    enable_tempo_tap = True
                    enable_rhythm_extractor = True
            except Exception as e:
                logger.warning(f"Could not load algorithm configuration: {e}, using defaults")
                enable_complex_rhythm = True
                enable_beat_tracking = True
                enable_tempo_tap = True
                enable_rhythm_extractor = True
            
            # Always extract basic rhythm features
            basic_rhythm = self._extract_simple_rhythm_features(audio)
            features.update(basic_rhythm)
            
            # Basic rhythm features are already properly mapped in _extract_simple_rhythm_features
            
            # Enhanced rhythm analysis if enabled
            if enable_complex_rhythm or enable_rhythm_extractor:
                try:
                    with SuppressOutput():
                        # Use RhythmExtractor2013 for comprehensive rhythm analysis with proper parameters
                        rhythm_extractor = es.RhythmExtractor2013(
                            maxTempo=208,
                            minTempo=40,
                            method='multifeature'
                        )
                        
                        # The algorithm returns: bpm, ticks, confidence, estimates, bpmIntervals
                        rhythm_bpm, rhythm_ticks, rhythm_confidence, rhythm_estimates, rhythm_bpm_intervals = rhythm_extractor(audio)
                        
                        if rhythm_bpm > 0 and rhythm_confidence > 0.1:
                            features['rhythm_bpm'] = safe_float(rhythm_bpm)
                            features['rhythm_confidence'] = safe_float(rhythm_confidence)
                            features['rhythm_ticks'] = safe_json_serialize(rhythm_ticks)
                            features['rhythm_estimates'] = safe_json_serialize(rhythm_estimates)
                            features['rhythm_bpm_intervals'] = safe_json_serialize(rhythm_bpm_intervals)
                            
                            logger.debug(f"RhythmExtractor2013: {rhythm_bpm:.1f} BPM (confidence: {rhythm_confidence:.3f})")
                            logger.debug(f"RhythmExtractor2013: {len(rhythm_ticks)} ticks, {len(rhythm_estimates)} estimates")
                except Exception as e:
                    logger.warning(f"RhythmExtractor2013 failed: {e}")
            
            # Beat tracking if enabled
            if enable_beat_tracking:
                try:
                    with SuppressOutput():
                        beat_result = self.beat_tracker(audio)
                        # Handle different return formats
                        if isinstance(beat_result, tuple) and len(beat_result) == 2:
                            beats, confidence = beat_result
                        elif isinstance(beat_result, tuple) and len(beat_result) == 3:
                            beats, confidence, _ = beat_result  # Ignore third return value
                        else:
                            beats = beat_result
                            confidence = 0.0
                        
                        # Check if beats is a valid array and has sufficient length
                        if isinstance(beats, np.ndarray) and beats.size > 2:
                            features['beats'] = beats.tolist() if hasattr(beats, 'tolist') else beats
                            features['beat_confidence'] = float(confidence)
                            
                            # Calculate beat intervals and statistics
                            beat_intervals = np.diff(beats)
                            features['beat_intervals_mean'] = safe_float(np.mean(beat_intervals))
                            features['beat_intervals_std'] = safe_float(np.std(beat_intervals))
                            features['num_beats'] = int(beats.size)
                            
                            logger.debug(f"BeatTrackerDegara: {beats.size} beats (confidence: {confidence:.3f})")
                        else:
                            logger.debug(f"BeatTrackerDegara: insufficient beats detected ({beats.size if isinstance(beats, np.ndarray) else 'invalid'})")
                except Exception as e:
                    logger.warning(f"BeatTrackerDegara failed: {e}")
            
            # Tempo tap analysis if enabled
            if enable_tempo_tap:
                try:
                    with SuppressOutput():
                        tempo_tap_bpm, tempo_tap_confidence = self.tempo_tap(audio)
                        
                        # Check if values are valid and not empty arrays
                        if (isinstance(tempo_tap_bpm, (int, float)) and tempo_tap_bpm > 0 and 
                            isinstance(tempo_tap_confidence, (int, float)) and tempo_tap_confidence > 0.1):
                            features['tempo_tap_bpm'] = safe_float(tempo_tap_bpm)
                            features['tempo_tap_confidence'] = safe_float(tempo_tap_confidence)
                            
                            logger.debug(f"TempoTap: {tempo_tap_bpm:.1f} BPM (confidence: {tempo_tap_confidence:.3f})")
                        else:
                            logger.debug(f"TempoTap: invalid results (BPM: {tempo_tap_bpm}, confidence: {tempo_tap_confidence})")
                except Exception as e:
                    logger.warning(f"TempoTap failed: {e}")
            
            # Onset detection for rhythm analysis
            try:
                with SuppressOutput():
                    # Frame the audio for onset detection
                    frames = es.FrameGenerator(
                        audio,
                        frameSize=self.config.frame_size,
                        hopSize=self.config.hop_size
                    )
                    
                    onset_strengths = []
                    for frame in frames:
                        windowed_frame = self.windowing(frame)
                        spectrum = self.spectrum(windowed_frame)
                        onset_strength = self.onset_detector(spectrum, spectrum)  # Using spectrum for both inputs
                        onset_strengths.append(onset_strength)
                    
                    if onset_strengths:
                        onset_strengths = np.array(onset_strengths)
                        features['onset_strength_mean'] = safe_float(np.mean(onset_strengths))
                        features['onset_strength_std'] = safe_float(np.std(onset_strengths))
                        features['onset_strength_max'] = safe_float(np.max(onset_strengths))
                        features['onset_count'] = int(np.sum(onset_strengths > 0.5))  # Count strong onsets
                        
                        logger.debug(f"Onset detection: {len(onset_strengths)} frames analyzed")
            except Exception as e:
                logger.warning(f"Onset detection failed: {e}")
            
            # Energy-based rhythm features
            features['energy_variance'] = safe_float(np.var(audio))
            features['energy_mean'] = safe_float(np.mean(np.abs(audio)))
            features['energy_std'] = safe_float(np.std(np.abs(audio)))
            
            # Spectral rhythm features
            try:
                frames = es.FrameGenerator(
                    audio,
                    frameSize=self.config.frame_size,
                    hopSize=self.config.hop_size
                )
                
                spectral_centroids = []
                for frame in frames:
                    windowed_frame = self.windowing(frame)
                    spectrum = self.spectrum(windowed_frame)
                    
                    # Calculate spectral centroid
                    freqs = np.linspace(0, self.config.sample_rate/2, len(spectrum))
                    centroid = np.sum(freqs * spectrum) / np.sum(spectrum)
                    spectral_centroids.append(centroid)
                
                if spectral_centroids:
                    features['spectral_centroid_variance'] = safe_float(np.var(spectral_centroids))
                    features['spectral_centroid_mean'] = safe_float(np.mean(spectral_centroids))
                    
            except Exception as e:
                logger.warning(f"Spectral rhythm analysis failed: {e}")
            
            # BPM values are now properly assigned by different algorithms in _extract_simple_rhythm_features
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract rhythm features: {e}")
            return {
                'tempo': -999.0, 
                'tempo_confidence': -999.0, 
                'tempo_methods_used': 0
            }
    
    def extract_harmonic_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract comprehensive harmonic features using Essentia algorithms.
        
        Args:
            audio: Audio data
            
        Returns:
            Dictionary of harmonic features
        """
        try:
            features = {}
            
            # Get configuration to check which algorithms are enabled
            try:
                config = analysis_config_loader.get_config()
                # Handle different possible configuration structures
                if hasattr(config, 'algorithms'):
                    enable_complex_harmonic = config.algorithms.enable_complex_harmonic
                    enable_pitch_analysis = config.algorithms.enable_pitch_analysis
                    enable_chord_detection = config.algorithms.enable_chord_detection
                elif hasattr(config, 'essentia') and hasattr(config.essentia, 'algorithms'):
                    try:
                        enable_complex_harmonic = config.essentia.algorithms.enable_complex_harmonic
                        enable_pitch_analysis = config.essentia.algorithms.enable_pitch_analysis
                        enable_chord_detection = config.essentia.algorithms.enable_chord_detection
                    except AttributeError:
                        # Fallback to defaults if essentia structure is invalid
                        enable_complex_harmonic = True
                        enable_pitch_analysis = True
                        enable_chord_detection = True
                else:
                    # Default to enabled if config structure is different
                    enable_complex_harmonic = True
                    enable_pitch_analysis = True
                    enable_chord_detection = True
            except Exception as e:
                logger.warning(f"Could not load algorithm configuration: {e}, using defaults")
                enable_complex_harmonic = True
                enable_pitch_analysis = True
                enable_chord_detection = True
            
            # Always extract basic harmonic features
            basic_harmonic = self._extract_simple_harmonic_features(audio)
            features.update(basic_harmonic)
            
            # Enhanced harmonic analysis if enabled
            if enable_complex_harmonic:
                # Chromagram analysis - use spectral approach for short audio
                try:
                    with SuppressOutput():
                        # For short audio, use spectral analysis to estimate chroma
                        if len(audio) >= 32768:  # Long audio - use chromagram
                            # Use frame-based approach for chromagram
                            frames = es.FrameGenerator(
                                audio,
                                frameSize=32768,  # Use the required frame size
                                hopSize=16384     # Half the frame size
                            )
                            
                            chromagram_frames = []
                            for frame in frames:
                                chromagram_frame = self.chromagram(frame)
                                chromagram_frames.append(chromagram_frame)
                            
                            if chromagram_frames:
                                chromagram = np.array(chromagram_frames)
                                features['chromagram'] = safe_json_serialize(chromagram)
                                
                                # Calculate chromagram statistics
                                if len(chromagram) > 0 and chromagram.size > 0:
                                    features['chromagram_mean'] = safe_json_serialize(np.mean(chromagram, axis=0))
                                    features['chromagram_std'] = safe_json_serialize(np.std(chromagram, axis=0))
                                    features['chromagram_max'] = safe_json_serialize(np.max(chromagram, axis=0))
                                    
                                    # Find dominant chroma
                                    chroma_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                                    chroma_means = np.mean(chromagram, axis=0)
                                    if len(chroma_means) == 12:  # Ensure we have 12 chroma values
                                        dominant_chroma_idx = int(np.argmax(chroma_means))
                                        features['dominant_chroma'] = chroma_names[dominant_chroma_idx]
                                        features['dominant_chroma_strength'] = safe_float(chroma_means[dominant_chroma_idx])
                                        
                                        logger.debug(f"Chromagram analysis: dominant chroma {features['dominant_chroma']}")
                        else:
                            # For short audio, use spectral peaks to estimate dominant frequency
                            # and map to chroma
                            frequencies, magnitudes = self.spectral_peaks(audio)
                            if len(frequencies) > 0:
                                # Find the strongest frequency
                                strongest_idx = np.argmax(magnitudes)
                                dominant_freq = frequencies[strongest_idx]
                                
                                # Map frequency to chroma
                                chroma_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                                if dominant_freq > 0:
                                    # Convert frequency to note number (A4 = 440Hz = note 69)
                                    note_num = 12 * np.log2(dominant_freq / 440.0) + 69
                                    chroma_idx = int(round(note_num)) % 12
                                    features['dominant_chroma'] = chroma_names[chroma_idx]
                                    features['dominant_chroma_strength'] = safe_float(magnitudes[strongest_idx])
                                    
                                    logger.debug(f"Spectral analysis: dominant chroma {features['dominant_chroma']} from {dominant_freq:.1f}Hz")
                except Exception as e:
                    logger.warning(f"Chromagram analysis failed: {e}")
                
                # Chord detection if enabled
                if enable_chord_detection:
                    try:
                        with SuppressOutput():
                            # Only perform chord detection for longer audio files
                            if len(audio) >= 32768:  # Minimum length for chromagram
                                # Use frame-based approach for chromagram
                                frames = es.FrameGenerator(
                                    audio,
                                    frameSize=32768,  # Use the required frame size
                                    hopSize=16384     # Half the frame size
                                )
                                
                                chromagram_frames = []
                                for frame in frames:
                                    chromagram_frame = self.chromagram(frame)
                                    chromagram_frames.append(chromagram_frame)
                                
                                if chromagram_frames:
                                    chromagram = np.array(chromagram_frames)
                                
                                    # Convert chromagram to list format for chord detection
                                    chromagram_list = chromagram.tolist() if hasattr(chromagram, 'tolist') else chromagram
                                    
                                    chords, strength = self.chords_detection(chromagram_list)
                                    features['chords'] = safe_json_serialize(chords)
                                    features['chord_strength'] = safe_json_serialize(strength)
                                    
                                    # Calculate chord statistics
                                    if len(chords) > 0:
                                        features['chord_count'] = len(chords)
                                        features['chord_strength_mean'] = safe_float(np.mean(strength))
                                        features['chord_strength_std'] = safe_float(np.std(strength))
                                        
                                        # Find most common chord
                                        unique_chords, counts = np.unique(chords, return_counts=True)
                                        most_common_idx = int(np.argmax(counts))
                                        features['most_common_chord'] = str(unique_chords[most_common_idx])
                                        features['most_common_chord_count'] = int(counts[most_common_idx])
                                        
                                        logger.debug(f"Chord detection: {len(chords)} chords detected")
                            else:
                                # For short audio, skip chord detection but add a placeholder
                                features['chords'] = []
                                features['chord_strength'] = []
                                features['chord_count'] = 0
                                logger.debug(f"Chord detection skipped for short audio ({len(audio)} samples)")
                    except Exception as e:
                        logger.warning(f"Chord detection failed: {e}")
            
            # Pitch analysis if enabled
            if enable_pitch_analysis:
                try:
                    with SuppressOutput():
                        # PitchYin analysis
                        pitch_yin, pitch_confidence = self.pitch_yin(audio)
                        features['pitch_yin'] = safe_json_serialize(pitch_yin)
                        features['pitch_yin_confidence'] = safe_json_serialize(pitch_confidence)
                        
                        # Calculate pitch statistics
                        if isinstance(pitch_yin, np.ndarray) and pitch_yin.size > 0:
                            # Filter out zero/unconfident pitches
                            confident_pitches = pitch_yin[pitch_confidence > 0.5]
                            if confident_pitches.size > 0:
                                features['pitch_mean'] = safe_float(np.mean(confident_pitches))
                                features['pitch_std'] = safe_float(np.std(confident_pitches))
                                features['pitch_min'] = safe_float(np.min(confident_pitches))
                                features['pitch_max'] = safe_float(np.max(confident_pitches))
                                features['pitch_median'] = safe_float(np.median(confident_pitches))
                                
                                # Convert to note names
                                def freq_to_note(freq):
                                    if freq <= 0:
                                        return "silence"
                                    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                                    note_num = 12 * np.log2(freq / 440.0) + 49
                                    note_index = int(round(note_num)) % 12
                                    return note_names[note_index]
                                
                                pitch_notes = [freq_to_note(f) for f in confident_pitches]
                                unique_notes, note_counts = np.unique(pitch_notes, return_counts=True)
                                most_common_note_idx = int(np.argmax(note_counts))
                                features['most_common_note'] = str(unique_notes[most_common_note_idx])
                                features['most_common_note_count'] = int(note_counts[most_common_note_idx])
                                
                                logger.debug(f"PitchYin analysis: {confident_pitches.size} confident pitches")
                except Exception as e:
                    logger.warning(f"PitchYin analysis failed: {e}")
                
                try:
                    with SuppressOutput():
                        # PitchMelodia analysis (for melody extraction)
                        pitch_melodia, pitch_confidence = self.pitch_melodia(audio)
                        features['pitch_melodia'] = pitch_melodia.tolist() if hasattr(pitch_melodia, 'tolist') else pitch_melodia
                        features['pitch_melodia_confidence'] = pitch_confidence.tolist() if hasattr(pitch_confidence, 'tolist') else pitch_confidence
                        
                        # Calculate melody statistics
                        if isinstance(pitch_melodia, np.ndarray) and pitch_melodia.size > 0:
                            confident_melody = pitch_melodia[pitch_confidence > 0.5]
                            if confident_melody.size > 0:
                                features['melody_mean'] = safe_float(np.mean(confident_melody))
                                features['melody_std'] = safe_float(np.std(confident_melody))
                                features['melody_range'] = safe_float(np.max(confident_melody) - np.min(confident_melody))
                                
                                logger.debug(f"PitchMelodia analysis: {confident_melody.size} confident melody points")
                except Exception as e:
                    logger.warning(f"PitchMelodia analysis failed: {e}")
            
            # Enhanced spectral analysis for harmonic content
            try:
                frames = es.FrameGenerator(
                    audio,
                    frameSize=self.config.frame_size,
                    hopSize=self.config.hop_size
                )
                
                spectral_peaks_list = []
                for frame in frames:
                    windowed_frame = self.windowing(frame)
                    spectrum = self.spectrum(windowed_frame)
                    
                    # Extract spectral peaks
                    frequencies, magnitudes = self.spectral_peaks(spectrum)
                    if len(frequencies) > 0:
                        spectral_peaks_list.append({
                            'frequencies': frequencies.tolist(),
                            'magnitudes': magnitudes.tolist()
                        })
                
                if spectral_peaks_list:
                    features['spectral_peaks_count'] = len(spectral_peaks_list)
                    
                    # Calculate harmonic content statistics
                    all_frequencies = []
                    all_magnitudes = []
                    for peaks in spectral_peaks_list:
                        all_frequencies.extend(peaks['frequencies'])
                        all_magnitudes.extend(peaks['magnitudes'])
                    
                    if all_frequencies:
                        features['harmonic_frequencies_mean'] = safe_float(np.mean(all_frequencies))
                        features['harmonic_frequencies_std'] = safe_float(np.std(all_frequencies))
                        features['harmonic_magnitudes_mean'] = safe_float(np.mean(all_magnitudes))
                        features['harmonic_magnitudes_std'] = safe_float(np.std(all_magnitudes))
                        
                        # Count strong harmonics
                        strong_harmonics = [f for f, m in zip(all_frequencies, all_magnitudes) if m > 0.5]
                        features['strong_harmonics_count'] = len(strong_harmonics)
                        
                        logger.debug(f"Spectral peaks analysis: {len(all_frequencies)} peaks detected")
                        
            except Exception as e:
                logger.warning(f"Spectral peaks analysis failed: {e}")
            
            return features
            
        except Exception as e:
            logger.error(f"Failed to extract harmonic features: {e}")
            return {
                'spectral_centroid_mean': -999.0,
                'spectral_centroid_std': -999.0,
                'spectral_rolloff_mean': -999.0,
                'spectral_rolloff_std': -999.0,
                'key': 'unknown',
                'scale': 'unknown',
                'key_strength': -999.0,
                'dominant_chroma': 'unknown',
                'dominant_chroma_strength': -999.0,
                'pitch_mean': -999.0,
                'melody_mean': -999.0,
                'harmonic_frequencies_mean': -999.0
            }
    
    def extract_musicnn_tags(self, audio_path: str) -> Dict[str, Any]:
        """
        Extract MusiCNN tags from audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary containing tag predictions
        """
        results = {"musicnn": {}}
        try:
            if not self.musicnn_models or 'musicnn' not in self.musicnn_models:
                logger.warning("MusiCNN models are not loaded")
                return results

            loader = es.MonoLoader(filename=str(audio_path), sampleRate=16000)
            audio_mono = loader()

            # Get predictions
            if "musicnn" in self.musicnn_models and "labels" in self.musicnn_models:
                predictions = self.musicnn_models["musicnn"](audio_mono)
                tag_probs = np.mean(predictions, axis=0).tolist()
                results["musicnn"] = dict(zip(self.musicnn_models["labels"], tag_probs))
                
                logger.info(f"Extracted {len(results['musicnn'])} MusiCNN tags")

        except Exception as e:
            logger.error(f"Failed to run MusiCNN tags: {e}")

        return safe_json_serialize(results)

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
        Analyze an audio file using Essentia with simplified 60-second analysis for playlist generation.
        
        Args:
            file_path: Path to the audio file
            include_tensorflow: Whether to include TensorFlow model analysis (disabled by default for performance)
            category: Track length category ('normal', 'long', 'very_long') - affects analysis strategy
        
        Returns:
            Dictionary containing essential analysis results for playlist generation
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting simplified 60-second analysis of {file_path} (category: {category})")
            
            # Load the entire audio file
            audio, sample_rate = self.load_audio(file_path)
            full_duration = len(audio) / sample_rate
            logger.info(f"Full audio duration: {full_duration:.2f}s")
            
            # Extract only the first 60 seconds for analysis
            analysis_duration = 60.0  # 60 seconds
            analysis_samples = int(analysis_duration * sample_rate)
            
            if len(audio) > analysis_samples:
                analysis_audio = audio[:analysis_samples]
                logger.info(f"Using first {analysis_duration}s for analysis")
            else:
                analysis_audio = audio
                analysis_duration = full_duration
                logger.info(f"Track shorter than 60s, using full track ({analysis_duration:.2f}s)")
            
            # Extract only essential features for playlist generation
            logger.info("Extracting essential features for playlist generation...")
            
            # 1. Basic features (energy, loudness, duration)
            basic_features = self._extract_essential_basic_features(analysis_audio)
            
            # 2. Rhythm features (BPM - most important for playlist generation)
            rhythm_features = self._extract_essential_rhythm_features(analysis_audio)
            
            # 3. Harmonic features (key - useful for playlist generation)
            harmonic_features = self._extract_essential_harmonic_features(analysis_audio)
            
            # 4. MusiCNN features (genre and mood) if requested
            musicnn_features = {}
            if include_tensorflow:
                try:
                    musicnn_features = self.extract_musicnn_tags(file_path)
                    logger.info("MusiCNN features extracted successfully")
                except Exception as e:
                    logger.warning(f"Failed to extract MusiCNN features: {e}")
                    musicnn_features = {"genre": {}, "mood": {}}
            
            # Combine results - only essential data for playlist generation
            results = {
                'basic_features': basic_features,
                'rhythm_features': rhythm_features,
                'harmonic_features': harmonic_features,
                'musicnn': musicnn_features,
                'metadata': {
                    'file_path': file_path,
                    'full_duration': full_duration,
                    'analysis_duration': analysis_duration,
                    'sample_rate': sample_rate,
                    'category': category,
                    'analysis_strategy': 'simplified_60_second',
                    'analysis_duration_seconds': time.time() - start_time
                }
            }
            
            logger.info(f"Simplified analysis completed in {time.time() - start_time:.2f}s")
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
            # For short tracks, analyze beginning, middle, and end with 60s segments
            if duration <= 60:  # Very short: analyze entire track
                segments = [(0, duration)]
            elif duration <= 180:  # Short: analyze beginning and end
                segments = [
                    (0, 60),  # First 60s
                    (duration - 60, duration)  # Last 60s
                ]
            else:  # Medium short: analyze beginning, middle, end
                segments = [
                    (0, 60),  # First 60s
                    (duration / 2 - 30, duration / 2 + 30),  # Middle 60s
                    (duration - 60, duration)  # Last 60s
                ]
                
        elif strategy == 'medium':  # 5-10 minutes: analyze strategic points
            # Analyze beginning, 1/4, 1/2, 3/4, and end with 60s segments
            segments = [
                (0, 60),  # First 60s
                (duration * 0.25 - 30, duration * 0.25 + 30),  # 1/4 point
                (duration * 0.5 - 30, duration * 0.5 + 30),  # Middle
                (duration * 0.75 - 30, duration * 0.75 + 30),  # 3/4 point
                (duration - 60, duration)  # Last 60s
            ]
            
        elif strategy == 'long':  # 10+ minutes: analyze key moments
            # Analyze beginning, key points, and end with 60s segments
            segments = [
                (0, 60),  # First 60s
                (duration * 0.2 - 30, duration * 0.2 + 30),  # 20% point
                (duration * 0.4 - 30, duration * 0.4 + 30),  # 40% point
                (duration * 0.6 - 30, duration * 0.6 + 30),  # 60% point
                (duration * 0.8 - 30, duration * 0.8 + 30),  # 80% point
                (duration - 60, duration)  # Last 60s
            ]
        
        # Ensure segments are within track bounds and have minimum duration
        valid_segments = []
        for start, end in segments:
            start = max(0, start)
            end = min(duration, end)
            if end - start >= 30:  # Minimum 30s segment for meaningful analysis
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
                'segment_results': safe_json_serialize(segment_results)
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
        """Aggregate rhythm features with intelligent BPM selection"""
        if not rhythm_features_list:
            return {}
        
        aggregated = {}
        
        # For BPM, use the most confident estimate or most common value
        valid_bpms = []
        bpm_confidences = []
        
        for features in rhythm_features_list:
            # Check for tempo (from rhythm extraction)
            if 'tempo' in features and features['tempo'] > 0 and features['tempo'] != -999.0:
                valid_bpms.append(features['tempo'])
                confidence = features.get('tempo_confidence', 0.5)
                bpm_confidences.append(confidence)
        
        if valid_bpms:
            # Use the BPM with highest confidence
            best_idx = int(np.argmax(bpm_confidences))  # Convert to regular Python int
            aggregated['tempo'] = valid_bpms[best_idx]
            aggregated['tempo_confidence'] = bpm_confidences[best_idx]
            aggregated['tempo_methods_used'] = len(valid_bpms)
            
            logger.info(f"Selected BPM from {len(valid_bpms)} estimates: {valid_bpms[best_idx]:.1f} (confidence: {bpm_confidences[best_idx]:.3f})")
        else:
            aggregated['tempo'] = -999.0
            aggregated['tempo_confidence'] = -999.0
            aggregated['tempo_methods_used'] = 0
            logger.warning("No valid BPM estimates found across chunks")
        
        # Average other numerical features
        other_features = self._average_features(rhythm_features_list)
        aggregated.update(other_features)
        
        return aggregated
    
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
                        averaged[model_name][output_name] = safe_json_serialize(np.mean(arrays, axis=0))
        
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

    def extract_feature_vector(self, file_path: str, include_tensorflow: bool = True, normalize: bool = True) -> np.ndarray:
        """
        Return a fixed-length numeric vector for similarity search.
        
        Args:
            file_path: Path to audio file
            include_tensorflow: Whether to include MusiCNN features
            normalize: Whether to normalize the vector
            
        Returns:
            Feature vector as numpy array
        """
        features = self.analyze_audio_file(file_path, include_tensorflow=include_tensorflow)
        vec: List[float] = []

        # Numeric low-level features
        vec.append(features["rhythm_features"]["tempo"])
        vec.append(features["rhythm_features"]["tempo_confidence"])
        vec.append(features["harmonic_features"]["key_strength"])

        # One-hot encode key (12 notes)
        keys = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        key_vec = [1.0 if features["harmonic_features"]["key"] == k else 0.0 for k in keys]
        vec.extend(key_vec)

        # One-hot encode scale (major/minor)
        scales = ["major","minor"]
        scale_vec = [1.0 if features["harmonic_features"]["scale"] == s else 0.0 for s in scales]
        vec.extend(scale_vec)

        # Add MusiCNN tags if present
        if include_tensorflow and "musicnn" in features:
            if "musicnn" in features["musicnn"]:
                vec.extend(list(features["musicnn"]["musicnn"].values()))

        arr = np.array(vec, dtype=np.float32)

        if normalize and np.linalg.norm(arr) > 0:
            arr = arr / np.linalg.norm(arr)

        return arr

    # === Playlist Matching Methods ===
    def add_to_library(self, file_path: str, include_tensorflow: bool = True):
        """
        Extract vector and store it in the in-memory library.
        
        Args:
            file_path: Path to audio file
            include_tensorflow: Whether to include MusiCNN features
        """
        vec = self.extract_feature_vector(file_path, include_tensorflow=include_tensorflow)
        self.track_library.append((file_path, vec))
        self.track_paths.append(file_path)
        
        # Rebuild FAISS index when we have enough vectors
        if FAISS_AVAILABLE and len(self.track_library) >= 10:
            self._rebuild_faiss_index()

    def add_multiple_to_library(self, file_paths: List[str], include_tensorflow: bool = True):
        """
        Add multiple tracks to the library efficiently.
        
        Args:
            file_paths: List of audio file paths
            include_tensorflow: Whether to include MusiCNN features
        """
        logger.info(f"Adding {len(file_paths)} tracks to library...")
        
        for i, file_path in enumerate(file_paths):
            try:
                vec = self.extract_feature_vector(file_path, include_tensorflow=include_tensorflow)
                self.track_library.append((file_path, vec))
                self.track_paths.append(file_path)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Added {i + 1}/{len(file_paths)} tracks")
                    
            except Exception as e:
                logger.warning(f"Failed to add {file_path}: {e}")
        
        # Build FAISS index after adding all tracks
        if FAISS_AVAILABLE and self.track_library:
            self._rebuild_faiss_index()
        
        logger.info(f"Successfully added {len(self.track_library)} tracks to library")

    def _rebuild_faiss_index(self):
        """Rebuild FAISS index from current track library"""
        if not FAISS_AVAILABLE or not self.track_library:
            return
        
        try:
            # Extract vectors from track library
            vectors = [vec for _, vec in self.track_library]
            self._build_faiss_index(vectors)
        except Exception as e:
            logger.error(f"Failed to rebuild FAISS index: {e}")

    def save_index(self, index_path: str):
        """
        Save FAISS index and track metadata to disk.
        
        Args:
            index_path: Path to save the index (without extension)
        """
        if not FAISS_AVAILABLE or self.faiss_index is None:
            logger.warning("No FAISS index to save")
            return
        
        try:
            # Save FAISS index
            faiss_path = f"{index_path}.faiss"
            faiss.write_index(self.faiss_index, faiss_path)
            
            # Save track metadata
            metadata_path = f"{index_path}.json"
            metadata = {
                'track_paths': self.track_paths,
                'vector_dimension': self.vector_dimension,
                'num_tracks': len(self.track_paths)
            }
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved FAISS index to {faiss_path} and metadata to {metadata_path}")
            
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    def load_index(self, index_path: str):
        """
        Load FAISS index and track metadata from disk.
        
        Args:
            index_path: Path to the saved index (without extension)
        """
        if not FAISS_AVAILABLE:
            logger.warning("FAISS not available, cannot load index")
            return
        
        try:
            # Load FAISS index
            faiss_path = f"{index_path}.faiss"
            if not os.path.exists(faiss_path):
                logger.warning(f"FAISS index file not found: {faiss_path}")
                return
            
            self.faiss_index = faiss.read_index(faiss_path)
            
            # Load track metadata
            metadata_path = f"{index_path}.json"
            if not os.path.exists(metadata_path):
                logger.warning(f"Metadata file not found: {metadata_path}")
                return
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            self.track_paths = metadata.get('track_paths', [])
            self.vector_dimension = metadata.get('vector_dimension')
            
            # Rebuild track library from paths (vectors will be regenerated when needed)
            self.track_library = [(path, None) for path in self.track_paths]
            
            logger.info(f"Loaded FAISS index with {len(self.track_paths)} tracks from {index_path}")
            
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")

    def get_library_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current library.
        
        Returns:
            Dictionary with library statistics
        """
        stats = {
            'total_tracks': len(self.track_library),
            'faiss_available': FAISS_AVAILABLE,
            'faiss_index_built': self.faiss_index is not None,
            'vector_dimension': self.vector_dimension
        }
        
        if self.faiss_index is not None:
            stats['faiss_index_type'] = type(self.faiss_index).__name__
            stats['faiss_index_size'] = self.faiss_index.ntotal
        
        return stats

    def _build_faiss_index(self, vectors: List[np.ndarray]):
        """
        Build FAISS index from vectors.
        
        Args:
            vectors: List of feature vectors
        """
        if not FAISS_AVAILABLE or not vectors:
            return
        
        try:
            # Convert to numpy array
            vectors_array = np.array(vectors, dtype=np.float32)
            self.vector_dimension = vectors_array.shape[1]
            
            # Choose appropriate FAISS index type based on dataset size
            num_vectors = len(vectors)
            
            if num_vectors < 1000:
                # Small dataset: use IndexFlatIP (Inner Product) for exact search
                self.faiss_index = faiss.IndexFlatIP(self.vector_dimension)
                logger.info(f"Created FAISS IndexFlatIP for {num_vectors} vectors")
            elif num_vectors < 10000:
                # Medium dataset: use IndexIVFFlat with clustering
                nlist = min(100, num_vectors // 10)  # Number of clusters
                quantizer = faiss.IndexFlatIP(self.vector_dimension)
                self.faiss_index = faiss.IndexIVFFlat(quantizer, self.vector_dimension, nlist)
                logger.info(f"Created FAISS IndexIVFFlat with {nlist} clusters for {num_vectors} vectors")
            else:
                # Large dataset: use IndexIVFPQ for memory efficiency
                nlist = min(1000, num_vectors // 10)
                m = 8  # Number of sub-vectors
                bits = 8  # Bits per sub-vector
                quantizer = faiss.IndexFlatIP(self.vector_dimension)
                self.faiss_index = faiss.IndexIVFPQ(quantizer, self.vector_dimension, nlist, m, bits)
                logger.info(f"Created FAISS IndexIVFPQ with {nlist} clusters for {num_vectors} vectors")
            
            # Add vectors to index
            self.faiss_index.add(vectors_array)
            logger.info(f"Added {num_vectors} vectors to FAISS index")
            
        except Exception as e:
            logger.error(f"Failed to build FAISS index: {e}")
            self.faiss_index = None

    def _search_faiss_index(self, query_vector: np.ndarray, top_n: int = 5) -> List[Tuple[int, float]]:
        """
        Search FAISS index for similar vectors.
        
        Args:
            query_vector: Query feature vector
            top_n: Number of similar vectors to return
            
        Returns:
            List of (index, similarity_score) tuples
        """
        if not FAISS_AVAILABLE or self.faiss_index is None:
            return []
        
        try:
            # Reshape query vector for FAISS
            query_vector = query_vector.reshape(1, -1).astype(np.float32)
            
            # Search the index
            similarities, indices = self.faiss_index.search(query_vector, min(top_n, len(self.track_paths)))
            
            # Convert to list of tuples
            results = []
            for idx, sim in zip(indices[0], similarities[0]):
                if idx != -1:  # FAISS returns -1 for invalid indices
                    results.append((int(idx), float(sim)))
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search FAISS index: {e}")
            return []

    def find_similar(self, query_path: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Find top N most similar tracks to the query file.
        
        Args:
            query_path: Path to query audio file
            top_n: Number of similar tracks to return
            
        Returns:
            List of (track_path, similarity_score) tuples
        """
        if not self.track_library:
            logger.warning("Library is empty. Add tracks with add_to_library().")
            return []

        query_vec = self.extract_feature_vector(query_path, include_tensorflow=True)

        # Use FAISS if available, otherwise fall back to basic search
        if FAISS_AVAILABLE and self.faiss_index is not None:
            # Use FAISS for efficient search
            similar_indices = self._search_faiss_index(query_vec, top_n)
            results = []
            for idx, similarity in similar_indices:
                if idx < len(self.track_paths):
                    results.append((self.track_paths[idx], similarity))
            return results
        else:
            # Fall back to basic similarity search
            similarities = []
            for path, vec in self.track_library:
                sim = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec))
                similarities.append((path, sim))

            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_n]

    def find_similar_batch(self, query_paths: List[str], top_n: int = 5) -> Dict[str, List[Tuple[str, float]]]:
        """
        Find similar tracks for multiple query files efficiently.
        
        Args:
            query_paths: List of query audio file paths
            top_n: Number of similar tracks to return per query
            
        Returns:
            Dictionary mapping query paths to similar tracks
        """
        results = {}
        
        for query_path in query_paths:
            try:
                similar_tracks = self.find_similar(query_path, top_n)
                results[query_path] = similar_tracks
            except Exception as e:
                logger.warning(f"Failed to find similar tracks for {query_path}: {e}")
                results[query_path] = []
        
        return results

    def search_by_vector(self, query_vector: np.ndarray, top_n: int = 5) -> List[Tuple[str, float]]:
        """
        Search for similar tracks using a pre-computed feature vector.
        
        Args:
            query_vector: Pre-computed feature vector
            top_n: Number of similar tracks to return
            
        Returns:
            List of (track_path, similarity_score) tuples
        """
        if not self.track_library:
            logger.warning("Library is empty. Add tracks with add_to_library().")
            return []

        # Use FAISS if available, otherwise fall back to basic search
        if FAISS_AVAILABLE and self.faiss_index is not None:
            # Use FAISS for efficient search
            similar_indices = self._search_faiss_index(query_vector, top_n)
            results = []
            for idx, similarity in similar_indices:
                if idx < len(self.track_paths):
                    results.append((self.track_paths[idx], similarity))
            return results
        else:
            # Fall back to basic similarity search
            similarities = []
            for path, vec in self.track_library:
                if vec is not None:  # Handle case where vector might be None
                    sim = np.dot(query_vector, vec) / (np.linalg.norm(query_vector) * np.linalg.norm(vec))
                    similarities.append((path, sim))

            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)
            return similarities[:top_n]

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
        results = analyzer.analyze_audio_file(str(file_path), include_tensorflow=True)
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
        results = analyzer.analyze_audio_file(str(file_path), include_tensorflow=True)
        print(json.dumps(results, indent=2))
