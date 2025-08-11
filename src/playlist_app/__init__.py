"""
Playlist App - Audio Discovery and Analysis System
"""

__version__ = "0.1.0"
__author__ = "Playlist App Team"
__description__ = "A playlist generation app with audio analysis using Essentia and TensorFlow"

from .core.config import DiscoveryConfig
from .models.database import create_tables, get_db
from .services.discovery import DiscoveryService

__all__ = [
    "DiscoveryConfig",
    "create_tables", 
    "get_db",
    "DiscoveryService"
]

