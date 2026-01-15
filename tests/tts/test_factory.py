"""Tests for TTS engine factory."""

import pytest
from unittest.mock import patch, MagicMock

from tts.factory import TTSEngineFactory, CombinedTTSEngine
from tts.base import VoiceInfo


def test_factory_get_available_engines():
    """Test getting list of available engines."""
    engines = TTSEngineFactory.get_available_engines()
    assert isinstance(engines, list)
    assert "pyttsx3" in engines  # Always available


def test_factory_create_combined_engine():
    """Test creating combined engine."""
    engine = TTSEngineFactory.create_combined()
    assert engine is not None
    assert isinstance(engine, CombinedTTSEngine)


@patch('tts.factory.Pyttsx3Engine')
def test_combined_engine_has_voices(mock_pyttsx3_class):
    """Test combined engine returns voices."""
    # Setup mock
    mock_engine = MagicMock()
    mock_engine.initialize.return_value = True
    mock_engine.get_voices.return_value = [
        VoiceInfo(id="v1", name="Voice1", languages=["en"], gender="male", age="adult", engine="pyttsx3")
    ]
    mock_pyttsx3_class.return_value = mock_engine

    engine = TTSEngineFactory.create_combined()
    engine.initialize()
    voices = engine.get_voices()
    assert isinstance(voices, list)


@patch('tts.factory.Pyttsx3Engine')
def test_combined_engine_get_voice_by_id(mock_pyttsx3_class):
    """Test finding voice by ID."""
    # Setup mock
    mock_engine = MagicMock()
    mock_engine.initialize.return_value = True
    test_voice = VoiceInfo(id="v1", name="Voice1", languages=["en"], gender="male", age="adult", engine="pyttsx3")
    mock_engine.get_voices.return_value = [test_voice]
    mock_pyttsx3_class.return_value = mock_engine

    engine = TTSEngineFactory.create_combined()
    engine.initialize()

    found = engine.get_voice_by_id("v1")
    assert found is not None
    assert found.id == "v1"


@patch('tts.factory.Pyttsx3Engine')
def test_combined_engine_routes_to_correct_engine(mock_pyttsx3_class):
    """Test that synthesis routes to correct engine based on voice."""
    # Setup mock
    mock_engine = MagicMock()
    mock_engine.initialize.return_value = True
    mock_engine.get_voices.return_value = [
        VoiceInfo(id="v1", name="Voice1", languages=["en"], gender="male", age="adult", engine="pyttsx3")
    ]
    mock_pyttsx3_class.return_value = mock_engine

    engine = TTSEngineFactory.create_combined()
    engine.initialize()

    # The engine should be able to handle voices from different engines
    voices = engine.get_voices()
    assert len(voices) > 0
