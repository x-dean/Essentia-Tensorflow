#!/usr/bin/env python3
"""
Genre Normalization System
Based on beets lastgenre genres-tree.yaml structure
Handles common genre variations and standardizes to canonical forms
"""

import re
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

class GenreNormalizer:
    """Normalizes genre names to standard canonical forms"""
    
    def __init__(self):
        # Core genre mappings based on beets lastgenre structure
        # Focus on the most common genres and their variations
        self.genre_mappings = {
            # Hip Hop variations
            'hip hop': [
                'hip-hop', 'hiphop', 'hip hop', 'rap', 'trap', 'drill', 'grime',
                'alternative hip hop', 'conscious hip hop', 'gangsta rap', 'golden age hip hop',
                'new school hip hop', 'old school hip hop', 'underground hip hop',
                'east coast hip hop', 'west coast hip hop', 'southern hip hop',
                'hardcore hip hop', 'jazz rap', 'political hip hop', 'hip hop soul'
            ],
            
            # Electronic variations
            'electronic': [
                'electronica', 'edm', 'electronic dance music', 'ambient', 'ambient house',
                'ambient techno', 'breakbeat', 'big beat', 'breakbeat garage', 'breakstep',
                'drum and bass', 'drum & bass', 'jungle', 'liquid funk', 'neurofunk',
                'dubstep', 'post-dubstep', 'future garage', 'uk garage', '2-step garage',
                'speed garage', 'bassline', 'grime', 'dub', 'dub techno', 'minimal',
                'microhouse', 'tech house', 'acid techno', 'detroit techno', 'minimal techno',
                'trance', 'acid trance', 'goa trance', 'psytrance', 'uplifting trance',
                'hardcore', 'gabber', 'happy hardcore', 'hardstyle', 'speedcore',
                'industrial', 'electro-industrial', 'industrial metal', 'industrial rock',
                'noise', 'power electronics', 'witch house', 'synthpop', 'synthpunk', 
                'indietronica', 'new rave'
            ],
            
            # House variations (separate from electronic)
            'house': [
                'acid house', 'deep house', 'progressive house', 'tech house',
                'chicago house', 'detroit house', 'french house', 'italian house',
                'latin house', 'microhouse', 'minimal house', 'tropical house',
                'future house', 'electro house', 'dutch house', 'swedish house',
                'vocal house', 'soulful house', 'gospel house', 'jazz house',
                'afro house', 'tribal house', 'funky house', 'disco house'
            ],
            
            # Rock variations
            'rock': [
                'rock n roll', 'rock & roll', 'rock and roll', 'hard rock',
                'alternative rock', 'art rock', 'beat music', 'chinese rock',
                'experimental rock', 'folk rock', 'garage rock', 'glam rock',
                'math rock', 'new wave', 'pop rock', 'post-punk', 'power pop',
                'progressive rock', 'psychedelic rock', 'acid rock', 'raga rock',
                'punk rock', 'anarcho punk', 'art punk', 'folk punk', 'garage punk',
                'hardcore punk', 'pop punk', 'ska punk', 'surf rock',
                'southern rock', 'stoner rock', 'mathcore', 'djent'
            ],
            
            # Metal variations (subset of rock)
            'metal': [
                'heavy metal', 'alternative metal', 'black metal', 'death metal',
                'doom metal', 'folk metal', 'glam metal', 'gothic metal',
                'industrial metal', 'metalcore', 'neoclassical metal', 'power metal',
                'progressive metal', 'sludge metal', 'speed metal', 'symphonic metal',
                'thrash metal', 'viking metal', 'melodic death metal', 'technical death metal'
            ],
            
            # Pop variations
            'pop': [
                'popular', 'mainstream', 'adult contemporary', 'arab pop', 'baroque pop',
                'bubblegum pop', 'chanson', 'christian pop', 'classical crossover',
                'europop', 'iranian pop', 'jangle pop', 'latin ballad', 'mexican pop',
                'new romanticism', 'pop rap', 'psychedelic pop', 'schlager',
                'soft rock', 'sophisti-pop', 'space age pop', 'sunshine pop',
                'surf pop', 'teen pop', 'traditional pop music', 'turkish pop',
                'wonky pop', 'britpop', 'dream pop', 'indie pop', 'noise pop'
            ],
            
            # Jazz variations
            'jazz': [
                'jazz fusion', 'smooth jazz', 'avant-garde jazz', 'bebop', 'boogie-woogie',
                'cool jazz', 'crossover jazz', 'dixieland', 'ethno jazz', 'free jazz',
                'gypsy jazz', 'hard bop', 'jazz rock', 'jazz-funk', 'kansas city jazz',
                'latin jazz', 'mainstream jazz', 'modal jazz', 'neo-bop jazz',
                'neo-swing', 'orchestral jazz', 'post-bop', 'punk jazz', 'ragtime',
                'ska jazz', 'soul jazz', 'stride jazz', 'swing', 'third stream',
                'trad jazz', 'vocal jazz', 'west coast jazz'
            ],
            
            # Classical variations
            'classical': [
                'orchestral', 'symphony', 'symphonic', 'ballet', 'baroque',
                'cantata', 'chamber music', 'string quartet', 'concerto',
                'contemporary classical', 'modern classical', 'opera', 'oratorio',
                'organum', 'mass', 'requiem', 'sacred music', 'cantique',
                'gregorian chant', 'sonata'
            ],
            
            # Country variations
            'country': [
                'country western', 'bluegrass', 'alternative country', 'cowpunk',
                'americana', 'australian country music', 'bakersfield sound',
                'progressive bluegrass', 'reactionary bluegrass', 'blues country',
                'cajun', 'christian country music', 'classic country', 'close harmony',
                'country pop', 'country rap', 'country rock', 'country soul',
                'cowboy/western music', 'honky tonk', 'nashville sound',
                'neotraditional country', 'outlaw country', 'progressive country',
                'psychobilly/punkabilly', 'red dirt', 'rockabilly', 'sertanejo',
                'texas country', 'traditional country music', 'truck-driving country',
                'western swing', 'zydeco'
            ],
            
            # Folk variations
            'folk': [
                'folk', 'folk rock', 'traditional', 'american folk revival', 'anti-folk',
                'british folk revival', 'celtic music', 'contemporary folk',
                'filk music', 'freak folk', 'indie folk', 'industrial folk',
                'neofolk', 'progressive folk', 'psychedelic folk', 'sung poetry',
                'techno-folk'
            ],
            
            # Blues variations
            'blues': [
                'african blues', 'blues rock', 'blues shouter', 'british blues',
                'canadian blues', 'chicago blues', 'classic female blues',
                'country blues', 'delta blues', 'detroit blues', 'electric blues',
                'gospel blues', 'hill country blues', 'hokum blues', 'jazz blues',
                'jump blues', 'kansas city blues', 'louisiana blues', 'memphis blues',
                'piano blues', 'piedmont blues', 'punk blues', 'soul blues',
                'st. louis blues', 'swamp blues', 'texas blues', 'west coast blues'
            ],
            
            # R&B/Soul variations
            'r&b': [
                'rhythm and blues', 'contemporary r&b', 'soul', 'blue-eyed soul',
                'neo soul', 'northern soul'
            ],
            
            # Funk variations (separate from R&B)
            'funk': [
                'funk', 'deep funk', 'go-go', 'p-funk', 'funk rock', 'funk metal',
                'funk jazz', 'jazz-funk', 'funk soul', 'funk pop', 'funk rap',
                'g-funk', 'funk carioca', 'funk ostentação', 'funk melody',
                'funk 150 bpm', 'funk consciente', 'funk proibidão', 'funk melody',
                'funk ostentação', 'funk universitário', 'funk de raiz'
            ],
            
            # Reggae variations
            'reggae': [
                'roots reggae', 'reggae fusion', 'reggae en español', 'spanish reggae',
                'reggae 110', 'reggae bultrón', 'romantic flow', 'lovers rock',
                'raggamuffin', 'ragga', 'dancehall', 'ska', '2 tone', 'dub', 'rocksteady'
            ],
            

            
            # Easy Listening variations
            'easy listening': [
                'background music', 'beautiful music', 'elevator music', 'furniture music',
                'lounge music', 'middle of the road', 'new-age music'
            ],
            
            # African variations
            'african': [
                'african heavy metal', 'african hip hop', 'afrobeat', 'apala', 'benga',
                'bikutsi', 'bongo flava', 'cape jazz', 'chimurenga', 'coupé-décalé',
                'fuji music', 'genge', 'highlife', 'hiplife', 'isicathamiya', 'jit',
                'jùjú', 'kapuka', 'kizomba', 'kuduro', 'kwaito', 'kwela', 'makossa',
                'maloya', 'marrabenta', 'mbalax', 'mbaqanga', 'mbube', 'morna',
                'museve', 'palm-wine', 'raï', 'sakara', 'sega', 'seggae', 'semba',
                'soukous', 'taarab', 'zouglou'
            ],
            
            # Latin variations
            'latin': [
                'bachata', 'baithak gana', 'bolero', 'calypso', 'chutney', 'chutney soca',
                'compas', 'mambo', 'merengue', 'méringue', 'chicha', 'criolla',
                'cumbia', 'huayno', 'mariachi', 'ranchera', 'tejano', 'punta',
                'punta rock', 'rasin', 'reggaeton', 'salsa', 'soca', 'son', 'timba',
                'twoubadou', 'zouk', 'axé', 'bossa nova', 'brega', 'choro', 'forró',
                'frevo', 'funk carioca', 'lambada', 'maracatu', 'música popular brasileira',
                'música sertaneja', 'pagode', 'samba', 'samba rock', 'tecnobrega',
                'tropicalia', 'zouk-lambada'
            ],
            
            # World variations
            'world': [
                'worldbeat', 'world fusion', 'world music', 'ethnic electronica',
                'global fusion', 'international', 'traditional world', 'folk world',
                'celtic world', 'middle eastern', 'arabic', 'indian classical',
                'hindustani', 'carnatic', 'qawwali', 'ghazal', 'flamenco', 'fado',
                'tango', 'milonga', 'capoeira', 'afro-cuban', 'son cubano', 'rumba', 
                'guaguancó', 'yoruba', 'santería', 'candomblé', 'umbanda', 'macumba', 
                'voodoo', 'vodou', 'balkan'
            ],
            
            # Alternative variations
            'alternative': [
                'indie', 'indie rock', 'indie pop', 'indie folk', 'alternative rock',
                'alternative pop', 'alternative metal', 'alternative dance',
                'post-punk', 'new wave', 'college rock', 'underground rock',
                'experimental rock', 'art rock', 'progressive rock'
            ]
        }
        
        # Create reverse mapping for quick lookup
        self.reverse_mappings = {}
        for canonical, variations in self.genre_mappings.items():
            for variation in variations:
                self.reverse_mappings[variation.lower()] = canonical
            # Also map the canonical form to itself
            self.reverse_mappings[canonical.lower()] = canonical
        
        # Common text cleaning patterns
        self.cleanup_patterns = [
            (r'\s+', ' '),  # Multiple spaces to single space
            (r'[^\w\s\-&]', ''),  # Remove special chars except hyphen, ampersand
        ]
        
        # Compiled patterns for more complex replacements
        self.compiled_patterns = [
            (re.compile(r'\b(music|song|track|tune|melody)\b', re.IGNORECASE), ''),  # Remove common suffixes
            (re.compile(r'\b(genre|style|type)\b', re.IGNORECASE), ''),  # Remove genre-related words
        ]
    
    def normalize_genre(self, genre: str) -> str:
        """Normalize a genre string to its canonical form"""
        if not genre:
            return ''
        
        # Clean up the input
        normalized = self._clean_genre_text(genre)
        
        # Try exact match first
        if normalized in self.reverse_mappings:
            canonical = self.reverse_mappings[normalized]
            logger.debug(f"Genre normalized: '{genre}' -> '{canonical}' (exact match)")
            return canonical
        
        # Try fuzzy matching for close variations
        fuzzy_match = self._fuzzy_match(normalized)
        if fuzzy_match:
            logger.debug(f"Genre normalized: '{genre}' -> '{fuzzy_match}' (fuzzy match)")
            return fuzzy_match
        
        # Handle multi-genre strings (e.g., "deep house black metal techno")
        if ' ' in normalized and len(normalized.split()) > 2:
            return self._handle_multi_genre_string(normalized)
        
        # Handle compound genres with "and" (e.g., "jazz and blues")
        if ' and ' in normalized:
            return self._handle_compound_genre(normalized)
        
        # If no match found, return cleaned version
        logger.debug(f"Genre not normalized: '{genre}' -> '{normalized}' (no match)")
        return normalized
    
    def _clean_genre_text(self, genre: str) -> str:
        """Clean up genre text by removing common artifacts"""
        cleaned = genre.lower().strip()
        
        # Apply simple cleanup patterns
        for pattern, replacement in self.cleanup_patterns:
            cleaned = re.sub(pattern, replacement, cleaned)
        
        # Apply compiled patterns
        for pattern, replacement in self.compiled_patterns:
            cleaned = pattern.sub(replacement, cleaned)
        
        # Final cleanup
        cleaned = cleaned.strip()
        
        return cleaned
    
    def _fuzzy_match(self, genre: str) -> Optional[str]:
        """Find close matches for genre variations"""
        # Handle common variations that don't have exact mappings
        variations = {
            'hiphop': 'hip hop',
            'hip-hop': 'hip hop',
            'edm': 'electronic',
            'electronic dance music': 'electronic',
            'electronica': 'electronic',
            'electronic dance': 'electronic',  # Handle cleaned version
            'techno': 'electronic',  # Map techno to electronic
            'rock n roll': 'rock',
            'rock & roll': 'rock',
            'rock and roll': 'rock',
            'heavy metal': 'metal',
            'popular': 'pop',
            'mainstream': 'pop',
            'jazz fusion': 'jazz',
            'smooth jazz': 'jazz',
            'orchestral': 'classical',
            'symphony': 'classical',
            'symphonic': 'classical',
            'country western': 'country',
            'bluegrass': 'country',
            'folk rock': 'folk',
            'traditional': 'folk',
            'celtic': 'folk',
            'celtic music': 'folk',
            'rhythm and blues': 'r&b',
            'contemporary r&b': 'r&b',
            'soul': 'r&b',
            'funk': 'funk',  # Keep funk as its own genre
            'deep funk': 'funk',
            'go-go': 'funk',
            'p-funk': 'funk',
            'house': 'house',  # Keep house as its own genre
            'deep house': 'house',
            'progressive house': 'house',
            'tech house': 'house',
            'acid house': 'house',
            'pop/rock': 'pop',  # Handle slash notation
            'pop\\rock': 'pop',
            'poprock': 'pop',  # Handle cleaned version
            'soul/r&b': 'r&b',
            'soul\\r&b': 'r&b',
            'soulr&b': 'r&b',  # Handle cleaned version
            'folk': 'folk',  # Keep folk as its own genre
            'roots reggae': 'reggae',
            'dancehall': 'reggae',
            'ska': 'reggae',
            'background music': 'easy listening',
            'elevator music': 'easy listening',
            'lounge music': 'easy listening',
            'new-age music': 'easy listening',
            'n/a': 'n/a',  # Handle N/A properly
            'na': 'n/a',
            # African variations
            'afrobeat': 'african',
            'highlife': 'african',
            'hiplife': 'african',
            'jùjú': 'african',
            'kwaito': 'african',
            'makossa': 'african',
            'mbalax': 'african',
            'raï': 'african',
            'soukous': 'african',
            # Latin variations
            'bachata': 'latin',
            'bolero': 'latin',
            'calypso': 'latin',
            'mambo': 'latin',
            'merengue': 'latin',
            'cumbia': 'latin',
            'mariachi': 'latin',
            'ranchera': 'latin',
            'reggaeton': 'latin',
            'salsa': 'latin',
            'soca': 'latin',
            'bossa nova': 'latin',
            'samba': 'latin',
            'tropicalia': 'latin',
            'choro': 'latin',
            # World variations
            'worldbeat': 'world',
            'world fusion': 'world',
            'world music': 'world',
            'ethnic electronica': 'world',
            'global fusion': 'world',
            'international': 'world',
            'middle eastern': 'world',
            'arabic': 'world',
            'indian classical': 'world',
            'hindustani': 'world',
            'carnatic': 'world',
            'flamenco': 'world',
            'fado': 'world',
            'tango': 'world',
            'afro-cuban': 'world',
            'tsonga disco': 'african',
            'disco': 'dance',
            'indie': 'alternative',
            'indie rock': 'rock',
            'indie pop': 'pop',
            'techno mix': 'electronic',
            'mix': 'electronic',
            'remix': 'electronic'
        }
        
        return variations.get(genre)
    
    def get_canonical_genres(self) -> List[str]:
        """Get list of all canonical genre names"""
        return list(self.genre_mappings.keys())
    
    def get_genre_variations(self, canonical_genre: str) -> List[str]:
        """Get all variations for a canonical genre"""
        return self.genre_mappings.get(canonical_genre, [])
    
    def is_canonical_genre(self, genre: str) -> bool:
        """Check if a genre is already in canonical form"""
        return genre.lower() in self.genre_mappings
    
    def normalize_genre_list(self, genres: List[str]) -> List[str]:
        """Normalize a list of genres and remove duplicates"""
        normalized = []
        seen = set()
        
        for genre in genres:
            if genre:
                canonical = self.normalize_genre(genre)
                if canonical and canonical not in seen:
                    normalized.append(canonical)
                    seen.add(canonical)
        
        return normalized
    
    def _handle_multi_genre_string(self, genre_string: str) -> str:
        """Handle multi-genre strings by selecting the most appropriate genre"""
        words = genre_string.split()
        
        # Priority order for genre selection
        priority_genres = [
            'house', 'techno', 'trance', 'dubstep', 'drum and bass',
            'metal', 'rock', 'pop', 'jazz', 'blues', 'folk', 'country',
            'hip hop', 'r&b', 'soul', 'funk', 'reggae', 'latin', 'world',
            'electronic', 'dance', 'classical', 'ambient', 'industrial'
        ]
        
        # Try to find the highest priority genre in the string
        for priority_genre in priority_genres:
            if priority_genre in words:
                return priority_genre
        
        # If no priority genre found, try to normalize each word and pick the first valid one
        for word in words:
            if word in self.reverse_mappings:
                return self.reverse_mappings[word]
        
        # If still no match, return the first word as fallback
        return words[0]
    
    def _handle_compound_genre(self, genre_string: str) -> str:
        """Handle compound genres with 'and' (e.g., 'jazz and blues')"""
        parts = genre_string.split(' and ')
        
        # Priority order for compound genres
        compound_priorities = {
            'jazz and blues': 'jazz',
            'rock and roll': 'rock',
            'rhythm and blues': 'r&b',
            'folk and country': 'folk',
            'pop and rock': 'pop',
            'soul and r&b': 'r&b',
            'funk and soul': 'funk',
            'house and techno': 'house',
            'trance and techno': 'electronic',
            'dubstep and drum and bass': 'dubstep'
        }
        
        # Check for known compound patterns
        if genre_string in compound_priorities:
            return compound_priorities[genre_string]
        
        # If not a known pattern, try to normalize each part and pick the first valid one
        for part in parts:
            part = part.strip()
            if part in self.reverse_mappings:
                return self.reverse_mappings[part]
            # Try fuzzy matching for each part
            fuzzy_match = self._fuzzy_match(part)
            if fuzzy_match:
                return fuzzy_match
        
        # If no match found, return the first part
        return parts[0].strip()
