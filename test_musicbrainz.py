#!/usr/bin/env python3
"""
Test script for MusicBrainz integration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.playlist_app.services.musicbrainz import musicbrainz_service

def test_musicbrainz():
    """Test MusicBrainz genre lookup"""
    print("Testing MusicBrainz integration...")
    
    # Test with a well-known artist
    test_cases = [
        {
            'artist': 'Coldplay',
            'title': 'Yellow',
            'album': 'Parachutes'
        },
        {
            'artist': 'The Beatles',
            'title': 'Hey Jude',
            'album': None
        },
        {
            'artist': 'Daft Punk',
            'title': 'Get Lucky',
            'album': 'Random Access Memories'
        }
    ]
    
    for case in test_cases:
        print(f"\nTesting: {case['artist']} - {case['title']}")
        
        # Test track search
        track_data = musicbrainz_service.search_track(
            case['artist'], 
            case['title'], 
            case['album']
        )
        
        if track_data:
            print(f"✓ Found track: {track_data.get('title', 'Unknown')}")
            
            # Test genre lookup
            genre = musicbrainz_service.get_track_genre(
                case['artist'], 
                case['title'], 
                case['album']
            )
            
            if genre:
                print(f"✓ Found genre: {genre}")
            else:
                print("✗ No genre found")
        else:
            print("✗ Track not found")
    
    print("\nMusicBrainz integration test completed!")

if __name__ == "__main__":
    test_musicbrainz()
