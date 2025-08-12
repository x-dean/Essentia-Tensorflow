# Configuration Action Plan

## Executive Summary

The analysis identified **47 hardcoded values** across **10 key files** that should be made configurable. This document provides a prioritized action plan for implementing these improvements.

## Quick Wins (Phase 1 - 1-2 days)

### 1. Update app_settings.json
**Priority**: Critical
**Effort**: 2 hours

Add missing configuration sections:

```json
{
  "api": {
    "timeouts": {
      "default": 60,
      "analysis": 300,
      "faiss": 300,
      "discovery": 120
    }
  },
  "discovery": {
    "supported_extensions": [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"],
    "cache_ttl": 3600,
    "batch_size": 100,
    "hash_algorithm": "md5"
  },
  "faiss": {
    "index_name": "music_library",
    "vector_dimension": 128,
    "similarity_threshold": 0.8
  }
}
```

### 2. Update database.json
**Priority**: Critical
**Effort**: 1 hour

Add retry settings:

```json
{
  "retry_settings": {
    "max_retries": 3,
    "initial_delay": 1,
    "backoff_multiplier": 2,
    "max_delay": 30
  },
  "connection_timeout": 30
}
```

### 3. Update logging.json
**Priority**: High
**Effort**: 1 hour

Add suppression settings:

```json
{
  "suppression": {
    "tensorflow": true,
    "essentia": true,
    "librosa": true,
    "matplotlib": true,
    "pil": true
  }
}
```

## Medium Priority (Phase 2 - 3-5 days)

### 4. Update analysis_config.json
**Priority**: High
**Effort**: 4 hours

Add new sections:

```json
{
  "performance": {
    "tensorflow_optimizations": {
      "enable_onednn": false,
      "gpu_allocator": "cpu",
      "cuda_visible_devices": "-1"
    }
  },
  "vector_analysis": {
    "feature_vector_size": 128,
    "similarity_metrics": ["cosine", "euclidean"],
    "index_type": "IVFFlat",
    "nlist": 100,
    "hash_algorithm": "md5"
  },
  "quality": {
    "fallback_values": {
      "default_float": -999.0
    }
  }
}
```

### 5. Update Core Configuration Classes
**Priority**: High
**Effort**: 6 hours

Files to update:
- `src/playlist_app/core/config.py`
- `src/playlist_app/core/config_loader.py`
- `src/playlist_app/core/config_manager.py`

### 6. Update Service Classes
**Priority**: Medium
**Effort**: 8 hours

Files to update:
- `src/playlist_app/services/essentia_analyzer.py`
- `src/playlist_app/services/audio_analysis_service.py`
- `src/playlist_app/services/faiss_service.py`
- `src/playlist_app/services/discovery.py`

## Low Priority (Phase 3 - 1-2 weeks)

### 7. Update Web UI Configuration
**Priority**: Medium
**Effort**: 4 hours

- Update `web-ui/src/services/api.ts` to use configuration
- Add configuration endpoint to backend
- Update frontend to fetch timeouts from API

### 8. Update CLI Tools
**Priority**: Low
**Effort**: 3 hours

- Update `scripts/batch_analyzer_cli.py`
- Add configuration file support
- Add environment variable support

### 9. Add Configuration Validation
**Priority**: Medium
**Effort**: 6 hours

- Add validation for numeric ranges
- Add validation for file paths
- Add validation for required settings
- Add cross-configuration dependency checks

## Implementation Steps

### Step 1: Create Enhanced Configuration Files
1. Update existing JSON configuration files with new sections
2. Add validation schemas for each configuration file
3. Create configuration migration scripts

### Step 2: Update Configuration Loading
1. Modify `config_loader.py` to handle new sections
2. Add fallback logic for missing configuration values
3. Add environment variable overrides

### Step 3: Update Service Classes
1. Replace hardcoded values with configuration lookups
2. Add proper error handling for missing configuration
3. Add logging for configuration changes

### Step 4: Update Main Application
1. Update `main.py` to use configuration values
2. Add configuration validation on startup
3. Add configuration reload capability

### Step 5: Update Web UI
1. Add configuration API endpoints
2. Update frontend to use configuration values
3. Add configuration management UI

### Step 6: Testing and Validation
1. Create configuration test suite
2. Test with different configuration combinations
3. Validate performance impact

## Risk Assessment

### Low Risk
- Adding new configuration sections
- Updating logging configuration
- Adding FAISS configuration

### Medium Risk
- Updating database retry logic
- Updating analysis parameters
- Updating discovery settings

### High Risk
- Updating core configuration loading
- Updating main application startup
- Updating web UI configuration

## Rollback Plan

1. **Configuration Changes**: Keep old hardcoded values as fallbacks
2. **Code Changes**: Use feature flags to enable/disable new configuration
3. **Database Changes**: No database schema changes required
4. **API Changes**: Maintain backward compatibility

## Success Metrics

### Phase 1 Success Criteria
- [ ] All hardcoded timeouts moved to configuration
- [ ] Database retry settings configurable
- [ ] Discovery settings configurable
- [ ] Logging suppression configurable

### Phase 2 Success Criteria
- [ ] Analysis parameters configurable
- [ ] FAISS settings configurable
- [ ] External API settings configurable
- [ ] Performance tuning options available

### Phase 3 Success Criteria
- [ ] Web UI uses configuration
- [ ] CLI tools use configuration
- [ ] Configuration validation implemented
- [ ] Documentation updated

## Timeline

### Week 1
- Day 1-2: Phase 1 implementation
- Day 3-5: Phase 2 implementation (core services)

### Week 2
- Day 1-3: Phase 2 implementation (remaining services)
- Day 4-5: Testing and validation

### Week 3
- Day 1-3: Phase 3 implementation
- Day 4-5: Documentation and final testing

## Resource Requirements

### Development
- 1 Backend developer (3 weeks)
- 1 Frontend developer (1 week)
- 1 QA engineer (1 week)

### Infrastructure
- No additional infrastructure required
- Configuration files can be version controlled
- Environment-specific configurations supported

## Next Steps

1. **Immediate**: Review and approve this action plan
2. **Week 1**: Begin Phase 1 implementation
3. **Week 2**: Begin Phase 2 implementation
4. **Week 3**: Begin Phase 3 implementation
5. **Ongoing**: Monitor and optimize configuration usage

## Configuration Best Practices

### Security
- Keep sensitive data in environment variables
- Validate all configuration inputs
- Use secure defaults

### Performance
- Cache configuration values
- Minimize configuration file size
- Use efficient configuration loading

### Maintainability
- Document all configuration options
- Provide sensible defaults
- Use consistent naming conventions

### Flexibility
- Support environment-specific configurations
- Allow runtime configuration updates
- Provide configuration validation
