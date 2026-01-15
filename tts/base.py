"""
TTS Engine Base Module
Abstract base class and shared types for TTS engines.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class VoiceInfo:
    """Information about an available TTS voice."""
    id: str
    name: str
    languages: list[str]
    gender: str  # 'male', 'female', 'neutral'
    age: str  # 'adult', 'child', etc.
    engine: str  # 'pyttsx3', 'kokoro'

    def __str__(self) -> str:
        gender_icon = '♂' if self.gender == 'male' else '♀' if self.gender == 'female' else '⚪'
        engine_tag = f"[{self.engine}]" if self.engine != 'pyttsx3' else ''
        return f"{gender_icon} {self.name} {engine_tag}".strip()


@dataclass
class TTSConfig:
    """Configuration for TTS synthesis."""
    voice_id: Optional[str] = None
    rate: int = 150  # Words per minute (typically 100-200)
    volume: float = 1.0  # 0.0 to 1.0
    pitch: int = 50  # 0-100, only supported on some engines


class TTSEngineBase(ABC):
    """Abstract base class for TTS engines."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the TTS engine. Returns True if successful."""
        pass

    @abstractmethod
    def get_voices(self) -> list[VoiceInfo]:
        """Get list of available voices."""
        pass

    @abstractmethod
    def get_voice_by_id(self, voice_id: str) -> Optional[VoiceInfo]:
        """Get voice info by ID."""
        pass

    @abstractmethod
    def configure(self, config: TTSConfig) -> None:
        """Apply TTS configuration."""
        pass

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak text directly (for preview)."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop current speech."""
        pass

    @abstractmethod
    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Synthesize text to an audio file."""
        pass

    @abstractmethod
    def synthesize_chapter(
        self,
        text: str,
        output_path: str,
        chunk_size: int = 5000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Synthesize a chapter, handling long text."""
        pass

    @abstractmethod
    def estimate_duration(self, text: str, rate: int = 150) -> float:
        """Estimate speech duration in seconds."""
        pass

    @abstractmethod
    def get_engine_name(self) -> str:
        """Get the name of this TTS engine."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass
