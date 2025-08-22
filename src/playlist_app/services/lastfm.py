#!/usr/bin/env python3
"""
Last.fm API Service for genre enrichment
Enhanced with rate limiting matching Discogs approach
"""

import requests
import time
import logging
from typing import Dict, Optional, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

class LastFMService:
    """Service for querying Last.fm API for genre information with enhanced rate limiting"""
    
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
        self.rate_limit = config.get('rate_limit', 1.2)  # Updated to match Discogs
        self.timeout = config.get('timeout', 10)
        self.enabled = config.get('enabled', True)
        
        # Retry configuration
        self.retry_settings = config.get('retry_settings', {
            "max_retries": 5,  # Increased from 3 to 5
            "backoff_factor": 2,
            "max_backoff": 120  # Increased from 60 to 120
        })
        
        # Cache configuration
        self.cache_settings = config.get('cache_settings', {
            "enabled": True,
            "ttl_seconds": 1800
        })
        
        # Rate limiting - matching Discogs approach
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 1.0
        
        # Simple in-memory cache for optimization
        self._cache = {}
        self._cache_timestamps = {}
    
    def _get_cache_key(self, artist: str, title: str = None, cache_type: str = 'track') -> str:
        """Generate cache key for lookup"""
        if cache_type == 'track':
            return f"track|{artist.lower().strip()}|{title.lower().strip()}"
        else:
            return f"artist|{artist.lower().strip()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get result from cache if available and not expired"""
        if not self.cache_settings.get("enabled", True):
            return None
        
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            ttl = self.cache_settings.get("ttl_seconds", 1800)
            
            if time.time() - timestamp < ttl:
                return self._cache[cache_key]
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
                del self._cache_timestamps[cache_key]
        
        return None
    
    def _set_cache(self, cache_key: str, value: str):
        """Set result in cache"""
        if self.cache_settings.get("enabled", True):
            self._cache[cache_key] = value
            self._cache_timestamps[cache_key] = time.time()
            
            # Simple cache size management
            if len(self._cache) > 1000:
                # Remove oldest entries
                oldest_keys = sorted(self._cache_timestamps.keys(), 
                                   key=lambda k: self._cache_timestamps[k])[:100]
                for key in oldest_keys:
                    del self._cache[key]
                    del self._cache_timestamps[key]
    
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
        
        max_retries = self.retry_settings.get("max_retries", 5)  # Increased from 3 to 5
        backoff_factor = self.retry_settings.get("backoff_factor", 2)
        max_backoff = self.retry_settings.get("max_backoff", 120)  # Increased from 60 to 120
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                # Add required parameters
                params.update({
                    'api_key': self.api_key,
                    'format': 'json'
                })
                
                response = requests.get(self.base_url, params=params, timeout=self.timeout)
                
                # Handle different response codes appropriately
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error(f"Last.fm API authentication failed (401): Invalid API key")
                    return None  # Don't retry on auth errors
                elif response.status_code == 404:
                    logger.debug(f"Last.fm API: Resource not found (404)")
                    return None  # Don't retry on 404 errors
                elif response.status_code == 429:
                    logger.warning(f"Last.fm API rate limit exceeded (429) - attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        # Calculate progressive backoff for rate limits
                        base_wait = 60  # Start with 60 seconds for rate limits
                        wait_time = min(base_wait * (backoff_factor ** attempt), max_backoff)
                        
                        # Add some jitter to avoid thundering herd
                        jitter = wait_time * 0.2 * (1 - 2 * (time.time() % 1))  # ±20% jitter
                        wait_time += jitter
                        
                        logger.info(f"Rate limit hit - waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Last.fm API rate limit exceeded after {max_retries} attempts - giving up")
                        return None
                elif response.status_code >= 500:
                    # Server errors - retry with exponential backoff
                    logger.warning(f"Last.fm API server error {response.status_code} (attempt {attempt + 1}/{max_retries})")
                    
                    if attempt < max_retries - 1:
                        backoff_time = min(backoff_factor ** attempt, max_backoff)
                        jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))
                        backoff_time += jitter
                        logger.info(f"Retrying server error in {backoff_time:.1f} seconds...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        logger.error(f"Last.fm API server error after {max_retries} attempts")
                        return None
                else:
                    # Other client errors (4xx) - don't retry
                    logger.warning(f"Last.fm API client error {response.status_code}: {response.text[:200]}")
                    return None
                
            except requests.exceptions.Timeout:
                logger.warning(f"Last.fm API timeout (attempt {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))
                    backoff_time += jitter
                    logger.info(f"Retrying timeout in {backoff_time:.1f} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Last.fm API timeout after {max_retries} attempts")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Last.fm API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Calculate backoff time with jitter
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))  # Add ±10% jitter
                    backoff_time += jitter
                    logger.info(f"Retrying in {backoff_time:.1f} seconds...")
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
        """Get genre for a specific track using Last.fm with caching"""
        if not artist or not title:
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(artist, title, 'track')
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for track {artist} - {title}")
            return cached_result
        
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
                    self._set_cache(cache_key, top_tag)
                    return top_tag
        
        # If no track tags, try artist tags
        artist_genre = self.get_artist_genre(artist)
        if artist_genre:
            self._set_cache(cache_key, artist_genre)
            return artist_genre
        
        return None
    
    def get_artist_genre(self, artist: str) -> Optional[str]:
        """Get genre for a specific artist using Last.fm with caching"""
        if not artist:
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(artist, cache_type='artist')
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for artist {artist}")
            return cached_result
        
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
                genre = tag['name']
                self._set_cache(cache_key, genre)
                return genre
        
        return None
    
    def _is_genre_tag(self, tag_name: str) -> bool:
        """Check if a tag is likely a genre tag with improved filtering"""
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
            'love', 'romantic', 'sad', 'happy', 'energetic',
            'catchy', 'melodic', 'atmospheric', 'dark', 'uplifting',
            'best', 'top', 'essential', 'classic', 'legendary'
        }
        
        if tag_name in non_genre_tags:
            return False
        
        # Common genre indicators with improved coverage
        genre_indicators = [
            'rock', 'pop', 'electronic', 'hip hop', 'jazz', 'classical',
            'country', 'folk', 'blues', 'reggae', 'punk', 'metal',
            'dance', 'house', 'trance', 'techno', 'dubstep', 'ambient',
            'indie', 'alternative', 'r&b', 'soul', 'funk', 'disco',
            'latin', 'world', 'experimental', 'soundtrack', 'edm',
            'progressive', 'deep', 'minimal', 'tech', 'acid', 'hardcore',
            'thrash', 'death', 'black', 'power', 'symphonic', 'folk metal',
            'bluegrass', 'americana', 'roots', 'gospel', 'spiritual',
            'ska', 'reggaeton', 'dancehall', 'grime', 'trap', 'drill',
            'electropop', 'synthpop', 'new wave', 'post-punk', 'shoegaze',
            'dream pop', 'trip hop', 'downtempo', 'chillout', 'lounge'
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
