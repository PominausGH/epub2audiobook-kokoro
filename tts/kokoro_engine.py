"""
Kokoro TTS Engine Module
High-quality neural TTS using Kokoro-82M model.
"""

import os
import tempfile
from typing import Optional, Callable

from .base import TTSEngineBase, VoiceInfo, TTSConfig

# Check if kokoro is available
try:
    from kokoro import KPipeline
    import soundfile as sf
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    KPipeline = None
    sf = None

# Kokoro voice definitions
# Format: voice_id -> {name, gender, lang_code}
KOKORO_VOICES = {
    # American English voices
    "af_heart": {"name": "Heart (American)", "gender": "female", "lang_code": "a"},
    "af_bella": {"name": "Bella (American)", "gender": "female", "lang_code": "a"},
    "af_nicole": {"name": "Nicole (American)", "gender": "female", "lang_code": "a"},
    "af_aoede": {"name": "Aoede (American)", "gender": "female", "lang_code": "a"},
    "af_kore": {"name": "Kore (American)", "gender": "female", "lang_code": "a"},
    "af_sarah": {"name": "Sarah (American)", "gender": "female", "lang_code": "a"},
    "af_sky": {"name": "Sky (American)", "gender": "female", "lang_code": "a"},
    "af_star": {"name": "Star (American)", "gender": "female", "lang_code": "a"},
    "am_adam": {"name": "Adam (American)", "gender": "male", "lang_code": "a"},
    "am_echo": {"name": "Echo (American)", "gender": "male", "lang_code": "a"},
    "am_eric": {"name": "Eric (American)", "gender": "male", "lang_code": "a"},
    "am_fenrir": {"name": "Fenrir (American)", "gender": "male", "lang_code": "a"},
    "am_liam": {"name": "Liam (American)", "gender": "male", "lang_code": "a"},
    "am_michael": {"name": "Michael (American)", "gender": "male", "lang_code": "a"},
    "am_onyx": {"name": "Onyx (American)", "gender": "male", "lang_code": "a"},
    "am_puck": {"name": "Puck (American)", "gender": "male", "lang_code": "a"},
    # British English voices
    "bf_alice": {"name": "Alice (British)", "gender": "female", "lang_code": "b"},
    "bf_emma": {"name": "Emma (British)", "gender": "female", "lang_code": "b"},
    "bf_lily": {"name": "Lily (British)", "gender": "female", "lang_code": "b"},
    "bm_daniel": {"name": "Daniel (British)", "gender": "male", "lang_code": "b"},
    "bm_fable": {"name": "Fable (British)", "gender": "male", "lang_code": "b"},
    "bm_george": {"name": "George (British)", "gender": "male", "lang_code": "b"},
    "bm_lewis": {"name": "Lewis (British)", "gender": "male", "lang_code": "b"},
}


class KokoroEngine(TTSEngineBase):
    """
    High-quality neural TTS engine using Kokoro-82M.
    Provides natural-sounding voices with 82M parameter model.
    """

    def __init__(self):
        self._pipelines: dict[str, any] = {}  # lang_code -> KPipeline
        self._voices: list[VoiceInfo] = []
        self._current_voice_id: Optional[str] = None
        self._current_config: Optional[TTSConfig] = None

    def initialize(self) -> bool:
        """Initialize the Kokoro engine."""
        if not KOKORO_AVAILABLE:
            print("Kokoro TTS not available. Install with: pip install kokoro soundfile")
            # Still load voices list for display purposes
            self._load_voices()
            return False

        try:
            # Pre-load voices list (pipelines loaded on demand)
            self._load_voices()
            return True
        except Exception as e:
            print(f"Failed to initialize Kokoro engine: {e}")
            return False

    def _get_pipeline(self, lang_code: str):
        """Get or create pipeline for language code."""
        if lang_code not in self._pipelines:
            self._pipelines[lang_code] = KPipeline(lang_code=lang_code)
        return self._pipelines[lang_code]

    def _load_voices(self) -> None:
        """Load available Kokoro voices."""
        self._voices = []

        for voice_id, info in KOKORO_VOICES.items():
            voice_info = VoiceInfo(
                id=f"kokoro:{voice_id}",
                name=info["name"],
                languages=[info["lang_code"]],
                gender=info["gender"],
                age="adult",
                engine="kokoro"
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
        self._current_config = config
        if config.voice_id:
            self._current_voice_id = config.voice_id

    def _get_kokoro_voice_id(self) -> str:
        """Extract kokoro voice ID from full ID."""
        if self._current_voice_id and self._current_voice_id.startswith("kokoro:"):
            return self._current_voice_id.replace("kokoro:", "")
        return "af_heart"  # Default voice

    def _get_lang_code(self) -> str:
        """Get language code for current voice."""
        kokoro_id = self._get_kokoro_voice_id()
        if kokoro_id in KOKORO_VOICES:
            return KOKORO_VOICES[kokoro_id]["lang_code"]
        return "a"  # Default to American English

    def speak(self, text: str) -> None:
        """Speak text directly (for preview)."""
        if not KOKORO_AVAILABLE:
            return

        try:
            # Generate to temp file and play
            import subprocess

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            if self.synthesize_to_file(text, temp_path):
                # Play using system audio (cross-platform)
                import platform
                if platform.system() == "Darwin":
                    subprocess.run(["afplay", temp_path], check=False)
                elif platform.system() == "Windows":
                    import winsound
                    winsound.PlaySound(temp_path, winsound.SND_FILENAME)
                else:
                    subprocess.run(["aplay", temp_path], check=False)

            os.unlink(temp_path)
        except Exception as e:
            print(f"Playback error: {e}")

    def stop(self) -> None:
        """Stop current speech (not implemented for file-based synthesis)."""
        pass

    def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Synthesize text to an audio file."""
        if not KOKORO_AVAILABLE:
            return False

        try:
            lang_code = self._get_lang_code()
            voice_id = self._get_kokoro_voice_id()
            pipeline = self._get_pipeline(lang_code)

            # Collect all audio segments
            audio_segments = []
            generator = pipeline(text, voice=voice_id)

            for gs, ps, audio in generator:
                audio_segments.append(audio)

            if not audio_segments:
                return False

            # Concatenate and save
            import numpy as np
            full_audio = np.concatenate(audio_segments)
            sf.write(output_path, full_audio, 24000)

            return os.path.exists(output_path)

        except Exception as e:
            print(f"Kokoro synthesis error: {e}")
            return False

    def synthesize_chapter(
        self,
        text: str,
        output_path: str,
        chunk_size: int = 5000,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """Synthesize a chapter with progress reporting."""
        if not KOKORO_AVAILABLE:
            return False

        try:
            lang_code = self._get_lang_code()
            voice_id = self._get_kokoro_voice_id()
            pipeline = self._get_pipeline(lang_code)

            # Split into paragraphs for progress
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if not paragraphs:
                paragraphs = [text]

            total = len(paragraphs)
            audio_segments = []

            for i, para in enumerate(paragraphs):
                if progress_callback:
                    progress_callback(i, total)

                generator = pipeline(para, voice=voice_id)
                for gs, ps, audio in generator:
                    audio_segments.append(audio)

            if progress_callback:
                progress_callback(total, total)

            if not audio_segments:
                return False

            import numpy as np
            full_audio = np.concatenate(audio_segments)
            sf.write(output_path, full_audio, 24000)

            return os.path.exists(output_path)

        except Exception as e:
            print(f"Kokoro chapter synthesis error: {e}")
            return False

    def estimate_duration(self, text: str, rate: int = 150) -> float:
        """Estimate speech duration in seconds."""
        # Kokoro produces ~1 minute per 1000 characters
        chars = len(text)
        return (chars / 1000) * 60

    def get_engine_name(self) -> str:
        """Get the name of this TTS engine."""
        return "Kokoro-82M (Neural)"

    def cleanup(self) -> None:
        """Clean up resources."""
        self._pipelines.clear()
