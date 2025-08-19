# Analyzer Verification Plan

## Overview

This document outlines the comprehensive verification plan for testing each analyzer independently and understanding their database integration. The plan covers database schema verification, control value analysis, individual analyzer testing, and end-to-end workflow validation.

## Database Schema and Control Values

### Database Tables Structure

The system uses a modular database schema with separate tables for each analyzer:

#### Core Tables
- **`files`** - Main file registry with status tracking
- **`audio_metadata`** - Extracted metadata from audio files

#### Analyzer Status Tables
- **`essentia_analysis_status`** - Essentia analyzer status tracking
- **`tensorflow_analysis_status`** - TensorFlow analyzer status tracking  
- **`faiss_analysis_status`** - FAISS analyzer status tracking

#### Analyzer Results Tables
- **`essentia_analysis_results`** - Essentia analysis results storage
- **`tensorflow_analysis_results`** - TensorFlow analysis results storage
- **`faiss_analysis_results`** - FAISS analysis results storage

#### Summary Tables
- **`track_analysis_summary`** - Consolidated view of all analyzer statuses
- **`faiss_index_metadata`** - FAISS index management metadata

### Control Values and Triggers

#### File Status Enum (`FileStatus`)
- **`DISCOVERED`** - File found but not yet processed
- **`HAS_METADATA`** - File has metadata extracted
- **`FAILED`** - File processing failed

#### Analyzer Status Enum (`AnalyzerStatus`)
- **`PENDING`** - Analysis not yet started
- **`ANALYZING`** - Analysis in progress
- **`ANALYZED`** - Analysis completed successfully
- **`FAILED`** - Analysis failed
- **`RETRY`** - Analysis failed but should be retried

#### Key Control Flags
- **`File.is_active`** - Whether file should be processed
- **`File.has_metadata`** - Whether metadata extraction completed
- **`File.status`** - Current processing status

### Trigger Conditions

#### Essentia Analyzer Triggers
- Files with `File.is_active = True`
- Files with `EssentiaAnalysisStatus.status = PENDING`
- Files that exist on disk

#### TensorFlow Analyzer Triggers
- Files with `File.is_active = True`
- Files with `TensorFlowAnalysisStatus.status = PENDING`
- Files that exist on disk
- Requires Essentia analysis to be completed first

#### FAISS Analyzer Triggers
- Files with `File.is_active = True`
- Files with `FAISSAnalysisStatus.status = PENDING`
- Files that exist on disk
- Requires both Essentia and TensorFlow analysis to be completed

## Individual Analyzer Testing

### 1. Essentia Analyzer (`IndependentEssentiaService`)

#### Purpose
Pure audio feature extraction using Essentia library

#### Features Tested
- Basic audio features (loudness, dynamic complexity, spectral complexity)
- Spectral features (centroid, rolloff, bandwidth, flatness)
- Rhythm features (BPM, beat tracking, rhythm confidence)
- Harmonic features (key detection, chord detection)
- MFCC features (mel-frequency cepstral coefficients)

#### Test Scenarios
1. **Service Initialization**
   - Verify service can be instantiated
   - Check configuration loading
   - Validate audio processing parameters

2. **Pending Files Detection**
   - Query files with `EssentiaAnalysisStatus.status = PENDING`
   - Verify file filtering logic
   - Check limit handling

3. **Single File Analysis**
   - Analyze one file end-to-end
   - Verify result structure
   - Check database status updates

4. **Batch Analysis**
   - Process multiple files
   - Verify error handling
   - Check progress tracking

5. **Database Integration**
   - Verify status record creation
   - Check result storage
   - Validate status transitions

### 2. TensorFlow Analyzer (`IndependentTensorFlowService`)

#### Purpose
Machine learning classification using TensorFlow models

#### Features Tested
- MusicNN model for music tag prediction
- Mel-spectrogram extraction
- Top prediction results with confidence scores
- Mood analysis features

#### Test Scenarios
1. **Service Initialization**
   - Verify TensorFlow availability
   - Check model loading
   - Validate configuration

2. **Pending Files Detection**
   - Query files with `TensorFlowAnalysisStatus.status = PENDING`
   - Verify dependency on Essentia completion
   - Check file filtering

3. **Single File Analysis**
   - Analyze one file with MusicNN
   - Verify prediction results
   - Check mood analysis

4. **Batch Analysis**
   - Process multiple files
   - Verify memory management
   - Check error handling

5. **Database Integration**
   - Verify result storage in JSON format
   - Check status updates
   - Validate cross-analyzer dependencies

### 3. FAISS Analyzer (`IndependentFAISSService`)

#### Purpose
Vector similarity search and indexing

#### Features Tested
- Vector indexing of audio features
- Similarity search capabilities
- Index persistence and management
- Integration with database storage

#### Test Scenarios
1. **Service Initialization**
   - Verify FAISS availability
   - Check index configuration
   - Validate vector dimensions

2. **Pending Files Detection**
   - Query files with `FAISSAnalysisStatus.status = PENDING`
   - Verify dependency on other analyzers
   - Check file filtering

3. **Single File Analysis**
   - Create feature vector for one file
   - Verify vector dimensions
   - Check index addition

4. **Batch Analysis**
   - Process multiple files
   - Verify index building
   - Check memory usage

5. **Database Integration**
   - Verify vector storage
   - Check index metadata
   - Validate similarity search

## Database Integration Testing

### Status Record Management
- Verify status records are created for all files
- Check status transitions (PENDING → ANALYZING → ANALYZED/FAILED)
- Validate error handling and retry logic

### Result Storage
- Verify analysis results are stored correctly
- Check JSON serialization of complex data
- Validate data integrity and consistency

### Cross-Analyzer Dependencies
- Verify proper sequencing of analyzers
- Check dependency enforcement
- Validate data flow between analyzers

### Database Consistency
- Check for orphaned records
- Verify foreign key relationships
- Validate data integrity constraints

## End-to-End Workflow Testing

### Complete Analysis Pipeline
1. **File Discovery** → Files added to database with `DISCOVERED` status
2. **Metadata Extraction** → Files updated to `HAS_METADATA` status
3. **Essentia Analysis** → Audio features extracted and stored
4. **TensorFlow Analysis** → ML predictions generated
5. **FAISS Analysis** → Vectors indexed for similarity search
6. **Summary Update** → Track analysis summary updated

### Workflow Validation
- Verify all steps complete successfully
- Check data consistency across all tables
- Validate final state of all files
- Test error recovery and retry mechanisms

## Verification Script Usage

### Running the Verification
```bash
python scripts/analyzer_verification_plan.py
```

### Expected Output
The script will:
1. Verify database schema and control values
2. Test each analyzer independently
3. Validate database integration
4. Test end-to-end workflows
5. Generate comprehensive test results

### Test Results
Results are saved to `analyzer_verification_results_YYYYMMDD_HHMMSS.json` with:
- Overall success/failure status
- Detailed results for each test category
- Error messages and debugging information
- Performance metrics and timing data

## Best Practices for Analyzer Verification

### 1. Independent Testing
- Test each analyzer in isolation
- Verify no cross-contamination between analyzers
- Check that analyzers can be enabled/disabled independently

### 2. Database Consistency
- Verify all database operations are atomic
- Check for proper transaction handling
- Validate foreign key relationships

### 3. Error Handling
- Test with invalid files
- Verify graceful degradation
- Check retry mechanisms

### 4. Performance Monitoring
- Monitor memory usage during analysis
- Check processing time per file
- Validate resource cleanup

### 5. Configuration Validation
- Test with different configuration settings
- Verify analyzer enable/disable flags
- Check parameter validation

## Troubleshooting Guide

### Common Issues

#### No Files to Analyze
- Check if files exist in database
- Verify file status is `DISCOVERED`
- Check if status records exist

#### Analyzer Dependencies
- Ensure Essentia analysis completes before TensorFlow
- Verify TensorFlow analysis completes before FAISS
- Check status transitions

#### Database Connection Issues
- Verify database is running
- Check connection parameters
- Validate table existence

#### File Access Issues
- Verify file paths are correct
- Check file permissions
- Validate file format support

### Debugging Steps
1. Check database schema verification results
2. Verify control values and trigger conditions
3. Test individual analyzer initialization
4. Check pending files detection
5. Validate database integration
6. Test end-to-end workflow

## Conclusion

This verification plan provides a comprehensive framework for testing the modular analysis system. By following this plan, you can ensure that each analyzer works correctly both independently and as part of the integrated system. The verification script automates most of the testing process and provides detailed results for debugging and optimization.
