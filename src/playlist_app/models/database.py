from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, BigInteger, ForeignKey, Enum, JSON, ARRAY, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
import hashlib
import os
import enum

Base = declarative_base()

# === ENUMERATIONS ===

class FileStatus(enum.Enum):
    """File processing status enumeration"""
    DISCOVERED = "discovered"
    HAS_METADATA = "has_metadata"
    FAILED = "failed"

class AnalyzerStatus(enum.Enum):
    """Analyzer status enumeration"""
    PENDING = "pending"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"
    RETRY = "retry"

# === DATABASE CONFIGURATION ===

# Database URL from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/playlist_db")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    connect_args={"options": "-c search_path=core,analysis,playlists,recommendations,ui,public"}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        # Set the search path to include all schemas
        db.execute(text("SET search_path TO core, analysis, playlists, recommendations, ui, public"))
        yield db
    finally:
        db.close()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

# === CORE TABLES ===

class File(Base):
    """Core files table for playlist generation"""
    __tablename__ = "files"
    __table_args__ = {'schema': 'core'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(BigInteger)
    file_extension = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Playlist generation fields
    is_favorite = Column(Boolean, default=False)
    rating = Column(Integer)  # 1-5 stars for playlist generation
    tags = Column(ARRAY(String), default=[])
    notes = Column(Text)
    is_hidden = Column(Boolean, default=False)
    custom_metadata = Column(JSON, default={})
    
    # Discovery and processing fields
    file_hash = Column(String, index=True)  # For duplicate detection
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime)
    status = Column(Enum(FileStatus), default=FileStatus.DISCOVERED)
    has_metadata = Column(Boolean, default=False)

class DiscoveryCache(Base):
    """Cache for file discovery to avoid re-scanning unchanged files"""
    __tablename__ = "discovery_cache"
    __table_args__ = {'schema': 'core'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String, nullable=False)
    last_checked = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class AudioMetadata(Base):
    """Audio metadata for playlist generation - essential fields only"""
    __tablename__ = "audio_metadata"
    __table_args__ = {'schema': 'core'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), unique=True, nullable=False)
    
    # Essential metadata for playlist generation
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    album_artist = Column(String)
    year = Column(Integer)
    genre = Column(String)
    duration = Column(Float)
    bpm = Column(Float)
    key = Column(String)
    
    # Technical metadata needed for analysis
    bitrate = Column(Integer)
    sample_rate = Column(Integer)
    channels = Column(Integer)
    file_format = Column(String)
    
    # Additional metadata for smart playlist generation
    mood = Column(String)  # Basic mood from tags
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class TrackAnalysisSummary(Base):
    """Musical analysis for smart playlist generation"""
    __tablename__ = "track_analysis_summary"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), unique=True, nullable=False)
    
    # Essentia analysis results (Audio Analysis)
    bpm = Column(Float)  # Tempo in BPM from audio analysis
    key = Column(String)  # Musical key (C, D, E, etc.) from audio analysis
    scale = Column(String)  # Major or minor scale from audio analysis
    energy = Column(Float)  # Energy level (0-1) from audio analysis
    danceability = Column(Float)  # Danceability score (0-1) from audio analysis
    
    # Additional Essentia features for playlist generation
    loudness = Column(Float)  # For volume normalization
    dynamic_complexity = Column(Float)  # For energy variation
    rhythm_confidence = Column(Float)  # For BPM reliability
    key_strength = Column(Float)  # For harmonic mixing confidence
    
    # TensorFlow analysis results (ML Predictions)
    tensorflow_valence = Column(Float)  # Positivity/negativity from mood analysis
    tensorflow_acousticness = Column(Float)  # Acoustic vs electronic from mood analysis
    tensorflow_instrumentalness = Column(Float)  # Instrumental vs vocal from mood analysis
    tensorflow_speechiness = Column(Float)  # Speech vs music (inverse of instrumentalness)
    tensorflow_liveness = Column(Float)  # Live vs studio from mood analysis
    
    # Analysis metadata
    analysis_status = Column(String, default="pending")
    analysis_date = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)
    analysis_errors = Column(Text)
    
    # Quality control for playlist generation
    analysis_quality_score = Column(Float)
    confidence_threshold = Column(Float, default=0.7)
    manual_override = Column(Boolean, default=False)
    override_reason = Column(Text)

class EssentiaAnalysisStatus(Base):
    """Essentia analyzer status tracking"""
    __tablename__ = "essentia_analysis_status"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TensorFlowAnalysisStatus(Base):
    """TensorFlow analyzer status tracking"""
    __tablename__ = "tensorflow_analysis_status"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FAISSAnalysisStatus(Base):
    """FAISS analyzer status tracking"""
    __tablename__ = "faiss_analysis_status"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TensorFlowAnalysisResults(Base):
    """Detailed TensorFlow/MusicNN analysis results"""
    __tablename__ = "tensorflow_analysis_results"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), unique=True, nullable=False)
    
    # MusicNN predictions
    top_predictions = Column(JSON)  # Top 15 predictions with scores
    all_predictions = Column(JSON)  # Full 50-dimensional prediction vector
    prediction_statistics = Column(JSON)  # Mean, max, entropy
    
    # Genre analysis
    genre_scores = Column(JSON)  # Scores for each genre
    dominant_genres = Column(JSON)  # Top genres with confidence
    
    # Mood analysis
    mood_scores = Column(JSON)  # Scores for all mood categories
    dominant_moods = Column(JSON)  # Top moods with confidence
    emotion_dimensions = Column(JSON)  # Valence, arousal, energy
    
    # Analysis metadata
    model_used = Column(String, default="MusicNN")
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)

class EssentiaAnalysisResults(Base):
    """Detailed Essentia analysis results"""
    __tablename__ = "essentia_analysis_results"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), unique=True, nullable=False)
    
    # Rhythm analysis
    bpm = Column(Float)
    rhythm_confidence = Column(Float)
    beat_loudness = Column(Float)
    beat_loudness_band_ratio = Column(JSON)  # Array of band ratios
    
    # Harmonic analysis
    key = Column(String)
    scale = Column(String)
    key_strength = Column(Float)
    key_scale_strength = Column(Float)
    hpcp = Column(JSON)  # Harmonic Profile Chroma
    
    # Spectral analysis
    spectral_centroid = Column(Float)
    spectral_rolloff = Column(Float)
    spectral_bandwidth = Column(Float)
    spectral_contrast = Column(JSON)
    spectral_peaks = Column(JSON)
    
    # Basic features
    energy = Column(Float)
    loudness = Column(Float)
    dynamic_complexity = Column(Float)
    zero_crossing_rate = Column(Float)
    
    # Danceability
    danceability = Column(Float)
    rhythm_strength = Column(Float)
    rhythm_regularity = Column(Float)
    
    # MFCC features
    mfcc = Column(JSON)  # 13-dimensional MFCC vector
    
    # Analysis metadata
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)
    analysis_version = Column(String, default="2.1")

class FAISSAnalysisResults(Base):
    """Detailed FAISS vector analysis results"""
    __tablename__ = "faiss_analysis_results"
    __table_args__ = {'schema': 'analysis'}
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("core.files.id"), unique=True, nullable=False)
    
    # Vector data
    vector_data = Column(JSON)  # Full feature vector as JSON array
    vector_dimension = Column(Integer)
    vector_hash = Column(String)  # MD5 hash for change detection
    
    # Index information
    index_type = Column(String, default="IndexFlatIP")
    index_position = Column(Integer)  # Position in FAISS index
    similarity_score = Column(Float)  # Score from similarity search
    
    # Analysis configuration
    includes_tensorflow = Column(Boolean, default=True)
    is_normalized = Column(Boolean, default=True)
    feature_weights = Column(JSON)  # Weights used for feature combination
    
    # Analysis metadata
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)
    analysis_version = Column(String, default="1.0")

# === PLAYLIST GENERATION TABLES ===

class Playlist(Base):
    """Generated playlists"""
    __tablename__ = "playlists"
    __table_args__ = {'schema': 'playlists'}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=True)
    cover_image_url = Column(String)
    
    # Playlist statistics
    total_duration = Column(Integer, default=0)  # in seconds
    track_count = Column(Integer, default=0)
    rating_avg = Column(Float, default=0.0)
    
    # Generation metadata
    generation_type = Column(String)  # "manual", "template", "smart", "similarity"
    generation_parameters = Column(JSON, default={})
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class PlaylistTrack(Base):
    """Tracks within generated playlists"""
    __tablename__ = "playlist_tracks"
    __table_args__ = {'schema': 'playlists'}
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.playlists.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    position = Column(Integer, nullable=False)
    
    # Track-specific data for playlist generation
    notes = Column(Text)
    rating = Column(Integer)  # 1-5 stars
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Generation metadata
    selection_reason = Column(String)  # "manual", "template_match", "similarity", "recommendation"
    selection_score = Column(Float)  # Confidence score for why this track was selected

class PlaylistTemplate(Base):
    """Templates for generating playlists"""
    __tablename__ = "playlist_templates"
    __table_args__ = {'schema': 'playlists'}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    template_type = Column(String, nullable=False)  # energy, mood, genre, custom
    parameters = Column(JSON, nullable=False)  # Template parameters
    is_system_template = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class GeneratedPlaylist(Base):
    """Tracking of generated playlists for analysis and improvement"""
    __tablename__ = "generated_playlists"
    __table_args__ = {'schema': 'playlists'}
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.playlists.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("playlists.playlist_templates.id"), nullable=False)
    generation_parameters = Column(JSON, nullable=False)
    generation_date = Column(DateTime, default=datetime.utcnow)
    generation_duration = Column(Float)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Generation quality metrics
    quality_score = Column(Float)  # How well the generation matched criteria
    user_feedback = Column(Integer)  # 1-5 rating from user
    regeneration_count = Column(Integer, default=0)  # How many times regenerated

class TrackSimilarityCache(Base):
    """Cached similarity scores for smart playlist generation"""
    __tablename__ = "track_similarity_cache"
    __table_args__ = {'schema': 'recommendations'}
    
    id = Column(Integer, primary_key=True, index=True)
    source_file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    target_file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    similarity_score = Column(Float, nullable=False)
    similarity_type = Column(String, nullable=False)  # essentia, tensorflow, combined
    created_at = Column(DateTime, default=datetime.utcnow)

class PlaylistRecommendation(Base):
    """Track recommendations for playlist generation"""
    __tablename__ = "playlist_recommendations"
    __table_args__ = {'schema': 'recommendations'}
    
    id = Column(Integer, primary_key=True, index=True)
    playlist_id = Column(Integer, ForeignKey("playlists.playlists.id"), nullable=False)
    recommended_file_id = Column(Integer, ForeignKey("core.files.id"), nullable=False)
    recommendation_score = Column(Float, nullable=False)
    recommendation_reason = Column(String)  # "similar_to_track_1", "fits_energy_profile", etc.
    recommendation_type = Column(String)  # "similarity", "template_match", "collaborative"
    created_at = Column(DateTime, default=datetime.utcnow)

class FAISSIndexMetadata(Base):
    """FAISS index metadata and configuration"""
    __tablename__ = "faiss_index_metadata"
    __table_args__ = {'schema': 'recommendations'}
    
    id = Column(Integer, primary_key=True, index=True)
    index_name = Column(String, unique=True, nullable=False)
    index_type = Column(String, nullable=False)  # "ivf", "hnsw", "flat", etc.
    dimension = Column(Integer, nullable=False)
    total_vectors = Column(Integer, default=0)
    is_trained = Column(Boolean, default=False)
    training_vectors = Column(Integer, default=0)
    index_size_bytes = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# === UI STATE AND PREFERENCES ===

class UIState(Base):
    """UI state persistence for playlist generation workflow"""
    __tablename__ = "ui_state"
    __table_args__ = {'schema': 'ui'}
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, nullable=False)
    state_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AppPreference(Base):
    """Application preferences for playlist generation"""
    __tablename__ = "app_preferences"
    __table_args__ = {'schema': 'ui'}
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
# === RELATIONSHIPS ===

# File relationships
File.metadata = relationship("AudioMetadata", back_populates="file", uselist=False)
File.analysis_summary = relationship("TrackAnalysisSummary", back_populates="file", uselist=False)
File.playlist_tracks = relationship("PlaylistTrack", back_populates="file")
File.similarity_source = relationship("TrackSimilarityCache", foreign_keys="TrackSimilarityCache.source_file_id")
File.similarity_target = relationship("TrackSimilarityCache", foreign_keys="TrackSimilarityCache.target_file_id")
File.recommendations = relationship("PlaylistRecommendation", back_populates="recommended_file")
File.essentia_status = relationship("EssentiaAnalysisStatus", back_populates="file", uselist=False)
File.tensorflow_status = relationship("TensorFlowAnalysisStatus", back_populates="file", uselist=False)
File.faiss_status = relationship("FAISSAnalysisStatus", back_populates="file", uselist=False)

# AudioMetadata relationships
AudioMetadata.file = relationship("File", back_populates="metadata")

# TrackAnalysisSummary relationships
TrackAnalysisSummary.file = relationship("File", back_populates="analysis_summary")

# Analyzer status relationships
EssentiaAnalysisStatus.file = relationship("File", back_populates="essentia_status")
TensorFlowAnalysisStatus.file = relationship("File", back_populates="tensorflow_status")
FAISSAnalysisStatus.file = relationship("File", back_populates="faiss_status")

# Playlist relationships
Playlist.tracks = relationship("PlaylistTrack", back_populates="playlist", order_by="PlaylistTrack.position")
Playlist.generated_playlists = relationship("GeneratedPlaylist", back_populates="playlist")
Playlist.recommendations = relationship("PlaylistRecommendation", back_populates="playlist")

# PlaylistTrack relationships
PlaylistTrack.playlist = relationship("Playlist", back_populates="tracks")
PlaylistTrack.file = relationship("File", back_populates="playlist_tracks")

# PlaylistTemplate relationships
PlaylistTemplate.generated_playlists = relationship("GeneratedPlaylist", back_populates="template")

# GeneratedPlaylist relationships
GeneratedPlaylist.playlist = relationship("Playlist", back_populates="generated_playlists")
GeneratedPlaylist.template = relationship("PlaylistTemplate", back_populates="generated_playlists")

# TrackSimilarityCache relationships
TrackSimilarityCache.source_file = relationship("File", foreign_keys="TrackSimilarityCache.source_file_id")
TrackSimilarityCache.target_file = relationship("File", foreign_keys="TrackSimilarityCache.target_file_id")

# PlaylistRecommendation relationships
PlaylistRecommendation.playlist = relationship("Playlist", back_populates="recommendations")
PlaylistRecommendation.recommended_file = relationship("File", back_populates="recommendations")
