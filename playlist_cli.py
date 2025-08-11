#!/usr/bin/env python3
"""
Playlist App CLI Entry Point
"""

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from scripts.playlist_cli import main

if __name__ == "__main__":
    sys.exit(main())




