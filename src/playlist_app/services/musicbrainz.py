#!/usr/bin/env python3
"""
MusicBrainz API Service for genre enrichment
Optimized for 300 requests per second rate limit
"""

import requests
import time
import logging
from typing import Dict, Optional, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

class MusicBrainzService:
    """Service for querying MusicBrainz API for genre information with optimized rate limiting"""
    
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
            
            # Rate limiting configuration - optimized for MusicBrainz's 300 req/s limit
            self.last_request_time = 0
            # MusicBrainz allows 300 req/s, but we'll be conservative and use 200 req/s
            # This gives us plenty of headroom while being respectful
            self.rate_limit = mb_config.get("rate_limit", 200.0)  # Increased from 1.2 to 200
            self.min_request_interval = 1.0 / self.rate_limit
            self.timeout = mb_config.get("timeout", 10)
            
            # Retry configuration
            self.retry_settings = mb_config.get("retry_settings", {
                "max_retries": 5,  # Increased from 3 to 5
                "backoff_factor": 2,
                "max_backoff": 120  # Increased from 60 to 120
            })
            
            # Cache configuration
            self.cache_settings = mb_config.get("cache_settings", {
                "enabled": True,
                "ttl_seconds": 3600
            })
            
            # Simple in-memory cache for optimization
            self._cache = {}
            self._cache_timestamps = {}
            
        except Exception as e:
            logger.warning(f"Failed to load MusicBrainz configuration: {e}, using defaults")
            self.base_url = "https://musicbrainz.org/ws/2"
            self.headers = {
                'User-Agent': 'PlaylistApp/1.0 (dean@example.com)'
            }
            self.last_request_time = 0
            self.rate_limit = 200.0  # Optimized rate limit for MusicBrainz
            self.min_request_interval = 1.0 / self.rate_limit
            self.timeout = 10
            self.retry_settings = {"max_retries": 5, "backoff_factor": 2, "max_backoff": 120}
            self.cache_settings = {"enabled": True, "ttl_seconds": 3600}
            self._cache = {}
            self._cache_timestamps = {}
    
    def _get_cache_key(self, artist: str, title: str, album: str = None) -> str:
        """Generate cache key for track lookup"""
        key_parts = [artist.lower().strip(), title.lower().strip()]
        if album:
            key_parts.append(album.lower().strip())
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[str]:
        """Get result from cache if available and not expired"""
        if not self.cache_settings.get("enabled", True):
            return None
        
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            ttl = self.cache_settings.get("ttl_seconds", 3600)
            
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
        """Ensure we don't exceed MusicBrainz rate limits with efficient throttling for high limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # For high rate limits (200 req/s), we can be more efficient
        # Only sleep if we're making requests too quickly
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            # For high rate limits, use microsecond precision for more efficient timing
            if sleep_time > 0.001:  # Only sleep if more than 1ms
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to MusicBrainz API with rate limiting and retry logic optimized for high limits"""
        max_retries = self.retry_settings.get("max_retries", 5)  # Increased from 3 to 5
        backoff_factor = self.retry_settings.get("backoff_factor", 2)
        max_backoff = self.retry_settings.get("max_backoff", 120)  # Increased from 60 to 120
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                url = f"{self.base_url}/{endpoint}"
                response = requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
                
                # Handle different response codes appropriately
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error(f"MusicBrainz API authentication failed (401): Invalid credentials")
                    return None  # Don't retry on auth errors
                elif response.status_code == 404:
                    logger.debug(f"MusicBrainz API: Resource not found (404) for {url}")
                    return None  # Don't retry on 404 errors
                elif response.status_code == 429:
                    logger.warning(f"MusicBrainz API rate limit exceeded (429) - attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        # For MusicBrainz, use shorter backoff since rate limits are much higher
                        base_wait = 10  # Start with 10 seconds for MusicBrainz (vs 60 for others)
                        wait_time = min(base_wait * (backoff_factor ** attempt), max_backoff)
                        
                        # Add some jitter to avoid thundering herd
                        jitter = wait_time * 0.2 * (1 - 2 * (time.time() % 1))  # ±20% jitter
                        wait_time += jitter
                        
                        logger.info(f"Rate limit hit - waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"MusicBrainz API rate limit exceeded after {max_retries} attempts - giving up")
                        return None
                elif response.status_code == 503:
                    # MusicBrainz returns 503 when rate limit is exceeded
                    logger.warning(f"MusicBrainz API service unavailable (503) - rate limit exceeded - attempt {attempt + 1}/{max_retries}")
                    
                    if attempt < max_retries - 1:
                        # Use shorter backoff for 503 errors since they're rate limit related
                        base_wait = 5  # Start with 5 seconds for 503 errors
                        wait_time = min(base_wait * (backoff_factor ** attempt), max_backoff)
                        
                        jitter = wait_time * 0.2 * (1 - 2 * (time.time() % 1))
                        wait_time += jitter
                        
                        logger.info(f"Service unavailable - waiting {wait_time:.1f} seconds before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"MusicBrainz API service unavailable after {max_retries} attempts - giving up")
                        return None
                elif response.status_code >= 500:
                    # Server errors - retry with exponential backoff
                    logger.warning(f"MusicBrainz API server error {response.status_code} (attempt {attempt + 1}/{max_retries})")
                    
                    if attempt < max_retries - 1:
                        backoff_time = min(backoff_factor ** attempt, max_backoff)
                        jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))
                        backoff_time += jitter
                        logger.info(f"Retrying server error in {backoff_time:.1f} seconds...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        logger.error(f"MusicBrainz API server error after {max_retries} attempts")
                        return None
                else:
                    # Other client errors (4xx) - don't retry
                    logger.warning(f"MusicBrainz API client error {response.status_code}: {response.text[:200]}")
                    return None
                
            except requests.exceptions.Timeout:
                logger.warning(f"MusicBrainz API timeout (attempt {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))
                    backoff_time += jitter
                    logger.info(f"Retrying timeout in {backoff_time:.1f} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"MusicBrainz API timeout after {max_retries} attempts")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"MusicBrainz API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Calculate backoff time with jitter
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))  # Add ±10% jitter
                    backoff_time += jitter
                    logger.info(f"Retrying in {backoff_time:.1f} seconds...")
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
        """Search for a track by artist and title with improved search logic"""
        if not artist or not title:
            return None
        
        # Try multiple search strategies for better results
        search_queries = []
        
        # Strategy 1: Exact match with quotes
        query_parts = [f'artist:"{artist}"', f'recording:"{title}"']
        if album:
            query_parts.append(f'release:"{album}"')
        search_queries.append(" AND ".join(query_parts))
        
        # Strategy 2: Less strict matching
        query_parts = [f'artist:{artist}', f'recording:{title}']
        if album:
            query_parts.append(f'release:{album}')
        search_queries.append(" AND ".join(query_parts))
        
        # Strategy 3: Artist + title only
        search_queries.append(f'artist:"{artist}" AND recording:"{title}"')
        
        # Strategy 4: Simple search
        search_queries.append(f'{artist} {title}')
        
        for query in search_queries:
            params = {
                'query': query,
                'fmt': 'json',
                'limit': 25,  # Increased from 5 to 25 for more comprehensive search results
                'inc': 'tags'
            }
            
            data = self._make_request('recording', params)
            if data and 'recordings' in data and data['recordings']:
                recordings = data['recordings']
                
                # Find the best match
                for recording in recordings:
                    recording_title = recording.get('title', '').lower()
                    recording_artist = ''
                    
                    if 'artist-credit' in recording and recording['artist-credit']:
                        recording_artist = recording['artist-credit'][0].get('artist', {}).get('name', '').lower()
                    
                    # Check if this is a good match
                    if (artist.lower() in recording_artist or recording_artist in artist.lower()) and \
                       (title.lower() in recording_title or recording_title in title.lower()):
                        return recording
                
                # If no exact match, return the first result
                return recordings[0]
        
        return None
    
    def get_track_genre(self, artist: str, title: str, album: str = None) -> Optional[str]:
        """Get genre for a specific track with caching"""
        if not artist or not title:
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(artist, title, album)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for {artist} - {title}")
            return cached_result
        
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
                    genre = tag['name']
                    self._set_cache(cache_key, genre)
                    return genre
        
        # Try to get genre from artist tags
        if 'artist-credit' in track_data and track_data['artist-credit']:
            artist_id = track_data['artist-credit'][0].get('artist', {}).get('id')
            if artist_id:
                genre = self.get_artist_genre(artist_id)
                if genre:
                    self._set_cache(cache_key, genre)
                    return genre
        
        return None
    
    def get_artist_genre(self, artist_id: str) -> Optional[str]:
        """Get genre for a specific artist by ID"""
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
    
    def get_artist_genre_by_name(self, artist: str) -> Optional[str]:
        """Get genre for a specific artist by name"""
        if not artist:
            return None
        
        # Search for artist first
        params = {
            'query': f'artist:"{artist}"',
            'fmt': 'json',
            'limit': 1,
            'inc': 'tags'
        }
        
        data = self._make_request('artist', params)
        if not data or 'artists' not in data or not data['artists']:
            return None
        
        artist_data = data['artists'][0]
        
        # Check if artist has tags
        if 'tags' in artist_data and artist_data['tags']:
            # Sort tags by count
            sorted_tags = sorted(artist_data['tags'], key=lambda x: x.get('count', 0), reverse=True)
            for tag in sorted_tags:
                tag_name = tag.get('name', '').lower()
                if self._is_genre_tag(tag_name):
                    return tag['name']
        
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
            'catchy', 'melodic', 'atmospheric', 'dark', 'uplifting'
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
            'ska', 'reggaeton', 'dancehall', 'grime', 'trap', 'drill'
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
