"""
Playlist App - Audio Discovery and Analysis System
"""

__version__ = "0.1.0"
__author__ = "Playlist App Team"
__description__ = "A playlist generation app with audio analysis using Essentia and TensorFlow"

from .core.config import DiscoveryConfig

# Optional database imports - only import if SQLAlchemy is available
try:
    from .models.database import create_tables, get_db
    DB_AVAILABLE = True
except ImportError:
    create_tables = None
    get_db = None
    DB_AVAILABLE = False

try:
    from .services.discovery import DiscoveryService
    DISCOVERY_AVAILABLE = True
except ImportError:
    DiscoveryService = None
    DISCOVERY_AVAILABLE = False

__all__ = [
    "DiscoveryConfig",
    "create_tables", 
    "get_db",
    "DiscoveryService",
    "DB_AVAILABLE",
    "DISCOVERY_AVAILABLE"
]

