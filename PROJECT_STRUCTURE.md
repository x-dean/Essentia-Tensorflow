# Project Structure

```
Essentia-Tensorflow/
├── src/
│   └── playlist_app/
│       ├── __init__.py              # Main package initialization
│       ├── api/                     # API endpoints
│       │   ├── __init__.py
│       │   └── discovery.py         # Discovery API endpoints
│       ├── core/                    # Core configuration and utilities
│       │   ├── __init__.py
│       │   └── config.py            # Configuration management
│       ├── models/                  # Database models
│       │   ├── __init__.py
│       │   └── database.py          # Database models and session management
│       ├── services/                # Business logic services
│       │   ├── __init__.py
│       │   └── discovery.py         # Discovery service implementation
│       └── utils/                   # Utility functions
│           └── __init__.py
├── scripts/                         # Executable scripts
│   └── playlist_cli.py              # CLI implementation
├── tests/                           # Test files
│   └── test_discovery.py            # Discovery system tests
├── docs/                            # Documentation
│   ├── discovery.md                 # Discovery system documentation
│   └── cli.md                       # CLI documentation
├── main.py                          # FastAPI application entry point
├── playlist_cli.py                  # CLI entry point
├── setup.py                         # Package setup and installation
├── requirements.txt                 # Python dependencies
├── Dockerfile                       # Docker configuration
├── Dockerfile.app                   # Application Docker configuration
├── README.md                        # Main project documentation
├── PROJECT_STRUCTURE.md             # This file
└── .gitignore                       # Git ignore rules
```

## Package Organization

### `src/playlist_app/`
The main Python package containing all application code.

#### `api/`
FastAPI route handlers and API endpoints.
- **discovery.py**: REST API endpoints for file discovery operations

#### `core/`
Core configuration and fundamental utilities.
- **config.py**: Environment-based configuration management

#### `models/`
Database models and ORM definitions.
- **database.py**: SQLAlchemy models, session management, and database utilities

#### `services/`
Business logic and service layer implementations.
- **discovery.py**: File discovery service with caching and database integration

#### `utils/`
Utility functions and helper modules.
- Currently empty, ready for future utility functions

### `scripts/`
Executable scripts and command-line tools.
- **playlist_cli.py**: Full CLI implementation with all commands

### `tests/`
Test files and test utilities.
- **test_discovery.py**: Comprehensive tests for the discovery system

### `docs/`
Project documentation.
- **discovery.md**: Detailed documentation for the discovery system
- **cli.md**: Complete CLI usage guide

## Key Files

### Entry Points
- **main.py**: FastAPI application server
- **playlist_cli.py**: CLI entry point for easy access

### Configuration
- **setup.py**: Package installation and distribution
- **requirements.txt**: Python dependencies
- **Dockerfile**: Container configuration

## Import Structure

### Internal Package Imports
```python
# Within the package
from ..models.database import File, DiscoveryCache
from ..core.config import DiscoveryConfig
from ..services.discovery import DiscoveryService
```

### External Package Imports
```python
# From outside the package
from src.playlist_app.models.database import create_tables
from src.playlist_app.services.discovery import DiscoveryService
from src.playlist_app.core.config import DiscoveryConfig
```

## Development Workflow

1. **API Development**: Add new endpoints in `src/playlist_app/api/`
2. **Service Logic**: Implement business logic in `src/playlist_app/services/`
3. **Database Models**: Define new models in `src/playlist_app/models/`
4. **Configuration**: Add new settings in `src/playlist_app/core/config.py`
5. **Testing**: Write tests in `tests/`
6. **Documentation**: Update docs in `docs/`

## Installation and Usage

### Development Installation
```bash
# Install in development mode
pip install -e .

# Run CLI
python playlist_cli.py scan

# Run API server
python main.py
```

### Package Structure Benefits
- **Modularity**: Clear separation of concerns
- **Maintainability**: Easy to locate and modify code
- **Testability**: Isolated components for testing
- **Scalability**: Easy to add new features
- **Documentation**: Organized documentation structure
