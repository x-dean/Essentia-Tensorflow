# Detailed Hardcoded Values Analysis

## File-by-File Breakdown

### 1. main.py

**Line 39**: `max_file_size=int(os.getenv("LOG_MAX_SIZE", "10485760"))` (10MB)
- **Current**: Hardcoded fallback value
- **Recommendation**: Move to `logging.json` under `max_file_size`

**Line 40**: `backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5"))`
- **Current**: Hardcoded fallback value
- **Recommendation**: Move to `logging.json` under `max_backups`

**Line 47**: `os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"`
- **Current**: Hardcoded TensorFlow log suppression
- **Recommendation**: Move to `logging.json` under `suppression.tensorflow_log_level`

**Line 79**: `discovery_interval = 300` (5 minutes)
- **Current**: Hardcoded discovery interval
- **Recommendation**: Move to `app_settings.json` under `discovery.interval`

**Line 145**: `max_retries = 30`
- **Current**: Hardcoded PostgreSQL connection retries
- **Recommendation**: Move to `database.json` under `retry_settings.max_retries`

**Line 158**: `logger.info(f"Waiting for PostgreSQL... (attempt {i+1}/{max_retries})")`
- **Current**: Hardcoded retry message format
- **Recommendation**: Make message format configurable

### 2. src/playlist_app/core/config.py

**Line 8**: `DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://playlist_user:playlist_password@localhost:5432/playlist_db")`
- **Current**: Hardcoded database URL fallback
- **Recommendation**: Move to `database.json` under `connection_url`

**Line 11**: `SEARCH_DIRECTORIES = os.getenv("SEARCH_DIRECTORIES", "/music,/audio").split(",")`
- **Current**: Hardcoded search directories fallback
- **Recommendation**: Move to `app_settings.json` under `discovery.search_directories`

**Line 14-17**: `SUPPORTED_EXTENSIONS = [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"]`
- **Current**: Hardcoded supported file extensions
- **Recommendation**: Move to `app_settings.json` under `discovery.supported_extensions`

**Line 20**: `DISCOVERY_CACHE_TTL = int(os.getenv("DISCOVERY_CACHE_TTL", "3600"))` (1 hour)
- **Current**: Hardcoded cache TTL fallback
- **Recommendation**: Move to `app_settings.json` under `discovery.cache_ttl`

**Line 21**: `DISCOVERY_BATCH_SIZE = int(os.getenv("DISCOVERY_BATCH_SIZE", "100"))`
- **Current**: Hardcoded batch size fallback
- **Recommendation**: Move to `app_settings.json` under `discovery.batch_size`

### 3. src/playlist_app/services/essentia_analyzer.py

**Line 22**: `os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"`
- **Current**: Hardcoded TensorFlow log suppression
- **Recommendation**: Move to `logging.json` under `suppression.tensorflow`

**Line 23**: `os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"`
- **Current**: Hardcoded TensorFlow optimization setting
- **Recommendation**: Move to `analysis_config.json` under `performance.tensorflow_optimizations`

**Line 24**: `os.environ["TF_GPU_ALLOCATOR"] = "cpu"`
- **Current**: Hardcoded GPU allocation setting
- **Recommendation**: Move to `analysis_config.json` under `performance.gpu_settings`

**Line 25**: `os.environ["CUDA_VISIBLE_DEVICES"] = "-1"`
- **Current**: Hardcoded GPU disable setting
- **Recommendation**: Move to `analysis_config.json` under `performance.gpu_settings`

**Line 30-32**: `essentia.log.infoActive = False`, `essentia.log.warningActive = False`
- **Current**: Hardcoded Essentia log suppression
- **Recommendation**: Move to `logging.json` under `suppression.essentia`

**Line 35**: `os.environ["LIBROSA_LOG_LEVEL"] = "WARNING"`
- **Current**: Hardcoded Librosa log level
- **Recommendation**: Move to `logging.json` under `suppression.librosa`

**Line 36**: `os.environ["PYTHONWARNINGS"] = "ignore"`
- **Current**: Hardcoded Python warnings suppression
- **Recommendation**: Move to `logging.json` under `suppression.python_warnings`

**Line 67**: `return -999.0` (in `safe_float` function)
- **Current**: Hardcoded fallback value
- **Recommendation**: Move to `analysis_config.json` under `quality.fallback_values.default_float`

### 4. src/playlist_app/services/audio_analysis_service.py

**Line 25**: `max_retries = 3`
- **Current**: Hardcoded database retry count
- **Recommendation**: Move to `database.json` under `retry_settings.max_retries`

**Line 26**: `retry_delay = 1` (seconds)
- **Current**: Hardcoded retry delay
- **Recommendation**: Move to `database.json` under `retry_settings.initial_delay`

**Line 42**: `retry_delay *= 2` (exponential backoff)
- **Current**: Hardcoded backoff multiplier
- **Recommendation**: Move to `database.json` under `retry_settings.backoff_multiplier`

### 5. src/playlist_app/services/faiss_service.py

**Line 25**: `index_name: str = "music_library"`
- **Current**: Hardcoded default index name
- **Recommendation**: Move to `app_settings.json` under `faiss.index_name`

**Line 100+**: Vector hash computation method
- **Current**: Hardcoded hash algorithm
- **Recommendation**: Move to `analysis_config.json` under `vector_analysis.hash_algorithm`

### 6. src/playlist_app/services/metadata.py

**Line 30-35**: Metadata field mappings
- **Current**: Hardcoded field mappings
- **Recommendation**: Move to `app_settings.json` under `metadata.field_mappings`

### 7. web-ui/src/services/api.ts

**Line 6**: `timeout: 60000` (60 seconds)
- **Current**: Hardcoded API timeout
- **Recommendation**: Move to `app_settings.json` under `api.timeouts.default`

**Line 245**: `timeout: 300000` (5 minutes for analysis)
- **Current**: Hardcoded analysis timeout
- **Recommendation**: Move to `app_settings.json` under `api.timeouts.analysis`

**Line 275**: `timeout: 300000` (5 minutes for FAISS)
- **Current**: Hardcoded FAISS timeout
- **Recommendation**: Move to `app_settings.json` under `api.timeouts.faiss`

### 8. scripts/batch_analyzer_cli.py

**Line 25**: `base_url: str = "http://localhost:8000"`
- **Current**: Hardcoded API base URL
- **Recommendation**: Move to environment variable or config file

**Line 35+**: Request timeout and retry logic
- **Current**: Hardcoded timeout values
- **Recommendation**: Move to configuration file

### 9. src/playlist_app/services/discovery.py

**Line 20**: `hash_input = f"{file_name}_{file_size}".encode('utf-8')`
- **Current**: Hardcoded hash input format
- **Recommendation**: Make hash format configurable

**Line 21**: `return hashlib.md5(hash_input).hexdigest()`
- **Current**: Hardcoded MD5 hash algorithm
- **Recommendation**: Move to `app_settings.json` under `discovery.hash_algorithm`

### 10. src/playlist_app/services/genre_enrichment.py

**Line 50+**: API rate limiting and timeout values
- **Current**: Hardcoded rate limits and timeouts
- **Recommendation**: Move to `app_settings.json` under `external_apis.*.rate_limit` and `external_apis.*.timeout`

## Configuration Categories

### 1. Performance Settings
- Timeouts (API, database, analysis)
- Retry counts and delays
- Worker counts and batch sizes
- Memory limits
- Cache settings

### 2. Logging Settings
- Log levels
- File sizes and rotation
- Suppression settings
- Output formats

### 3. Discovery Settings
- Search directories
- Supported file extensions
- Cache TTL
- Batch sizes
- Hash algorithms

### 4. Analysis Settings
- Audio processing parameters
- Algorithm enable/disable flags
- Quality thresholds
- Fallback values
- Vector analysis settings

### 5. External API Settings
- Rate limits
- Timeouts
- User agents
- API keys (should be in environment variables)

### 6. Database Settings
- Connection pool settings
- Retry logic
- Timeout values

### 7. FAISS Settings
- Index names
- Vector dimensions
- Similarity thresholds
- Index types

## Implementation Notes

### Environment Variables vs Configuration Files
- **Sensitive data** (API keys, passwords): Use environment variables
- **Application settings** (timeouts, limits): Use configuration files
- **Development vs production**: Use environment-specific config files

### Default Values
- Always provide sensible defaults
- Document all default values
- Allow environment variable overrides

### Validation
- Validate numeric ranges
- Check file path existence
- Validate required vs optional settings
- Cross-reference dependencies

### Migration Strategy
1. Add new configuration sections
2. Update code to use config with fallbacks
3. Remove hardcoded values
4. Add validation and documentation

## Priority Implementation Order

### Phase 1 (Critical)
1. Database retry settings
2. API timeouts
3. Discovery settings
4. Logging suppression

### Phase 2 (Important)
1. Analysis parameters
2. FAISS settings
3. External API settings
4. Performance tuning

### Phase 3 (Nice to have)
1. Advanced logging options
2. CLI configuration
3. Metadata mappings
4. Hash algorithms
