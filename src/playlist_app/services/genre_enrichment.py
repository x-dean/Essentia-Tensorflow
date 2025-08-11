#!/usr/bin/env python3
"""
Genre Enrichment Manager - Orchestrates multiple API services for genre detection
"""

import logging
from typing import Dict, Optional
from .musicbrainz import musicbrainz_service
from .lastfm import LastFMService
from .discogs import DiscogsService
from ..core.config_loader import config_loader

logger = logging.getLogger(__name__)

class GenreEnrichmentManager:
    """Manages genre enrichment using multiple API services in fallback order"""
    
    def __init__(self):
        self.app_config = config_loader.get_app_settings()
        self.external_apis_config = self.app_config.get('external_apis', {})
        
        # Initialize services
        self.musicbrainz_service = musicbrainz_service
        self.lastfm_service = LastFMService(self.external_apis_config.get('lastfm', {}))
        self.discogs_service = DiscogsService(self.external_apis_config.get('discogs', {}))
        
        # Service priority order (first to try, then fallback)
        self.services = [
            ('MusicBrainz', self.musicbrainz_service),
            ('Last.fm', self.lastfm_service),
            ('Discogs', self.discogs_service)
        ]
    
    def enrich_metadata(self, metadata: Dict) -> Dict:
        """Enrich metadata with genre information using multiple services"""
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
        
        logger.info(f"Starting genre enrichment for: {artist} - {title}")
        
        # Try each service in order until we find a genre
        for service_name, service in self.services:
            try:
                logger.info(f"Trying {service_name} for genre enrichment...")
                
                # Use the service's enrich_metadata method
                enriched_metadata = service.enrich_metadata(metadata.copy())
                
                # Check if we got a new genre
                new_genre = enriched_metadata.get('genre', '').lower()
                if new_genre and new_genre not in ['other', 'unknown', 'none', '']:
                    metadata['genre'] = enriched_metadata['genre']
                    logger.info(f"✓ Found genre '{enriched_metadata['genre']}' using {service_name}")
                    return metadata
                else:
                    logger.info(f"✗ No genre found using {service_name}")
                    
            except Exception as e:
                logger.warning(f"Error using {service_name} for genre enrichment: {e}")
                continue
        
        logger.warning(f"No genre found for {artist} - {title} using any service")
        return metadata
    
    def get_service_status(self) -> Dict:
        """Get status of all genre enrichment services"""
        status = {}
        
        for service_name, service in self.services:
            if service_name == 'MusicBrainz':
                status[service_name] = {
                    'enabled': True,  # MusicBrainz is always enabled
                    'configured': True
                }
            elif hasattr(service, 'enabled'):
                status[service_name] = {
                    'enabled': service.enabled,
                    'configured': bool(service.api_key) if hasattr(service, 'api_key') else True
                }
            else:
                status[service_name] = {
                    'enabled': True,
                    'configured': True
                }
        
        return status
    
    def test_services(self, artist: str = "Coldplay", title: str = "Yellow") -> Dict:
        """Test all genre enrichment services with a sample track"""
        results = {}
        
        for service_name, service in self.services:
            try:
                logger.info(f"Testing {service_name}...")
                
                # Create test metadata
                test_metadata = {
                    'artist': artist,
                    'title': title,
                    'genre': 'other'
                }
                
                # Test the service
                enriched_metadata = service.enrich_metadata(test_metadata.copy())
                
                # Check result
                new_genre = enriched_metadata.get('genre', '').lower()
                if new_genre and new_genre not in ['other', 'unknown', 'none', '']:
                    results[service_name] = {
                        'status': 'success',
                        'genre_found': enriched_metadata['genre'],
                        'error': None
                    }
                else:
                    results[service_name] = {
                        'status': 'no_genre_found',
                        'genre_found': None,
                        'error': None
                    }
                    
            except Exception as e:
                results[service_name] = {
                    'status': 'error',
                    'genre_found': None,
                    'error': str(e)
                }
        
        return results

# Global instance
genre_enrichment_manager = GenreEnrichmentManager()
