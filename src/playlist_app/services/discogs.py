#!/usr/bin/env python3
"""
Discogs API Service for genre enrichment
Enhanced with proper rate limiting using Discogs API headers
"""

import logging
import time
import requests
from typing import Dict, Optional
from ..core.config_loader import config_loader

logger = logging.getLogger(__name__)

class DiscogsService:
    """Discogs API service for genre enrichment with proper rate limiting"""
    
    def __init__(self, config: Dict):
        self.enabled = config.get('enabled', True)
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', 'https://api.discogs.com/')
        self.user_agent = config.get('user_agent', 'PlaylistApp/1.0')
        self.timeout = config.get('timeout', 10)
        
        # Rate limiting settings
        self.rate_limit = config.get('rate_limit', 1.2)  # Increased from 1.0 to 1.2
        self.min_request_interval = 1.0 / self.rate_limit
        self.last_request_time = 0
        
        # Rate limit tracking from API headers
        self.rate_limit_total = 60  # Default for authenticated requests
        self.rate_limit_used = 0
        self.rate_limit_remaining = 60
        self.rate_limit_window_start = time.time()
        
        # Retry settings
        self.retry_settings = config.get('retry_settings', {
            "max_retries": 5,  # Increased from 3 to 5
            "backoff_factor": 2,
            "max_backoff": 120  # Increased from 60 to 120
        })
        
        # Cache settings
        self.cache_settings = config.get('cache_settings', {
            "enabled": True,
            "ttl_seconds": 3600
        })
        
        # Simple in-memory cache for optimization
        self._cache = {}
        self._cache_timestamps = {}
    
    def _get_cache_key(self, artist: str, title: str) -> str:
        """Generate cache key for track lookup"""
        return f"{artist.lower().strip()}|{title.lower().strip()}"
    
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
    
    def _update_rate_limits_from_headers(self, headers: Dict):
        """Update rate limit tracking from Discogs API response headers"""
        try:
            # Update rate limit information from headers
            if 'X-Discogs-Ratelimit' in headers:
                self.rate_limit_total = int(headers['X-Discogs-Ratelimit'])
            
            if 'X-Discogs-Ratelimit-Used' in headers:
                self.rate_limit_used = int(headers['X-Discogs-Ratelimit-Used'])
            
            if 'X-Discogs-Ratelimit-Remaining' in headers:
                self.rate_limit_remaining = int(headers['X-Discogs-Ratelimit-Remaining'])
                
            # Reset window if we're starting fresh
            if self.rate_limit_used == 1:
                self.rate_limit_window_start = time.time()
                
        except (ValueError, KeyError) as e:
            logger.debug(f"Error parsing rate limit headers: {e}")
    
    def _should_throttle(self) -> bool:
        """Check if we should throttle based on rate limit remaining"""
        # If we have very few requests remaining, throttle more aggressively
        if self.rate_limit_remaining <= 5:
            return True
        
        # If we're using more than 80% of our rate limit, throttle
        if self.rate_limit_used > (self.rate_limit_total * 0.8):
            return True
        
        return False
    
    def _calculate_throttle_delay(self) -> float:
        """Calculate how long to wait before next request"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Base interval from config
        base_interval = self.min_request_interval
        
        # If we should throttle, increase the delay
        if self._should_throttle():
            # More aggressive throttling when rate limit is low
            if self.rate_limit_remaining <= 2:
                base_interval *= 3  # Wait 3x longer
            elif self.rate_limit_remaining <= 5:
                base_interval *= 2  # Wait 2x longer
            else:
                base_interval *= 1.5  # Wait 1.5x longer
        
        # Ensure minimum interval is respected
        if time_since_last < base_interval:
            return base_interval - time_since_last
        
        return 0
    
    def _rate_limit(self):
        """Ensure we don't exceed Discogs rate limits with proper throttling"""
        delay = self._calculate_throttle_delay()
        if delay > 0:
            logger.debug(f"Rate limiting: waiting {delay:.2f} seconds (remaining: {self.rate_limit_remaining})")
            time.sleep(delay)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to Discogs API with proper rate limiting and retry logic"""
        if not self.enabled:
            return None
        
        max_retries = self.retry_settings.get("max_retries", 5)  # Increased from 3 to 5
        backoff_factor = self.retry_settings.get("backoff_factor", 2)
        max_backoff = self.retry_settings.get("max_backoff", 120)  # Increased from 60 to 120
        
        for attempt in range(max_retries):
            try:
                self._rate_limit()
                
                url = f"{self.base_url}{endpoint}"
                headers = {
                    'User-Agent': self.user_agent
                }
                
                # Fix: Use correct authentication format according to Discogs API docs
                if self.api_key:
                    headers['Authorization'] = f'Discogs token={self.api_key}'
                
                response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
                
                # Update rate limit tracking from response headers
                self._update_rate_limits_from_headers(response.headers)
                
                # Handle different response codes appropriately
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error(f"Discogs API authentication failed (401): Invalid API key or authentication")
                    logger.error(f"URL: {url}")
                    return None  # Don't retry on auth errors
                elif response.status_code == 404:
                    logger.debug(f"Discogs API: Resource not found (404) for {url}")
                    return None  # Don't retry on 404 errors
                elif response.status_code == 429:
                    logger.warning(f"Discogs API rate limit exceeded (429) - attempt {attempt + 1}/{max_retries}")
                    logger.warning(f"Rate limit: {self.rate_limit_used}/{self.rate_limit_total} used, {self.rate_limit_remaining} remaining")
                    
                    # Check if we have retry attempts left
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
                        logger.error(f"Discogs API rate limit exceeded after {max_retries} attempts - giving up")
                        return None
                elif response.status_code >= 500:
                    # Server errors - retry with exponential backoff
                    logger.warning(f"Discogs API server error {response.status_code} (attempt {attempt + 1}/{max_retries})")
                    
                    if attempt < max_retries - 1:
                        backoff_time = min(backoff_factor ** attempt, max_backoff)
                        jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))
                        backoff_time += jitter
                        logger.info(f"Retrying server error in {backoff_time:.1f} seconds...")
                        time.sleep(backoff_time)
                        continue
                    else:
                        logger.error(f"Discogs API server error after {max_retries} attempts")
                        return None
                else:
                    # Other client errors (4xx) - don't retry
                    logger.warning(f"Discogs API client error {response.status_code}: {response.text[:200]}")
                    return None
                
            except requests.exceptions.Timeout:
                logger.warning(f"Discogs API timeout (attempt {attempt + 1}/{max_retries})")
                
                if attempt < max_retries - 1:
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))
                    backoff_time += jitter
                    logger.info(f"Retrying timeout in {backoff_time:.1f} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Discogs API timeout after {max_retries} attempts")
                    return None
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Discogs API request failed (attempt {attempt + 1}/{max_retries}): {e}")
                
                if attempt < max_retries - 1:
                    # Calculate backoff time with jitter
                    backoff_time = min(backoff_factor ** attempt, max_backoff)
                    jitter = backoff_time * 0.1 * (1 - 2 * (time.time() % 1))  # Add ±10% jitter
                    backoff_time += jitter
                    logger.info(f"Retrying in {backoff_time:.1f} seconds...")
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(f"Discogs API request failed after {max_retries} attempts: {e}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error in Discogs request: {e}")
                return None
        
        return None
    
    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        """Search for a track by artist and title with improved search logic"""
        if not artist or not title:
            return None
        
        logger.info(f"Querying Discogs for genre: {artist} - {title}")
        
        # Build search query - try different search strategies
        search_queries = [
            f"{artist} {title}",  # Artist + Title
            f'"{artist}" "{title}"',  # Exact match
            f"{artist} - {title}",  # Artist - Title format
            f"{artist} {title} single",  # Add format hint
            f"{artist} {title} album",  # Add format hint
        ]
        
        for i, query in enumerate(search_queries, 1):
            logger.debug(f"Discogs search strategy {i}: {query}")
            
            params = {
                'q': query,
                'type': 'release',
                'limit': 25  # Increased from 5 to 25 for more comprehensive search results
            }
            
            data = self._make_request('database/search', params)
            if data and 'results' in data and data['results']:
                results = data['results']
                logger.debug(f"Found {len(results)} results for query: {query}")
                
                # Find the best match by checking if artist and title are in the result
                for result in results:
                    result_title = result.get('title', '').lower()
                    result_artist = result.get('artist', '').lower()
                    
                    # Check if both artist and title are present in the result
                    if (artist.lower() in result_artist or result_artist in artist.lower()) and \
                       (title.lower() in result_title or result_title in title.lower()):
                        logger.debug(f"Found exact match: {result.get('title', 'Unknown')}")
                        return result
                
                # If no exact match found, return the first result
                logger.debug(f"Using first result: {results[0].get('title', 'Unknown')}")
                return results[0]
            else:
                logger.debug(f"No results found for query: {query}")
        
        logger.warning(f"No genre found for {artist} - {title}")
        return None
    
    def get_track_genre(self, artist: str, title: str) -> Optional[str]:
        """Get genre for a specific track using Discogs with caching"""
        if not artist or not title:
            return None
        
        # Check cache first
        cache_key = self._get_cache_key(artist, title)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for {artist} - {title}")
            return cached_result
        
        track_data = self.search_track(artist, title)
        if not track_data:
            return None
        
        # Check if release has genres
        if 'genre' in track_data and track_data['genre']:
            genres = track_data['genre']
            if isinstance(genres, list) and genres:
                # Return the first genre
                genre = genres[0]
                self._set_cache(cache_key, genre)
                return genre
            elif isinstance(genres, str):
                self._set_cache(cache_key, genres)
                return genres
        
        # Check if release has styles
        if 'style' in track_data and track_data['style']:
            styles = track_data['style']
            if isinstance(styles, list) and styles:
                # Return the first style (often more specific than genre)
                style = styles[0]
                self._set_cache(cache_key, style)
                return style
            elif isinstance(styles, str):
                self._set_cache(cache_key, styles)
                return styles
        
        return None
    
    def get_artist_genre(self, artist: str) -> Optional[str]:
        """Get genre for a specific artist using Discogs"""
        if not artist:
            return None
        
        # Search for artist
        params = {
            'q': artist,
            'type': 'artist',
            'limit': 1
        }
        
        data = self._make_request('database/search', params)
        if not data or 'results' not in data or not data['results']:
            return None
        
        artist_data = data['results'][0]
        
        # Get artist details
        artist_id = artist_data.get('id')
        if not artist_id:
            return None
        
        artist_details = self._make_request(f'artists/{artist_id}')
        if not artist_details:
            return None
        
        # Check for genres in artist profile
        if 'profile' in artist_details:
            profile = artist_details['profile']
            # Look for genre mentions in the profile text
            profile_lower = profile.lower()
            
            genre_keywords = [
                'rock', 'pop', 'electronic', 'hip hop', 'jazz', 'classical',
                'country', 'folk', 'blues', 'reggae', 'punk', 'metal',
                'dance', 'house', 'trance', 'techno', 'dubstep', 'ambient',
                'indie', 'alternative', 'r&b', 'soul', 'funk', 'disco',
                'latin', 'world', 'experimental', 'soundtrack', 'edm',
                'progressive', 'deep', 'minimal', 'tech', 'acid', 'hardcore'
            ]
            
            for keyword in genre_keywords:
                if keyword in profile_lower:
                    return keyword.title()
        
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
            'awesome', 'beautiful', 'amazing', 'great'
        }
        
        if tag_name.lower() in non_genre_tags:
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
        
        return any(indicator in tag_name.lower() for indicator in genre_indicators)
    
    def enrich_metadata(self, metadata: Dict) -> Dict:
        """Enrich metadata with genre information from Discogs"""
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
        
        logger.info(f"Querying Discogs for genre: {artist} - {title}")
        
        genre = self.get_track_genre(artist, title)
        if genre:
            metadata['genre'] = genre
            logger.info(f"Found genre '{genre}' for {artist} - {title}")
        else:
            logger.warning(f"No genre found for {artist} - {title}")
        
        return metadata

