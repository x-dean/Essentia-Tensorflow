import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis
from mutagen.asf import ASF
from mutagen.mp4 import MP4
from mutagen.wave import WAVE
from sqlalchemy.orm import Session
from datetime import datetime

from ..models.database import File, AudioMetadata, get_db, FileStatus
from ..core.config_loader import config_loader
from .genre_enrichment import genre_enrichment_manager
from .genre_normalizer import GenreNormalizer
from ..core.logging import get_logger

logger = logging.getLogger(__name__)

class AudioMetadataAnalyzer:
    """Audio metadata analyzer using Mutagen with focused playlist-relevant mappings"""
    
    def __init__(self):
        self.metadata_mapping = self._load_metadata_mapping()
        self.genre_normalizer = GenreNormalizer()  # Initialize genre normalizer
        self.supported_formats = {
            '.mp3': self._extract_mp3_metadata,
            '.flac': self._extract_flac_metadata,
            '.ogg': self._extract_ogg_metadata,
            '.m4a': self._extract_m4a_metadata,
            '.wav': self._extract_wav_metadata,
            '.wma': self._extract_wma_metadata,
            '.aac': self._extract_aac_metadata,
            '.opus': self._extract_opus_metadata
        }
    
    def _load_metadata_mapping(self) -> Dict[str, str]:
        """Load metadata field mapping with playlist-relevant fields"""
        config = config_loader.get_discovery_config()
        mapping_config = config.get('metadata_mapping', {})
        
        # Essential playlist-relevant mappings
        default_mapping = {
            # Core playlist fields (Priority 1)
            'title': 'title',
            'TIT2': 'title',
            'TITLE': 'title',
            '©nam': 'title',  # iTunes
            
            'artist': 'artist',
            'TPE1': 'artist',
            'ARTIST': 'artist',
            '©ART': 'artist',  # iTunes
            
            'album': 'album',
            'TALB': 'album',
            'ALBUM': 'album',
            '©alb': 'album',  # iTunes
            
            'track_number': 'track_number',
            'TRCK': 'track_number',
            'TRACK': 'track_number',
            'TRACKNUMBER': 'track_number',
            'trkn': 'track_number',  # iTunes
            
            'year': 'year',
            'TDRC': 'year',
            'TYER': 'year',
            'YEAR': 'year',
            'DATE': 'year',
            '©day': 'year',  # iTunes
            
            'genre': 'genre',
            'TCON': 'genre',
            'GENRE': 'genre',
            '©gen': 'genre',  # iTunes
            
            # Secondary playlist fields (Priority 2)
            'album_artist': 'album_artist',
            'TPE2': 'album_artist',
            'ALBUMARTIST': 'album_artist',
            
            'disc_number': 'disc_number',
            'TPOS': 'disc_number',
            'DISC': 'disc_number',
            'DISCNUMBER': 'disc_number',
            'disk': 'disc_number',  # iTunes
            
            'composer': 'composer',
            'TCOM': 'composer',
            'COMPOSER': 'composer',
            '©wrt': 'composer',  # iTunes
            
            'duration': 'duration',
            'length': 'duration',
            'TLEN': 'duration',
            
            'bpm': 'bpm',
            'TBPM': 'bpm',
            'BPM': 'bpm',
            'TEMPO': 'bpm',
            'tmpo': 'bpm',  # iTunes
            
            'key': 'key',
            'TKEY': 'key',
            'KEY': 'key',
            
            # Additional useful fields (Priority 3)
            'comment': 'comment',
            'COMM': 'comment',
            'COMMENT': 'comment',
            
            'mood': 'mood',
            'TMOO': 'mood',
            'MOOD': 'mood',
            
            'rating': 'rating',
            'POPM': 'rating',
            'RATING': 'rating',
            
            'isrc': 'isrc',
            'TSRC': 'isrc',
            'ISRC': 'isrc',
            
            'encoder': 'encoder',
            'TENC': 'encoder',
            'ENCODER': 'encoder',
            '©too': 'encoder',  # iTunes
            
            # Technical info
            'bitrate': 'bitrate',
            'sample_rate': 'sample_rate',
            'channels': 'channels',
            'format': 'format',
            
            # ReplayGain (for volume normalization)
            'replaygain_track_gain': 'replaygain_track_gain',
            'replaygain_album_gain': 'replaygain_album_gain',
            'replaygain_track_peak': 'replaygain_track_peak',
            'replaygain_album_peak': 'replaygain_album_peak',
            
            # MusicBrainz IDs (for accurate identification)
            'musicbrainz_track_id': 'musicbrainz_track_id',
            'musicbrainz_artist_id': 'musicbrainz_artist_id',
            'musicbrainz_album_id': 'musicbrainz_album_id',
            'musicbrainz_album_artist_id': 'musicbrainz_album_artist_id',
            
            # Custom TXXX tags
            'TXXX:REPLAYGAIN_TRACK_GAIN': 'replaygain_track_gain',
            'TXXX:REPLAYGAIN_ALBUM_GAIN': 'replaygain_album_gain',
            'TXXX:REPLAYGAIN_TRACK_PEAK': 'replaygain_track_peak',
            'TXXX:REPLAYGAIN_ALBUM_PEAK': 'replaygain_album_peak',
            'TXXX:MUSICBRAINZ_TRACKID': 'musicbrainz_track_id',
            'TXXX:MUSICBRAINZ_ARTISTID': 'musicbrainz_artist_id',
            'TXXX:MUSICBRAINZ_ALBUMID': 'musicbrainz_album_id',
            'TXXX:MUSICBRAINZ_ALBUMARTISTID': 'musicbrainz_album_artist_id',
            
            # iTunes custom tags
            '----:com.apple.iTunes:replaygain_track_gain': 'replaygain_track_gain',
            '----:com.apple.iTunes:replaygain_album_gain': 'replaygain_album_gain',
            '----:com.apple.iTunes:replaygain_track_peak': 'replaygain_track_peak',
            '----:com.apple.iTunes:replaygain_album_peak': 'replaygain_album_peak',
        }
        
        # Merge with configuration mapping
        default_mapping.update(mapping_config)
        return default_mapping
    
    def analyze_file(self, file_path: str, db: Session) -> Optional[Dict[str, Any]]:
        """Analyze audio file and extract metadata"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Get file extension
            extension = file_path.suffix.lower()
            if extension not in self.supported_formats:
                logger.warning(f"Unsupported format: {extension}")
                return None
            
            # Extract raw metadata
            raw_metadata = self.supported_formats[extension](file_path)
            if not raw_metadata:
                logger.warning(f"No metadata found for: {file_path}")
                return None
            
            # Normalize metadata using mapping
            normalized_metadata = self._normalize_metadata(raw_metadata)
            
            # Add technical information
            technical_info = self._extract_technical_info(file_path)
            normalized_metadata.update(technical_info)
            
            # Save to database
            self._save_metadata_to_db(file_path, normalized_metadata, db)
            
            logger.info(f"Successfully analyzed: {file_path}")
            return normalized_metadata
            
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {str(e)}")
            # Mark file as failed
            try:
                file_record = db.query(File).filter(File.file_path == str(file_path)).first()
                if file_record:
                    file_record.status = FileStatus.FAILED
                    db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update file status to FAILED: {db_error}")
            return None
    
    def _extract_mp3_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from MP3 files"""
        metadata = {}
        
        try:
            # Try EasyID3 first (simpler format)
            try:
                audio = EasyID3(str(file_path))
                for key, value in audio.items():
                    if value and len(value) > 0:
                        metadata[key] = value[0]
            except Exception as e:
                logger.debug(f"EasyID3 extraction failed: {e}")
            
            # Try ID3 for extended metadata
            try:
                audio = ID3(str(file_path))
                for key, frame in audio.items():
                    if hasattr(frame, 'text') and frame.text:
                        # Handle ID3TimeStamp objects
                        if hasattr(frame.text[0], 'year'):
                            metadata[key] = frame.text[0]  # Keep as object for later conversion
                        else:
                            metadata[key] = str(frame.text[0])
                    elif hasattr(frame, 'data'):
                        metadata[key] = str(frame.data)
            except Exception as e:
                logger.debug(f"ID3 extraction failed: {e}")
            
            # Get basic audio info
            try:
                audio = MP3(str(file_path))
                if audio.info:
                    metadata['duration'] = audio.info.length
                    metadata['bitrate'] = audio.info.bitrate
                    metadata['sample_rate'] = audio.info.sample_rate
            except Exception as e:
                logger.debug(f"MP3 info extraction failed: {e}")
                
        except Exception as e:
            logger.error(f"Error extracting MP3 metadata: {e}")
        
        return metadata
    
    def _extract_flac_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from FLAC files"""
        metadata = {}
        
        try:
            audio = FLAC(str(file_path))
            
            # Extract tags
            for key, value in audio.tags.items():
                metadata[key] = value[0] if value else None
            
            # Get audio info
            if audio.info:
                metadata['duration'] = audio.info.length
                metadata['sample_rate'] = audio.info.sample_rate
                metadata['channels'] = audio.info.channels
                # Calculate bitrate for FLAC: (file_size * 8) / duration
                # For FLAC, we'll use bits_per_sample * sample_rate * channels as approximation
                if audio.info.bits_per_sample and audio.info.sample_rate and audio.info.channels:
                    metadata['bitrate'] = audio.info.bits_per_sample * audio.info.sample_rate * audio.info.channels
                else:
                    # Fallback: calculate from file size and duration
                    file_size = file_path.stat().st_size
                    if metadata.get('duration') and metadata['duration'] > 0:
                        metadata['bitrate'] = int((file_size * 8) / metadata['duration'])
                
        except Exception as e:
            logger.error(f"Error extracting FLAC metadata: {e}")
        
        return metadata
    
    def _extract_ogg_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from OGG files"""
        metadata = {}
        
        try:
            audio = OggVorbis(str(file_path))
            
            # Extract tags
            for key, value in audio.tags.items():
                metadata[key] = value[0] if value else None
            
            # Get audio info
            if audio.info:
                metadata['duration'] = audio.info.length
                metadata['sample_rate'] = audio.info.sample_rate
                metadata['channels'] = audio.info.channels
                metadata['bitrate'] = audio.info.bitrate
                
        except Exception as e:
            logger.error(f"Error extracting OGG metadata: {e}")
        
        return metadata
    
    def _extract_m4a_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from M4A files"""
        metadata = {}
        
        try:
            audio = MP4(str(file_path))
            
            # Extract tags
            for key, value in audio.tags.items():
                if isinstance(value, list) and value:
                    metadata[key] = value[0]
                else:
                    metadata[key] = value
            
            # Get audio info
            if audio.info:
                metadata['duration'] = audio.info.length
                metadata['sample_rate'] = audio.info.sample_rate
                metadata['channels'] = audio.info.channels
                metadata['bitrate'] = audio.info.bitrate
                
        except Exception as e:
            logger.error(f"Error extracting M4A metadata: {e}")
        
        return metadata
    
    def _extract_wav_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from WAV files"""
        metadata = {}
        
        try:
            audio = WAVE(str(file_path))
            
            # Get audio info
            if audio.info:
                metadata['duration'] = audio.info.length
                metadata['sample_rate'] = audio.info.sample_rate
                metadata['channels'] = audio.info.channels
                # Calculate bitrate for WAV: bits_per_sample * sample_rate * channels
                if audio.info.bits_per_sample and audio.info.sample_rate and audio.info.channels:
                    metadata['bitrate'] = audio.info.bits_per_sample * audio.info.sample_rate * audio.info.channels
                
        except Exception as e:
            logger.error(f"Error extracting WAV metadata: {e}")
        
        return metadata
    
    def _extract_wma_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from WMA files"""
        metadata = {}
        
        try:
            audio = ASF(str(file_path))
            
            # Extract tags
            for key, value in audio.tags.items():
                if isinstance(value, list) and value:
                    metadata[key] = value[0]
                else:
                    metadata[key] = value
            
            # Get audio info
            if audio.info:
                metadata['duration'] = audio.info.length
                metadata['sample_rate'] = audio.info.sample_rate
                metadata['channels'] = audio.info.channels
                metadata['bitrate'] = audio.info.bitrate
                
        except Exception as e:
            logger.error(f"Error extracting WMA metadata: {e}")
        
        return metadata
    
    def _extract_aac_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from AAC files"""
        # AAC files might be in M4A container
        return self._extract_m4a_metadata(file_path)
    
    def _extract_opus_metadata(self, file_path: Path) -> Dict[str, Any]:
        """Extract metadata from OPUS files"""
        # OPUS files might be in OGG container
        return self._extract_ogg_metadata(file_path)
    
    def _normalize_metadata(self, raw_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata using mapping and apply genre normalization"""
        normalized = {}
        
        for raw_key, value in raw_metadata.items():
            # Find mapped field name
            mapped_key = self.metadata_mapping.get(raw_key, raw_key.lower())
            
            # Clean and validate value
            if value is not None:
                if isinstance(value, str):
                    value = value.strip()
                    if value:  # Only add non-empty strings
                        normalized[mapped_key] = value
                else:
                    normalized[mapped_key] = value
        
        # Post-process and convert data types
        normalized = self._convert_data_types(normalized)
        
        # Normalize genre if present
        if 'genre' in normalized and normalized['genre']:
            original_genre = normalized['genre']
            normalized_genre = self.genre_normalizer.normalize_genre(original_genre)
            if normalized_genre != original_genre:
                logger.info(f"Genre normalized: '{original_genre}' -> '{normalized_genre}'")
            normalized['genre'] = normalized_genre
        
        # Validate and override obviously wrong genres based on album context
        normalized = self._validate_genre_context(normalized)
        
        # Enrich genre information from MusicBrainz if needed
        normalized = self._enrich_genre_from_musicbrainz(normalized)
        
        return normalized
    
    def _convert_data_types(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Convert metadata values to appropriate data types"""
        converted = metadata.copy()
        
        # Convert year field
        if 'year' in converted:
            year_value = converted['year']
            if hasattr(year_value, 'year'):  # ID3TimeStamp object
                converted['year'] = year_value.year
            elif isinstance(year_value, str):
                # Try to extract year from date string
                try:
                    if '-' in year_value:
                        year_str = year_value.split('-')[0]
                        converted['year'] = int(year_str)
                    else:
                        converted['year'] = int(year_value)
                except (ValueError, IndexError):
                    converted['year'] = -999  # Standardized out-of-range fallback
        
        # Convert track_number
        if 'track_number' in converted:
            track_value = converted['track_number']
            if isinstance(track_value, str):
                try:
                    # Handle formats like "1", "1/10", "01", etc.
                    if '/' in track_value:
                        track_str = track_value.split('/')[0]
                        converted['track_number'] = int(track_str)
                    else:
                        converted['track_number'] = int(track_value)
                except ValueError:
                    converted['track_number'] = -999  # Standardized out-of-range fallback
            elif isinstance(track_value, tuple):
                # Handle M4A tuple format like (68, 100) or (1, 0)
                try:
                    converted['track_number'] = int(track_value[0])
                except (ValueError, IndexError):
                    converted['track_number'] = -999  # Standardized out-of-range fallback
        
        # Convert disc_number
        if 'disc_number' in converted:
            disc_value = converted['disc_number']
            if isinstance(disc_value, str):
                try:
                    # Handle formats like "1", "1/2", "01", etc.
                    if '/' in disc_value:
                        disc_str = disc_value.split('/')[0]
                        converted['disc_number'] = int(disc_str)
                    else:
                        converted['disc_number'] = int(disc_value)
                except ValueError:
                    converted['disc_number'] = -999  # Standardized out-of-range fallback
            elif isinstance(disc_value, tuple):
                # Handle M4A tuple format like (1, 0)
                try:
                    converted['disc_number'] = int(disc_value[0])
                except (ValueError, IndexError):
                    converted['disc_number'] = -999  # Standardized out-of-range fallback
        
        # Convert bpm
        if 'bpm' in converted:
            bpm_value = converted['bpm']
            if isinstance(bpm_value, str):
                try:
                    converted['bpm'] = float(bpm_value)
                except ValueError:
                    converted['bpm'] = -999.0  # Standardized out-of-range fallback
            elif isinstance(bpm_value, (int, float)):
                if bpm_value > 0:
                    converted['bpm'] = float(bpm_value)
                else:
                    converted['bpm'] = -999.0  # Standardized out-of-range fallback
        
        # Convert duration
        if 'duration' in converted:
            duration_value = converted['duration']
            if isinstance(duration_value, (int, float)):
                if duration_value > 0:
                    converted['duration'] = float(duration_value)
                else:
                    converted['duration'] = -999.0  # Standardized out-of-range fallback
            else:
                converted['duration'] = -999.0  # Standardized out-of-range fallback
        
        # Convert ReplayGain values
        replaygain_fields = ['replaygain_track_gain', 'replaygain_album_gain', 
                           'replaygain_track_peak', 'replaygain_album_peak']
        
        for field in replaygain_fields:
            if field in converted:
                value = converted[field]
                if isinstance(value, str):
                    try:
                        # Remove "dB" and convert to float
                        if 'dB' in value:
                            numeric_value = value.replace('dB', '').strip()
                            converted[field] = float(numeric_value)
                        else:
                            converted[field] = float(value)
                    except ValueError:
                        converted[field] = -999.0  # Out-of-range fallback for ReplayGain
                elif isinstance(value, (int, float)):
                    converted[field] = float(value)
        
        # Convert numeric fields
        numeric_fields = ['bitrate', 'sample_rate', 'channels', 'rating']
        for field in numeric_fields:
            if field in converted:
                value = converted[field]
                if isinstance(value, str):
                    try:
                        if field in ['bitrate', 'sample_rate', 'channels', 'rating']:
                            converted[field] = int(value)
                        else:
                            converted[field] = float(value)
                    except ValueError:
                        if field in ['bitrate', 'sample_rate', 'channels', 'rating']:
                            converted[field] = -999  # Standardized out-of-range fallback for integers
                        else:
                            converted[field] = -999.0  # Standardized out-of-range fallback for floats
                elif isinstance(value, (int, float)):
                    if field in ['bitrate', 'sample_rate', 'channels', 'rating']:
                        if value > 0:
                            converted[field] = int(value)
                        else:
                            converted[field] = -999  # Standardized out-of-range fallback for integers
                    else:
                        if value > 0:
                            converted[field] = float(value)
                        else:
                            converted[field] = -999.0  # Standardized out-of-range fallback for floats
        
        return converted
    
    def _validate_genre_context(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and override obviously wrong genres using dynamic lookup"""
        genre = metadata.get('genre', '').lower()
        album = metadata.get('album', '').lower()
        artist = metadata.get('artist', '').lower()
        title = metadata.get('title', '').lower()
        file_path = metadata.get('file_path', '')
        
        if not genre:
            return metadata
        
        # Step 1: Check album context patterns (these are still useful)
        album_override = self._check_album_context(genre, album)
        if album_override:
            metadata['genre'] = album_override['genre']
            metadata['genre_source'] = album_override['source']
            return metadata
        
        # Step 2: Dynamic artist genre lookup
        artist_override = self._check_artist_genre(genre, artist, title)
        if artist_override:
            metadata['genre'] = artist_override['genre']
            metadata['genre_source'] = artist_override['source']
            metadata['genre_confidence'] = artist_override.get('confidence', 0.6)
            return metadata
        
        # Step 3: Filename pattern analysis
        filename_override = self._check_filename_patterns(genre, file_path)
        if filename_override:
            metadata['genre'] = filename_override['genre']
            metadata['genre_source'] = filename_override['source']
            metadata['genre_confidence'] = filename_override.get('confidence', 0.4)
            return metadata
        
        return metadata
    
    def _check_album_context(self, current_genre: str, album: str) -> Optional[Dict[str, Any]]:
        """Check album context patterns for genre hints"""
        if not album:
            return None
        
        # Album context patterns that indicate specific genres
        album_genre_patterns = {
            # Rap/Hip-Hop albums
            'rap hits': 'hip hop',
            'rap hits 2000': 'hip hop',
            'rap hits 2024': 'hip hop',
            'hip hop': 'hip hop',
            'hip-hop': 'hip hop',
            'rap': 'hip hop',
            'r&b': 'r&b',
            'soul': 'r&b',
            
            # House/Electronic albums
            'deep & hot': 'house',
            'deep and hot': 'house',
            'afro house': 'house',
            'house music': 'house',
            'summer evening': 'house',  # Common house compilation pattern
            'club sandwich': 'house',   # Club music reference
            'electronic': 'electronic',
            'techno': 'electronic',
            'trance': 'electronic',
            'dance': 'dance',
            
            # Reggaeton/Latin albums
            'baila reggaeton': 'latin',
            'reggaeton': 'latin',
            'latin': 'latin',
            'salsa': 'latin',
            
            # Rock albums
            'rock hits': 'rock',
            'rock music': 'rock',
            'metal': 'metal',
            'punk': 'rock',
            
            # Pop albums
            'pop hits': 'pop',
            'pop music': 'pop',
            'top hits': 'pop',
            'chart hits': 'pop',
            
            # Jazz albums
            'jazz': 'jazz',
            'smooth jazz': 'jazz',
            'jazz fusion': 'jazz',
            
            # Classical albums
            'classical': 'classical',
            'symphony': 'classical',
            'orchestra': 'classical',
            
            # Country albums
            'country': 'country',
            'country hits': 'country',
            'bluegrass': 'country',
            
            # Folk albums
            'folk': 'folk',
            'traditional': 'folk',
            'celtic': 'folk',
            
            # Blues albums
            'blues': 'blues',
            'delta blues': 'blues',
            'chicago blues': 'blues',
            
            # Reggae albums
            'reggae': 'reggae',
            'roots reggae': 'reggae',
            'dancehall': 'reggae',
            
            # World music albums
            'world music': 'world',
            'african': 'african',
            'latin': 'latin',
            'middle eastern': 'world',
            'indian': 'world',
            'chinese': 'world',
            'japanese': 'world'
        }
        
        # Check if album context suggests a specific genre
        for pattern, expected_genre in album_genre_patterns.items():
            if pattern in album:
                # If the current genre is obviously wrong for this album context
                if self._is_genre_mismatch(current_genre, expected_genre):
                    logger.info(f"Genre context override: '{current_genre}' -> '{expected_genre}' (album: {album})")
                    return {'genre': expected_genre, 'source': 'album_context'}
        
        return None
    
    def _check_artist_genre(self, current_genre: str, artist: str, title: str) -> Optional[Dict[str, Any]]:
        """Dynamically lookup artist genre using external APIs"""
        if not artist:
            return None
        
        try:
            # Use the existing genre enrichment manager for dynamic lookup
            from .genre_enrichment import genre_enrichment_manager
            
            # First try artist-track combination
            enrichment_result = genre_enrichment_manager.enrich_metadata({
                'artist': artist,
                'title': title
            })
            
            if enrichment_result and enrichment_result.get('genre'):
                expected_genre = enrichment_result['genre'].lower()
                if self._is_genre_mismatch(current_genre, expected_genre):
                    logger.info(f"Genre artist lookup override: '{current_genre}' -> '{expected_genre}' (artist: {artist})")
                    return {
                        'genre': expected_genre, 
                        'source': 'artist_lookup',
                        'confidence': enrichment_result.get('confidence', 0.6)
                    }
            
            # If no track-specific result, try artist-only lookup
            # Use MusicBrainz service directly for artist genre lookup
            from .musicbrainz import MusicBrainzService
            musicbrainz = MusicBrainzService()
            artist_genre = musicbrainz.get_artist_genre_by_name(artist)
            
            if artist_genre:
                expected_genre = artist_genre.lower()
                if self._is_genre_mismatch(current_genre, expected_genre):
                    logger.info(f"Genre artist-only override: '{current_genre}' -> '{expected_genre}' (artist: {artist})")
                    return {
                        'genre': expected_genre, 
                        'source': 'artist_only_lookup',
                        'confidence': 0.5
                    }
                    
        except Exception as e:
            logger.debug(f"Artist genre lookup failed for {artist}: {e}")
        
        return None
    
    def _check_filename_patterns(self, current_genre: str, file_path: str) -> Optional[Dict[str, Any]]:
        """Extract genre hints from filename patterns"""
        if not file_path:
            return None
        
        filename = file_path.lower()
        
        # Filename genre patterns
        filename_patterns = {
            # House/Electronic patterns
            'house': 'house',
            'deep house': 'house',
            'progressive house': 'house',
            'tech house': 'house',
            'acid house': 'house',
            'electronic': 'electronic',
            'techno': 'electronic',
            'trance': 'electronic',
            'dubstep': 'electronic',
            'drum and bass': 'electronic',
            'dnb': 'electronic',
            'ambient': 'electronic',
            
            # Hip-hop patterns
            'hip hop': 'hip hop',
            'hiphop': 'hip hop',
            'rap': 'hip hop',
            'trap': 'hip hop',
            'grime': 'hip hop',
            
            # Rock patterns
            'rock': 'rock',
            'metal': 'metal',
            'punk': 'rock',
            'grunge': 'rock',
            'alternative': 'rock',
            'indie': 'rock',
            
            # Pop patterns
            'pop': 'pop',
            'mainstream': 'pop',
            
            # Other patterns
            'jazz': 'jazz',
            'blues': 'blues',
            'country': 'country',
            'folk': 'folk',
            'classical': 'classical',
            'reggae': 'reggae',
            'latin': 'latin',
            'salsa': 'latin',
            'reggaeton': 'latin',
            'world': 'world',
            'african': 'african'
        }
        
        # Check filename for genre patterns
        for pattern, expected_genre in filename_patterns.items():
            if pattern in filename:
                if self._is_genre_mismatch(current_genre, expected_genre):
                    logger.info(f"Genre filename override: '{current_genre}' -> '{expected_genre}' (filename: {filename})")
                    return {
                        'genre': expected_genre, 
                        'source': 'filename_pattern',
                        'confidence': 0.4  # Lower confidence for filename patterns
                    }
        
        return None
    
    def _is_genre_mismatch(self, current_genre: str, expected_genre: str) -> bool:
        """Check if current genre is obviously wrong for expected genre"""
        if not current_genre or not expected_genre:
            return False
        
        # Define genre families
        genre_families = {
            'hip hop': ['hip hop', 'rap', 'r&b', 'soul', 'trap', 'grime'],
            'house': ['house', 'deep house', 'progressive house', 'tech house', 'acid house'],
            'electronic': ['electronic', 'techno', 'trance', 'dubstep', 'drum and bass', 'ambient'],
            'rock': ['rock', 'alternative', 'indie', 'punk', 'grunge'],
            'metal': ['metal', 'heavy metal', 'black metal', 'death metal', 'thrash metal'],
            'pop': ['pop', 'mainstream', 'adult contemporary'],
            'jazz': ['jazz', 'smooth jazz', 'jazz fusion'],
            'classical': ['classical', 'orchestral', 'symphony'],
            'country': ['country', 'bluegrass', 'americana'],
            'folk': ['folk', 'traditional', 'celtic'],
            'blues': ['blues', 'delta blues', 'chicago blues'],
            'reggae': ['reggae', 'roots reggae', 'dancehall'],
            'latin': ['latin', 'salsa', 'reggaeton', 'bachata'],
            'world': ['world', 'african', 'middle eastern', 'indian'],
            'dance': ['dance', 'disco', 'eurodance']
        }
        
        # Check if current genre belongs to a different family than expected
        current_family = None
        expected_family = None
        
        for family, genres in genre_families.items():
            if current_genre in genres:
                current_family = family
            if expected_genre in genres:
                expected_family = family
        
        # If genres belong to different families, it's likely a mismatch
        if current_family and expected_family and current_family != expected_family:
            return True
        
        # Specific obvious mismatches
        obvious_mismatches = [
            ('deep house black metal techno', 'hip hop'),  # Your specific case
            ('techno', 'hip hop'),
            ('metal', 'hip hop'),
            ('classical', 'hip hop'),
            ('jazz', 'hip hop'),
            ('jazz', 'house'),  # Jazz is wrong for house music
            ('jazz', 'electronic'),  # Jazz is wrong for electronic music
            ('country', 'hip hop'),
            ('folk', 'hip hop'),
            ('blues', 'hip hop'),
            ('reggae', 'hip hop'),
            ('latin', 'hip hop'),
            ('world', 'hip hop'),
            ('dance', 'hip hop'),
        ]
        
        for wrong_genre, correct_genre in obvious_mismatches:
            if wrong_genre in current_genre and expected_genre == correct_genre:
                return True
        
        return False
    
    def _enrich_genre_from_musicbrainz(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich genre information using multiple API services"""
        try:
            # Only enrich if we have artist and title, and genre is missing or generic
            artist = metadata.get('artist')
            title = metadata.get('title')
            current_genre = metadata.get('genre', '').lower()
            
            if not artist or not title:
                return metadata
            
            # Skip if we already have a good genre (after normalization)
            if current_genre and current_genre not in ['other', 'unknown', 'none', '']:
                return metadata
            
            # Use the genre enrichment manager to try multiple services
            enriched_metadata = genre_enrichment_manager.enrich_metadata(metadata)
            
            return enriched_metadata
            
        except Exception as e:
            logger.warning(f"Failed to enrich genre: {e}")
            return metadata
    
    def _extract_technical_info(self, file_path: Path) -> Dict[str, Any]:
        """Extract technical information about the file"""
        try:
            stat = file_path.stat()
            return {
                'file_size': stat.st_size,
                'file_format': file_path.suffix.lower(),
                'last_modified': stat.st_mtime,
                'created_time': stat.st_ctime
            }
        except Exception as e:
            logger.error(f"Error extracting technical info: {e}")
            return {}
    
    def _save_metadata_to_db(self, file_path: Path, metadata: Dict[str, Any], db: Session):
        """Save metadata to database"""
        try:
            # Find the file record
            file_record = db.query(File).filter(File.file_path == str(file_path)).first()
            if not file_record:
                logger.warning(f"File record not found for: {file_path}")
                return
            
            # Filter metadata to only include essential fields for playlist generation
            valid_fields = {
                'title', 'artist', 'album', 'album_artist', 'year', 'genre',
                'duration', 'bpm', 'key', 'bitrate', 'sample_rate', 'channels',
                'file_format', 'mood', 'energy', 'danceability', 'valence'
            }
            
            filtered_metadata = {k: v for k, v in metadata.items() if k in valid_fields}
            
            # Log the metadata being saved for debugging
            logger.debug(f"Saving metadata for {file_path}: {filtered_metadata}")
            
            # Check if metadata already exists
            existing_metadata = db.query(AudioMetadata).filter(
                AudioMetadata.file_id == file_record.id
            ).first()
            
            if existing_metadata:
                # Update existing metadata
                for key, value in filtered_metadata.items():
                    if hasattr(existing_metadata, key):
                        try:
                            setattr(existing_metadata, key, value)
                        except Exception as field_error:
                            logger.warning(f"Failed to set field {key} with value {value}: {field_error}")
                existing_metadata.updated_at = datetime.utcnow()
            else:
                # Create new metadata record
                try:
                    metadata_record = AudioMetadata(
                        file_id=file_record.id,
                        **filtered_metadata
                    )
                    db.add(metadata_record)
                except Exception as create_error:
                    logger.error(f"Failed to create metadata record: {create_error}")
                    logger.error(f"Metadata fields: {filtered_metadata}")
                    raise
            
            # Mark file as analyzed
            file_record.has_metadata = True
            file_record.status = FileStatus.HAS_METADATA
            file_record.last_modified = datetime.utcnow()
            
            db.commit()
            logger.info(f"Metadata saved to database for: {file_path}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving metadata to database: {e}")
            logger.error(f"Metadata that failed to save: {metadata}")
            raise
    
    def analyze_multiple_files(self, file_paths: List[str], db: Session) -> Dict[str, Any]:
        """Analyze multiple files and return summary"""
        results = {
            'total_files': len(file_paths),
            'successful': 0,
            'failed': 0,
            'errors': []
        }
        
        for file_path in file_paths:
            try:
                metadata = self.analyze_file(file_path, db)
                if metadata:
                    results['successful'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{file_path}: {str(e)}")
        
        return results

# Global analyzer instance
audio_metadata_analyzer = AudioMetadataAnalyzer()
