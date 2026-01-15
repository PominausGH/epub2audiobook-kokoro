"""TTS engine wrapper module."""

from .base import TTSEngineBase, VoiceInfo, TTSConfig
from .pyttsx3_engine import Pyttsx3Engine
from .kokoro_engine import KokoroEngine, KOKORO_AVAILABLE
from .factory import TTSEngineFactory, CombinedTTSEngine

# Backwards compatibility alias
TTSEngine = CombinedTTSEngine

__all__ = [
    'TTSEngineBase',
    'VoiceInfo',
    'TTSConfig',
    'Pyttsx3Engine',
    'KokoroEngine',
    'KOKORO_AVAILABLE',
    'TTSEngineFactory',
    'CombinedTTSEngine',
    'TTSEngine',  # Backwards compat
]
