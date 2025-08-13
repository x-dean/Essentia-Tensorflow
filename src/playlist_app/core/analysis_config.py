"""
Analysis Configuration Management

This module provides configuration management for the audio analysis system,
allowing dynamic configuration of Essentia parameters, performance settings,
and analysis strategies.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class AudioProcessingConfig:
    """Audio processing configuration"""
    sample_rate: int = 44100
    channels: int = 1
    frame_size: int = 2048
    hop_size: int = 1024
    window_type: str = "hann"
    zero_padding: int = 0

@dataclass
class SpectralAnalysisConfig:
    """Spectral analysis configuration"""
    min_frequency: float = 20.0
    max_frequency: float = 8000.0
    n_mels: int = 96
    n_mfcc: int = 40
    n_spectral_peaks: int = 100
    silence_threshold: float = -60.0

@dataclass
class TrackAnalysisConfig:
    """Track analysis configuration"""
    min_track_length: float = 1.0
    max_track_length: float = 600.0
    chunk_duration: float = 30.0
    overlap_ratio: float = 0.5

@dataclass
class AlgorithmConfig:
    """Algorithm enable/disable configuration"""
    enable_tensorflow: bool = False
    enable_faiss: bool = True
    enable_complex_rhythm: bool = False
    enable_complex_harmonic: bool = False
    enable_beat_tracking: bool = False
    enable_tempo_tap: bool = False
    enable_rhythm_extractor: bool = False
    enable_pitch_analysis: bool = False
    enable_chord_detection: bool = False

@dataclass
class ParallelProcessingConfig:
    """Parallel processing configuration"""
    max_workers: int = 4
    chunk_size: int = 10
    timeout_per_file: int = 300
    memory_limit_mb: int = 512

@dataclass
class CachingConfig:
    """Caching configuration"""
    enable_cache: bool = True
    cache_duration_hours: int = 24
    max_cache_size_mb: int = 1024

@dataclass
class OptimizationConfig:
    """Optimization configuration"""
    use_ffmpeg_streaming: bool = True
    smart_segmentation: bool = True
    skip_existing_analysis: bool = True
    batch_size: int = 50

@dataclass
class AnalysisStrategyConfig:
    """Analysis strategy configuration"""
    max_duration: float = 300.0
    strategy: str = "key_segments"
    segments: List[str] = field(default_factory=lambda: ["beginning", "middle", "end"])
    segment_duration: int = 30

@dataclass
class OutputConfig:
    """Output configuration"""
    store_individual_columns: bool = True
    store_complete_json: bool = True
    compress_json: bool = False
    include_segment_details: bool = True
    include_processing_metadata: bool = True

@dataclass
class QualityConfig:
    """Quality and error handling configuration"""
    min_confidence_threshold: float = 0.3
    fallback_values: Dict[str, Any] = field(default_factory=lambda: {
        "tempo": 120.0,
        "key": "C",
        "scale": "major",
        "key_strength": 0.0
    })
    continue_on_error: bool = True
    log_errors: bool = True
    retry_failed: bool = False
    max_retries: int = 3

@dataclass
class AnalysisConfig:
    """Complete analysis configuration"""
    audio_processing: AudioProcessingConfig = field(default_factory=AudioProcessingConfig)
    spectral_analysis: SpectralAnalysisConfig = field(default_factory=SpectralAnalysisConfig)
    track_analysis: TrackAnalysisConfig = field(default_factory=TrackAnalysisConfig)
    algorithms: AlgorithmConfig = field(default_factory=AlgorithmConfig)
    parallel_processing: ParallelProcessingConfig = field(default_factory=ParallelProcessingConfig)
    caching: CachingConfig = field(default_factory=CachingConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    analysis_strategies: Dict[str, AnalysisStrategyConfig] = field(default_factory=dict)
    output: OutputConfig = field(default_factory=OutputConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)

class AnalysisConfigLoader:
    """Configuration loader for analysis settings"""
    
    def __init__(self, config_path: Optional[str] = None):
        # Use relative path from project root, fallback to absolute path
        if config_path is None:
            # Try multiple possible config locations
            possible_paths = [
                "config/analysis_config.json",
                "/app/config/analysis_config.json",
                "src/playlist_app/config/analysis_config.json"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    config_path = path
                    break
            else:
                config_path = "config/analysis_config.json"  # Default fallback
        
        self.config_path = config_path
        self._config: Optional[AnalysisConfig] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from file or use defaults"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                self._config = self._parse_config(config_data)
                logger.info(f"Loaded analysis configuration from {self.config_path}")
            else:
                self._config = self._get_default_config()
                logger.info("Using default analysis configuration")
        except Exception as e:
            logger.warning(f"Failed to load analysis config: {e}, using defaults")
            self._config = self._get_default_config()
    
    def _parse_config(self, config_data: Dict[str, Any]) -> AnalysisConfig:
        """Parse configuration dictionary into dataclass"""
        try:
            # Parse audio processing
            audio_processing = AudioProcessingConfig(**config_data.get("essentia", {}).get("audio_processing", {}))
            
            # Parse spectral analysis
            spectral_analysis = SpectralAnalysisConfig(**config_data.get("essentia", {}).get("spectral_analysis", {}))
            
            # Parse track analysis
            track_analysis = TrackAnalysisConfig(**config_data.get("essentia", {}).get("track_analysis", {}))
            
            # Parse algorithms
            algorithms = AlgorithmConfig(**config_data.get("essentia", {}).get("algorithms", {}))
            
            # Parse parallel processing
            parallel_processing = ParallelProcessingConfig(**config_data.get("performance", {}).get("parallel_processing", {}))
            
            # Parse caching
            caching = CachingConfig(**config_data.get("performance", {}).get("caching", {}))
            
            # Parse optimization
            optimization = OptimizationConfig(**config_data.get("performance", {}).get("optimization", {}))
            
            # Parse analysis strategies
            strategies_data = config_data.get("analysis_strategies", {})
            analysis_strategies = {}
            for strategy_name, strategy_data in strategies_data.items():
                analysis_strategies[strategy_name] = AnalysisStrategyConfig(**strategy_data)
            
            # Parse output
            output = OutputConfig(**config_data.get("output", {}))
            
            # Parse quality
            quality_data = config_data.get("quality", {})
            fallback_values = quality_data.get("fallback_values", {})
            error_handling = quality_data.get("error_handling", {})
            quality = QualityConfig(
                min_confidence_threshold=quality_data.get("min_confidence_threshold", 0.3),
                fallback_values=fallback_values,
                continue_on_error=error_handling.get("continue_on_error", True),
                log_errors=error_handling.get("log_errors", True),
                retry_failed=error_handling.get("retry_failed", False),
                max_retries=error_handling.get("max_retries", 3)
            )
            
            return AnalysisConfig(
                audio_processing=audio_processing,
                spectral_analysis=spectral_analysis,
                track_analysis=track_analysis,
                algorithms=algorithms,
                parallel_processing=parallel_processing,
                caching=caching,
                optimization=optimization,
                analysis_strategies=analysis_strategies,
                output=output,
                quality=quality
            )
            
        except Exception as e:
            logger.error(f"Failed to parse analysis config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> AnalysisConfig:
        """Get default configuration"""
        return AnalysisConfig(
            analysis_strategies={
                "short_tracks": AnalysisStrategyConfig(
                    max_duration=300.0,
                    strategy="key_segments",
                    segments=["beginning", "middle", "end"],
                    segment_duration=30
                ),
                "medium_tracks": AnalysisStrategyConfig(
                    max_duration=600.0,
                    strategy="three_point",
                    segments=["beginning", "quarter", "middle", "three_quarter", "end"],
                    segment_duration=30
                ),
                "long_tracks": AnalysisStrategyConfig(
                    max_duration=3600.0,
                    strategy="strategic_points",
                    segments=["beginning", "20_percent", "40_percent", "60_percent", "80_percent", "end"],
                    segment_duration=30
                )
            }
        )
    
    def get_config(self) -> AnalysisConfig:
        """Get current configuration"""
        logger.info(f"Getting config, type: {type(self._config)}")
        return self._config
    
    def reload_config(self):
        """Reload configuration from file"""
        self._load_config()
    
    def get_strategy_for_duration(self, duration: float) -> AnalysisStrategyConfig:
        """Get analysis strategy based on track duration"""
        for strategy_name, strategy_config in self._config.analysis_strategies.items():
            if duration <= strategy_config.max_duration:
                return strategy_config
        
        # Default to long tracks strategy
        return self._config.analysis_strategies.get("long_tracks", 
            AnalysisStrategyConfig(max_duration=3600.0, strategy="strategic_points"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        try:
            logger.info(f"Converting config to dict, config type: {type(self._config)}")
            logger.info(f"Config attributes: {dir(self._config)}")
            
            return {
                "essentia": {
                    "audio_processing": self._config.audio_processing.__dict__,
                    "spectral_analysis": self._config.spectral_analysis.__dict__,
                    "track_analysis": self._config.track_analysis.__dict__,
                    "algorithms": self._config.algorithms.__dict__
                },
                "performance": {
                    "parallel_processing": self._config.parallel_processing.__dict__,
                    "caching": self._config.caching.__dict__,
                    "optimization": self._config.optimization.__dict__
                },
                "analysis_strategies": {
                    name: strategy.__dict__ for name, strategy in self._config.analysis_strategies.items()
                },
                "output": self._config.output.__dict__,
                "quality": {
                    "min_confidence_threshold": self._config.quality.min_confidence_threshold,
                    "fallback_values": self._config.quality.fallback_values,
                    "error_handling": {
                        "continue_on_error": self._config.quality.continue_on_error,
                        "log_errors": self._config.quality.log_errors,
                        "retry_failed": self._config.quality.retry_failed,
                        "max_retries": self._config.quality.max_retries
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error in to_dict: {e}")
            raise
    
    def save_config(self, config: AnalysisConfig = None):
        """Save configuration to file"""
        try:
            if config is not None:
                self._config = config
            
            logger.info(f"About to save config, config type: {type(self._config)}")
            logger.info(f"Config attributes: {dir(self._config)}")
            
            # Ensure config directory exists
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir, exist_ok=True)
            
            # Convert to dictionary and save
            config_dict = self.to_dict()
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"Analysis configuration saved to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save analysis configuration: {e}")
            return False

# Global configuration instance
analysis_config_loader = AnalysisConfigLoader()
