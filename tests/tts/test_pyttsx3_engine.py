"""Tests for Pyttsx3 TTS engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tts.pyttsx3_engine import Pyttsx3Engine
from tts.base import TTSEngineBase, VoiceInfo, TTSConfig


def test_pyttsx3_engine_inherits_base():
    """Test that Pyttsx3Engine inherits from TTSEngineBase."""
    assert issubclass(Pyttsx3Engine, TTSEngineBase)


def test_pyttsx3_engine_creation():
    """Test Pyttsx3Engine can be instantiated."""
    engine = Pyttsx3Engine()
    assert engine is not None


@patch('tts.pyttsx3_engine.pyttsx3')
def test_initialize_success(mock_pyttsx3):
    """Test successful initialization."""
    mock_engine = MagicMock()
    mock_pyttsx3.init.return_value = mock_engine
    mock_engine.getProperty.return_value = []

    engine = Pyttsx3Engine()
    result = engine.initialize()

    assert result is True
    mock_pyttsx3.init.assert_called_once()


@patch('tts.pyttsx3_engine.pyttsx3')
def test_get_voices_returns_voice_info_with_engine(mock_pyttsx3):
    """Test that voices include engine field."""
    mock_engine = MagicMock()
    mock_pyttsx3.init.return_value = mock_engine

    mock_voice = Mock()
    mock_voice.id = "voice1"
    mock_voice.name = "Test Voice"
    mock_voice.gender = "male"
    mock_voice.languages = ["en"]
    mock_voice.age = "adult"
    mock_engine.getProperty.return_value = [mock_voice]

    engine = Pyttsx3Engine()
    engine.initialize()
    voices = engine.get_voices()

    assert len(voices) == 1
    assert voices[0].engine == "pyttsx3"
    assert isinstance(voices[0], VoiceInfo)


def test_get_engine_name_contains_platform():
    """Test engine name reflects platform."""
    engine = Pyttsx3Engine()
    name = engine.get_engine_name()
    assert isinstance(name, str)
    assert len(name) > 0
