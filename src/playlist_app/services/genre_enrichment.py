#!/usr/bin/env python3
"""
Genre Enrichment Manager - Orchestrates multiple API services for genre detection
Uses weighted scoring system for optimal genre selection with genre normalization
"""

import logging
import re
from typing import Dict, Optional, List, Tuple
from .musicbrainz import musicbrainz_service
from .lastfm import LastFMService
from .discogs import DiscogsService
from .genre_normalizer import GenreNormalizer
from .genre_inference import GenreInference
from ..core.config_loader import config_loader

logger = logging.getLogger(__name__)

class GenreEnrichmentManager:
    """Manages genre enrichment using multiple API services with weighted scoring
    Searches all services and selects the best result based on confidence scores"""
    
    def __init__(self):
        # Use get_external_config() instead of get_app_settings() to get the external_apis section
        self.external_apis_config = config_loader.get_external_config()
        
        # Initialize services
        self.musicbrainz_service = musicbrainz_service
        self.lastfm_service = LastFMService(self.external_apis_config.get('lastfm', {}))
        self.discogs_service = DiscogsService(self.external_apis_config.get('discogs', {}))
        
        # Initialize genre normalizer and inference system
        self.genre_normalizer = GenreNormalizer()
        self.genre_inference = GenreInference()
        
        # Service configuration with weights and characteristics
        # Higher weight = higher priority in selection
        self.services = [
            {
                'name': 'Discogs',
                'service': self.discogs_service,
                'weight': 0.4,  # Highest weight - most reliable for genre accuracy
                'description': 'Broad categories, excellent genre accuracy, good for electronic/hip-hop'
            },
            {
                'name': 'Last.fm',
                'service': self.lastfm_service,
                'weight': 0.35,  # High weight - consistent, playlist-friendly genres
                'description': 'Consistent genres, good for mainstream music'
            },
            {
                'name': 'MusicBrainz',
                'service': self.musicbrainz_service,
                'weight': 0.25,  # Lower weight - detailed but sometimes inconsistent
                'description': 'Detailed genres, good for classical/jazz, sometimes too specific'
            }
        ]
        
        logger.info("Genre Enrichment Manager initialized with weighted scoring system, genre normalization, and inference:")
        for service in self.services:
            logger.info(f"  {service['name']} (Weight: {service['weight']}) - {service['description']}")
        logger.info(f"  Genre Normalizer: {len(self.genre_normalizer.get_canonical_genres())} canonical genres supported")
        logger.info(f"  Genre Inference: Context-based genre guessing when APIs fail")
    
    def _validate_genre_consistency(self, artist: str, title: str, album: str, genre: str) -> bool:
        """Validate if the genre makes sense for the given track"""
        if not genre:
            return False
        
        genre_lower = genre.lower()
        artist_lower = artist.lower()
        title_lower = title.lower()
        album_lower = album.lower() if album else ""
        
        # Check for obvious inconsistencies
        inconsistencies = []
        
        # House/Electronic context checks
        house_keywords = ['house', 'deep house', 'funk house', 'sexy house', 'funky house']
        if any(keyword in album_lower for keyword in house_keywords):
            if genre_lower in ['pop', 'rock', 'country', 'folk', 'jazz', 'classical', 'r&b', 'soul', 'blues']:
                inconsistencies.append(f"House album but got {genre}")
        
        # Electronic context checks
        electronic_keywords = ['electronic', 'edm', 'dance', 'techno', 'trance', 'deep house', 'progressive']
        if any(keyword in album_lower for keyword in electronic_keywords):
            if genre_lower in ['pop', 'rock', 'country', 'folk', 'jazz', 'classical', 'r&b', 'soul', 'blues']:
                inconsistencies.append(f"Electronic compilation album but got {genre}")
        
        # Rap/Hip Hop context checks
        rap_keywords = ['rap', 'hip hop', 'hip-hop', 'trap', 'drill', 'grime']
        if any(keyword in album_lower for keyword in rap_keywords):
            if genre_lower in ['pop', 'rock', 'electronic', 'dance', 'house', 'techno', 'trance', 'deep house', 'black metal']:
                inconsistencies.append(f"Rap compilation album but got {genre}")
        
        # Artist name genre hints
        if any(keyword in artist_lower for keyword in rap_keywords):
            if genre_lower in ['pop', 'rock', 'electronic', 'dance', 'house', 'techno', 'trance', 'deep house', 'black metal']:
                inconsistencies.append(f"Artist name suggests rap but got {genre}")
        
        # Title genre hints
        if any(keyword in title_lower for keyword in rap_keywords):
            if genre_lower in ['pop', 'rock', 'electronic', 'dance', 'house', 'techno', 'trance', 'deep house', 'black metal']:
                inconsistencies.append(f"Title suggests rap but got {genre}")
        
        # Rock context checks
        rock_keywords = ['rock', 'metal', 'punk', 'grunge', 'alternative']
        if any(keyword in album_lower for keyword in rock_keywords):
            if genre_lower in ['pop', 'hip hop', 'rap', 'electronic', 'dance', 'house', 'techno']:
                inconsistencies.append(f"Rock compilation album but got {genre}")
        
        # Log inconsistencies
        if inconsistencies:
            logger.warning(f"Genre inconsistency detected for {artist} - {title}: {', '.join(inconsistencies)}")
            return False
        
        return True
    
    def _calculate_genre_score(self, genre: str, service_weight: float, artist: str, title: str, album: str) -> float:
        """Calculate a confidence score for a genre result"""
        if not genre:
            return 0.0
        
        # Normalize the genre first
        normalized_genre = self.genre_normalizer.normalize_genre(genre)
        
        # Start with service weight
        score = service_weight
        
        # Boost score for genre consistency
        if self._validate_genre_consistency(artist, title, album, normalized_genre):
            score += 0.2  # Bonus for consistency
        else:
            score -= 0.3  # Penalty for inconsistency
        
        # Boost score for specific, well-known genres
        specific_genres = ['hip hop', 'rap', 'electronic', 'rock', 'pop', 'jazz', 'classical', 'country', 'folk']
        if normalized_genre.lower() in specific_genres:
            score += 0.1
        
        # Penalty for overly specific or unusual genres
        unusual_genres = ['metallica', 'black metal']
        if normalized_genre.lower() in unusual_genres:
            score -= 0.1
        
        # Context-based scoring
        album_lower = album.lower() if album else ""
        artist_lower = artist.lower()
        
        # Boost if genre matches album context - House/Electronic
        if any(keyword in album_lower for keyword in ['house', 'deep house', 'funk house', 'sexy house', 'funky house']):
            if normalized_genre.lower() in ['house', 'electronic', 'dance', 'deep house', 'funk house']:
                score += 0.25  # Strong boost for house albums
            elif normalized_genre.lower() in ['r&b', 'soul', 'blues', 'pop', 'rock', 'country', 'folk', 'jazz', 'classical']:
                score -= 0.4  # Strong penalty for non-electronic genres on house albums
            elif normalized_genre.lower() in ['dubstep', 'techno', 'trance', 'ambient', 'industrial']:
                score -= 0.2  # Penalty for other electronic genres on house albums (house should be preferred)
        
        # Boost if genre matches album context - Electronic
        elif any(keyword in album_lower for keyword in ['electronic', 'edm', 'techno', 'trance', 'progressive']):
            if normalized_genre.lower() in ['electronic', 'dance', 'techno', 'trance', 'progressive', 'house']:
                score += 0.2
            elif normalized_genre.lower() in ['r&b', 'soul', 'blues', 'pop', 'rock', 'country', 'folk', 'jazz', 'classical']:
                score -= 0.3
        
        # Boost if genre matches album context - Rap/Hip Hop
        elif any(keyword in album_lower for keyword in ['rap', 'hip hop', 'hip-hop', 'trap', 'drill', 'grime']):
            if normalized_genre.lower() in ['hip hop', 'rap', 'trap', 'drill', 'grime']:
                score += 0.2
            elif normalized_genre.lower() in ['pop', 'rock', 'electronic', 'dance', 'house', 'techno', 'trance']:
                score -= 0.3
        
        # Boost if genre matches album context - Rock
        elif any(keyword in album_lower for keyword in ['rock', 'metal', 'punk', 'grunge', 'alternative']):
            if normalized_genre.lower() in ['rock', 'metal', 'punk', 'grunge', 'alternative']:
                score += 0.2
            elif normalized_genre.lower() in ['pop', 'hip hop', 'rap', 'electronic', 'dance', 'house', 'techno']:
                score -= 0.3
        
        # General context matching
        elif 'rap' in album_lower and 'hip hop' in normalized_genre.lower():
            score += 0.15
        elif 'electronic' in album_lower and 'electronic' in normalized_genre.lower():
            score += 0.15
        elif 'rock' in album_lower and 'rock' in normalized_genre.lower():
            score += 0.15
        
        return max(0.0, min(1.0, score))  # Clamp between 0 and 1
    
    def _clean_track_title(self, title: str) -> str:
        """Clean track title by removing common suffixes and special characters"""
        if not title:
            return title
        
        # Remove common mix suffixes
        suffixes_to_remove = [
            r'\s*\(original\s*mix\)',
            r'\s*\(remix\)',
            r'\s*\(club\s*mix\)',
            r'\s*\(radio\s*mix\)',
            r'\s*\(extended\s*mix\)',
            r'\s*\(vocal\s*mix\)',
            r'\s*\(instrumental\s*mix\)',
            r'\s*\(deep\s*mix\)',
            r'\s*\(progressive\s*mix\)',
            r'\s*\(tech\s*mix\)',
            r'\s*\(starwaves\s*gold\s*mix\)',
            r'\s*\(miami\s*beach\s*mix\)',
            r'\s*\(lovers\s*mix\)',
            r'\s*\(rhythm\s*code\s*remix\)',
            r'\s*\(aaron\s*king\s*remix\)',
            r'\s*\(mixed\)',
            r'\s*\(feat\.\s*[^)]+\)',
            r'\s*\(featuring\s*[^)]+\)',
            r'\s*\(gogo\s*mix\)',
            r'\s*\(edit\)',
            r'\s*\(radio\s*edit\)',
            r'\s*\(clean\s*version\)',
            r'\s*\(explicit\)',
            r'\s*\(explicit\s*version\)',
            r'\s*\(clean\)',
            r'\s*\(album\s*version\)',
            r'\s*\(single\s*version\)',
            r'\s*\(demo\)',
            r'\s*\(live\)',
            r'\s*\(live\s*version\)',
            r'\s*\(studio\s*version\)',
            r'\s*\(acoustic\)',
            r'\s*\(acoustic\s*version\)',
            r'\s*\(unplugged\)',
            r'\s*\(unplugged\s*version\)',
            r'\s*\(instrumental\)',
            r'\s*\(instrumental\s*version\)',
            r'\s*\(karaoke\)',
            r'\s*\(karaoke\s*version\)',
            r'\s*\(cover\)',
            r'\s*\(cover\s*version\)',
            r'\s*\(reprise\)',
            r'\s*\(outro\)',
            r'\s*\(intro\)',
            r'\s*\(interlude\)',
            r'\s*\(skit\)',
            r'\s*\(bonus\s*track\)',
            r'\s*\(hidden\s*track\)',
            r'\s*\(preview\)',
            r'\s*\(snippet\)',
            r'\s*\(clip\)',
            r'\s*\(short\s*version\)',
            r'\s*\(long\s*version\)',
            r'\s*\(full\s*version\)',
            r'\s*\(part\s*\d+\)',
            r'\s*\(version\s*\d+\)',
            r'\s*\(mix\s*\d+\)',
            r'\s*\(remix\s*\d+\)',
            r'\s*\(dub\)',
            r'\s*\(dub\s*mix\)',
            r'\s*\(dubstep\s*mix\)',
            r'\s*\(house\s*mix\)',
            r'\s*\(techno\s*mix\)',
            r'\s*\(trance\s*mix\)',
            r'\s*\(ambient\s*mix\)',
            r'\s*\(chill\s*mix\)',
            r'\s*\(dance\s*mix\)',
            r'\s*\(electronic\s*mix\)',
            r'\s*\(rock\s*mix\)',
            r'\s*\(pop\s*mix\)',
            r'\s*\(hip\s*hop\s*mix\)',
            r'\s*\(rap\s*mix\)',
            r'\s*\(jazz\s*mix\)',
            r'\s*\(classical\s*mix\)',
            r'\s*\(country\s*mix\)',
            r'\s*\(folk\s*mix\)',
            r'\s*\(blues\s*mix\)',
            r'\s*\(reggae\s*mix\)',
            r'\s*\(punk\s*mix\)',
            r'\s*\(metal\s*mix\)',
            r'\s*\(indie\s*mix\)',
            r'\s*\(alternative\s*mix\)',
            r'\s*\(r&b\s*mix\)',
            r'\s*\(soul\s*mix\)',
            r'\s*\(funk\s*mix\)',
            r'\s*\(disco\s*mix\)',
            r'\s*\(latin\s*mix\)',
            r'\s*\(world\s*mix\)',
            r'\s*\(experimental\s*mix\)',
            r'\s*\(soundtrack\s*mix\)',
            r'\s*\(edm\s*mix\)',
            r'\s*\(progressive\s*mix\)',
            r'\s*\(minimal\s*mix\)',
            r'\s*\(tech\s*mix\)',
            r'\s*\(acid\s*mix\)',
            r'\s*\(hardcore\s*mix\)',
            r'\s*\(thrash\s*mix\)',
            r'\s*\(death\s*mix\)',
            r'\s*\(black\s*mix\)',
            r'\s*\(power\s*mix\)',
            r'\s*\(symphonic\s*mix\)',
            r'\s*\(folk\s*metal\s*mix\)',
            r'\s*\(bluegrass\s*mix\)',
            r'\s*\(americana\s*mix\)',
            r'\s*\(roots\s*mix\)',
            r'\s*\(gospel\s*mix\)',
            r'\s*\(spiritual\s*mix\)',
            r'\s*\(ska\s*mix\)',
            r'\s*\(reggaeton\s*mix\)',
            r'\s*\(dancehall\s*mix\)',
            r'\s*\(grime\s*mix\)',
            r'\s*\(trap\s*mix\)',
            r'\s*\(drill\s*mix\)',
            r'\s*\(electropop\s*mix\)',
            r'\s*\(synthpop\s*mix\)',
            r'\s*\(new\s*wave\s*mix\)',
            r'\s*\(post-punk\s*mix\)',
            r'\s*\(shoegaze\s*mix\)',
            r'\s*\(dream\s*pop\s*mix\)',
            r'\s*\(trip\s*hop\s*mix\)',
            r'\s*\(downtempo\s*mix\)',
            r'\s*\(chillout\s*mix\)',
            r'\s*\(lounge\s*mix\)'
        ]
        
        cleaned = title
        for pattern in suffixes_to_remove:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove special characters but keep spaces and basic punctuation
        cleaned = re.sub(r'[^\w\s\-&\.]', '', cleaned)
        
        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove leading/trailing spaces
        cleaned = cleaned.strip()
        
        return cleaned

    def _get_all_genre_results(self, artist: str, title: str, album: str) -> List[Tuple[str, str, float]]:
        """Get genre results from all services with scores"""
        results = []
        
        # Clean the title for better API matching
        cleaned_title = self._clean_track_title(title)
        if cleaned_title != title:
            logger.info(f"Cleaned title: '{title}' -> '{cleaned_title}'")
        
        for service_config in self.services:
            service_name = service_config['name']
            service = service_config['service']
            weight = service_config['weight']
            
            try:
                logger.info(f"Querying {service_name} for genre...")
                
                # First try artist-track combination
                test_metadata = {
                    'artist': artist,
                    'title': cleaned_title,  # Use cleaned title
                    'album': album,
                    'genre': ''
                }
                
                enriched_metadata = service.enrich_metadata(test_metadata.copy())
                raw_genre = enriched_metadata.get('genre', '').lower()
                
                # If no genre found from artist-track, try artist-only
                if not raw_genre or raw_genre in ['other', 'unknown', 'none', '']:
                    logger.info(f"  {service_name}: No genre from artist-track, trying artist-only...")
                    
                    # Try artist-only query
                    if hasattr(service, 'get_artist_genre'):
                        if service_name == 'MusicBrainz':
                            # MusicBrainz has a specific method for artist name queries
                            artist_genre = service.get_artist_genre_by_name(artist)
                        else:
                            # Other services use the standard get_artist_genre method
                            artist_genre = service.get_artist_genre(artist)
                        
                        if artist_genre:
                            raw_genre = artist_genre.lower()
                            logger.info(f"  {service_name}: Found artist genre: {artist_genre}")
                
                if raw_genre and raw_genre not in ['other', 'unknown', 'none', '']:
                    # Normalize the genre
                    normalized_genre = self.genre_normalizer.normalize_genre(raw_genre)
                    
                    if normalized_genre != raw_genre:
                        logger.info(f"  {service_name}: {raw_genre} -> {normalized_genre}")
                    
                    score = self._calculate_genre_score(normalized_genre, weight, artist, title, album)
                    results.append((service_name, normalized_genre, score))
                    logger.info(f"  {service_name}: {normalized_genre} (score: {score:.3f})")
                else:
                    logger.info(f"  {service_name}: No genre found")
                    
            except Exception as e:
                logger.warning(f"Error querying {service_name}: {e}")
                continue
        
        return results
    
    def enrich_metadata(self, metadata: Dict) -> Dict:
        """Enrich metadata with genre information using weighted scoring
        Searches all services and selects the best result based on confidence scores"""
        if not metadata:
            return metadata
        
        # Skip if we already have a good genre
        current_genre = metadata.get('genre', '').lower()
        if current_genre and current_genre not in ['other', 'unknown', 'none', '']:
            # Normalize existing genre
            normalized_genre = self.genre_normalizer.normalize_genre(current_genre)
            if normalized_genre != current_genre:
                logger.info(f"Normalizing existing genre: '{current_genre}' -> '{normalized_genre}'")
                metadata['genre'] = normalized_genre
            return metadata
        
        artist = metadata.get('artist')
        title = metadata.get('title')
        album = metadata.get('album', '')
        
        if not artist or not title:
            return metadata
        
        logger.info(f"Starting weighted genre enrichment for: {artist} - {title}")
        
        # Get results from all services
        results = self._get_all_genre_results(artist, title, album)
        
        if not results:
            logger.warning(f"No genre found for {artist} - {title} using any service")
            
            # Try genre inference as fallback
            logger.info(f"Attempting genre inference for {artist} - {title}")
            inferred_genre = self.genre_inference.infer_genre(artist, title, album)
            
            if inferred_genre:
                logger.info(f"Inferred genre '{inferred_genre}' for {artist} - {title}")
                metadata['genre'] = inferred_genre
                return metadata
            else:
                logger.warning(f"No genre could be inferred for {artist} - {title}")
                return metadata
        
        # Check if we have a genre inference result that matches the album context
        inferred_genre = self.genre_inference.infer_genre(artist, title, album)
        if inferred_genre:
            logger.info(f"Genre inference result: '{inferred_genre}' for {artist} - {title}")
            
            # Check if the inferred genre matches the album context
            album_lower = album.lower() if album else ""
            context_match = False
            
            if any(keyword in album_lower for keyword in ['house', 'deep house', 'funk house', 'sexy house', 'funky house']):
                if inferred_genre.lower() in ['house', 'electronic', 'dance', 'deep house', 'funk house']:
                    context_match = True
            elif any(keyword in album_lower for keyword in ['electronic', 'edm', 'techno', 'trance', 'progressive']):
                if inferred_genre.lower() in ['electronic', 'dance', 'techno', 'trance', 'progressive', 'house']:
                    context_match = True
            elif any(keyword in album_lower for keyword in ['rap', 'hip hop', 'hip-hop', 'trap', 'drill', 'grime']):
                if inferred_genre.lower() in ['hip hop', 'rap', 'trap', 'drill', 'grime']:
                    context_match = True
            elif any(keyword in album_lower for keyword in ['rock', 'metal', 'punk', 'grunge', 'alternative']):
                if inferred_genre.lower() in ['rock', 'metal', 'punk', 'grunge', 'alternative']:
                    context_match = True
            
            # If inferred genre matches context, give it a high score
            if context_match:
                inferred_score = 0.8  # High base score for context-matching inference
                results.append(('Genre Inference', inferred_genre, inferred_score))
                logger.info(f"Added context-matching inferred genre '{inferred_genre}' with score {inferred_score}")
        
        # Sort by score (highest first)
        results.sort(key=lambda x: x[2], reverse=True)
        
        # Select the best result
        best_service, best_genre, best_score = results[0]
        
        logger.info(f"Selected '{best_genre}' from {best_service} (score: {best_score:.3f})")
        
        # Log all results for transparency
        if len(results) > 1:
            logger.info("All results:")
            for service, genre, score in results:
                logger.info(f"  {service}: {genre} (score: {score:.3f})")
        
        metadata['genre'] = best_genre
        return metadata
    
    def get_service_status(self) -> Dict:
        """Get status of all genre enrichment services"""
        status = {}
        
        for service_config in self.services:
            service_name = service_config['name']
            service = service_config['service']
            
            if service_name == 'MusicBrainz':
                status[service_name] = {
                    'enabled': True,  # MusicBrainz is always enabled
                    'configured': True,
                    'priority': 'secondary'
                }
            elif service_name == 'Last.fm':
                status[service_name] = {
                    'enabled': service.enabled if hasattr(service, 'enabled') else True,
                    'configured': bool(service.api_key) if hasattr(service, 'api_key') else True,
                    'priority': 'primary'
                }
            elif service_name == 'Discogs':
                status[service_name] = {
                    'enabled': service.enabled if hasattr(service, 'enabled') else True,
                    'configured': bool(service.api_key) if hasattr(service, 'api_key') else True,
                    'priority': 'tertiary'
                }
            else:
                status[service_name] = {
                    'enabled': True,
                    'configured': True,
                    'priority': 'unknown'
                }
        
        return status
    
    def test_services(self, artist: str = "Coldplay", title: str = "Yellow") -> Dict:
        """Test all genre enrichment services with a sample track"""
        results = {}
        
        for service_config in self.services:
            service_name = service_config['name']
            service = service_config['service']
            
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
    
    def get_primary_service(self):
        """Get the primary service (Last.fm) for direct access"""
        return self.lastfm_service
    
    def get_service_by_name(self, service_name: str):
        """Get a specific service by name"""
        service_map = {
            'lastfm': self.lastfm_service,
            'musicbrainz': self.musicbrainz_service,
            'discogs': self.discogs_service
        }
        return service_map.get(service_name.lower())

# Global instance
genre_enrichment_manager = GenreEnrichmentManager()
