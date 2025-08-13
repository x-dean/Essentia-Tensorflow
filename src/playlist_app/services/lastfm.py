#!/usr/bin/env python3
"""
Last.fm API Service for genre enrichment
"""

import requests
import time
import logging
from typing import Dict, Optional, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

class LastFMService:
    """Service for querying Last.fm API for genre information"""
    
    def __init__(self, config: Dict = None):
        # Load configuration from app settings if not provided
        if config is None:
            try:
                from ..core.config_loader import config_loader
                app_config = config_loader.get_app_settings()
                config = app_config.get("external_apis", {}).get("lastfm", {})
            except Exception as e:
                logger.warning(f"Failed to load LastFM configuration: {e}, using defaults")
                config = {}
        
        self.config = config
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', 'https://ws.audioscrobbler.com/2.0/')
        self.rate_limit = config.get('rate_limit', 0.5)  # requests per second
        self.timeout = config.get('timeout', 10)
        self.enabled = config.get('enabled', True)
        
        # Retry configuration
        self.retry_settings = config.get('retry_settings', {
            "max_retries": 3,
            "backoff_factor": 2,
            "max_backoff": 60
        })
        
        # Cache configuration
        self.cache_settings = config.get('cache_settings', {
            "enabled": True,
            "ttl_seconds": 1800
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 1.0
    
    def _rate_limit(self):
        """Ensure we don't exceed Last.fm rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Make a request to Last.fm API with rate limiting and retry logic"""
        if not self.enabled or not self.api_key:
            return None
        
        max_retries = self.retry_settings.get("max_retries", 3)
        backoff_factor = self.retry_settings.get("backoff_factor", 2)
        max_backoff = self.retry_settings.get("max_backoff", 60)
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                # Add required parameters
                params.update({
                    'api_key': self.api_key,
                    'format': 'json'
                })
                
                response = requests.get(self.base_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Last.fm API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Calculate backoff time
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    logger.info(f"Retrying in {backoff_time} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Last.fm API request failed after {max_retries} attempts: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error in Last.fm request: {e}")
                return None
        
        return None
    
    def get_track_genre(self, artist: str, title: str) -> Optional[str]:
        """Get genre for a specific track using Last.fm"""
        if not artist or not title:
            return None
        
        # Try track.getInfo method first
        params = {
            'method': 'track.getInfo',
            'artist': artist,
            'track': title
        }
        
        data = self._make_request(params)
        if not data or 'track' not in data:
            return None
        
        track_data = data['track']
        
        # Check if track has tags
        if 'toptags' in track_data and 'tag' in track_data['toptags']:
            tags = track_data['toptags']['tag']
            if tags:
                # Get the top tag (most popular)
                top_tag = tags[0]['name']
                if self._is_genre_tag(top_tag):
                    return top_tag
        
        # If no track tags, try artist tags
        return self.get_artist_genre(artist)
    
    def get_artist_genre(self, artist: str) -> Optional[str]:
        """Get genre for a specific artist using Last.fm"""
        if not artist:
            return None
        
        params = {
            'method': 'artist.getTopTags',
            'artist': artist
        }
        
        data = self._make_request(params)
        if not data or 'toptags' not in data or 'tag' not in data['toptags']:
            return None
        
        tags = data['toptags']['tag']
        if not tags:
            return None
        
        # Find the first tag that looks like a genre
        for tag in tags:
            tag_name = tag['name'].lower()
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
            'under 2000 listeners', 'under 1000 listeners',
            'awesome', 'beautiful', 'amazing', 'great',
            'love', 'romantic', 'sad', 'happy', 'energetic'
        }
        
        if tag_name in non_genre_tags:
            return False
        
        # Common genre indicators
        genre_indicators = [
            'rock', 'pop', 'electronic', 'hip hop', 'jazz', 'classical',
            'country', 'folk', 'blues', 'reggae', 'punk', 'metal',
            'dance', 'house', 'trance', 'techno', 'dubstep', 'ambient',
            'indie', 'alternative', 'r&b', 'soul', 'funk', 'disco',
            'latin', 'world', 'experimental', 'soundtrack', 'edm',
            'progressive', 'deep', 'minimal', 'tech', 'acid', 'hardcore'
        ]
        
        return any(indicator in tag_name for indicator in genre_indicators)
    
    def enrich_metadata(self, metadata: Dict) -> Dict:
        """Enrich metadata with genre information from Last.fm"""
        if not metadata:
            return metadata
        
        # Skip if we already have a good genre
        current_genre = metadata.get('genre', '').lower()
        if current_genre and current_genre not in ['other', 'unknown', 'none', '']:
            return metadata
        
        artist = metadata.get('artist')
        title = metadata.get('title')
        
        if not artist or not title:
            return metadata
        
        logger.info(f"Querying Last.fm for genre: {artist} - {title}")
        
        genre = self.get_track_genre(artist, title)
        if genre:
            metadata['genre'] = genre
            logger.info(f"Found genre '{genre}' for {artist} - {title}")
        else:
            logger.warning(f"No genre found for {artist} - {title}")
        
        return metadata
