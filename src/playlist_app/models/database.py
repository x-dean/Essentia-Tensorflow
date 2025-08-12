from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, BigInteger, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import hashlib
import os
import enum

Base = declarative_base()

class FileStatus(enum.Enum):
    """File processing status enumeration"""
    DISCOVERED = "discovered"
    HAS_METADATA = "has_metadata"
    ANALYZED = "analyzed"
    FAISS_ANALYZED = "faiss_analyzed"
    FAILED = "failed"

class File(Base):
    """Model for discovered audio files"""
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String, unique=True, index=True, nullable=False)
    file_extension = Column(String, nullable=False)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    last_modified = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(FileStatus), default=FileStatus.DISCOVERED, index=True)
    is_analyzed = Column(Boolean, default=False)
    has_metadata = Column(Boolean, default=False)
    has_audio_analysis = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    audio_metadata = relationship("AudioMetadata", back_populates="file", uselist=False)
    audio_analysis = relationship("AudioAnalysis", back_populates="file", uselist=False)
    vector_index = relationship("VectorIndex", back_populates="file", uselist=False)
    
    def __repr__(self):
        return f"<File(id={self.id}, name='{self.file_name}', path='{self.file_path}')>"

class DiscoveryCache(Base):
    """Cache for discovery process to avoid recalculating hashes"""
    __tablename__ = "discovery_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    file_size = Column(Integer, nullable=False)
    file_hash = Column(String, nullable=False)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<DiscoveryCache(path='{self.file_path}', hash='{self.file_hash}')>"

class AudioMetadata(Base):
    """Audio metadata extracted from files"""
    __tablename__ = "audio_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    
    # Core playlist fields
    title = Column(String, index=True)
    artist = Column(String, index=True)
    album = Column(String, index=True)
    track_number = Column(Integer, index=True)
    year = Column(Integer, index=True)
    genre = Column(String, index=True)
    
    # Secondary playlist fields
    album_artist = Column(String, index=True)
    disc_number = Column(Integer, index=True)
    composer = Column(String, index=True)
    duration = Column(Float, index=True)
    bpm = Column(Float, index=True)
    key = Column(String, index=True)
    
    # Additional fields
    comment = Column(Text)
    mood = Column(String, index=True)
    rating = Column(Integer, index=True)
    isrc = Column(String, index=True)
    encoder = Column(String)
    
    # Technical info
    bitrate = Column(Integer)
    sample_rate = Column(Integer)
    channels = Column(Integer)
    format = Column(String)
    file_size = Column(BigInteger)
    file_format = Column(String)
    
    # ReplayGain (for volume normalization)
    replaygain_track_gain = Column(Float)
    replaygain_album_gain = Column(Float)
    replaygain_track_peak = Column(Float)
    replaygain_album_peak = Column(Float)
    
    # MusicBrainz IDs
    musicbrainz_track_id = Column(String, index=True)
    musicbrainz_artist_id = Column(String, index=True)
    musicbrainz_album_id = Column(String, index=True)
    musicbrainz_album_artist_id = Column(String, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="audio_metadata")
    
    def __repr__(self):
        return f"<AudioMetadata(file_id={self.file_id}, title='{self.title}', artist='{self.artist}')>"

class AudioAnalysis(Base):
    """Audio analysis results from Essentia"""
    __tablename__ = "audio_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)  # Time taken for analysis in seconds
    sample_rate = Column(Integer)
    duration = Column(Float)
    
    # Basic features
    rms = Column(Float)
    energy = Column(Float)
    loudness = Column(Float)
    duration = Column(Float)
    
    # Note: Advanced spectral features are stored in complete_analysis JSON
    # spectral_centroid_mean, spectral_centroid_std
    # spectral_rolloff_mean, spectral_rolloff_std
    # spectral_contrast_mean, spectral_contrast_std
    # spectral_complexity_mean, spectral_complexity_std
    # mfcc_mean, mfcc_bands_mean
    
    # Rhythm features
    tempo = Column(Float)
    tempo_confidence = Column(Float)
    tempo_methods_used = Column(Integer)  # Number of tempo estimation methods used
    
    # Note: Advanced rhythm features are stored in complete_analysis JSON
    # beats, rhythm_ticks, rhythm_estimates, onset_detections
    
    # Harmonic features
    key = Column(String)
    scale = Column(String)
    key_strength = Column(Float)
    dominant_chroma = Column(String)  # Dominant chroma (C, C#, D, etc.)
    dominant_chroma_strength = Column(Float)  # Strength of dominant chroma
    
    # Note: Advanced harmonic features are stored in complete_analysis JSON
    # chords, chord_strengths, pitch_yin, pitch_yin_confidence
    # pitch_melodia, pitch_melodia_confidence, chromagram
    
    # TensorFlow features (stored as JSON)
    tensorflow_features = Column(Text)  # JSON object with model outputs
    
    # Complete analysis results (for detailed access)
    complete_analysis = Column(Text)  # JSON object with all analysis data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="audio_analysis")
    
    def __repr__(self):
        return f"<AudioAnalysis(file_id={self.file_id}, duration={self.duration}, tempo={self.tempo})>"

class VectorIndex(Base):
    """FAISS vector index metadata and track mappings"""
    __tablename__ = "vector_index"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    
    # Vector information
    vector_dimension = Column(Integer, nullable=False)
    vector_data = Column(Text)  # JSON array of feature vector values
    vector_hash = Column(String, index=True)  # Hash of vector for change detection
    
    # Index metadata
    index_type = Column(String)  # Type of FAISS index used
    index_position = Column(Integer)  # Position in the FAISS index
    similarity_score = Column(Float)  # Last computed similarity score
    
    # Feature flags
    includes_tensorflow = Column(Boolean, default=True)
    is_normalized = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="vector_index")
    
    def __repr__(self):
        return f"<VectorIndex(file_id={self.file_id}, dimension={self.vector_dimension}, index_type='{self.index_type}')>"

class FAISSIndexMetadata(Base):
    """Global FAISS index metadata"""
    __tablename__ = "faiss_index_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Index configuration
    index_name = Column(String, unique=True, index=True, nullable=False)
    index_type = Column(String, nullable=False)  # IndexFlatIP, IndexIVFFlat, IndexIVFPQ
    vector_dimension = Column(Integer, nullable=False)
    total_vectors = Column(Integer, default=0)
    
    # Index parameters
    nlist = Column(Integer)  # Number of clusters for IVF indexes
    m = Column(Integer)  # Number of sub-vectors for PQ indexes
    bits = Column(Integer)  # Bits per sub-vector for PQ indexes
    
    # File paths
    index_file_path = Column(String)  # Path to .faiss file
    metadata_file_path = Column(String)  # Path to .json metadata file
    
    # Performance metrics
    build_time = Column(Float)  # Time taken to build index
    search_time_avg = Column(Float)  # Average search time
    memory_usage_mb = Column(Float)  # Memory usage in MB
    
    # Status
    is_active = Column(Boolean, default=True)
    last_rebuild = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<FAISSIndexMetadata(name='{self.index_name}', type='{self.index_type}', vectors={self.total_vectors})>"

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
