#!/usr/bin/env python3
"""
Genre Fusion Service - Intelligently combines multiple genre sources
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

from .genre_normalizer import GenreNormalizer
from .genre_enrichment import genre_enrichment_manager

logger = logging.getLogger(__name__)

@dataclass
class GenreSource:
    """Represents a genre prediction from a specific source"""
    genre: str
    confidence: float
    source: str  # 'metadata', 'context', 'tensorflow', 'enrichment'
    raw_value: str  # Original value before normalization
    metadata: Dict[str, Any] = None  # Additional source-specific data

class GenreFusionService:
    """
    Intelligently combines genre predictions from multiple sources:
    1. Metadata extraction (Mutagen)
    2. Context validation (album/artist context)
    3. TensorFlow/MusicNN prediction
    4. External API enrichment (MusicBrainz, Last.fm, Discogs)
    
    Uses confidence scoring and source reliability to determine the best genre.
    """
    
    def __init__(self):
        self.genre_normalizer = GenreNormalizer()
        
        # Source reliability weights (higher = more trusted)
        self.source_weights = {
            'tensorflow': 0.8,      # AI prediction from audio content
            'context': 0.7,         # Album/artist context validation
            'enrichment': 0.6,      # External API results
            'metadata': 0.4         # Raw metadata from file tags
        }
        
        # Confidence thresholds
        self.high_confidence_threshold = 0.7
        self.medium_confidence_threshold = 0.5
        self.low_confidence_threshold = 0.3
    
    def fuse_genres(self, 
                   metadata_genre: Optional[str] = None,
                   context_genre: Optional[str] = None,
                   tensorflow_genre: Optional[str] = None,
                   tensorflow_confidence: float = 0.0,
                   tensorflow_predictions: Optional[Dict] = None,
                   enrichment_genre: Optional[str] = None,
                   enrichment_confidence: float = 0.0,
                   album: Optional[str] = None,
                   artist: Optional[str] = None,
                   title: Optional[str] = None) -> Dict[str, Any]:
        """
        Fuse genre predictions from multiple sources
        
        Returns:
            Dictionary with fused genre result and detailed analysis
        """
        
        sources = []
        
        # 1. Process metadata genre
        if metadata_genre:
            normalized_genre = self.genre_normalizer.normalize_genre(metadata_genre)
            sources.append(GenreSource(
                genre=normalized_genre,
                confidence=0.4,  # Base confidence for metadata
                source='metadata',
                raw_value=metadata_genre,
                metadata={'original': metadata_genre}
            ))
        
        # 2. Process context-validated genre
        if context_genre:
            sources.append(GenreSource(
                genre=context_genre,
                confidence=0.7,  # High confidence for context validation
                source='context',
                raw_value=context_genre,
                metadata={'album': album, 'artist': artist}
            ))
        
        # 3. Process TensorFlow prediction
        if tensorflow_genre and tensorflow_confidence > 0:
            normalized_tf_genre = self.genre_normalizer.normalize_genre(tensorflow_genre)
            # Adjust confidence based on TensorFlow prediction quality
            adjusted_confidence = self._adjust_tensorflow_confidence(
                tensorflow_confidence, tensorflow_predictions
            )
            sources.append(GenreSource(
                genre=normalized_tf_genre,
                confidence=adjusted_confidence,
                source='tensorflow',
                raw_value=tensorflow_genre,
                metadata={
                    'raw_confidence': tensorflow_confidence,
                    'predictions': tensorflow_predictions
                }
            ))
        
        # 4. Process enrichment genre
        if enrichment_genre:
            sources.append(GenreSource(
                genre=enrichment_genre,
                confidence=enrichment_confidence,
                source='enrichment',
                raw_value=enrichment_genre,
                metadata={'enrichment_source': 'external_api'}
            ))
        
        # 5. Run enrichment if no good sources available
        if not sources or all(s.confidence < self.low_confidence_threshold for s in sources):
            if album and artist and title:
                enrichment_result = genre_enrichment_manager.enrich_metadata({
                    'title': title,
                    'artist': artist,
                    'album': album
                })
                if enrichment_result.get('genre'):
                    sources.append(GenreSource(
                        genre=enrichment_result['genre'],
                        confidence=0.6,
                        source='enrichment',
                        raw_value=enrichment_result['genre'],
                        metadata={'enrichment_source': 'fallback'}
                    ))
        
        # 6. Fuse all sources
        fused_result = self._fuse_sources(sources)
        
        return {
            'final_genre': fused_result['genre'],
            'final_confidence': fused_result['confidence'],
            'fusion_method': fused_result['method'],
            'sources': [
                {
                    'genre': s.genre,
                    'confidence': s.confidence,
                    'source': s.source,
                    'raw_value': s.raw_value
                } for s in sources
            ],
            'analysis': {
                'source_count': len(sources),
                'high_confidence_sources': len([s for s in sources if s.confidence >= self.high_confidence_threshold]),
                'medium_confidence_sources': len([s for s in sources if self.medium_confidence_threshold <= s.confidence < self.high_confidence_threshold]),
                'low_confidence_sources': len([s for s in sources if s.confidence < self.medium_confidence_threshold]),
                'consensus': self._check_consensus(sources),
                'conflicts': self._detect_conflicts(sources)
            }
        }
    
    def _adjust_tensorflow_confidence(self, base_confidence: float, predictions: Optional[Dict]) -> float:
        """Adjust TensorFlow confidence based on prediction quality"""
        if not predictions:
            return base_confidence
        
        # Factors that increase confidence
        confidence_boost = 0.0
        
        # Check if top predictions are consistent
        top_predictions = predictions.get('top_predictions', [])
        if len(top_predictions) >= 2:
            top1 = top_predictions[0]['confidence'] if top_predictions else 0
            top2 = top_predictions[1]['confidence'] if len(top_predictions) > 1 else 0
            
            # If top 2 predictions are close, it's more uncertain
            if abs(top1 - top2) < 0.1:
                confidence_boost -= 0.1
            # If top prediction is much higher, it's more certain
            elif top1 - top2 > 0.3:
                confidence_boost += 0.1
        
        # Check prediction entropy (lower entropy = more certain)
        statistics = predictions.get('statistics', {})
        entropy = statistics.get('prediction_entropy', 0)
        if entropy < 1.0:  # Low entropy = high confidence
            confidence_boost += 0.1
        elif entropy > 3.0:  # High entropy = low confidence
            confidence_boost -= 0.1
        
        # Check number of high-confidence predictions
        high_conf_count = statistics.get('high_confidence_count', 0)
        if high_conf_count > 5:  # Many high-confidence predictions
            confidence_boost += 0.05
        elif high_conf_count < 2:  # Few high-confidence predictions
            confidence_boost -= 0.05
        
        return max(0.0, min(1.0, base_confidence + confidence_boost))
    
    def _fuse_sources(self, sources: List[GenreSource]) -> Dict[str, Any]:
        """Fuse multiple genre sources using weighted voting"""
        if not sources:
            return {'genre': 'unknown', 'confidence': 0.0, 'method': 'no_sources'}
        
        if len(sources) == 1:
            return {
                'genre': sources[0].genre,
                'confidence': sources[0].confidence,
                'method': 'single_source'
            }
        
        # Group by genre and calculate weighted scores
        genre_scores = {}
        for source in sources:
            genre = source.genre
            weight = self.source_weights.get(source.source, 0.5)
            weighted_score = source.confidence * weight
            
            if genre not in genre_scores:
                genre_scores[genre] = {
                    'total_score': 0.0,
                    'weighted_score': 0.0,
                    'source_count': 0,
                    'sources': []
                }
            
            genre_scores[genre]['total_score'] += source.confidence
            genre_scores[genre]['weighted_score'] += weighted_score
            genre_scores[genre]['source_count'] += 1
            genre_scores[genre]['sources'].append(source)
        
        # Find the genre with highest weighted score
        best_genre = max(genre_scores.items(), key=lambda x: x[1]['weighted_score'])
        genre_name, genre_data = best_genre
        
        # Calculate final confidence
        final_confidence = min(1.0, genre_data['weighted_score'])
        
        # Determine fusion method
        if genre_data['source_count'] > 1:
            method = 'weighted_consensus'
        elif genre_data['weighted_score'] > self.high_confidence_threshold:
            method = 'high_confidence_single'
        else:
            method = 'best_available'
        
        return {
            'genre': genre_name,
            'confidence': final_confidence,
            'method': method
        }
    
    def _check_consensus(self, sources: List[GenreSource]) -> Dict[str, Any]:
        """Check if sources agree on genre"""
        if len(sources) < 2:
            return {'has_consensus': False, 'consensus_genre': None, 'agreement_level': 0.0}
        
        # Group by genre
        genre_counts = {}
        for source in sources:
            genre = source.genre
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        # Find most common genre
        most_common = max(genre_counts.items(), key=lambda x: x[1])
        consensus_genre, count = most_common
        
        # Calculate agreement level
        agreement_level = count / len(sources)
        
        return {
            'has_consensus': agreement_level >= 0.5,
            'consensus_genre': consensus_genre,
            'agreement_level': agreement_level,
            'genre_distribution': genre_counts
        }
    
    def _detect_conflicts(self, sources: List[GenreSource]) -> List[Dict[str, Any]]:
        """Detect conflicts between different sources"""
        conflicts = []
        
        if len(sources) < 2:
            return conflicts
        
        # Check for high-confidence conflicts
        high_conf_sources = [s for s in sources if s.confidence >= self.high_confidence_threshold]
        
        if len(high_conf_sources) >= 2:
            genres = [s.genre for s in high_conf_sources]
            unique_genres = set(genres)
            
            if len(unique_genres) > 1:
                conflicts.append({
                    'type': 'high_confidence_conflict',
                    'sources': [s.source for s in high_conf_sources],
                    'genres': list(unique_genres),
                    'severity': 'high'
                })
        
        # Check for source-specific conflicts
        source_genres = {}
        for source in sources:
            if source.source not in source_genres:
                source_genres[source.source] = []
            source_genres[source.source].append(source.genre)
        
        for source_name, genres in source_genres.items():
            if len(set(genres)) > 1:
                conflicts.append({
                    'type': 'source_internal_conflict',
                    'source': source_name,
                    'genres': list(set(genres)),
                    'severity': 'medium'
                })
        
        return conflicts
