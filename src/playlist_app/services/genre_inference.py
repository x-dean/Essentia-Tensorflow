#!/usr/bin/env python3
"""
Genre Inference System
Guesses genres based on album names, artist names, and contextual clues
when external APIs fail to find genres
"""

import re
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class GenreInference:
    """Infers genres based on contextual clues when external APIs fail"""
    
    def __init__(self):
        # Album name patterns that indicate specific genres
        self.album_patterns = {
            'house': [
                # Specific house patterns (highest priority)
                r'deep\s*sexy\s*funky\s*house', r'deep\s*house', r'sexy\s*house', r'funky\s*house', r'funk\s*house',
                r'house\s*classics', r'house\s*hits', r'house\s*anthems', r'house\s*beats', r'house\s*music',
                r'deep\s*funk', r'sexy\s*funk', r'funky\s*deep', r'deep\s*sexy', r'progressive\s*house', r'tech\s*house', r'acid\s*house'
            ],
            'electronic': [
                r'deep\s*&\s*hot', r'electronic', r'edm', r'techno', r'trance',
                r'winter\s*\d{4}', r'spring\s*\d{4}', r'summer\s*\d{4}', r'autumn\s*\d{4}',
                r'dj\s*mix', r'remix', r'original\s*mix', r'club\s*mix', r'radio\s*mix',
                r'extended\s*mix', r'vocal\s*mix', r'instrumental\s*mix'
            ],
            'latin': [
                r'baila\s*reggaeton', r'reggaeton', r'salsa', r'bachata', r'merengue',
                r'cumbia', r'ranchera', r'mariachi', r'bolero', r'tango', r'flamenco',
                r'latin\s*pop', r'latin\s*ballad', r'latino', r'hispanic'
            ],
            'african': [
                r'african', r'afrobeat', r'highlife', r'hiplife', r'kwaito', r'makossa',
                r'mbalax', r'soukous', r'raï', r'jùjú', r'fuji', r'apala', r'benga'
            ],
            'world': [
                r'world\s*music', r'worldbeat', r'ethnic', r'global', r'international',
                r'traditional', r'folk\s*world', r'celtic\s*world', r'middle\s*eastern',
                r'arabic', r'indian\s*classical', r'hindustani', r'carnatic'
            ],
            'hip hop': [
                r'rap\s*hits', r'hip\s*hop', r'trap', r'drill', r'grime', r'underground',
                r'golden\s*age', r'new\s*school', r'old\s*school', r'conscious\s*rap'
            ],
            'rock': [
                r'rock\s*hits', r'hard\s*rock', r'alternative\s*rock', r'punk\s*rock',
                r'classic\s*rock', r'progressive\s*rock', r'psychedelic\s*rock'
            ],
            'metal': [
                r'heavy\s*metal', r'black\s*metal', r'death\s*metal', r'thrash\s*metal',
                r'power\s*metal', r'symphonic\s*metal', r'folk\s*metal'
            ],
            'pop': [
                r'pop\s*hits', r'top\s*40', r'chart\s*hits', r'mainstream', r'teen\s*pop',
                r'bubblegum\s*pop', r'adult\s*contemporary'
            ],
            'jazz': [
                r'jazz', r'bebop', r'swing', r'smooth\s*jazz', r'fusion', r'cool\s*jazz',
                r'hard\s*bop', r'free\s*jazz', r'acid\s*jazz'
            ],
            'classical': [
                r'classical', r'orchestral', r'symphony', r'opera', r'ballet', r'baroque',
                r'chamber\s*music', r'string\s*quartet', r'concerto'
            ],
            'country': [
                r'country\s*hits', r'bluegrass', r'honky\s*tonk', r'western', r'americana',
                r'nashville', r'texas\s*country', r'outlaw\s*country'
            ],
            'folk': [
                r'folk', r'traditional', r'celtic', r'american\s*folk', r'british\s*folk',
                r'contemporary\s*folk', r'progressive\s*folk'
            ],
            'blues': [
                r'blues', r'delta\s*blues', r'chicago\s*blues', r'electric\s*blues',
                r'rhythm\s*&\s*blues', r'soul\s*blues', r'piano\s*blues'
            ],
            'r&b': [
                r'r&b', r'rhythm\s*and\s*blues', r'soul', r'neo\s*soul',
                r'contemporary\s*r&b', r'blue\s*eyed\s*soul'
                # Removed 'funk' from r&b patterns to avoid conflicts with house music
            ],
            'reggae': [
                r'reggae', r'roots\s*reggae', r'dancehall', r'ska', r'dub', r'rocksteady',
                r'raggamuffin', r'ragga'
            ]
        }
        
        # Artist name patterns that indicate specific genres
        self.artist_patterns = {
            'electronic': [
                r'dj\s+', r'producer', r'remixer', r'electronic', r'techno', r'house',
                r'trance', r'ambient', r'industrial', r'experimental'
            ],
            'latin': [
                r'profeta', r'yao', r'aguila', r'gogo', r'latin', r'hispanic',
                r'spanish', r'portuguese', r'brazilian', r'mexican'
            ],
            'african': [
                r'aman', r'remzie', r'aurela', r'african', r'afro', r'highlife',
                r'kwaito', r'makossa', r'mbalax', r'soukous'
            ],
            'hip hop': [
                r'mc\s+', r'rapper', r'hip\s*hop', r'trap', r'drill', r'grime',
                r'underground', r'conscious', r'political'
            ],
            'rock': [
                r'rock', r'punk', r'metal', r'grunge', r'alternative', r'progressive',
                r'psychedelic', r'garage', r'hardcore'
            ],
            'jazz': [
                r'jazz', r'bebop', r'swing', r'fusion', r'cool', r'hard\s*bop',
                r'free\s*jazz', r'acid\s*jazz', r'smooth\s*jazz'
            ]
        }
        
        # Title patterns that indicate specific genres
        self.title_patterns = {
            'electronic': [
                r'original\s*mix', r'remix', r'club\s*mix', r'radio\s*mix',
                r'extended\s*mix', r'vocal\s*mix', r'instrumental\s*mix',
                r'deep\s*mix', r'progressive\s*mix', r'tech\s*mix'
            ],
            'latin': [
                r'reggaeton', r'salsa', r'bachata', r'merengue', r'cumbia',
                r'ranchera', r'tango', r'flamenco', r'latino'
            ],
            'african': [
                r'afrobeat', r'highlife', r'hiplife', r'kwaito', r'makossa',
                r'mbalax', r'soukous', r'raï', r'jùjú'
            ]
        }
        
        # Compile regex patterns for efficiency
        self.compiled_album_patterns = {}
        self.compiled_artist_patterns = {}
        self.compiled_title_patterns = {}
        
        for genre, patterns in self.album_patterns.items():
            self.compiled_album_patterns[genre] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        for genre, patterns in self.artist_patterns.items():
            self.compiled_artist_patterns[genre] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        for genre, patterns in self.title_patterns.items():
            self.compiled_title_patterns[genre] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def infer_genre(self, artist: str, title: str, album: str) -> Optional[str]:
        """Infer genre based on contextual clues"""
        if not artist and not title and not album:
            return None
        
        # Score each genre based on matches
        genre_scores = {}
        
        # Check album patterns (highest weight)
        if album:
            album_lower = album.lower()
            for genre, patterns in self.compiled_album_patterns.items():
                score = 0
                for pattern in patterns:
                    if pattern.search(album_lower):
                        score += 3  # High weight for album matches
                if score > 0:
                    genre_scores[genre] = genre_scores.get(genre, 0) + score
        
        # Check artist patterns (medium weight)
        if artist:
            artist_lower = artist.lower()
            for genre, patterns in self.compiled_artist_patterns.items():
                score = 0
                for pattern in patterns:
                    if pattern.search(artist_lower):
                        score += 2  # Medium weight for artist matches
                if score > 0:
                    genre_scores[genre] = genre_scores.get(genre, 0) + score
        
        # Check title patterns (lowest weight)
        if title:
            title_lower = title.lower()
            for genre, patterns in self.compiled_title_patterns.items():
                score = 0
                for pattern in patterns:
                    if pattern.search(title_lower):
                        score += 1  # Low weight for title matches
                if score > 0:
                    genre_scores[genre] = genre_scores.get(genre, 0) + score
        
        # Return the genre with the highest score
        if genre_scores:
            best_genre = max(genre_scores.items(), key=lambda x: x[1])
            if best_genre[1] >= 2:  # Minimum confidence threshold
                logger.info(f"Inferred genre '{best_genre[0]}' for '{artist} - {title}' (score: {best_genre[1]})")
                return best_genre[0]
        
        return None
    
    def get_inference_confidence(self, artist: str, title: str, album: str) -> Dict[str, float]:
        """Get confidence scores for all possible genres"""
        if not artist and not title and not album:
            return {}
        
        genre_scores = {}
        
        # Calculate scores for all genres
        all_patterns = {
            'album': self.compiled_album_patterns,
            'artist': self.compiled_artist_patterns,
            'title': self.compiled_title_patterns
        }
        
        weights = {'album': 3, 'artist': 2, 'title': 1}
        
        for source, patterns_dict in all_patterns.items():
            text = ''
            if source == 'album' and album:
                text = album.lower()
            elif source == 'artist' and artist:
                text = artist.lower()
            elif source == 'title' and title:
                text = title.lower()
            
            if text:
                for genre, patterns in patterns_dict.items():
                    score = 0
                    for pattern in patterns:
                        if pattern.search(text):
                            score += weights[source]
                    if score > 0:
                        genre_scores[genre] = genre_scores.get(genre, 0) + score
        
        # Normalize scores to 0-1 range
        if genre_scores:
            max_score = max(genre_scores.values())
            return {genre: score / max_score for genre, score in genre_scores.items()}
        
        return {}
