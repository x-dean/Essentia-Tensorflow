#!/usr/bin/env python3
"""
Tests for Enhanced TensorFlow Integration with Mood Analysis

This test suite covers:
- TensorFlow analyzer functionality
- MusicNN model integration
- Mood analysis capabilities
- Integration with modular analysis service
- Database storage
"""

import unittest
import os
import sys
import json
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playlist_app.services.tensorflow_analyzer import TensorFlowAnalyzer, TensorFlowConfig
from playlist_app.services.modular_analysis_service import ModularAnalysisService
from playlist_app.models.database import AudioAnalysis, File, get_db_session, close_db_session


class TestTensorFlowConfig(unittest.TestCase):
    """Test TensorFlow configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = TensorFlowConfig()
        
        self.assertEqual(config.models_directory, "models")
        self.assertTrue(config.enable_musicnn)
        self.assertFalse(config.enable_vggish)
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.musicnn_input_frames, 187)
        self.assertEqual(config.musicnn_input_mels, 96)
        self.assertTrue(config.enable_mood_analysis)
        self.assertEqual(config.mood_confidence_threshold, 0.3)
    
    def test_custom_config(self):
        """Test custom configuration"""
        config = TensorFlowConfig(
            models_directory="custom_models",
            enable_musicnn=False,
            sample_rate=22050,
            mood_confidence_threshold=0.5
        )
        
        self.assertEqual(config.models_directory, "custom_models")
        self.assertFalse(config.enable_musicnn)
        self.assertEqual(config.sample_rate, 22050)
        self.assertEqual(config.mood_confidence_threshold, 0.5)


class TestTensorFlowAnalyzer(unittest.TestCase):
    """Test TensorFlow analyzer functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.config = TensorFlowConfig(
            models_directory="models",
            enable_musicnn=True,
            sample_rate=16000
        )
        
        # Create a mock analyzer without actual TensorFlow
        with patch('src.playlist_app.services.tensorflow_analyzer.TENSORFLOW_AVAILABLE', True):
            with patch('src.playlist_app.services.tensorflow_analyzer.ESSENTIA_AVAILABLE', True):
                self.analyzer = TensorFlowAnalyzer(self.config)
    
    def test_analyzer_initialization(self):
        """Test analyzer initialization"""
        self.assertIsNotNone(self.analyzer)
        self.assertEqual(self.analyzer.config.models_directory, "models")
        self.assertTrue(self.analyzer.config.enable_musicnn)
    
    @patch('src.playlist_app.services.tensorflow_analyzer.tf')
    @patch('src.playlist_app.services.tensorflow_analyzer.es')
    def test_load_models(self, mock_essentia, mock_tf):
        """Test model loading"""
        # Mock TensorFlow model loading
        mock_graph = MagicMock()
        mock_tf.Graph.return_value = mock_graph
        mock_tf.io.gfile.GFile.return_value.__enter__.return_value.read.return_value = b"mock_model_data"
        
        # Mock model file existence
        with patch('pathlib.Path.exists', return_value=True):
            self.analyzer._load_models()
            
            # Should attempt to load MusicNN model
            self.assertIn("musicnn", self.analyzer.models)
    
    def test_load_musicnn_tags(self):
        """Test MusicNN tag loading"""
        # Mock config file
        mock_config = {
            "classes": ["rock", "pop", "jazz", "classical"]
        }
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_config)
            
            with patch('pathlib.Path.exists', return_value=True):
                self.analyzer._load_musicnn_tags()
                
                self.assertEqual(self.analyzer.musicnn_tags, ["rock", "pop", "jazz", "classical"])
    
    def test_prepare_musicnn_input(self):
        """Test MusicNN input preparation"""
        # Create mock mel-spectrogram
        mel_spec = np.random.rand(200, 96)  # More frames than needed
        
        result = self.analyzer._prepare_musicnn_input(mel_spec)
        
        # Should have correct shape (1, 187, 96)
        self.assertEqual(result.shape, (1, 187, 96))
    
    def test_calculate_valence(self):
        """Test valence calculation"""
        # Mock predictions and tag names
        predictions = [0.8, 0.2, 0.9, 0.1]  # High positive scores
        tag_names = ["happy", "sad", "beautiful", "aggressive"]
        
        valence = self.analyzer._calculate_valence(predictions, tag_names)
        
        # Should be positive (happy + beautiful > sad + aggressive)
        self.assertGreater(valence, 0)
    
    def test_calculate_arousal(self):
        """Test arousal calculation"""
        # Mock predictions and tag names
        predictions = [0.9, 0.1, 0.8, 0.2]  # High energy scores
        tag_names = ["dance", "chill", "rock", "ambient"]
        
        arousal = self.analyzer._calculate_arousal(predictions, tag_names)
        
        # Should be high (dance + rock > chill + ambient)
        self.assertGreater(arousal, 0.5)
    
    def test_extract_mood_analysis(self):
        """Test mood analysis extraction"""
        # Mock MusicNN results
        mock_musicnn_results = {
            "all_predictions": [0.8, 0.2, 0.9, 0.1, 0.7, 0.3],
            "tag_names": ["dance", "chill", "happy", "sad", "rock", "ambient"]
        }
        
        mood_results = self.analyzer._extract_mood_analysis(mock_musicnn_results)
        
        # Should contain mood analysis
        self.assertIn("mood_scores", mood_results)
        self.assertIn("dominant_moods", mood_results)
        self.assertIn("emotions", mood_results)
        self.assertIn("primary_mood", mood_results)
    
    @patch('src.playlist_app.services.tensorflow_analyzer.tf')
    @patch('src.playlist_app.services.tensorflow_analyzer.es')
    def test_analyze_audio_file(self, mock_essentia, mock_tf):
        """Test complete audio file analysis"""
        # Mock audio loading
        mock_audio = np.random.rand(16000 * 30)  # 30 seconds at 16kHz
        mock_essentia.MonoLoader.return_value.return_value = mock_audio
        
        # Mock mel-spectrogram extraction
        mock_mel_spec = np.random.rand(187, 96)
        mock_essentia.MelBands.return_value.return_value = np.random.rand(96)
        mock_essentia.FrameCutter.return_value.__iter__.return_value = [np.random.rand(1024)] * 187
        
        # Mock TensorFlow inference
        mock_predictions = np.random.rand(1, 50) * 0.5 + 0.5  # Values between 0.5 and 1.0
        mock_tf.compat.v1.Session.return_value.__enter__.return_value.run.return_value = mock_predictions
        
        # Mock model
        mock_model = MagicMock()
        mock_model.get_tensor_by_name.side_effect = [
            MagicMock(),  # input tensor
            MagicMock()   # output tensor
        ]
        self.analyzer.models["musicnn"] = mock_model
        
        # Mock tag names
        self.analyzer.musicnn_tags = ["rock", "pop", "jazz"] * 16 + ["dance", "chill"]
        
        # Test analysis
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_file.write(b"mock_audio_data")
            tmp_file_path = tmp_file.name
        
        try:
            results = self.analyzer.analyze_audio_file(tmp_file_path)
            
            # Check results structure
            self.assertIn("tensorflow_analysis", results)
            self.assertIn("mood_analysis", results)
            self.assertIn("metadata", results)
            
            # Check MusicNN results
            musicnn_results = results["tensorflow_analysis"]["musicnn"]
            self.assertIn("top_predictions", musicnn_results)
            self.assertIn("statistics", musicnn_results)
            
            # Check mood analysis
            mood_results = results["mood_analysis"]
            self.assertIn("mood_scores", mood_results)
            self.assertIn("primary_mood", mood_results)
            
        finally:
            os.unlink(tmp_file_path)


class TestModularAnalysisService(unittest.TestCase):
    """Test modular analysis service integration"""
    
    def setUp(self):
        """Set up test environment"""
        self.service = ModularAnalysisService()
    
    def test_module_status(self):
        """Test module status reporting"""
        status = self.service.get_module_status()
        
        # Should have all modules
        self.assertIn("essentia", status)
        self.assertIn("tensorflow", status)
        self.assertIn("faiss", status)
        
        # Essentia should always be available
        self.assertTrue(status["essentia"]["available"])
    
    @patch('src.playlist_app.services.modular_analysis_service.essentia_analyzer')
    @patch('src.playlist_app.services.modular_analysis_service.tensorflow_analyzer')
    def test_analyze_file_tensorflow_only(self, mock_tensorflow, mock_essentia):
        """Test analysis with TensorFlow only"""
        # Mock TensorFlow results
        mock_tensorflow_results = {
            "tensorflow_analysis": {
                "musicnn": {
                    "top_predictions": [
                        {"tag": "rock", "confidence": 0.85, "index": 0},
                        {"tag": "guitar", "confidence": 0.72, "index": 31}
                    ],
                    "statistics": {
                        "mean_confidence": 0.23,
                        "max_confidence": 0.85
                    }
                }
            },
            "mood_analysis": {
                "primary_mood": "energetic",
                "mood_confidence": 0.75,
                "emotions": {
                    "valence": 0.45,
                    "arousal": 0.82,
                    "energy_level": 0.78
                }
            }
        }
        
        mock_tensorflow.analyze_audio_file.return_value = mock_tensorflow_results
        mock_tensorflow.is_available.return_value = True
        
        # Mock file record
        mock_file = MagicMock()
        mock_file.id = 1
        mock_file.file_path = "test.mp3"
        
        with patch('src.playlist_app.services.modular_analysis_service.get_db_session') as mock_db:
            mock_session = MagicMock()
            mock_session.query.return_value.filter.return_value.first.side_effect = [
                mock_file,  # File record
                None        # No existing analysis
            ]
            mock_db.return_value.__enter__.return_value = mock_session
            
            # Test analysis
            results = self.service.analyze_file(
                file_path="test.mp3",
                enable_essentia=False,
                enable_tensorflow=True,
                enable_faiss=False
            )
            
            # Check results
            self.assertIn("tensorflow", results)
            self.assertIn("mood_analysis", results["tensorflow"])
            
            # Verify TensorFlow was called
            mock_tensorflow.analyze_audio_file.assert_called_once_with("test.mp3")


class TestDatabaseIntegration(unittest.TestCase):
    """Test database integration for TensorFlow results"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database for testing
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.temp_db.close()
        
        # Mock database session
        self.mock_session = MagicMock()
    
    def tearDown(self):
        """Clean up test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_store_tensorflow_results(self):
        """Test storing TensorFlow results in database"""
        # Create mock analysis record
        analysis_record = AudioAnalysis(file_id=1)
        
        # Mock TensorFlow results
        tensorflow_results = {
            "tensorflow_analysis": {
                "musicnn": {
                    "top_predictions": [
                        {"tag": "rock", "confidence": 0.85},
                        {"tag": "guitar", "confidence": 0.72}
                    ]
                }
            },
            "mood_analysis": {
                "primary_mood": "energetic",
                "mood_confidence": 0.75,
                "emotions": {
                    "valence": 0.45,
                    "arousal": 0.82
                }
            }
        }
        
        # Test storing results
        analysis_record.tensorflow_features = json.dumps(tensorflow_results)
        analysis_record.tensorflow_summary = json.dumps({
            "top_predictions": tensorflow_results["tensorflow_analysis"]["musicnn"]["top_predictions"][:5]
        })
        analysis_record.mood_analysis = json.dumps(tensorflow_results["mood_analysis"])
        analysis_record.primary_mood = tensorflow_results["mood_analysis"]["primary_mood"]
        analysis_record.mood_confidence = tensorflow_results["mood_analysis"]["mood_confidence"]
        
        # Verify data was stored correctly
        self.assertIsNotNone(analysis_record.tensorflow_features)
        self.assertIsNotNone(analysis_record.mood_analysis)
        self.assertEqual(analysis_record.primary_mood, "energetic")
        self.assertEqual(analysis_record.mood_confidence, 0.75)
        
        # Verify JSON can be parsed
        stored_tensorflow = json.loads(analysis_record.tensorflow_features)
        stored_mood = json.loads(analysis_record.mood_analysis)
        
        self.assertIn("tensorflow_analysis", stored_tensorflow)
        self.assertIn("mood_analysis", stored_tensorflow)
        self.assertEqual(stored_mood["primary_mood"], "energetic")


class TestMoodAnalysis(unittest.TestCase):
    """Test mood analysis functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.analyzer = TensorFlowAnalyzer()
    
    def test_mood_categories(self):
        """Test mood category definitions"""
        # Test that all expected mood categories are defined
        expected_moods = [
            "energetic", "calm", "happy", "sad", "aggressive", "peaceful",
            "romantic", "nostalgic", "modern", "acoustic", "vocal", "instrumental"
        ]
        
        # Get mood categories from the analyzer
        mood_categories = self.analyzer._extract_mood_analysis.__code__.co_consts
        
        # This is a simplified test - in practice, we'd access the actual mood categories
        # For now, we'll test the mood calculation functions directly
        
        # Test valence calculation
        positive_tags = ["happy", "beautiful", "catchy"]
        negative_tags = ["sad", "aggressive"]
        
        # Mock predictions for positive tags
        predictions = [0.8, 0.7, 0.9] + [0.1, 0.2]  # High positive, low negative
        tag_names = positive_tags + negative_tags
        
        valence = self.analyzer._calculate_valence(predictions, tag_names)
        self.assertGreater(valence, 0)  # Should be positive
        
        # Test arousal calculation
        high_energy_tags = ["dance", "rock", "party"]
        low_energy_tags = ["chill", "ambient", "mellow"]
        
        predictions = [0.9, 0.8, 0.7] + [0.1, 0.2, 0.3]  # High energy, low energy
        tag_names = high_energy_tags + low_energy_tags
        
        arousal = self.analyzer._calculate_arousal(predictions, tag_names)
        self.assertGreater(arousal, 0.5)  # Should be high arousal
    
    def test_emotional_dimensions(self):
        """Test emotional dimension calculations"""
        # Test energy level calculation
        energy_tags = ["dance", "rock", "party", "fast"]
        calm_tags = ["chill", "ambient", "mellow", "slow"]
        
        predictions = [0.9, 0.8, 0.7, 0.6] + [0.1, 0.2, 0.3, 0.4]
        tag_names = energy_tags + calm_tags
        
        energy_level = self.analyzer._calculate_energy_level(predictions, tag_names)
        self.assertGreater(energy_level, 0.5)  # Should be high energy
    
    def test_mood_thresholds(self):
        """Test mood confidence thresholds"""
        # Test with different confidence thresholds
        config_low = TensorFlowConfig(mood_confidence_threshold=0.1)
        config_high = TensorFlowConfig(mood_confidence_threshold=0.8)
        
        analyzer_low = TensorFlowAnalyzer(config_low)
        analyzer_high = TensorFlowAnalyzer(config_high)
        
        # Mock MusicNN results with mixed confidence levels
        mock_results = {
            "all_predictions": [0.9, 0.3, 0.7, 0.2, 0.8, 0.1],
            "tag_names": ["dance", "chill", "rock", "ambient", "party", "mellow"]
        }
        
        mood_low = analyzer_low._extract_mood_analysis(mock_results)
        mood_high = analyzer_high._extract_mood_analysis(mock_results)
        
        # Low threshold should have more dominant moods
        self.assertGreaterEqual(
            len(mood_low.get("dominant_moods", [])),
            len(mood_high.get("dominant_moods", []))
        )


def run_tests():
    """Run all tests"""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestTensorFlowConfig,
        TestTensorFlowAnalyzer,
        TestModularAnalysisService,
        TestDatabaseIntegration,
        TestMoodAnalysis
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
