import logging
import numpy as np
import os
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import warnings

# Suppress TensorFlow logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

logger = logging.getLogger(__name__)

# TensorFlow imports with error handling
try:
    import tensorflow as tf
    TENSORFLOW_AVAILABLE = True
    logger.info(f"TensorFlow {tf.__version__} is available")
except ImportError:
    TENSORFLOW_AVAILABLE = False
    logger.warning("TensorFlow not available. Install with: pip install tensorflow")

try:
    import essentia.standard as es
    ESSENTIA_AVAILABLE = True
except ImportError:
    ESSENTIA_AVAILABLE = False
    logger.warning("Essentia not available for TensorFlow preprocessing")

@dataclass
class TensorFlowConfig:
    """Configuration for TensorFlow analysis"""
    models_directory: str = "models"
    enable_musicnn: bool = True
    enable_vggish: bool = False
    enable_tempo_cnn: bool = False
    enable_fsd_sinet: bool = False
    sample_rate: int = 16000
    hop_size: int = 512
    frame_size: int = 1024
    mel_bands: int = 96
    fmin: float = 0.0
    fmax: float = 8000.0

class TensorFlowAnalyzer:
    """
    TensorFlow-based audio analysis module.
    
    This module handles only TensorFlow/MusicNN analysis,
    separate from Essentia audio feature extraction.
    """
    
    def __init__(self, config: Optional[TensorFlowConfig] = None):
        self.config = config or TensorFlowConfig()
        self.models = {}
        self._load_config()
        self._load_models()
    
    def _load_config(self):
        """Load configuration from analysis config"""
        try:
            from ..core.analysis_config import analysis_config_loader
            config = analysis_config_loader.get_config()
            tf_config = config.get("tensorflow", {})
            
            # Update config with loaded values
            self.config.models_directory = tf_config.get("models_directory", self.config.models_directory)
            self.config.enable_musicnn = tf_config.get("enable_musicnn", self.config.enable_musicnn)
            self.config.enable_vggish = tf_config.get("enable_vggish", self.config.enable_vggish)
            self.config.enable_tempo_cnn = tf_config.get("enable_tempo_cnn", self.config.enable_tempo_cnn)
            self.config.enable_fsd_sinet = tf_config.get("enable_fsd_sinet", self.config.enable_fsd_sinet)
            
            # Audio processing settings
            audio_config = tf_config.get("audio_processing", {})
            self.config.sample_rate = audio_config.get("sample_rate", self.config.sample_rate)
            self.config.hop_size = audio_config.get("hop_size", self.config.hop_size)
            self.config.frame_size = audio_config.get("frame_size", self.config.frame_size)
            self.config.mel_bands = audio_config.get("mel_bands", self.config.mel_bands)
            self.config.fmin = audio_config.get("fmin", self.config.fmin)
            self.config.fmax = audio_config.get("fmax", self.config.fmax)
            
        except Exception as e:
            logger.warning(f"Failed to load TensorFlow configuration: {e}, using defaults")
    
    def _load_models(self):
        """Load TensorFlow models"""
        if not TENSORFLOW_AVAILABLE:
            logger.warning("TensorFlow not available, skipping model loading")
            return
        
        try:
            models_path = Path(self.config.models_directory)
            if not models_path.exists():
                logger.warning(f"Models directory not found: {models_path}")
                return
            
            # Load MusicNN model
            if self.config.enable_musicnn:
                musicnn_path = models_path / "msd-musicnn-1.pb"
                if musicnn_path.exists():
                    self.models["musicnn"] = self._load_tensorflow_model(str(musicnn_path))
                    logger.info("MusicNN model loaded successfully")
                else:
                    logger.warning(f"MusicNN model not found: {musicnn_path}")
            
            # Load other models as needed
            # VGGish, TempoCNN, FSD-SINet can be added here
            
        except Exception as e:
            logger.error(f"Failed to load TensorFlow models: {e}")
    
    def _load_tensorflow_model(self, model_path: str):
        """Load a TensorFlow model from file"""
        try:
            with tf.io.gfile.GFile(model_path, 'rb') as f:
                graph_def = tf.compat.v1.GraphDef()
                graph_def.ParseFromString(f.read())
            
            graph = tf.Graph()
            with graph.as_default():
                tf.import_graph_def(graph_def, name='')
            
            return graph
        except Exception as e:
            logger.error(f"Failed to load TensorFlow model {model_path}: {e}")
            return None
    
    def is_available(self) -> bool:
        """Check if TensorFlow analysis is available"""
        return TENSORFLOW_AVAILABLE and len(self.models) > 0
    
    def analyze_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze an audio file using TensorFlow models.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing TensorFlow analysis results
        """
        if not self.is_available():
            raise RuntimeError("TensorFlow analysis not available")
        
        try:
            logger.info(f"Starting TensorFlow analysis for: {file_path}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Audio file not found: {file_path}")
            
            results = {
                "tensorflow_analysis": {},
                "metadata": {
                    "file_path": file_path,
                    "analysis_timestamp": time.time(),
                    "analyzer": "tensorflow",
                    "models_used": list(self.models.keys())
                }
            }
            
            # Extract features for each model
            for model_name, model in self.models.items():
                try:
                    model_results = self._analyze_with_model(file_path, model_name, model)
                    results["tensorflow_analysis"][model_name] = model_results
                except Exception as e:
                    logger.error(f"Analysis with {model_name} failed: {e}")
                    results["tensorflow_analysis"][model_name] = {"error": str(e)}
            
            logger.info(f"TensorFlow analysis completed for: {file_path}")
            return results
            
        except Exception as e:
            logger.error(f"TensorFlow analysis failed for {file_path}: {e}")
            raise
    
    def _analyze_with_model(self, file_path: str, model_name: str, model) -> Dict[str, Any]:
        """Analyze audio with a specific TensorFlow model"""
        if model_name == "musicnn":
            return self._analyze_with_musicnn(file_path, model)
        else:
            return {"error": f"Unknown model: {model_name}"}
    
    def _analyze_with_musicnn(self, file_path: str, model) -> Dict[str, Any]:
        """Analyze audio with MusicNN model"""
        try:
            # Load and preprocess audio
            audio = self._load_audio_for_tensorflow(file_path)
            
            # Extract mel-spectrogram
            mel_spec = self._extract_mel_spectrogram(audio)
            
            # Run inference
            with tf.compat.v1.Session(graph=model) as sess:
                # Get input and output tensors
                input_tensor = model.get_tensor_by_name('model/Placeholder:0')
                output_tensor = model.get_tensor_by_name('model/Sigmoid:0')
                
                # Run inference
                predictions = sess.run(output_tensor, {input_tensor: mel_spec})
                
                # Process results
                results = self._process_musicnn_predictions(predictions)
                
                return results
                
        except Exception as e:
            logger.error(f"MusicNN analysis failed: {e}")
            return {"error": str(e)}
    
    def _load_audio_for_tensorflow(self, file_path: str) -> np.ndarray:
        """Load audio file for TensorFlow processing"""
        try:
            if ESSENTIA_AVAILABLE:
                # Use Essentia for audio loading
                audio = es.MonoLoader(filename=file_path, sampleRate=self.config.sample_rate)()
            else:
                # Fallback to other methods
                import soundfile as sf
                audio, sr = sf.read(file_path)
                if len(audio.shape) > 1:
                    audio = audio[:, 0]  # Take first channel
                if sr != self.config.sample_rate:
                    # Resample if needed
                    from scipy import signal
                    audio = signal.resample(audio, int(len(audio) * self.config.sample_rate / sr))
            
            return audio
            
        except Exception as e:
            logger.error(f"Failed to load audio for TensorFlow: {e}")
            raise
    
    def _extract_mel_spectrogram(self, audio: np.ndarray) -> np.ndarray:
        """Extract mel-spectrogram for TensorFlow models"""
        try:
            if ESSENTIA_AVAILABLE:
                # Use Essentia for mel-spectrogram extraction
                mel_bands = es.MelBands(
                    numberBands=self.config.mel_bands,
                    sampleRate=self.config.sample_rate,
                    lowFrequencyBound=self.config.fmin,
                    highFrequencyBound=self.config.fmax
                )
                
                # Extract frames
                frame_cutter = es.FrameCutter(
                    frameSize=self.config.frame_size,
                    hopSize=self.config.hop_size
                )
                
                window = es.Windowing(type='hann')
                spectrum = es.Spectrum()
                
                mel_specs = []
                for frame in frame_cutter(audio):
                    spec = spectrum(window(frame))
                    mel_spec = mel_bands(spec)
                    mel_specs.append(mel_spec)
                
                return np.array(mel_specs)
                
            else:
                # Fallback to librosa
                import librosa
                mel_spec = librosa.feature.melspectrogram(
                    y=audio,
                    sr=self.config.sample_rate,
                    n_mels=self.config.mel_bands,
                    hop_length=self.config.hop_size,
                    n_fft=self.config.frame_size,
                    fmin=self.config.fmin,
                    fmax=self.config.fmax
                )
                return mel_spec.T  # Transpose to match Essentia format
                
        except Exception as e:
            logger.error(f"Failed to extract mel-spectrogram: {e}")
            raise
    
    def _process_musicnn_predictions(self, predictions: np.ndarray) -> Dict[str, Any]:
        """Process MusicNN model predictions"""
        try:
            # MusicNN outputs 50 music tags
            # We'll return the top predictions and overall statistics
            
            # Get top predictions
            top_indices = np.argsort(predictions[0])[-10:][::-1]  # Top 10
            top_scores = predictions[0][top_indices]
            
            # MusicNN tag names (simplified)
            tag_names = [
                "rock", "pop", "electronic", "hip hop", "jazz", "classical", "country", "blues",
                "folk", "reggae", "punk", "metal", "r&b", "soul", "funk", "disco", "house",
                "techno", "dance", "ambient", "experimental", "indie", "alternative", "gospel",
                "latin", "world", "new age", "soundtrack", "comedy", "spoken word", "children's",
                "holiday", "vocal", "instrumental", "acoustic", "electric", "live", "studio",
                "remix", "cover", "original", "fast", "slow", "loud", "quiet", "energetic",
                "calm", "happy", "sad", "aggressive", "peaceful"
            ]
            
            top_tags = []
            for idx, score in zip(top_indices, top_scores):
                tag_name = tag_names[idx] if idx < len(tag_names) else f"tag_{idx}"
                top_tags.append({
                    "tag": tag_name,
                    "confidence": float(score)
                })
            
            return {
                "top_predictions": top_tags,
                "mean_confidence": float(np.mean(predictions[0])),
                "max_confidence": float(np.max(predictions[0])),
                "prediction_entropy": float(-np.sum(predictions[0] * np.log(predictions[0] + 1e-10))),
                "all_predictions": predictions[0].tolist()
            }
            
        except Exception as e:
            logger.error(f"Failed to process MusicNN predictions: {e}")
            return {"error": str(e)}

# Global instance
tensorflow_analyzer = TensorFlowAnalyzer()
