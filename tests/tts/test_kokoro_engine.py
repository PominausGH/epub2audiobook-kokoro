"""Tests for Kokoro TTS engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tts.kokoro_engine import KokoroEngine, KOKORO_VOICES, KOKORO_AVAILABLE
from tts.base import TTSEngineBase, VoiceInfo, TTSConfig


def test_kokoro_engine_inherits_base():
    """Test that KokoroEngine inherits from TTSEngineBase."""
    assert issubclass(KokoroEngine, TTSEngineBase)


def test_kokoro_engine_creation():
    """Test KokoroEngine can be instantiated."""
    engine = KokoroEngine()
    assert engine is not None


def test_kokoro_voices_constant():
    """Test KOKORO_VOICES contains expected structure."""
    assert isinstance(KOKORO_VOICES, dict)
    if KOKORO_VOICES:
        first_key = list(KOKORO_VOICES.keys())[0]
        voice = KOKORO_VOICES[first_key]
        assert 'name' in voice
        assert 'gender' in voice
        assert 'lang_code' in voice


def test_get_engine_name():
    """Test engine name."""
    engine = KokoroEngine()
    name = engine.get_engine_name()
    assert "Kokoro" in name


@pytest.mark.skipif(not KOKORO_AVAILABLE, reason="Kokoro not installed")
def test_initialize_with_kokoro():
    """Test initialization when kokoro is available."""
    engine = KokoroEngine()
    result = engine.initialize()
    assert result is True


def test_get_voices_returns_kokoro_voices():
    """Test that voices have kokoro engine tag."""
    engine = KokoroEngine()
    engine.initialize()
    voices = engine.get_voices()

    for voice in voices:
        assert voice.engine == "kokoro"
        assert isinstance(voice, VoiceInfo)


def test_estimate_duration():
    """Test duration estimation."""
    engine = KokoroEngine()
    duration = engine.estimate_duration("This is a test with ten words here now.", rate=150)
    assert duration > 0
    assert isinstance(duration, float)
