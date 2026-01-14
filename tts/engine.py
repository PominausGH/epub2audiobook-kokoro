"""
TTS Engine Module
Wraps pyttsx3 which provides cross-platform TTS using native engines:
- Windows: SAPI5
- macOS: NSSpeechSynthesizer
- Linux: espeak-ng
"""

import os
import sys
import tempfile
import wave
import threading
from dataclasses import dataclass
from typing import Optional, Callable
from pathlib import Path

import pyttsx3


@dataclass
class VoiceInfo:
    """Information about an available TTS voice."""
    id: str
    name: str
    languages: list[str]
    gender: str  # 'male', 'female', 'neutral'
    age: str  # 'adult', 'child', etc.

    def __str__(self) -> str:
        gender_icon = '♂' if self.gender == 'male' else '♀' if self.gender == 'female' else '⚪'
        return f"{gender_icon} {self.name}"


@dataclass
class TTSConfig:
    """Configuration for TTS synthesis."""
    voice_id: Optional[str] = None
    rate: int = 150  # Words per minute (typically 100-200)
    volume: float = 1.0  # 0.0 to 1.0
    pitch: int = 50  # 0-100, only supported on some engines


class TTSEngine:
    """
    Cross-platform TTS engine wrapper.
    Uses pyttsx3 which automatically selects the appropriate native engine.
    """

    def __init__(self):
        self._engine: Optional[pyttsx3.Engine] = None
        self._voices: list[VoiceInfo] = []
        self._is_speaking = False
        self._lock = threading.Lock()

    def initialize(self) -> bool:
        """Initialize the TTS engine."""
        try:
            self._engine = pyttsx3.init()
            self._load_voices()
            return True
        except Exception as e:
            print(f"Failed to initialize TTS engine: {e}")
            return False

    def _load_voices(self) -> None:
        """Load available voices from the engine."""
        if not self._engine:
            return

        self._voices = []
        voices = self._engine.getProperty('voices')

        for voice in voices:
            # Parse voice properties
            gender = 'neutral'
            if hasattr(voice, 'gender'):
                if 'female' in str(voice.gender).lower():
                    gender = 'female'
                elif 'male' in str(voice.gender).lower():
                    gender = 'male'
            elif 'female' in voice.name.lower():
                gender = 'female'
            elif 'male' in voice.name.lower():
                gender = 'male'

            # Get languages
            languages = []
            if hasattr(voice, 'languages') and voice.languages:
                languages = [str(l) for l in voice.languages]

            # Parse age
            age = 'adult'
            if hasattr(voice, 'age'):
                age = str(voice.age)

            voice_info = VoiceInfo(
                id=voice.id,
                name=voice.name,
                languages=languages,
                gender=gender,
                age=age
            )
            self._voices.append(voice_info)

    def get_voices(self) -> list[VoiceInfo]:
        """Get list of available voices."""
        return self._voices

    def get_voice_by_id(self, voice_id: str) -> Optional[VoiceInfo]:
        """Get voice info by ID."""
        for voice in self._voices:
            if voice.id == voice_id:
                return voice
        return None

    def configure(self, config: TTSConfig) -> None:
        """Apply TTS configuration."""
        if not self._engine:
            return

        if config.voice_id:
            self._engine.setProperty('voice', config.voice_id)

        # Set rate (words per minute)
        self._engine.setProperty('rate', config.rate)

        # Set volume (0.0 to 1.0)
        self._engine.setProperty('volume', config.volume)

        # Note: pitch is not universally supported
        # Some engines like espeak support it via rate adjustment

    def speak(self, text: str) -> None:
        """Speak text directly (for preview)."""
        if not self._engine:
            return

        with self._lock:
            self._is_speaking = True

        try:
            self._engine.say(text)
            self._engine.runAndWait()
        finally:
            with self._lock:
                self._is_speaking = False

    def stop(self) -> None:
        """Stop current speech."""
        if self._engine and self._is_speaking:
            self._engine.stop()

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Synthesize text to an audio file.

        Args:
            text: Text to synthesize
            output_path: Path for output audio file
            progress_callback: Optional callback(current, total) for progress

        Returns:
            True if successful
        """
        if not self._engine:
            return False

        try:
            # pyttsx3 can save to file directly
            self._engine.save_to_file(text, output_path)
            self._engine.runAndWait()

            # Verify file was created
            return os.path.exists(output_path)

        except Exception as e:
            print(f"Synthesis error: {e}")
            return False

    def synthesize_chapter(
        self,
        text: str,
        output_path: str,
        chunk_size: int = 5000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Synthesize a chapter, handling long text by chunking.

        Args:
            text: Chapter text
            output_path: Output file path
            chunk_size: Characters per chunk (for progress reporting)
            progress_callback: Progress callback

        Returns:
            True if successful
        """
        if not self._engine:
            return False

        # For shorter texts, synthesize directly
        if len(text) <= chunk_size:
            if progress_callback:
                progress_callback(0, 1)
            result = self.synthesize_to_file(text, output_path)
            if progress_callback:
                progress_callback(1, 1)
            return result

        # For longer texts, we still synthesize as one piece
        # (pyttsx3 handles this well), but report progress based on estimation
        total_chunks = (len(text) + chunk_size - 1) // chunk_size

        if progress_callback:
            progress_callback(0, total_chunks)

        result = self.synthesize_to_file(text, output_path)

        if progress_callback:
            progress_callback(total_chunks, total_chunks)

        return result

    def estimate_duration(self, text: str, rate: int = 150) -> float:
        """
        Estimate speech duration in seconds.

        Args:
            text: Text to estimate
            rate: Words per minute

        Returns:
            Estimated duration in seconds
        """
        words = len(text.split())
        return (words / rate) * 60

    def get_engine_name(self) -> str:
        """Get the name of the underlying TTS engine."""
        if sys.platform == 'win32':
            return 'SAPI5 (Windows)'
        elif sys.platform == 'darwin':
            return 'NSSpeechSynthesizer (macOS)'
        else:
            return 'espeak-ng (Linux)'

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._engine:
            self._engine.stop()
            # Note: pyttsx3 doesn't have explicit cleanup
            self._engine = None


class TTSEngineFactory:
    """Factory for creating TTS engines with specific backends."""

    @staticmethod
    def create_default() -> TTSEngine:
        """Create a TTS engine with default settings."""
        engine = TTSEngine()
        engine.initialize()
        return engine

    @staticmethod
    def get_available_backends() -> list[str]:
        """Get list of available TTS backends on this system."""
        backends = []

        if sys.platform == 'win32':
            backends.append('sapi5')
        elif sys.platform == 'darwin':
            backends.append('nsss')
        else:
            # Linux - check for espeak
            if os.path.exists('/usr/bin/espeak-ng') or os.path.exists('/usr/bin/espeak'):
                backends.append('espeak')

        return backends
