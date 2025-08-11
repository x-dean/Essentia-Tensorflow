from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, BigInteger, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import hashlib
import os

Base = declarative_base()

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
    is_analyzed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationship
    audio_metadata = relationship("AudioMetadata", back_populates="file", uselist=False)
    
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
