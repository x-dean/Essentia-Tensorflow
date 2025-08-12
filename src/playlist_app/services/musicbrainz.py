#!/usr/bin/env python3
"""
MusicBrainz API Service for genre enrichment
"""

import requests
import time
import logging
from typing import Dict, Optional, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

class MusicBrainzService:
    """Service for querying MusicBrainz API for genre information"""
    
    def __init__(self):
        # Load configuration
        try:
            from ..core.config_loader import config_loader
            app_config = config_loader.get_app_settings()
            mb_config = app_config.get("external_apis", {}).get("musicbrainz", {})
            
            self.base_url = "https://musicbrainz.org/ws/2"
            self.headers = {
                'User-Agent': mb_config.get("user_agent", "PlaylistApp/1.0 (dean@example.com)")
            }
            
            # Rate limiting configuration
            self.last_request_time = 0
            self.min_request_interval = 1.0 / mb_config.get("rate_limit", 1.0)
            self.timeout = mb_config.get("timeout", 10)
            
            # Retry configuration
            self.retry_settings = mb_config.get("retry_settings", {
                "max_retries": 3,
                "backoff_factor": 2,
                "max_backoff": 60
            })
            
            # Cache configuration
            self.cache_settings = mb_config.get("cache_settings", {
                "enabled": True,
                "ttl_seconds": 3600
            })
            
        except Exception as e:
            logger.warning(f"Failed to load MusicBrainz configuration: {e}, using defaults")
            self.base_url = "https://musicbrainz.org/ws/2"
            self.headers = {
                'User-Agent': 'PlaylistApp/1.0 (dean@example.com)'
            }
            self.last_request_time = 0
            self.min_request_interval = 1.0
            self.timeout = 10
            self.retry_settings = {"max_retries": 3, "backoff_factor": 2, "max_backoff": 60}
            self.cache_settings = {"enabled": True, "ttl_seconds": 3600}
    
    def _rate_limit(self):
        """Ensure we don't exceed MusicBrainz rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to MusicBrainz API with rate limiting and retry logic"""
        max_retries = self.retry_settings.get("max_retries", 3)
        backoff_factor = self.retry_settings.get("backoff_factor", 2)
        max_backoff = self.retry_settings.get("max_backoff", 60)
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                url = f"{self.base_url}/{endpoint}"
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"MusicBrainz API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Calculate backoff time
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"MusicBrainz API request failed after {max_retries} attempts: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error in MusicBrainz request: {e}")
                return None
        
        return None
    
    def search_track(self, artist: str, title: str, album: str = None) -> Optional[Dict]:
        """Search for a track by artist and title"""
        if not artist or not title:
            return None
        
        # Build search query
        query_parts = [f'artist:"{artist}"', f'recording:"{title}"']
        if album:
            query_parts.append(f'release:"{album}"')
        
        query = " AND ".join(query_parts)
        
        params = {
            'query': query,
            'fmt': 'json',
            'limit': 5,
            'inc': 'tags'
        }
        
        data = self._make_request('recording', params)
        if not data or 'recordings' not in data:
            return None
        
        recordings = data['recordings']
        if not recordings:
            return None
        
        # Return the first (most relevant) result
        return recordings[0]
    
    def get_track_genre(self, artist: str, title: str, album: str = None) -> Optional[str]:
        """Get genre for a specific track"""
        track_data = self.search_track(artist, title, album)
        if not track_data:
            return None
        
        # Try to get genre from the track's tags
        if 'tags' in track_data and track_data['tags']:
            # Sort by count (most popular tags first)
            sorted_tags = sorted(track_data['tags'], key=lambda x: x.get('count', 0), reverse=True)
            for tag in sorted_tags:
                tag_name = tag.get('name', '').lower()
                # Filter out non-genre tags
                if self._is_genre_tag(tag_name):
                    return tag['name']
        
        # Try to get genre from artist tags
        if 'artist-credit' in track_data and track_data['artist-credit']:
            artist_id = track_data['artist-credit'][0].get('artist', {}).get('id')
            if artist_id:
                return self.get_artist_genre(artist_id)
        
        return None
    
    def get_artist_genre(self, artist_id: str) -> Optional[str]:
        """Get genre for a specific artist"""
        params = {
            'fmt': 'json',
            'inc': 'tags'
        }
        
        data = self._make_request(f'artist/{artist_id}', params)
        if not data or 'tags' not in data:
            return None
        
        # Sort tags by count
        sorted_tags = sorted(data['tags'], key=lambda x: x.get('count', 0), reverse=True)
        for tag in sorted_tags:
            tag_name = tag.get('name', '').lower()
            if self._is_genre_tag(tag_name):
                return tag['name']
        
        return None
    
    def _is_genre_tag(self, tag_name: str) -> bool:
        """Check if a tag is likely a genre tag"""
        # Common non-genre tags to exclude
        non_genre_tags = {
            'favorites', 'favourite', 'favorite', 'favourites',
            'seen live', 'seen-live', 'live', 'studio',
            'instrumental', 'vocal', 'acoustic', 'electric',
            'remix', 'cover', 'original', 'demo',
            'single', 'album', 'ep', 'compilation',
            'explicit', 'clean', 'radio edit',
            'female vocalists', 'male vocalists',
            'under 2000 listeners', 'under 1000 listeners'
        }
        
        if tag_name in non_genre_tags:
            return False
        
        # Common genre indicators
        genre_indicators = [
            'rock', 'pop', 'electronic', 'hip hop', 'jazz', 'classical',
            'country', 'folk', 'blues', 'reggae', 'punk', 'metal',
            'dance', 'house', 'trance', 'techno', 'dubstep', 'ambient',
            'indie', 'alternative', 'r&b', 'soul', 'funk', 'disco',
            'latin', 'world', 'experimental', 'soundtrack'
        ]
        
        return any(indicator in tag_name for indicator in genre_indicators)
    
    def enrich_metadata(self, metadata: Dict) -> Dict:
        """Enrich metadata with genre information from MusicBrainz"""
        if not metadata:
            return metadata
        
        # Skip if we already have a good genre
        current_genre = metadata.get('genre', '').lower()
        if current_genre and current_genre not in ['other', 'unknown', 'none', '']:
            return metadata
        
        artist = metadata.get('artist')
        title = metadata.get('title')
        album = metadata.get('album')
        
        if not artist or not title:
            return metadata
        
        logger.info(f"Querying MusicBrainz for genre: {artist} - {title}")
        
        genre = self.get_track_genre(artist, title, album)
        if genre:
            metadata['genre'] = genre
            logger.info(f"Found genre '{genre}' for {artist} - {title}")
        else:
            logger.warning(f"No genre found for {artist} - {title}")
        
        return metadata

# Global instance
musicbrainz_service = MusicBrainzService()
