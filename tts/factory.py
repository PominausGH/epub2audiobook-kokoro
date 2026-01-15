"""
TTS Engine Factory Module
Creates and combines TTS engines with unified voice selection.
"""

from typing import Optional, Callable

from .base import TTSEngineBase, VoiceInfo, TTSConfig
from .pyttsx3_engine import Pyttsx3Engine
from .kokoro_engine import KokoroEngine, KOKORO_AVAILABLE


class CombinedTTSEngine(TTSEngineBase):
    """
    Combined TTS engine that manages multiple backend engines.
    Routes synthesis to the appropriate engine based on voice selection.
    """

    def __init__(self):
        self._engines: dict[str, TTSEngineBase] = {}
        self._voices: list[VoiceInfo] = []
        self._current_voice: Optional[VoiceInfo] = None
        self._current_config: Optional[TTSConfig] = None

    def initialize(self) -> bool:
        """Initialize all available engines."""
        success = False

        # Always try pyttsx3
        pyttsx3_engine = Pyttsx3Engine()
        if pyttsx3_engine.initialize():
            self._engines["pyttsx3"] = pyttsx3_engine
            self._voices.extend(pyttsx3_engine.get_voices())
            success = True

        # Try Kokoro if available
        if KOKORO_AVAILABLE:
            kokoro_engine = KokoroEngine()
            if kokoro_engine.initialize():
                self._engines["kokoro"] = kokoro_engine
                self._voices.extend(kokoro_engine.get_voices())
                success = True

        return success

    def _get_engine_for_voice(self, voice_id: str) -> Optional[TTSEngineBase]:
        """Get the appropriate engine for a voice ID."""
        voice = self.get_voice_by_id(voice_id)
        if voice and voice.engine in self._engines:
            return self._engines[voice.engine]
        # Fallback to first available engine
        if self._engines:
            return list(self._engines.values())[0]
        return None

    def get_voices(self) -> list[VoiceInfo]:
        """Get combined list of voices from all engines."""
        return self._voices

    def get_voice_by_id(self, voice_id: str) -> Optional[VoiceInfo]:
        """Get voice info by ID."""
        for voice in self._voices:
            if voice.id == voice_id:
                return voice
        return None

    def configure(self, config: TTSConfig) -> None:
        """Apply TTS configuration to the appropriate engine."""
        self._current_config = config

        if config.voice_id:
            self._current_voice = self.get_voice_by_id(config.voice_id)
            engine = self._get_engine_for_voice(config.voice_id)
            if engine:
                engine.configure(config)

    def speak(self, text: str) -> None:
        """Speak text using the configured voice's engine."""
        if self._current_config and self._current_config.voice_id:
            engine = self._get_engine_for_voice(self._current_config.voice_id)
            if engine:
                engine.speak(text)

    def stop(self) -> None:
        """Stop speech on all engines."""
        for engine in self._engines.values():
            engine.stop()

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Synthesize to file using configured voice's engine."""
        if self._current_config and self._current_config.voice_id:
            engine = self._get_engine_for_voice(self._current_config.voice_id)
            if engine:
                return engine.synthesize_to_file(text, output_path, progress_callback)
        return False

    def synthesize_chapter(
        self,
        text: str,
        output_path: str,
        chunk_size: int = 5000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Synthesize chapter using configured voice's engine."""
        if self._current_config and self._current_config.voice_id:
            engine = self._get_engine_for_voice(self._current_config.voice_id)
            if engine:
                return engine.synthesize_chapter(text, output_path, chunk_size, progress_callback)
        return False

    def estimate_duration(self, text: str, rate: int = 150) -> float:
        """Estimate duration using current engine."""
        if self._current_config and self._current_config.voice_id:
            engine = self._get_engine_for_voice(self._current_config.voice_id)
            if engine:
                return engine.estimate_duration(text, rate)
        # Default estimation
        words = len(text.split())
        return (words / rate) * 60

    def get_engine_name(self) -> str:
        """Get name of current engine or combined info."""
        if self._current_voice:
            engine = self._engines.get(self._current_voice.engine)
            if engine:
                return engine.get_engine_name()

        names = [e.get_engine_name() for e in self._engines.values()]
        return " + ".join(names) if names else "No engine"

    def cleanup(self) -> None:
        """Clean up all engines."""
        for engine in self._engines.values():
            engine.cleanup()
        self._engines.clear()


class TTSEngineFactory:
    """Factory for creating TTS engines."""

    @staticmethod
    def get_available_engines() -> list[str]:
        """Get list of available TTS engine types."""
        engines = ["pyttsx3"]  # Always available
        if KOKORO_AVAILABLE:
            engines.append("kokoro")
        return engines

    @staticmethod
    def create_combined() -> CombinedTTSEngine:
        """Create a combined engine with all available backends."""
        return CombinedTTSEngine()

    @staticmethod
    def create_pyttsx3() -> Pyttsx3Engine:
        """Create a pyttsx3-only engine."""
        return Pyttsx3Engine()

    @staticmethod
    def create_kokoro() -> Optional[KokoroEngine]:
        """Create a Kokoro-only engine if available."""
        if KOKORO_AVAILABLE:
            return KokoroEngine()
        return None
