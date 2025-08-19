# Database Architecture Plan - Essentia TensorFlow Playlist System

## Executive Summary

This document outlines a comprehensive database architecture redesign for the Essentia TensorFlow playlist system. The current system has strong analysis capabilities but lacks proper playlist management, user control, and web UI integration features.

## Current State Analysis

### Strengths
- Robust file discovery and metadata extraction
- Comprehensive audio analysis (Essentia, TensorFlow, FAISS)
- Good separation of concerns with independent analyzer services
- Proper status tracking for analysis processes

### Gaps Identified
- **No playlist management system**
- **No user control/authentication**
- **Limited web UI integration points**
- **Missing control fields for playlist operations**
- **No collaborative features**
- **Limited query optimization for playlist generation**

## Proposed Database Architecture

### 1. Core Control Tables

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);
```

#### User Sessions Table
```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_activity TIMESTAMP DEFAULT NOW()
);
```

### 2. Playlist Management Tables

#### Playlists Table
```sql
CREATE TABLE playlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    is_collaborative BOOLEAN DEFAULT FALSE,
    cover_image_url VARCHAR(500),
    total_duration INTEGER DEFAULT 0, -- in seconds
    track_count INTEGER DEFAULT 0,
    play_count INTEGER DEFAULT 0,
    rating_avg FLOAT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_played TIMESTAMP
);
```

#### Playlist Tracks Table
```sql
CREATE TABLE playlist_tracks (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    added_by_user_id INTEGER REFERENCES users(id),
    added_at TIMESTAMP DEFAULT NOW(),
    notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    play_count INTEGER DEFAULT 0,
    last_played TIMESTAMP,
    UNIQUE(playlist_id, position)
);
```

#### Playlist Collaborators Table
```sql
CREATE TABLE playlist_collaborators (
    id SERIAL PRIMARY KEY,
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission_level VARCHAR(20) DEFAULT 'edit', -- 'view', 'edit', 'admin'
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(playlist_id, user_id)
);
```

### 3. Enhanced Control Fields

#### File Control Fields (Add to existing files table)
```sql
ALTER TABLE files ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE files ADD COLUMN is_favorite BOOLEAN DEFAULT FALSE;
ALTER TABLE files ADD COLUMN play_count INTEGER DEFAULT 0;
ALTER TABLE files ADD COLUMN last_played TIMESTAMP;
ALTER TABLE files ADD COLUMN rating INTEGER CHECK (rating >= 1 AND rating <= 5);
ALTER TABLE files ADD COLUMN skip_count INTEGER DEFAULT 0;
ALTER TABLE files ADD COLUMN tags TEXT[] DEFAULT '{}';
ALTER TABLE files ADD COLUMN notes TEXT;
ALTER TABLE files ADD COLUMN is_hidden BOOLEAN DEFAULT FALSE;
ALTER TABLE files ADD COLUMN custom_metadata JSONB DEFAULT '{}';
```

#### Analysis Control Fields (Add to existing analysis tables)
```sql
-- Add to TrackAnalysisSummary
ALTER TABLE track_analysis_summary ADD COLUMN analysis_quality_score FLOAT;
ALTER TABLE track_analysis_summary ADD COLUMN confidence_threshold FLOAT DEFAULT 0.7;
ALTER TABLE track_analysis_summary ADD COLUMN manual_override BOOLEAN DEFAULT FALSE;
ALTER TABLE track_analysis_summary ADD COLUMN override_reason TEXT;
ALTER TABLE track_analysis_summary ADD COLUMN override_by_user_id INTEGER REFERENCES users(id);
```

### 4. Playlist Generation Tables

#### Playlist Templates Table
```sql
CREATE TABLE playlist_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_type VARCHAR(50) NOT NULL, -- 'mood', 'genre', 'era', 'energy', 'custom'
    parameters JSONB NOT NULL, -- Template-specific parameters
    is_system_template BOOLEAN DEFAULT FALSE,
    created_by_user_id INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Generated Playlists Table
```sql
CREATE TABLE generated_playlists (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES playlist_templates(id),
    user_id INTEGER REFERENCES users(id),
    playlist_id INTEGER REFERENCES playlists(id),
    generation_parameters JSONB NOT NULL,
    generation_score FLOAT, -- Quality score of the generation
    track_count INTEGER DEFAULT 0,
    total_duration INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. Smart Features Tables

#### Track Similarity Cache Table
```sql
CREATE TABLE track_similarity_cache (
    id SERIAL PRIMARY KEY,
    source_file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    target_file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    similarity_score FLOAT NOT NULL,
    similarity_type VARCHAR(50) NOT NULL, -- 'essentia', 'tensorflow', 'faiss', 'hybrid'
    confidence_score FLOAT,
    calculated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_file_id, target_file_id, similarity_type)
);
```

#### Playlist Recommendations Table
```sql
CREATE TABLE playlist_recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    playlist_id INTEGER REFERENCES playlists(id) ON DELETE CASCADE,
    recommended_file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    recommendation_score FLOAT NOT NULL,
    recommendation_reason TEXT,
    recommendation_type VARCHAR(50), -- 'similar_tracks', 'user_preferences', 'collaborative'
    is_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### User Listening History Table
```sql
CREATE TABLE user_listening_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    playlist_id INTEGER REFERENCES playlists(id),
    played_at TIMESTAMP DEFAULT NOW(),
    duration_played INTEGER, -- seconds played
    completed BOOLEAN DEFAULT FALSE,
    skipped BOOLEAN DEFAULT FALSE,
    session_id VARCHAR(255)
);
```

### 6. Web UI Integration Tables

#### UI State Table
```sql
CREATE TABLE ui_state (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    component_name VARCHAR(100) NOT NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, component_name)
);
```

#### User Preferences Table
```sql
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, preference_key)
);
```

#### Notification Settings Table
```sql
CREATE TABLE notification_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT FALSE,
    web_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, notification_type)
);
```

## Indexing Strategy

### Performance Indexes
```sql
-- User performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);

-- Playlist performance
CREATE INDEX idx_playlists_user_id ON playlists(user_id);
CREATE INDEX idx_playlists_public ON playlists(is_public) WHERE is_public = TRUE;
CREATE INDEX idx_playlist_tracks_playlist_position ON playlist_tracks(playlist_id, position);
CREATE INDEX idx_playlist_tracks_file_id ON playlist_tracks(file_id);

-- Analysis performance
CREATE INDEX idx_files_user_id ON files(user_id);
CREATE INDEX idx_files_favorite ON files(is_favorite) WHERE is_favorite = TRUE;
CREATE INDEX idx_files_rating ON files(rating) WHERE rating IS NOT NULL;
CREATE INDEX idx_files_play_count ON files(play_count);

-- Similarity and recommendations
CREATE INDEX idx_track_similarity_source ON track_similarity_cache(source_file_id, similarity_score);
CREATE INDEX idx_track_similarity_target ON track_similarity_cache(target_file_id, similarity_score);
CREATE INDEX idx_playlist_recommendations_user ON playlist_recommendations(user_id, recommendation_score);

-- History and analytics
CREATE INDEX idx_listening_history_user_time ON user_listening_history(user_id, played_at DESC);
CREATE INDEX idx_listening_history_file ON user_listening_history(file_id, played_at DESC);
```

## API Integration Points

### New API Endpoints Required

#### Authentication
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/register`
- `GET /api/auth/profile`

#### Playlist Management
- `GET /api/playlists` - List user's playlists
- `POST /api/playlists` - Create new playlist
- `GET /api/playlists/{id}` - Get playlist details
- `PUT /api/playlists/{id}` - Update playlist
- `DELETE /api/playlists/{id}` - Delete playlist
- `POST /api/playlists/{id}/tracks` - Add track to playlist
- `DELETE /api/playlists/{id}/tracks/{track_id}` - Remove track from playlist
- `PUT /api/playlists/{id}/tracks/reorder` - Reorder tracks

#### Smart Features
- `POST /api/playlists/generate` - Generate playlist from template
- `GET /api/tracks/{id}/similar` - Get similar tracks
- `GET /api/playlists/{id}/recommendations` - Get playlist recommendations
- `POST /api/tracks/{id}/play` - Record track play
- `POST /api/tracks/{id}/skip` - Record track skip

#### User Preferences
- `GET /api/user/preferences` - Get user preferences
- `PUT /api/user/preferences` - Update user preferences
- `GET /api/user/history` - Get listening history
- `GET /api/user/statistics` - Get user statistics

## Web UI Integration

### React TypeScript Interfaces
```typescript
// User management
interface User {
  id: number;
  username: string;
  email: string;
  display_name?: string;
  avatar_url?: string;
  is_admin: boolean;
  preferences: Record<string, any>;
}

// Playlist management
interface Playlist {
  id: number;
  name: string;
  description?: string;
  is_public: boolean;
  is_collaborative: boolean;
  cover_image_url?: string;
  total_duration: number;
  track_count: number;
  play_count: number;
  rating_avg: number;
  created_at: string;
  updated_at: string;
  tracks: PlaylistTrack[];
}

interface PlaylistTrack {
  id: number;
  file_id: number;
  position: number;
  added_by_user_id: number;
  added_at: string;
  notes?: string;
  rating?: number;
  play_count: number;
  track: Track; // Extended track info
}

// Smart features
interface PlaylistTemplate {
  id: number;
  name: string;
  description?: string;
  template_type: 'mood' | 'genre' | 'era' | 'energy' | 'custom';
  parameters: Record<string, any>;
}

interface TrackRecommendation {
  id: number;
  track: Track;
  recommendation_score: number;
  recommendation_reason: string;
  recommendation_type: string;
}
```

### State Management
- **User Context**: Authentication, preferences, permissions
- **Playlist Context**: Current playlist, editing state, collaboration
- **Player Context**: Currently playing, queue, history
- **Analysis Context**: Analysis results, similarity data

## Migration Strategy

### Phase 1: Core Infrastructure
1. Create new tables (users, sessions, playlists)
2. Add control fields to existing tables
3. Implement authentication system
4. Basic playlist CRUD operations

### Phase 2: Smart Features
1. Implement playlist templates
2. Add similarity caching
3. Build recommendation engine
4. Add listening history tracking

### Phase 3: Advanced Features
1. Collaborative playlists
2. Advanced analytics
3. Performance optimizations
4. Web UI integration

### Phase 4: Polish & Optimization
1. Advanced indexing
2. Query optimization
3. Caching strategies
4. Performance monitoring

## Performance Considerations

### Database Optimization
- **Connection pooling**: Already configured for 20 connections
- **Read replicas**: Consider for heavy read operations
- **Partitioning**: Partition listening history by date
- **Caching**: Redis for frequently accessed data

### Query Optimization
- **Eager loading**: Use SQLAlchemy relationships efficiently
- **Pagination**: Implement cursor-based pagination for large datasets
- **Materialized views**: For complex analytics queries
- **Background jobs**: Use Celery for heavy operations

### Scalability
- **Horizontal scaling**: Database sharding by user_id
- **CDN**: For static assets and cover images
- **Load balancing**: Multiple API instances
- **Monitoring**: Comprehensive metrics and alerting

## Security Considerations

### Authentication & Authorization
- **JWT tokens**: Secure session management
- **Password hashing**: bcrypt with salt
- **Rate limiting**: Prevent abuse
- **CORS**: Proper cross-origin configuration

### Data Protection
- **Input validation**: Sanitize all user inputs
- **SQL injection**: Use parameterized queries
- **XSS protection**: Sanitize output
- **Privacy**: User data encryption

## Monitoring & Analytics

### Key Metrics
- **User engagement**: Playlist creation, track plays
- **System performance**: Query times, response times
- **Analysis quality**: Confidence scores, manual overrides
- **Recommendation accuracy**: Acceptance rates

### Logging Strategy
- **Structured logging**: JSON format for easy parsing
- **Audit trails**: Track all user actions
- **Error tracking**: Comprehensive error logging
- **Performance monitoring**: Query performance tracking

## Conclusion

This comprehensive database architecture provides:

1. **Complete playlist management** with collaborative features
2. **User control and authentication** system
3. **Smart features** for playlist generation and recommendations
4. **Web UI integration** with proper state management
5. **Performance optimization** for large-scale usage
6. **Security and monitoring** best practices

The architecture is designed to scale from personal use to collaborative music discovery platforms while maintaining the existing robust analysis capabilities.
