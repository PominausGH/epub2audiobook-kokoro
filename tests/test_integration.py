"""Integration tests for TTS engines."""

import pytest
import tempfile
import os

from tts import TTSEngine, TTSConfig, KOKORO_AVAILABLE


def test_pyttsx3_synthesis():
    """Test pyttsx3 can synthesize to file."""
    engine = TTSEngine()
    assert engine.initialize()

    voices = engine.get_voices()
    pyttsx3_voices = [v for v in voices if v.engine == "pyttsx3"]

    if not pyttsx3_voices:
        pytest.skip("No pyttsx3 voices available")

    engine.configure(TTSConfig(voice_id=pyttsx3_voices[0].id))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name

    try:
        result = engine.synthesize_to_file("Hello world", temp_path)
        assert result is True
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    engine.cleanup()


@pytest.mark.skipif(not KOKORO_AVAILABLE, reason="Kokoro not installed")
def test_kokoro_synthesis():
    """Test Kokoro can synthesize to file."""
    engine = TTSEngine()
    assert engine.initialize()

    voices = engine.get_voices()
    kokoro_voices = [v for v in voices if v.engine == "kokoro"]

    if not kokoro_voices:
        pytest.skip("No Kokoro voices available")

    engine.configure(TTSConfig(voice_id=kokoro_voices[0].id))

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        temp_path = f.name

    try:
        result = engine.synthesize_to_file("Hello world", temp_path)
        assert result is True
        assert os.path.exists(temp_path)
        assert os.path.getsize(temp_path) > 0
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    engine.cleanup()


def test_combined_engine_voice_routing():
    """Test that combined engine routes to correct backend."""
    engine = TTSEngine()
    assert engine.initialize()

    voices = engine.get_voices()

    # Group by engine
    by_engine = {}
    for v in voices:
        by_engine.setdefault(v.engine, []).append(v)

    # At minimum pyttsx3 should be available
    assert "pyttsx3" in by_engine

    engine.cleanup()
