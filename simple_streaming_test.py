#!/usr/bin/env python3
import sys
import os
import time
sys.path.insert(0, '/app/src')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig

print('=== Streaming TensorFlow Analysis Test ===')

config = TensorFlowConfig()
config.enable_streaming = True
config.chunk_duration = 30.0
config.overlap_ratio = 0.5
config.max_chunks = 5

print(f'Streaming enabled: {config.enable_streaming}')
print(f'Chunk duration: {config.chunk_duration}s')
print(f'Max chunks: {config.max_chunks}')

analyzer = TensorFlowAnalyzer(config)
print('TensorFlow analyzer created successfully')

audio_file = '/music/Mark Ambor - Belong Together.mp3'
print(f'Testing with: {audio_file}')

start_time = time.time()
result = analyzer.analyze_audio_file(audio_file)
analysis_time = time.time() - start_time

print(f'Analysis time: {analysis_time:.2f}s')

if 'metadata' in result:
    metadata = result['metadata']
    print(f'Analysis strategy: {metadata.get("analysis_strategy", "unknown")}')
    print(f'Audio duration: {metadata.get("audio_duration", 0):.1f}s')

if 'tensorflow_analysis' in result:
    tf_results = result['tensorflow_analysis']
    if 'musicnn' in tf_results:
        musicnn = tf_results['musicnn']
        if 'error' not in musicnn:
            print('MusicNN analysis successful!')
            if 'chunk_count' in musicnn:
                print(f'Chunks processed: {musicnn["chunk_count"]}')
            if 'top_predictions' in musicnn:
                print('Top MusicNN predictions:')
                for i, pred in enumerate(musicnn['top_predictions'][:3], 1):
                    print(f'  {i}. {pred["tag"]}: {pred["confidence"]:.3f}')

print('Test completed successfully!')
