#!/usr/bin/env python3
"""
Configuration validation module with JSON schemas
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from jsonschema import validate, ValidationError, SchemaError

logger = logging.getLogger(__name__)

class ConfigValidator:
    """Configuration validator with JSON schemas"""
    
    # Schema for app_settings.json
    APP_SETTINGS_SCHEMA = {
        "type": "object",
        "properties": {
            "api": {
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                    "workers": {"type": "integer", "minimum": 1},
                    "reload": {"type": "boolean"},
                    "timeouts": {
                        "type": "object",
                        "properties": {
                            "default": {"type": "integer", "minimum": 1},
                            "analysis": {"type": "integer", "minimum": 1},
                            "faiss": {"type": "integer", "minimum": 1},
                            "discovery": {"type": "integer", "minimum": 1}
                        },
                        "required": ["default", "analysis", "faiss", "discovery"]
                    },
                    "cors": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "origins": {"type": "array", "items": {"type": "string"}},
                            "methods": {"type": "array", "items": {"type": "string"}},
                            "headers": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            },
            "performance": {
                "type": "object",
                "properties": {
                    "max_concurrent_requests": {"type": "integer", "minimum": 1},
                    "request_timeout": {"type": "integer", "minimum": 1},
                    "background_tasks": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "max_workers": {"type": "integer", "minimum": 1}
                        }
                    }
                }
            },
            "discovery": {
                "type": "object",
                "properties": {
                    "background_enabled": {"type": "boolean"},
                    "interval": {"type": "integer", "minimum": 1},
                    "auto_scan_on_startup": {"type": "boolean"},
                    "supported_extensions": {
                        "type": "array",
                        "items": {"type": "string", "pattern": "^\\..*$"}
                    },
                    "cache_ttl": {"type": "integer", "minimum": 0},
                    "batch_size": {"type": "integer", "minimum": 1},
                    "hash_algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"]
                    }
                }
            },
            "faiss": {
                "type": "object",
                "properties": {
                    "index_name": {"type": "string"},
                    "vector_dimension": {"type": "integer", "minimum": 1},
                    "similarity_threshold": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    }
                }
            },
            "external_apis": {
                "type": "object",
                "properties": {
                    "musicbrainz": {"$ref": "#/definitions/external_api_config"},
                    "lastfm": {"$ref": "#/definitions/external_api_config"},
                    "discogs": {"$ref": "#/definitions/external_api_config"}
                }
            }
        },
        "definitions": {
            "external_api_config": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean"},
                    "rate_limit": {"type": "number", "minimum": 0.1},
                    "timeout": {"type": "integer", "minimum": 1},
                    "user_agent": {"type": "string"},
                    "api_key": {"type": "string"},
                    "base_url": {"type": "string", "format": "uri"},
                    "retry_settings": {
                        "type": "object",
                        "properties": {
                            "max_retries": {"type": "integer", "minimum": 0},
                            "backoff_factor": {"type": "number", "minimum": 1.0},
                            "max_backoff": {"type": "integer", "minimum": 1}
                        }
                    },
                    "cache_settings": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "ttl_seconds": {"type": "integer", "minimum": 0}
                        }
                    }
                }
            }
        }
    }
    
    # Schema for database.json
    DATABASE_SCHEMA = {
        "type": "object",
        "properties": {
            "pool_size": {"type": "integer", "minimum": 1, "maximum": 100},
            "max_overflow": {"type": "integer", "minimum": 0},
            "pool_timeout": {"type": "integer", "minimum": 1},
            "pool_recycle": {"type": "integer", "minimum": 0},
            "retry_settings": {
                "type": "object",
                "properties": {
                    "max_retries": {"type": "integer", "minimum": 0},
                    "initial_delay": {"type": "number", "minimum": 0.1},
                    "backoff_multiplier": {"type": "number", "minimum": 1.0},
                    "max_delay": {"type": "number", "minimum": 1.0}
                },
                "required": ["max_retries", "initial_delay", "backoff_multiplier", "max_delay"]
            },
            "connection_timeout": {"type": "integer", "minimum": 1}
        }
    }
    
    # Schema for logging.json
    LOGGING_SCHEMA = {
        "type": "object",
        "properties": {
            "log_level": {
                "type": "string",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            },
            "max_file_size": {"type": "integer", "minimum": 1024},
            "max_backups": {"type": "integer", "minimum": 0},
            "compress": {"type": "boolean"},
            "suppression": {
                "type": "object",
                "properties": {
                    "tensorflow": {"type": "boolean"},
                    "essentia": {"type": "boolean"},
                    "librosa": {"type": "boolean"},
                    "matplotlib": {"type": "boolean"},
                    "pil": {"type": "boolean"}
                }
            }
        }
    }
    
    # Schema for discovery.json
    DISCOVERY_SCHEMA = {
        "type": "object",
        "properties": {
            "search_directories": {
                "type": "array",
                "items": {"type": "string"}
            },
            "supported_extensions": {
                "type": "array",
                "items": {"type": "string", "pattern": "^\\..*$"}
            },
            "cache_settings": {
                "type": "object",
                "properties": {
                    "ttl": {"type": "integer", "minimum": 0},
                    "max_size": {"type": "integer", "minimum": 1},
                    "enable_cache": {"type": "boolean"}
                }
            },
            "scan_settings": {
                "type": "object",
                "properties": {
                    "batch_size": {"type": "integer", "minimum": 1},
                    "recursive": {"type": "boolean"},
                    "follow_symlinks": {"type": "boolean"},
                    "max_file_size": {"type": "integer", "minimum": 1}
                }
            },
            "hash_settings": {
                "type": "object",
                "properties": {
                    "algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"]
                    },
                    "include_filename": {"type": "boolean"},
                    "include_filesize": {"type": "boolean"},
                    "include_path": {"type": "boolean"}
                }
            }
        }
    }

    # Schema for analysis_config.json
    ANALYSIS_CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "performance": {
                "type": "object",
                "properties": {
                    "parallel_processing": {
                        "type": "object",
                        "properties": {
                            "max_workers": {"type": "integer", "minimum": 1},
                            "chunk_size": {"type": "integer", "minimum": 1},
                            "timeout_per_file": {"type": "integer", "minimum": 1},
                            "memory_limit_mb": {"type": "integer", "minimum": 1}
                        }
                    },
                    "caching": {
                        "type": "object",
                        "properties": {
                            "enable_cache": {"type": "boolean"},
                            "cache_duration_hours": {"type": "integer", "minimum": 0},
                            "max_cache_size_mb": {"type": "integer", "minimum": 1}
                        }
                    },
                    "optimization": {
                        "type": "object",
                        "properties": {
                            "use_ffmpeg_streaming": {"type": "boolean"},
                            "smart_segmentation": {"type": "boolean"},
                            "skip_existing_analysis": {"type": "boolean"},
                            "batch_size": {"type": "integer", "minimum": 1}
                        }
                    },
                    "tensorflow_optimizations": {
                        "type": "object",
                        "properties": {
                            "enable_onednn": {"type": "boolean"},
                            "gpu_allocator": {
                                "type": "string",
                                "enum": ["cpu", "gpu"]
                            },
                            "cuda_visible_devices": {"type": "string"},
                            "memory_growth": {"type": "boolean"},
                            "mixed_precision": {"type": "boolean"}
                        }
                    }
                }
            },
            "vector_analysis": {
                "type": "object",
                "properties": {
                    "feature_vector_size": {"type": "integer", "minimum": 1},
                    "similarity_metrics": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["cosine", "euclidean"]
                        }
                    },
                    "index_type": {
                        "type": "string",
                        "enum": ["IndexFlatIP", "IndexIVFFlat", "IndexIVFPQ"]
                    },
                    "nlist": {"type": "integer", "minimum": 1},
                    "hash_algorithm": {
                        "type": "string",
                        "enum": ["md5", "sha1", "sha256"]
                    },
                    "normalization": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "method": {
                                "type": "string",
                                "enum": ["l1", "l2"]
                            }
                        }
                    }
                }
            },
            "quality": {
                "type": "object",
                "properties": {
                    "min_confidence_threshold": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "fallback_values": {
                        "type": "object",
                        "properties": {
                            "tempo": {"type": "number"},
                            "key": {"type": "string"},
                            "scale": {"type": "string"},
                            "key_strength": {"type": "number"},
                            "default_float": {"type": "number"}
                        }
                    },
                    "error_handling": {
                        "type": "object",
                        "properties": {
                            "continue_on_error": {"type": "boolean"},
                            "log_errors": {"type": "boolean"},
                            "retry_failed": {"type": "boolean"},
                            "max_retries": {"type": "integer", "minimum": 0}
                        }
                    }
                }
            }
        }
    }
    
    def __init__(self):
        self.schemas = {
            "app_settings": self.APP_SETTINGS_SCHEMA,
            "database": self.DATABASE_SCHEMA,
            "logging": self.LOGGING_SCHEMA,
            "analysis_config": self.ANALYSIS_CONFIG_SCHEMA,
            "discovery": self.DISCOVERY_SCHEMA
        }
    
    def validate_config(self, config_name: str, config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate configuration against its schema
        
        Args:
            config_name: Name of the configuration (e.g., "app_settings")
            config_data: Configuration data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if config_name not in self.schemas:
            return False, [f"Unknown configuration type: {config_name}"]
        
        schema = self.schemas[config_name]
        errors = []
        
        try:
            validate(instance=config_data, schema=schema)
            return True, []
        except ValidationError as e:
            errors.append(f"Validation error: {e.message}")
            if e.path:
                errors.append(f"Path: {'.'.join(str(p) for p in e.path)}")
        except SchemaError as e:
            errors.append(f"Schema error: {e.message}")
        except Exception as e:
            errors.append(f"Unexpected error: {str(e)}")
        
        return False, errors
    
    def validate_all_configs(self, configs: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Validate all configurations
        
        Args:
            configs: Dictionary of configuration data
            
        Returns:
            Dictionary with validation results
        """
        results = {}
        
        for config_name, config_data in configs.items():
            is_valid, errors = self.validate_config(config_name, config_data)
            results[config_name] = {
                "valid": is_valid,
                "errors": errors,
                "config_keys": list(config_data.keys()) if config_data else []
            }
        
        return results
    
    def get_schema(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific configuration"""
        return self.schemas.get(config_name)
    
    def list_schemas(self) -> List[str]:
        """List all available schemas"""
        return list(self.schemas.keys())

# Global validator instance
config_validator = ConfigValidator()
