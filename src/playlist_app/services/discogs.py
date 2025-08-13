#!/usr/bin/env python3
"""
Discogs API Service for genre enrichment
"""

import requests
import time
import logging
from typing import Dict, Optional, List
from urllib.parse import quote

logger = logging.getLogger(__name__)

class DiscogsService:
    """Service for querying Discogs API for genre information"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', 'https://api.discogs.com/')
        self.rate_limit = config.get('rate_limit', 1.0)  # requests per second
        self.timeout = config.get('timeout', 10)
        self.user_agent = config.get('user_agent', 'PlaylistApp/1.0')
        self.enabled = config.get('enabled', True)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 1.0
    
    def _rate_limit(self):
        """Ensure we don't exceed Discogs rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            time.sleep(sleep_time)
        self.last_request_time = time.time()
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to Discogs API with rate limiting"""
        if not self.enabled:
            return None
            
        try:
            self._rate_limit()
            
            url = f"{self.base_url}{endpoint}"
            headers = {
                'User-Agent': self.user_agent
            }
            
            if self.api_key:
                headers['Authorization'] = f'Discogs key={self.api_key}'
            
            response = requests.get(url, headers=headers, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Discogs API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Discogs request: {e}")
            return None
    
    def search_track(self, artist: str, title: str) -> Optional[Dict]:
        """Search for a track by artist and title"""
        if not artist or not title:
            return None
        
        # Build search query
        query = f"{artist} {title}"
        
        params = {
            'q': query,
            'type': 'release',
            'format': 'vinyl,cd,digital',
            'limit': 5
        }
        
        data = self._make_request('database/search', params)
        if not data or 'results' not in data:
            return None
        
        results = data['results']
        if not results:
            return None
        
        # Return the first (most relevant) result
        return results[0]
    
    def get_track_genre(self, artist: str, title: str) -> Optional[str]:
        """Get genre for a specific track using Discogs"""
        track_data = self.search_track(artist, title)
        if not track_data:
            return None
        
        # Check if release has genres
        if 'genre' in track_data and track_data['genre']:
            genres = track_data['genre']
            if isinstance(genres, list) and genres:
                # Return the first genre
                return genres[0]
            elif isinstance(genres, str):
                return genres
        
        # Check if release has styles
        if 'style' in track_data and track_data['style']:
            styles = track_data['style']
            if isinstance(styles, list) and styles:
                # Return the first style (often more specific than genre)
                return styles[0]
            elif isinstance(styles, str):
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
                'latin', 'world', 'experimental', 'soundtrack', 'edm'
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
