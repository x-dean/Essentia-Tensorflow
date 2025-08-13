# Settings Application Fix

## Issue Description

The settings in the web UI were not being applied to the running application. Users could change settings in the Settings page, and the changes would be saved to the configuration files, but the running application would continue to use the old settings.

## Root Cause

The application had two separate configuration systems that were not properly integrated:

1. **Static Configuration System**: Used by the running application components
   - `DiscoveryConfig` class with static class variables
   - Environment variables
   - Hardcoded fallback values

2. **Dynamic Configuration System**: Used by the settings UI
   - JSON configuration files
   - `config_loader` and `config_manager` classes
   - Settings UI components

The settings UI was saving changes to JSON files, but the running application components were still reading from static class variables and environment variables, not from the JSON configuration files.

## Solution Implemented

### 1. Modified DiscoveryConfig Class

Updated `src/playlist_app/core/config.py` to read from JSON configuration files instead of using static class variables:

```python
@classmethod
def get_supported_extensions(cls) -> List[str]:
    """Get supported file extensions from config"""
    try:
        # Try to get from JSON config first
        discovery_config = config_loader.get_discovery_config()
        if discovery_config and "supported_extensions" in discovery_config:
            return discovery_config["supported_extensions"]
        
        # Fallback to app settings
        app_settings = config_loader.get_app_settings()
        if app_settings and "discovery" in app_settings and "supported_extensions" in app_settings["discovery"]:
            return app_settings["discovery"]["supported_extensions"]
    except Exception:
        pass
    
    # Fallback to hardcoded values
    return [".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"]
```

### 2. Added Dynamic Configuration Reloading

Created a `reload_configurations()` function in `main.py` that:
- Clears the configuration cache
- Reloads settings from JSON files
- Updates global variables with new values
- Applies logging configuration changes

### 3. Updated Configuration Update Endpoints

Modified both the main application (`main.py`) and API router (`src/playlist_app/api/config.py`) to:
- Save settings to JSON files
- Call `reload_configurations()` to apply changes immediately
- Clear configuration cache to ensure fresh values are loaded

### 4. Enhanced Error Handling

Added proper error handling and fallback mechanisms:
- Try to read from JSON config first
- Fallback to app settings if not found
- Fallback to environment variables
- Fallback to hardcoded values as last resort

## Files Modified

1. **`src/playlist_app/core/config.py`**
   - Updated `DiscoveryConfig` class to read from JSON files
   - Added fallback mechanisms for all configuration methods

2. **`main.py`**
   - Added `reload_configurations()` function
   - Updated config update endpoints to reload configurations
   - Added app_settings section to handle app settings updates

3. **`src/playlist_app/api/config.py`**
   - Updated `/update` endpoint to reload configurations after saving

4. **`test_settings_application.py`** (new)
   - Test script to verify settings are being applied correctly

## Testing

The fix can be tested using the provided test script:

```bash
python test_settings_application.py
```

This script will:
1. Get current configuration
2. Update discovery settings
3. Verify the changes were saved to JSON files
4. Check that runtime configuration reflects the changes

## Benefits

1. **Immediate Application**: Settings changes are now applied immediately to the running application
2. **Consistent Configuration**: Single source of truth for all configuration
3. **Better User Experience**: Users see their changes take effect without restarting the application
4. **Robust Fallbacks**: Multiple fallback mechanisms ensure the application continues to work even if configuration files are corrupted

## Configuration Priority

The application now uses the following priority order for configuration:

1. **JSON Configuration Files** (highest priority)
2. **App Settings** (from consolidated config)
3. **Environment Variables**
4. **Hardcoded Defaults** (lowest priority)

This ensures that user changes in the settings UI take precedence over all other configuration sources.
