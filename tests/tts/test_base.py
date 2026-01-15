"""Tests for TTS base classes."""

import pytest
from tts.base import TTSEngineBase, VoiceInfo, TTSConfig


def test_voice_info_creation():
    """Test VoiceInfo dataclass creation."""
    voice = VoiceInfo(
        id="test_voice",
        name="Test Voice",
        languages=["en"],
        gender="male",
        age="adult",
        engine="pyttsx3"
    )
    assert voice.id == "test_voice"
    assert voice.engine == "pyttsx3"


def test_voice_info_str_male():
    """Test VoiceInfo string representation for male voice."""
    voice = VoiceInfo(
        id="test", name="David", languages=["en"],
        gender="male", age="adult", engine="pyttsx3"
    )
    assert "David" in str(voice)


def test_voice_info_str_female():
    """Test VoiceInfo string representation for female voice."""
    voice = VoiceInfo(
        id="test", name="Zira", languages=["en"],
        gender="female", age="adult", engine="pyttsx3"
    )
    assert "Zira" in str(voice)


def test_tts_config_defaults():
    """Test TTSConfig default values."""
    config = TTSConfig()
    assert config.voice_id is None
    assert config.rate == 150
    assert config.volume == 1.0


def test_tts_engine_base_is_abstract():
    """Test that TTSEngineBase cannot be instantiated directly."""
    with pytest.raises(TypeError):
        TTSEngineBase()
