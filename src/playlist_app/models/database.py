from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, BigInteger, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from datetime import datetime
import hashlib
import os
import enum

Base = declarative_base()

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
    has_metadata = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    audio_metadata = relationship("AudioMetadata", back_populates="file", uselist=False)
    essentia_status = relationship("EssentiaAnalysisStatus", back_populates="file", uselist=False)
    tensorflow_status = relationship("TensorFlowAnalysisStatus", back_populates="file", uselist=False)
    faiss_status = relationship("FAISSAnalysisStatus", back_populates="file", uselist=False)
    track_summary = relationship("TrackAnalysisSummary", back_populates="file", uselist=False)
    
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

# === INDEPENDENT ANALYZER STATUS TABLES ===

class EssentiaAnalysisStatus(Base):
    """Essentia analyzer status tracking"""
    __tablename__ = "essentia_analysis_status"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="essentia_status")
    results = relationship("EssentiaAnalysisResults", back_populates="status", uselist=False)
    
    def __repr__(self):
        return f"<EssentiaAnalysisStatus(file_id={self.file_id}, status='{self.status}')>"

class TensorFlowAnalysisStatus(Base):
    """TensorFlow analyzer status tracking"""
    __tablename__ = "tensorflow_analysis_status"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="tensorflow_status")
    results = relationship("TensorFlowAnalysisResults", back_populates="status", uselist=False)
    
    def __repr__(self):
        return f"<TensorFlowAnalysisStatus(file_id={self.file_id}, status='{self.status}')>"

class FAISSAnalysisStatus(Base):
    """FAISS analyzer status tracking"""
    __tablename__ = "faiss_analysis_status"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="faiss_status")
    results = relationship("FAISSAnalysisResults", back_populates="status", uselist=False)
    
    def __repr__(self):
        return f"<FAISSAnalysisStatus(file_id={self.file_id}, status='{self.status}')>"

# === ANALYZER RESULTS TABLES ===

class EssentiaAnalysisResults(Base):
    """Essentia analysis results"""
    __tablename__ = "essentia_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    status_id = Column(Integer, ForeignKey("essentia_analysis_status.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)  # Time taken for analysis in seconds
    sample_rate = Column(Integer)
    duration = Column(Float)
    
    # Basic features (essential for playlist apps)
    rms = Column(Float)
    energy = Column(Float)
    loudness = Column(Float)
    dynamic_complexity = Column(Float)
    zero_crossing_rate = Column(Float)
    
    # Rhythm features (essential for playlist apps)
    tempo = Column(Float)
    tempo_confidence = Column(Float)
    tempo_methods_used = Column(Integer)  # Number of tempo estimation methods used
    danceability = Column(Float)  # Essential for dance/party playlists
    
    # Harmonic features
    key = Column(String)
    scale = Column(String)
    key_strength = Column(Float)
    dominant_chroma = Column(String)  # Dominant chroma (C, C#, D, etc.)
    dominant_chroma_strength = Column(Float)  # Strength of dominant chroma
    
    # Complete analysis results (for detailed access)
    complete_analysis = Column(Text)  # JSON object with all analysis data
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    status = relationship("EssentiaAnalysisStatus", back_populates="results")
    
    def __repr__(self):
        return f"<EssentiaAnalysisResults(status_id={self.status_id}, duration={self.duration}, tempo={self.tempo})>"

class TensorFlowAnalysisResults(Base):
    """TensorFlow analysis results"""
    __tablename__ = "tensorflow_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    status_id = Column(Integer, ForeignKey("tensorflow_analysis_status.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float)  # Time taken for analysis in seconds
    model_used = Column(String)  # Which model was used (MusicNN, VGGish, etc.)
    
    # TensorFlow features (stored as JSON)
    tensorflow_features = Column(Text)  # JSON object with model outputs
    tensorflow_summary = Column(Text)   # JSON summary of top predictions
    
    # Mood analysis features
    mood_analysis = Column(Text)        # JSON object with mood analysis results
    primary_mood = Column(String)       # Primary mood (energetic, calm, happy, etc.)
    mood_confidence = Column(Float)     # Confidence score for primary mood
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    status = relationship("TensorFlowAnalysisStatus", back_populates="results")
    
    def __repr__(self):
        return f"<TensorFlowAnalysisResults(status_id={self.status_id}, model='{self.model_used}')>"

class FAISSAnalysisResults(Base):
    """FAISS analysis results"""
    __tablename__ = "faiss_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    status_id = Column(Integer, ForeignKey("faiss_analysis_status.id"), nullable=False, index=True)
    
    # Analysis metadata
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)
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
    status = relationship("FAISSAnalysisStatus", back_populates="results")
    
    def __repr__(self):
        return f"<FAISSAnalysisResults(status_id={self.status_id}, dimension={self.vector_dimension}, index_type='{self.index_type}')>"

# === CONSOLIDATED QUERY TABLE ===

class TrackAnalysisSummary(Base):
    """Consolidated view for easy querying of all analyzer statuses"""
    __tablename__ = "track_analysis_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False, index=True)
    
    # Individual analyzer statuses
    essentia_status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING, index=True)
    tensorflow_status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING, index=True)
    faiss_status = Column(Enum(AnalyzerStatus), default=AnalyzerStatus.PENDING, index=True)
    
    # Completion timestamps
    essentia_completed_at = Column(DateTime)
    tensorflow_completed_at = Column(DateTime)
    faiss_completed_at = Column(DateTime)
    
    # Overall status
    overall_status = Column(String, index=True)  # "complete", "partial", "failed", "pending"
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    file = relationship("File", back_populates="track_summary")
    
    def __repr__(self):
        return f"<TrackAnalysisSummary(file_id={self.file_id}, overall_status='{self.overall_status}')>"

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
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@playlist-postgres:5432/playlist_db")

# Improved engine configuration for concurrent operations
engine = create_engine(
    DATABASE_URL,
    # Connection pool settings for concurrent operations
    pool_size=20,  # Increased from default 5
    max_overflow=30,  # Allow overflow connections
    pool_timeout=30,  # Timeout for getting connection
    pool_recycle=3600,  # Recycle connections every hour
    pool_pre_ping=True,  # Verify connections before use
    # Transaction isolation
    isolation_level="READ_COMMITTED",  # Better for concurrent access
    # Connection settings
    connect_args={
        "connect_timeout": 10,
        "application_name": "playlist_app"
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session with proper error handling"""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db_session():
    """Get a new database session for manual management"""
    return SessionLocal()

def close_db_session(db: Session):
    """Safely close a database session"""
    try:
        db.close()
    except Exception as e:
        # Log but don't raise - session might already be closed
        pass
