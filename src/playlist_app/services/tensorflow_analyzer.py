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
    # MusicNN specific settings
    musicnn_input_frames: int = 187
    musicnn_input_mels: int = 96
    # Mood analysis settings
    enable_mood_analysis: bool = True
    mood_confidence_threshold: float = 0.3
    # Streaming settings (using Essentia's approach)
    enable_streaming: bool = True
    chunk_duration: float = 30.0  # seconds per chunk
    overlap_ratio: float = 0.5    # overlap between chunks
    max_chunks: int = 5           # maximum chunks to process
    memory_limit_mb: int = 512    # memory limit per analysis

class TensorFlowAnalyzer:
    """
    Enhanced TensorFlow-based audio analysis module using Essentia's pipeline approach.
    
    This module handles TensorFlow/MusicNN analysis and mood detection,
    integrated with the audio values extraction pipeline.
    
    Features:
    - Uses Essentia's efficient streaming pipeline
    - Keeps TensorFlow models in memory (loaded once)
    - Memory-efficient audio processing
    - Configurable memory limits
    """
    
    def __init__(self, config: Optional[TensorFlowConfig] = None):
        self.config = config or TensorFlowConfig()
        self.models = {}
        self.musicnn_tags = []
        self.musicnn_predictor = None  # Keep model in memory
        self._load_config()
        self._load_models()
        self._load_musicnn_tags()
        self._initialize_models()
    
    def _load_config(self):
        """Load configuration from analysis config"""
        try:
            from ..core.analysis_config import analysis_config_loader
            config = analysis_config_loader.get_config()
            
            # Use the algorithms configuration for TensorFlow settings
            self.config.enable_musicnn = config.algorithms.enable_tensorflow
            
            # Use audio processing settings from the main config
            self.config.sample_rate = config.audio_processing.sample_rate
            self.config.frame_size = config.audio_processing.frame_size
            self.config.hop_size = config.audio_processing.hop_size
            
            # Use spectral analysis settings
            self.config.mel_bands = config.spectral_analysis.n_mels
            self.config.fmin = config.spectral_analysis.min_frequency
            self.config.fmax = config.spectral_analysis.max_frequency
            
            # Use performance settings for streaming
            try:
                self.config.memory_limit_mb = config.performance.parallel_processing.memory_limit_mb
            except AttributeError:
                # Fallback if performance config not available
                pass
            
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
                    self.models["musicnn"] = str(musicnn_path)
                    logger.info("MusicNN model path registered successfully")
                else:
                    logger.warning(f"MusicNN model not found: {musicnn_path}")
            
            # Load other models as needed
            # VGGish, TempoCNN, FSD-SINet can be added here
            
        except Exception as e:
            logger.error(f"Failed to load TensorFlow models: {e}")
    
    def _initialize_models(self):
        """Initialize TensorFlow models in memory (load once)"""
        if not TENSORFLOW_AVAILABLE or not ESSENTIA_AVAILABLE:
            return
        
        try:
            # Initialize MusicNN predictor once
            if self.config.enable_musicnn and "musicnn" in self.models:
                from essentia.standard import TensorflowPredictMusiCNN
                
                model_path = self.models["musicnn"]
                self.musicnn_predictor = TensorflowPredictMusiCNN(
                    graphFilename=model_path,
                    output="model/Sigmoid:0"
                )
                logger.info("MusicNN model loaded and kept in memory")
                
        except Exception as e:
            logger.error(f"Failed to initialize TensorFlow models: {e}")
    
    def _unload_models(self):
        """Unload TensorFlow models to free memory"""
        try:
            if self.musicnn_predictor is not None:
                del self.musicnn_predictor
                self.musicnn_predictor = None
                logger.info("MusicNN model unloaded from memory")
                
            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            logger.error(f"Failed to unload TensorFlow models: {e}")
    
    def __del__(self):
        """Cleanup when analyzer is destroyed"""
        self._unload_models()
    
    def _load_musicnn_tags(self):
        """Load MusicNN tag names from model configuration"""
        try:
            models_path = Path(self.config.models_directory)
            musicnn_config_path = models_path / "msd-musicnn-1.json"
            
            if musicnn_config_path.exists():
                import json
                with open(musicnn_config_path, 'r') as f:
                    config = json.load(f)
                    self.musicnn_tags = config.get("classes", [])
                    logger.info(f"Loaded {len(self.musicnn_tags)} MusicNN tags")
            else:
                # Fallback to hardcoded tags
                self.musicnn_tags = [
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
                logger.warning("Using fallback MusicNN tags")
                
        except Exception as e:
            logger.error(f"Failed to load MusicNN tags: {e}")
            self.musicnn_tags = []
    
    def _get_musicnn_categories(self):
        """Get comprehensive category mappings for MusicNN tags"""
        return {
            # Genre categories
            "genres": {
                "rock": ["rock", "alternative rock", "classic rock", "hard rock", "Progressive rock", "indie rock"],
                "pop": ["pop", "indie pop"],
                "electronic": ["electronic", "electronica", "electro", "House"],
                "jazz": ["jazz"],
                "folk": ["folk"],
                "country": ["country"],
                "blues": ["blues"],
                "soul": ["soul"],
                "rnb": ["rnb"],
                "hip_hop": ["Hip-Hop"],
                "punk": ["punk"],
                "metal": ["metal", "heavy metal"],
                "ambient": ["ambient"],
                "funk": ["funk"],
                "dance": ["dance"]
            },
            
            # Mood categories
            "moods": {
                "energetic": ["dance", "party", "catchy", "rock", "metal", "hard rock", "heavy metal", "punk"],
                "calm": ["chill", "chillout", "ambient", "Mellow", "easy listening", "beautiful"],
                "happy": ["happy", "catchy", "party", "dance", "funk", "sexy"],
                "sad": ["sad", "Mellow", "chill", "chillout"],
                "aggressive": ["metal", "hard rock", "heavy metal", "punk", "rock"],
                "peaceful": ["ambient", "chill", "chillout", "beautiful", "easy listening"],
                "romantic": ["sexy", "beautiful", "soul", "rnb"],
                "nostalgic": ["oldies", "60s", "70s", "80s", "90s", "00s", "classic rock"],
                "modern": ["electronic", "electro", "House", "techno", "dance"],
                "acoustic": ["acoustic", "folk", "country", "guitar", "instrumental"],
                "vocal": ["female vocalists", "male vocalists", "female vocalist"],
                "instrumental": ["instrumental", "guitar", "acoustic"]
            },
            
            # Era categories
            "eras": {
                "60s": ["60s", "oldies"],
                "70s": ["70s", "classic rock"],
                "80s": ["80s"],
                "90s": ["90s"],
                "00s": ["00s"],
                "modern": ["electronic", "electro", "House", "indie", "alternative"]
            },
            
            # Instrument categories
            "instruments": {
                "guitar": ["guitar", "acoustic", "rock", "folk", "country"],
                "vocal": ["female vocalists", "male vocalists", "female vocalist"],
                "electronic": ["electronic", "electronica", "electro", "House"],
                "acoustic": ["acoustic", "folk", "country", "guitar"]
            },
            
            # Style categories
            "styles": {
                "alternative": ["alternative", "alternative rock", "indie", "indie rock", "indie pop"],
                "experimental": ["experimental"],
                "mainstream": ["pop", "rock", "dance"],
                "underground": ["indie", "experimental", "punk"],
                "commercial": ["pop", "dance", "catchy"],
                "artistic": ["beautiful", "experimental", "ambient"]
            }
        }
    
    def is_available(self) -> bool:
        """Check if TensorFlow analysis is available"""
        return TENSORFLOW_AVAILABLE and len(self.models) > 0
    
    def analyze_audio_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze an audio file using TensorFlow models with chunk-based streaming.
        
        Strategy:
        - Short tracks (< 30s): Analyze full track
        - Medium tracks (30s - 5min): Analyze single 60s segment
        - Long tracks (> 5min): Use chunk-based streaming analysis
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing TensorFlow analysis results with mood analysis
        """
        if not self.is_available():
            return {
                "tensorflow_analysis": {},
                "mood_analysis": {},
                "metadata": {
                    "file_path": file_path,
                    "analysis_timestamp": time.time(),
                    "analyzer": "tensorflow",
                    "error": "TensorFlow analysis not available"
                }
            }
        
        try:
            logger.info(f"Starting TensorFlow analysis for: {file_path}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                return {
                    "tensorflow_analysis": {},
                    "mood_analysis": {},
                    "metadata": {
                        "file_path": file_path,
                        "analysis_timestamp": time.time(),
                        "analyzer": "tensorflow",
                        "error": f"Audio file not found: {file_path}"
                    }
                }
            
            # Get audio duration efficiently
            duration = self._get_audio_duration(file_path)
            if duration is None:
                return {
                    "tensorflow_analysis": {},
                    "mood_analysis": {},
                    "metadata": {
                        "file_path": file_path,
                        "analysis_timestamp": time.time(),
                        "analyzer": "tensorflow",
                        "error": "Failed to get audio duration"
                    }
                }
            
            logger.info(f"Audio duration: {duration:.2f} seconds")
            
            # Determine analysis strategy with aggressive memory optimization
            if duration < 30:
                logger.info(f"Short track ({duration:.1f}s), analyzing full track")
                results = self._analyze_full_track(file_path)
                strategy = "full_track"
            elif duration > 120:  # > 2 minutes - use aggressive streaming
                logger.info(f"Long track ({duration:.1f}s), using aggressive streaming (first 60s only)")
                results = self._analyze_aggressive_streaming(file_path, duration)
                strategy = "aggressive_streaming"
            else:
                logger.info(f"Medium track ({duration:.1f}s), analyzing 60s segment")
                results = self._analyze_segment(file_path, 30, 60)
                strategy = "segment"
            
            # Add metadata
            results["metadata"] = {
                "file_path": file_path,
                "sample_rate": self.config.sample_rate,
                "audio_duration": duration,
                "analysis_timestamp": time.time(),
                "analyzer": "tensorflow",
                "analysis_strategy": strategy,
                "models_used": list(self.models.keys())
            }
            
            logger.info(f"TensorFlow analysis completed for: {file_path}")
            return results
            
        except Exception as e:
            logger.error(f"TensorFlow analysis failed for {file_path}: {e}")
            return {
                "tensorflow_analysis": {},
                "mood_analysis": {},
                "metadata": {
                    "file_path": file_path,
                    "analysis_timestamp": time.time(),
                    "analyzer": "tensorflow",
                    "error": str(e)
                }
            }
    
    def _get_audio_duration(self, file_path: str) -> Optional[float]:
        """Get audio duration efficiently using FFmpeg"""
        try:
            # Try FFmpeg first (most efficient)
            try:
                import ffmpeg
                
                # Use FFmpeg to get duration without loading audio
                probe = ffmpeg.probe(file_path)
                duration = float(probe['format']['duration'])
                logger.debug(f"FFmpeg duration: {duration:.2f}s")
                return duration
                
            except ImportError:
                logger.warning("ffmpeg-python not available, falling back to Essentia")
                pass
            except Exception as e:
                logger.warning(f"FFmpeg duration extraction failed: {e}, falling back to Essentia")
                pass
            
            # Fallback to Essentia
            if ESSENTIA_AVAILABLE:
                # Use Essentia's MonoLoader just for duration
                loader = es.MonoLoader(filename=file_path, sampleRate=self.config.sample_rate)
                audio = loader()
                return len(audio) / self.config.sample_rate
            else:
                # Fallback using soundfile
                import soundfile as sf
                info = sf.info(file_path)
                return info.duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return None
    
    def _analyze_full_track(self, file_path: str) -> Dict[str, Any]:
        """Analyze the full audio track"""
        audio = self._load_audio_streaming(file_path)
        if audio is None:
            return {"error": "Failed to load audio"}
        
        return self._extract_tensorflow_features(audio)
    
    def _analyze_segment(self, file_path: str, start_time: float, duration: float) -> Dict[str, Any]:
        """Analyze a specific segment of the track"""
        audio = self._load_audio_streaming(file_path)
        if audio is None:
            return {"error": "Failed to load audio"}
        
        segment_audio = self._extract_segment(audio, start_time, duration)
        return self._extract_tensorflow_features(segment_audio)
    
    def _analyze_with_streaming(self, file_path: str, duration: float) -> Dict[str, Any]:
        """Analyze long tracks using chunk-based streaming"""
        try:
            logger.info(f"Starting streaming analysis for {duration:.1f}s track")
            
            # Calculate chunk parameters
            chunk_duration = self.config.chunk_duration
            overlap_ratio = self.config.overlap_ratio
            max_chunks = self.config.max_chunks
            
            # Calculate step size (non-overlapping part)
            step_size = chunk_duration * (1 - overlap_ratio)
            
            # Calculate number of chunks
            total_chunks = int((duration - chunk_duration) / step_size) + 1
            chunks_to_process = min(total_chunks, max_chunks)
            
            logger.info(f"Processing {chunks_to_process} chunks of {chunk_duration}s each")
            
            # Process chunks
            chunk_results = []
            for i in range(chunks_to_process):
                start_time = i * step_size
                end_time = min(start_time + chunk_duration, duration)
                
                logger.info(f"Processing chunk {i+1}/{chunks_to_process}: {start_time:.1f}s - {end_time:.1f}s")
                
                # Extract and analyze chunk
                chunk_audio = self._extract_audio_segment(file_path, start_time, end_time - start_time)
                if chunk_audio is not None:
                    chunk_result = self._extract_tensorflow_features(chunk_audio)
                    chunk_result["chunk_metadata"] = {
                        "chunk_index": i,
                        "start_time": start_time,
                        "end_time": end_time,
                        "duration": end_time - start_time
                    }
                    chunk_results.append(chunk_result)
                else:
                    logger.warning(f"Failed to extract chunk {i+1}")
            
            if not chunk_results:
                return {"error": "No chunks processed successfully"}
            
            # Aggregate results from all chunks
            aggregated_results = self._aggregate_chunk_results(chunk_results)
            
            # Add streaming metadata
            aggregated_results["streaming_metadata"] = {
                "chunk_count": len(chunk_results),
                "total_chunks_available": total_chunks,
                "chunk_duration": chunk_duration,
                "overlap_ratio": overlap_ratio,
                "aggregation_method": "average"
            }
            
            logger.info(f"Streaming analysis completed: {len(chunk_results)} chunks processed")
            return aggregated_results
            
        except Exception as e:
            logger.error(f"Streaming analysis failed: {e}")
            return {"error": str(e)}
    
    def _analyze_aggressive_streaming(self, file_path: str, duration: float) -> Dict[str, Any]:
         """Analyze long tracks using aggressive memory optimization (first 60s only)"""
         try:
             logger.info(f"Starting aggressive streaming analysis for {duration:.1f}s track")
             
             # Only analyze the first 60 seconds for very long tracks
             max_analysis_duration = 60.0
             
             # Use smaller chunks for memory efficiency
             chunk_duration = 15.0
             overlap_ratio = 0.2
             max_chunks = 2
             
             # Calculate chunk parameters
             step_size = chunk_duration * (1 - overlap_ratio)
             
             # Calculate number of chunks for first 60s
             total_chunks = int((max_analysis_duration - chunk_duration) / step_size) + 1
             chunks_to_process = min(total_chunks, max_chunks)
             
             logger.info(f"Processing {chunks_to_process} chunks of {chunk_duration}s each (first {max_analysis_duration}s only)")
             
             # Process chunks
             chunk_results = []
             for i in range(chunks_to_process):
                 start_time = i * step_size
                 end_time = min(start_time + chunk_duration, max_analysis_duration)
                 
                 logger.info(f"Processing chunk {i+1}/{chunks_to_process}: {start_time:.1f}s - {end_time:.1f}s")
                 
                 # Extract and analyze chunk
                 chunk_audio = self._extract_audio_segment(file_path, start_time, end_time - start_time)
                 if chunk_audio is not None:
                     chunk_result = self._extract_tensorflow_features(chunk_audio)
                     chunk_result["chunk_metadata"] = {
                         "chunk_index": i,
                         "start_time": start_time,
                         "end_time": end_time,
                         "duration": end_time - start_time
                     }
                     chunk_results.append(chunk_result)
                     
                     # Force garbage collection after each chunk
                     import gc
                     gc.collect()
                 else:
                     logger.warning(f"Failed to extract chunk {i+1}")
             
             if not chunk_results:
                 return {"error": "No chunks processed successfully"}
             
             # Aggregate results from all chunks
             aggregated_results = self._aggregate_chunk_results(chunk_results)
             
             # Add streaming metadata
             aggregated_results["streaming_metadata"] = {
                 "chunk_count": len(chunk_results),
                 "total_chunks_available": total_chunks,
                 "chunk_duration": chunk_duration,
                 "overlap_ratio": overlap_ratio,
                 "aggregation_method": "average",
                 "analysis_duration": max_analysis_duration,
                 "full_track_duration": duration,
                 "strategy": "aggressive_streaming"
             }
             
             logger.info(f"Aggressive streaming analysis completed: {len(chunk_results)} chunks processed")
             return aggregated_results
             
         except Exception as e:
             logger.error(f"Aggressive streaming analysis failed: {e}")
             return {"error": str(e)}
    
    def _extract_audio_segment(self, file_path: str, start_time: float, duration: float) -> Optional[np.ndarray]:
        """Extract a specific audio segment from file using FFmpeg"""
        try:
            # Try FFmpeg first (most efficient)
            try:
                import ffmpeg
                
                # Use FFmpeg to extract segment directly
                stream = ffmpeg.input(file_path, ss=start_time, t=duration)
                stream = ffmpeg.output(stream, 'pipe:', format='f32le', acodec='pcm_f32le', 
                                     ac=1, ar=self.config.sample_rate, loglevel='error')
                
                # Run FFmpeg and get audio data
                out, _ = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, quiet=True)
                
                # Convert bytes to numpy array
                audio = np.frombuffer(out, dtype=np.float32)
                
                logger.debug(f"FFmpeg extracted segment: {len(audio)} samples, {len(audio)/self.config.sample_rate:.2f}s")
                return audio
                
            except ImportError:
                logger.warning("ffmpeg-python not available, falling back to Essentia")
                pass
            except Exception as e:
                logger.warning(f"FFmpeg extraction failed: {e}, falling back to Essentia")
                pass
            
            # Fallback to Essentia
            if ESSENTIA_AVAILABLE:
                # Load full audio and extract segment (Essentia MonoLoader doesn't support start/end time)
                loader = es.MonoLoader(filename=file_path, sampleRate=self.config.sample_rate)
                audio = loader()
                
                start_sample = int(start_time * self.config.sample_rate)
                end_sample = min(start_sample + int(duration * self.config.sample_rate), len(audio))
                segment = audio[start_sample:end_sample]
                
                return segment.astype(np.float32)
            else:
                # Fallback: load full audio and extract segment
                import soundfile as sf
                audio, sr = sf.read(file_path)
                if len(audio.shape) > 1:
                    audio = audio[:, 0]
                
                start_sample = int(start_time * sr)
                end_sample = min(start_sample + int(duration * sr), len(audio))
                segment = audio[start_sample:end_sample]
                
                if sr != self.config.sample_rate:
                    from scipy import signal
                    segment = signal.resample(segment, int(len(segment) * self.config.sample_rate / sr))
                
                return segment.astype(np.float32)
                
        except Exception as e:
            logger.error(f"Failed to extract audio segment: {e}")
            return None
    
    def _aggregate_chunk_results(self, chunk_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple chunks"""
        try:
            aggregated = {
                "tensorflow_analysis": {},
                "mood_analysis": {},
                "genre_analysis": {}
            }
            
            # Group results by model
            model_results = {}
            for chunk_result in chunk_results:
                if "tensorflow_analysis" in chunk_result:
                    for model_name, model_result in chunk_result["tensorflow_analysis"].items():
                        if model_name not in model_results:
                            model_results[model_name] = []
                        model_results[model_name].append(model_result)
            
            # Aggregate each model's results
            for model_name, results_list in model_results.items():
                if model_name == "musicnn":
                    aggregated["tensorflow_analysis"][model_name] = self._aggregate_musicnn_results(results_list)
                else:
                    # For other models, just take the first result
                    aggregated["tensorflow_analysis"][model_name] = results_list[0]
            
            # Aggregate mood analysis (average across chunks)
            mood_results = [r.get("mood_analysis", {}) for r in chunk_results if "mood_analysis" in r]
            if mood_results:
                aggregated["mood_analysis"] = self._aggregate_mood_results(mood_results)
            
            # Aggregate genre analysis (average across chunks)
            genre_results = [r.get("genre_analysis", {}) for r in chunk_results if "genre_analysis" in r]
            if genre_results:
                aggregated["genre_analysis"] = self._aggregate_genre_results(genre_results)
            
            return aggregated
            
        except Exception as e:
            logger.error(f"Failed to aggregate chunk results: {e}")
            return {"error": str(e)}
    
    def _aggregate_musicnn_results(self, results_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate MusicNN results from multiple chunks"""
        try:
            if not results_list:
                return {"error": "No results to aggregate"}
            
            # Collect all predictions
            all_predictions = []
            all_top_predictions = []
            
            for result in results_list:
                if "error" in result:
                    continue
                
                # Look for all_predictions (the correct key from _process_musicnn_predictions)
                if "all_predictions" in result:
                    all_predictions.append(result["all_predictions"])
                
                if "top_predictions" in result:
                    all_top_predictions.extend(result["top_predictions"])
            
            if not all_predictions:
                return {"error": "No valid predictions found"}
            
            # Average predictions across chunks
            avg_predictions = np.mean(all_predictions, axis=0)
            
            # Process averaged predictions
            aggregated_result = self._process_musicnn_predictions(avg_predictions)
            
            # Add aggregation metadata
            aggregated_result["aggregation_metadata"] = {
                "chunks_processed": len(results_list),
                "aggregation_method": "average",
                "original_chunk_count": len(all_predictions)
            }
            
            return aggregated_result
            
        except Exception as e:
            logger.error(f"Failed to aggregate MusicNN results: {e}")
            return {"error": str(e)}
    
    def _aggregate_mood_results(self, mood_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate mood analysis results from multiple chunks"""
        try:
            if not mood_results:
                return {"error": "No mood results to aggregate"}
            
            # Filter out error results
            valid_results = [r for r in mood_results if "error" not in r]
            if not valid_results:
                return {"error": "No valid mood results found"}
            
            # Average emotional dimensions
            emotions_list = [r.get("emotions", {}) for r in valid_results]
            if emotions_list:
                avg_emotions = {}
                for emotion in ["valence", "arousal", "energy_level"]:
                    values = [e.get(emotion, 0) for e in emotions_list if emotion in e]
                    if values:
                        avg_emotions[emotion] = sum(values) / len(values)
                
                # Determine primary mood based on averaged emotions
                primary_mood = self._determine_primary_mood(avg_emotions)
                mood_confidence = self._calculate_mood_confidence(avg_emotions)
                
                return {
                    "emotions": avg_emotions,
                    "primary_mood": primary_mood,
                    "mood_confidence": mood_confidence,
                    "aggregation_metadata": {
                        "chunks_processed": len(valid_results),
                        "aggregation_method": "average"
                    }
                }
            
            return {"error": "No valid emotion data found"}
            
        except Exception as e:
            logger.error(f"Failed to aggregate mood results: {e}")
            return {"error": str(e)}
    
    def _aggregate_genre_results(self, genre_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate genre analysis results from multiple chunks"""
        try:
            if not genre_results:
                return {"error": "No genre results to aggregate"}
            
            # Filter out error results
            valid_results = [r for r in genre_results if "error" not in r]
            if not valid_results:
                return {"error": "No valid genre results found"}
            
            # Average genre scores
            genre_scores = {}
            for result in valid_results:
                if "genre_scores" in result:
                    for genre, score in result["genre_scores"].items():
                        if genre not in genre_scores:
                            genre_scores[genre] = []
                        genre_scores[genre].append(score)
            
            # Calculate average scores
            avg_genre_scores = {}
            for genre, scores in genre_scores.items():
                avg_genre_scores[genre] = sum(scores) / len(scores)
            
            # Find primary genre
            if avg_genre_scores:
                primary_genre = max(avg_genre_scores.items(), key=lambda x: x[1])
                return {
                    "genre_scores": avg_genre_scores,
                    "primary_genre": primary_genre[0],
                    "genre_confidence": primary_genre[1],
                    "aggregation_metadata": {
                        "chunks_processed": len(valid_results),
                        "aggregation_method": "average"
                    }
                }
            
            return {"error": "No valid genre data found"}
            
        except Exception as e:
            logger.error(f"Failed to aggregate genre results: {e}")
            return {"error": str(e)}
    
    def _determine_primary_mood(self, emotions: Dict[str, float]) -> str:
        """Determine primary mood based on averaged emotions"""
        valence = emotions.get("valence", 0.5)
        arousal = emotions.get("arousal", 0.5)
        energy = emotions.get("energy_level", 0.5)
        
        if valence > 0.6 and arousal > 0.6:
            return "happy"
        elif valence > 0.6 and arousal < 0.4:
            return "calm"
        elif valence < 0.4 and arousal > 0.6:
            return "aggressive"
        elif valence < 0.4 and arousal < 0.4:
            return "sad"
        elif energy > 0.6:
            return "energetic"
        else:
            return "neutral"
    
    def _calculate_mood_confidence(self, emotions: Dict[str, float]) -> float:
        """Calculate confidence for primary mood"""
        # Simple confidence based on how far emotions are from neutral (0.5)
        deviations = [abs(v - 0.5) for v in emotions.values()]
        return sum(deviations) / len(deviations) if deviations else 0.0
    
    def _load_audio_streaming(self, file_path: str) -> Optional[np.ndarray]:
        """Load audio using Essentia's streaming MonoLoader"""
        try:
            if ESSENTIA_AVAILABLE:
                # Use Essentia's streaming MonoLoader (same as Essentia analyzer)
                loader = es.MonoLoader(filename=file_path, sampleRate=self.config.sample_rate)
                audio = loader()
                logger.info(f"Audio loaded successfully, length: {len(audio)} samples")
                return audio
            else:
                # Fallback using soundfile
                import soundfile as sf
                audio, sr = sf.read(file_path)
                if len(audio.shape) > 1:
                    audio = audio[:, 0]  # Take first channel
                if sr != self.config.sample_rate:
                    from scipy import signal
                    audio = signal.resample(audio, int(len(audio) * self.config.sample_rate / sr))
                return audio.astype(np.float32)
                
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            return None
    
    def _extract_segment(self, audio: np.ndarray, start_time: float, duration: float) -> np.ndarray:
        """Extract a segment from the audio (same as Essentia)"""
        start_sample = int(start_time * self.config.sample_rate)
        end_sample = min(start_sample + int(duration * self.config.sample_rate), len(audio))
        return audio[start_sample:end_sample]
    
    def _extract_tensorflow_features(self, audio: np.ndarray) -> Dict[str, Any]:
        """
        Extract TensorFlow features using pre-loaded models.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Dictionary of extracted TensorFlow features
        """
        results = {
            "tensorflow_analysis": {},
            "mood_analysis": {}
        }
        
                # Extract features for each model
        for model_name in self.models.keys():
            try:
                model_results = self._analyze_with_model(audio, model_name)
                results["tensorflow_analysis"][model_name] = model_results
                
                # Extract mood analysis from MusicNN results
                if model_name == "musicnn" and self.config.enable_mood_analysis:
                    mood_results = self._extract_mood_analysis(model_results)
                    results["mood_analysis"] = mood_results
                    
                    # Extract genre analysis
                    genre_results = self._extract_genre_analysis(model_results)
                    results["genre_analysis"] = genre_results
                    
            except Exception as e:
                logger.error(f"Analysis with {model_name} failed: {e}")
                results["tensorflow_analysis"][model_name] = {"error": str(e)}
        
        return results
    
    def _analyze_with_model(self, audio: np.ndarray, model_name: str) -> Dict[str, Any]:
        """Analyze audio with a specific TensorFlow model using pre-loaded predictor"""
        if model_name == "musicnn":
            return self._analyze_with_musicnn(audio)
        else:
            return {"error": f"Unknown model: {model_name}"}
    
    def _analyze_with_musicnn(self, audio: np.ndarray) -> Dict[str, Any]:
        """Analyze audio with MusicNN model using pre-loaded predictor"""
        try:
            if self.musicnn_predictor is not None:
                # Use pre-loaded predictor (much faster)
                predictions = self.musicnn_predictor(audio)
                results = self._process_musicnn_predictions(predictions)
                return results
            else:
                # Fallback to loading predictor on demand
                if ESSENTIA_AVAILABLE:
                    from essentia.standard import TensorflowPredictMusiCNN
                    
                    model_path = self.models["musicnn"]
                    predictor = TensorflowPredictMusiCNN(
                        graphFilename=model_path,
                        output="model/Sigmoid:0"
                    )
                    
                    predictions = predictor(audio)
                    results = self._process_musicnn_predictions(predictions)
                    return results
                else:
                    return {"error": "Essentia not available for MusicNN analysis"}
                
        except Exception as e:
            logger.error(f"MusicNN analysis failed: {e}")
            return {"error": str(e)}
    
    def _process_musicnn_predictions(self, predictions: np.ndarray) -> Dict[str, Any]:
        """Process MusicNN model predictions with enhanced analysis"""
        try:
            # Handle both 1D (aggregated) and 2D (raw) predictions
            if predictions.ndim == 2:
                predictions_array = predictions[0]
            else:
                predictions_array = predictions
            
            # Get top predictions
            top_indices = np.argsort(predictions_array)[-15:][::-1]  # Top 15
            top_scores = predictions_array[top_indices]
            
            # Use actual tag names from model config
            top_tags = []
            for idx, score in zip(top_indices, top_scores):
                if idx < len(self.musicnn_tags):
                    tag_name = self.musicnn_tags[idx]
                else:
                    tag_name = f"tag_{idx}"
                
                top_tags.append({
                    "tag": tag_name,
                    "confidence": float(score),
                    "index": int(idx)
                })
            
            # Calculate statistics
            mean_confidence = float(np.mean(predictions_array))
            max_confidence = float(np.max(predictions_array))
            prediction_entropy = float(-np.sum(predictions_array * np.log(predictions_array + 1e-10)))
            
            # Find high-confidence predictions
            high_confidence_threshold = 0.5
            high_confidence_indices = np.where(predictions_array > high_confidence_threshold)[0]
            high_confidence_tags = []
            
            for idx in high_confidence_indices:
                if idx < len(self.musicnn_tags):
                    tag_name = self.musicnn_tags[idx]
                else:
                    tag_name = f"tag_{idx}"
                
                high_confidence_tags.append({
                    "tag": tag_name,
                    "confidence": float(predictions_array[idx]),
                    "index": int(idx)
                })
            
            return {
                "top_predictions": top_tags,
                "high_confidence_predictions": high_confidence_tags,
                "statistics": {
                    "mean_confidence": mean_confidence,
                    "max_confidence": max_confidence,
                    "prediction_entropy": prediction_entropy,
                    "high_confidence_count": len(high_confidence_tags)
                },
                "all_predictions": predictions_array.tolist(),
                "tag_names": self.musicnn_tags
            }
            
        except Exception as e:
            logger.error(f"Failed to process MusicNN predictions: {e}")
            return {"error": str(e)}
    
    def _extract_mood_analysis(self, musicnn_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract mood and emotion analysis from MusicNN predictions"""
        try:
            if "error" in musicnn_results:
                return {"error": musicnn_results["error"]}
            
            # Get comprehensive category mappings
            categories = self._get_musicnn_categories()
            mood_categories = categories["moods"]
            
            # Get predictions
            all_predictions = musicnn_results.get("all_predictions", [])
            tag_names = musicnn_results.get("tag_names", [])
            
            if not all_predictions or not tag_names:
                return {"error": "No predictions available for mood analysis"}
            
            # Calculate mood scores
            mood_scores = {}
            for mood, associated_tags in mood_categories.items():
                score = 0.0
                count = 0
                
                for tag in associated_tags:
                    if tag in tag_names:
                        tag_index = tag_names.index(tag)
                        if tag_index < len(all_predictions):
                            score += all_predictions[tag_index]
                            count += 1
                
                # Average score for this mood
                if count > 0:
                    mood_scores[mood] = score / count
                else:
                    mood_scores[mood] = 0.0
            
            # Find dominant moods
            sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
            dominant_moods = []
            
            for mood, score in sorted_moods:
                if score > self.config.mood_confidence_threshold:
                    dominant_moods.append({
                        "mood": mood,
                        "confidence": float(score)
                    })
            
            # Extract specific emotions
            emotions = {
                "valence": self._calculate_valence(all_predictions, tag_names),
                "arousal": self._calculate_arousal(all_predictions, tag_names),
                "energy_level": self._calculate_energy_level(all_predictions, tag_names)
            }
            
            return {
                "mood_scores": mood_scores,
                "dominant_moods": dominant_moods,
                "emotions": emotions,
                "primary_mood": dominant_moods[0]["mood"] if dominant_moods else "neutral",
                "mood_confidence": dominant_moods[0]["confidence"] if dominant_moods else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to extract mood analysis: {e}")
            return {"error": str(e)}
    
    def _extract_genre_analysis(self, musicnn_results: Dict[str, Any]) -> Dict[str, Any]:
        """Extract genre analysis from MusicNN predictions"""
        try:
            if "error" in musicnn_results:
                return {"error": musicnn_results["error"]}
            
            # Get comprehensive category mappings
            categories = self._get_musicnn_categories()
            genre_categories = categories["genres"]
            
            # Get predictions
            all_predictions = musicnn_results.get("all_predictions", [])
            tag_names = musicnn_results.get("tag_names", [])
            
            if not all_predictions or not tag_names:
                return {"error": "No predictions available for genre analysis"}
            
            # Calculate genre scores
            genre_scores = {}
            for genre, associated_tags in genre_categories.items():
                max_score = 0.0
                found_scores = []
                
                for tag in associated_tags:
                    if tag in tag_names:
                        tag_index = tag_names.index(tag)
                        if tag_index < len(all_predictions):
                            tag_score = all_predictions[tag_index]
                            found_scores.append(tag_score)
                            max_score = max(max_score, tag_score)
                
                # Use maximum score for this genre (more accurate than averaging)
                genre_scores[genre] = max_score
            
            # Find dominant genres
            sorted_genres = sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)
            dominant_genres = []
            
            for genre, score in sorted_genres:
                if score > self.config.mood_confidence_threshold:
                    dominant_genres.append({
                        "genre": genre,
                        "confidence": float(score)
                    })
            
            # Extract era analysis
            era_scores = {}
            era_categories = categories["eras"]
            for era, associated_tags in era_categories.items():
                max_score = 0.0
                
                for tag in associated_tags:
                    if tag in tag_names:
                        tag_index = tag_names.index(tag)
                        if tag_index < len(all_predictions):
                            tag_score = all_predictions[tag_index]
                            max_score = max(max_score, tag_score)
                
                era_scores[era] = max_score
            
            return {
                "genre_scores": genre_scores,
                "dominant_genres": dominant_genres,
                "era_scores": era_scores,
                "primary_genre": dominant_genres[0]["genre"] if dominant_genres else "unknown",
                "genre_confidence": dominant_genres[0]["confidence"] if dominant_genres else 0.0
            }
            
        except Exception as e:
            logger.error(f"Failed to extract genre analysis: {e}")
            return {"error": str(e)}
    
    def _calculate_valence(self, predictions: List[float], tag_names: List[str]) -> float:
        """Calculate valence (positive vs negative emotion)"""
        positive_tags = ["happy", "beautiful", "catchy", "sexy", "party"]
        negative_tags = ["sad", "aggressive", "dark"]
        
        positive_score = 0.0
        negative_score = 0.0
        
        for tag in positive_tags:
            if tag in tag_names:
                idx = tag_names.index(tag)
                if idx < len(predictions):
                    positive_score += predictions[idx]
        
        for tag in negative_tags:
            if tag in tag_names:
                idx = tag_names.index(tag)
                if idx < len(predictions):
                    negative_score += predictions[idx]
        
        # Normalize to -1 to 1 range
        total = positive_score + negative_score
        if total > 0:
            return (positive_score - negative_score) / total
        return 0.0
    
    def _calculate_arousal(self, predictions: List[float], tag_names: List[str]) -> float:
        """Calculate arousal (high vs low energy)"""
        high_energy_tags = ["dance", "rock", "metal", "party", "catchy", "energetic"]
        low_energy_tags = ["chill", "chillout", "ambient", "Mellow", "easy listening"]
        
        high_score = 0.0
        low_score = 0.0
        
        for tag in high_energy_tags:
            if tag in tag_names:
                idx = tag_names.index(tag)
                if idx < len(predictions):
                    high_score += predictions[idx]
        
        for tag in low_energy_tags:
            if tag in tag_names:
                idx = tag_names.index(tag)
                if idx < len(predictions):
                    low_score += predictions[idx]
        
        # Normalize to 0 to 1 range
        total = high_score + low_score
        if total > 0:
            return high_score / total
        return 0.5
    
    def _calculate_energy_level(self, predictions: List[float], tag_names: List[str]) -> float:
        """Calculate overall energy level"""
        energy_tags = ["dance", "rock", "metal", "party", "catchy", "energetic", "fast"]
        calm_tags = ["chill", "chillout", "ambient", "Mellow", "slow"]
        
        energy_score = 0.0
        calm_score = 0.0
        
        for tag in energy_tags:
            if tag in tag_names:
                idx = tag_names.index(tag)
                if idx < len(predictions):
                    energy_score += predictions[idx]
        
        for tag in calm_tags:
            if tag in tag_names:
                idx = tag_names.index(tag)
                if idx < len(predictions):
                    calm_score += predictions[idx]
        
        # Normalize to 0 to 1 range
        total = energy_score + calm_score
        if total > 0:
            return energy_score / total
        return 0.5

# Global instance
tensorflow_analyzer = TensorFlowAnalyzer()
