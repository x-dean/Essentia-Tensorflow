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
from ..core.logging import get_logger

logger = logging.getLogger(__name__)

class AudioMetadataAnalyzer:
    """Audio metadata analyzer using Mutagen with focused playlist-relevant mappings"""
    
    def __init__(self):
        self.metadata_mapping = self._load_metadata_mapping()
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
        """Normalize metadata using field mapping"""
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
    
    def _enrich_genre_from_musicbrainz(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich genre information using multiple API services"""
        try:
            # Only enrich if we have artist and title, and genre is missing or generic
            artist = metadata.get('artist')
            title = metadata.get('title')
            current_genre = metadata.get('genre', '').lower()
            
            if not artist or not title:
                return metadata
            
            # Skip if we already have a good genre
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
