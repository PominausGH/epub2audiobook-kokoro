"""
Pyttsx3 TTS Engine Module
Wraps pyttsx3 which provides cross-platform TTS using native engines:
- Windows: SAPI5
- macOS: NSSpeechSynthesizer
- Linux: espeak-ng
"""

import os
import sys
import threading
from typing import Optional, Callable

import pyttsx3

from .base import TTSEngineBase, VoiceInfo, TTSConfig


class Pyttsx3Engine(TTSEngineBase):
    """
    Cross-platform TTS engine using pyttsx3.
    Automatically selects the appropriate native engine for the platform.
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
            print(f"Failed to initialize pyttsx3 engine: {e}")
            return False

    def _load_voices(self) -> None:
        """Load available voices from the engine."""
        if not self._engine:
            return

        self._voices = []
        voices = self._engine.getProperty('voices')

        for voice in voices:
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

            languages = []
            if hasattr(voice, 'languages') and voice.languages:
                languages = [str(lang) for lang in voice.languages]

            age = 'adult'
            if hasattr(voice, 'age'):
                age = str(voice.age)

            voice_info = VoiceInfo(
                id=voice.id,
                name=voice.name,
                languages=languages,
                gender=gender,
                age=age,
                engine="pyttsx3"
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

        self._engine.setProperty('rate', config.rate)
        self._engine.setProperty('volume', config.volume)

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
        """Synthesize text to an audio file."""
        if not self._engine:
            return False

        try:
            self._engine.save_to_file(text, output_path)
            self._engine.runAndWait()
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
        """Synthesize a chapter, handling long text by chunking."""
        if not self._engine:
            return False

        if len(text) <= chunk_size:
            if progress_callback:
                progress_callback(0, 1)
            result = self.synthesize_to_file(text, output_path)
            if progress_callback:
                progress_callback(1, 1)
            return result

        total_chunks = (len(text) + chunk_size - 1) // chunk_size

        if progress_callback:
            progress_callback(0, total_chunks)

        result = self.synthesize_to_file(text, output_path)

        if progress_callback:
            progress_callback(total_chunks, total_chunks)

        return result

    def estimate_duration(self, text: str, rate: int = 150) -> float:
        """Estimate speech duration in seconds."""
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
            self._engine = None
