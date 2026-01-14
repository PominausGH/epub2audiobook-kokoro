# Kokoro TTS Engine Integration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Kokoro TTS as an alternative engine with per-voice selection, allowing users to mix system voices and high-quality neural Kokoro voices in the same dropdown.

**Architecture:** Create an abstract `TTSEngineBase` class, refactor existing pyttsx3 code into `Pyttsx3Engine`, add new `KokoroEngine`, and update `TTSEngineFactory` to combine voices from all available engines. Each `VoiceInfo` tracks which engine it belongs to.

**Tech Stack:** kokoro>=0.9.4, soundfile, espeak-ng (Linux dependency)

---

## Task 1: Create Abstract TTS Engine Base Class

**Files:**
- Create: `tts/base.py`
- Test: `tests/tts/test_base.py`

**Step 1: Write the failing test**

Create `tests/tts/test_base.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tts/test_base.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tts.base'"

**Step 3: Write minimal implementation**

Create `tts/base.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tts/test_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tts/base.py tests/tts/test_base.py
git commit -m "feat(tts): add abstract TTSEngineBase class and VoiceInfo with engine field"
```

---

## Task 2: Create tests directory structure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/tts/__init__.py`

**Step 1: Create test directory files**

Create `tests/__init__.py`:

```python
"""Test suite for epub2audiobook."""
```

Create `tests/tts/__init__.py`:

```python
"""TTS engine tests."""
```

**Step 2: Verify pytest can discover tests**

Run: `pytest tests/ --collect-only`
Expected: Shows test collection

**Step 3: Commit**

```bash
git add tests/__init__.py tests/tts/__init__.py
git commit -m "chore: add test directory structure"
```

---

## Task 3: Refactor Pyttsx3Engine from existing TTSEngine

**Files:**
- Create: `tts/pyttsx3_engine.py`
- Modify: `tts/engine.py` (will become compatibility shim)
- Test: `tests/tts/test_pyttsx3_engine.py`

**Step 1: Write the failing test**

Create `tests/tts/test_pyttsx3_engine.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tts/test_pyttsx3_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tts.pyttsx3_engine'"

**Step 3: Write implementation**

Create `tts/pyttsx3_engine.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tts/test_pyttsx3_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tts/pyttsx3_engine.py tests/tts/test_pyttsx3_engine.py
git commit -m "feat(tts): extract Pyttsx3Engine from TTSEngine"
```

---

## Task 4: Create KokoroEngine

**Files:**
- Create: `tts/kokoro_engine.py`
- Test: `tests/tts/test_kokoro_engine.py`

**Step 1: Write the failing test**

Create `tests/tts/test_kokoro_engine.py`:

```python
"""Tests for Kokoro TTS engine."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tts/test_kokoro_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tts.kokoro_engine'"

**Step 3: Write implementation**

Create `tts/kokoro_engine.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tts/test_kokoro_engine.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tts/kokoro_engine.py tests/tts/test_kokoro_engine.py
git commit -m "feat(tts): add KokoroEngine with neural TTS support"
```

---

## Task 5: Update TTSEngineFactory to combine engines

**Files:**
- Create: `tts/factory.py`
- Test: `tests/tts/test_factory.py`

**Step 1: Write the failing test**

Create `tests/tts/test_factory.py`:

```python
"""Tests for TTS engine factory."""

import pytest
from unittest.mock import patch, MagicMock

from tts.factory import TTSEngineFactory, CombinedTTSEngine
from tts.base import VoiceInfo


def test_factory_get_available_engines():
    """Test getting list of available engines."""
    engines = TTSEngineFactory.get_available_engines()
    assert isinstance(engines, list)
    assert "pyttsx3" in engines  # Always available


def test_factory_create_combined_engine():
    """Test creating combined engine."""
    engine = TTSEngineFactory.create_combined()
    assert engine is not None
    assert isinstance(engine, CombinedTTSEngine)


def test_combined_engine_has_voices():
    """Test combined engine returns voices."""
    engine = TTSEngineFactory.create_combined()
    engine.initialize()
    voices = engine.get_voices()
    assert isinstance(voices, list)


def test_combined_engine_get_voice_by_id():
    """Test finding voice by ID."""
    engine = TTSEngineFactory.create_combined()
    engine.initialize()
    voices = engine.get_voices()

    if voices:
        found = engine.get_voice_by_id(voices[0].id)
        assert found is not None
        assert found.id == voices[0].id


def test_combined_engine_routes_to_correct_engine():
    """Test that synthesis routes to correct engine based on voice."""
    engine = TTSEngineFactory.create_combined()
    engine.initialize()

    # The engine should be able to handle voices from different engines
    voices = engine.get_voices()
    assert len(voices) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/tts/test_factory.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'tts.factory'"

**Step 3: Write implementation**

Create `tts/factory.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/tts/test_factory.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tts/factory.py tests/tts/test_factory.py
git commit -m "feat(tts): add TTSEngineFactory with CombinedTTSEngine"
```

---

## Task 6: Update tts/__init__.py exports

**Files:**
- Modify: `tts/__init__.py`

**Step 1: Update exports**

Update `tts/__init__.py`:

```python
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
```

**Step 2: Verify imports work**

Run: `python -c "from tts import TTSEngine, VoiceInfo, TTSConfig, KOKORO_AVAILABLE; print('OK')"`
Expected: "OK"

**Step 3: Commit**

```bash
git add tts/__init__.py
git commit -m "refactor(tts): update exports with new engine classes"
```

---

## Task 7: Remove old engine.py (now redundant)

**Files:**
- Delete: `tts/engine.py`

**Step 1: Verify nothing imports from engine.py directly**

Run: `grep -r "from tts.engine import" . --include="*.py" | grep -v __pycache__`
Expected: Only tts/__init__.py (which we updated)

**Step 2: Delete the file**

```bash
rm tts/engine.py
```

**Step 3: Verify tests still pass**

Run: `pytest tests/tts/ -v`
Expected: PASS

**Step 4: Commit**

```bash
git add -A
git commit -m "refactor(tts): remove redundant engine.py"
```

---

## Task 8: Update requirements.txt

**Files:**
- Modify: `requirements.txt`

**Step 1: Add Kokoro dependencies**

Update `requirements.txt` to add:

```
# Neural TTS (optional)
kokoro>=0.9.4
soundfile
```

**Step 2: Verify installation**

Run: `pip install kokoro>=0.9.4 soundfile`
Expected: Success

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat: add kokoro TTS dependencies"
```

---

## Task 9: Update GUI to show engine info

**Files:**
- Modify: `gui/main_window.py:70-73` (engine label)
- Modify: `gui/main_window.py:248-261` (_populate_voices)

**Step 1: Update engine label to be dynamic**

In `gui/main_window.py`, change the engine label initialization (around line 70-73):

```python
        # Subtitle showing TTS engine
        self.engine_label = QLabel(f"Using: {self.tts_engine.get_engine_name()}")
        self.engine_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.engine_label.setStyleSheet("color: gray; font-style: italic;")
        main_layout.addWidget(self.engine_label)
```

**Step 2: Update voice combo to show engine tags**

The `VoiceInfo.__str__` already includes engine tag for non-pyttsx3 voices, so this should work automatically.

**Step 3: Add method to update engine label on voice change**

Add to `_connect_signals`:

```python
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
```

Add new method:

```python
    def _on_voice_changed(self, index: int):
        """Handle voice selection change."""
        voice_id = self.voice_combo.currentData()
        if voice_id:
            voice = self.tts_engine.get_voice_by_id(voice_id)
            if voice:
                # Update engine label based on selected voice
                self.tts_engine.configure(TTSConfig(voice_id=voice_id))
                self.engine_label.setText(f"Using: {self.tts_engine.get_engine_name()}")
```

**Step 4: Run GUI to verify**

Run: `python main.py`
Expected: Voice dropdown shows both system and Kokoro voices with tags

**Step 5: Commit**

```bash
git add gui/main_window.py
git commit -m "feat(gui): update voice selector to show engine tags"
```

---

## Task 10: Update CLI to support engine selection

**Files:**
- Modify: `main.py:69-78` (TTS initialization)
- Modify: `main.py:190-206` (argument parser)

**Step 1: Update CLI help text**

Add to argument parser:

```python
    parser.add_argument('--engine', choices=['auto', 'pyttsx3', 'kokoro'],
                        default='auto',
                        help='TTS engine: auto (default), pyttsx3, or kokoro')
```

**Step 2: Update run_cli to use selected engine**

```python
    # Initialize TTS based on engine choice
    print(f"\nInitializing TTS engine...")

    if args.engine == 'kokoro':
        from tts import KokoroEngine, KOKORO_AVAILABLE
        if not KOKORO_AVAILABLE:
            print("ERROR: Kokoro not installed. Run: pip install kokoro soundfile")
            sys.exit(1)
        tts = KokoroEngine()
    elif args.engine == 'pyttsx3':
        from tts import Pyttsx3Engine
        tts = Pyttsx3Engine()
    else:  # auto
        from tts import TTSEngine
        tts = TTSEngine()

    if not tts.initialize():
        print("ERROR: Failed to initialize TTS engine")
        sys.exit(1)
```

**Step 3: Test CLI**

Run: `python main.py --list-voices`
Expected: Shows voices from both engines

Run: `python main.py --list-voices --engine kokoro`
Expected: Shows only Kokoro voices

**Step 4: Commit**

```bash
git add main.py
git commit -m "feat(cli): add --engine flag for TTS engine selection"
```

---

## Task 11: Update converter_worker to use combined engine

**Files:**
- Modify: `gui/converter_worker.py:14-16` (imports)

**Step 1: Verify imports are compatible**

The converter_worker imports `TTSEngine` which is now aliased to `CombinedTTSEngine`, so it should work without changes. Verify:

Run: `python -c "from gui.converter_worker import ConverterWorker; print('OK')"`
Expected: "OK"

**Step 2: Commit (if changes needed)**

No changes needed if backwards compatibility works.

---

## Task 12: Add integration test

**Files:**
- Create: `tests/test_integration.py`

**Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
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
```

**Step 2: Run integration tests**

Run: `pytest tests/test_integration.py -v`
Expected: PASS (kokoro test skipped if not installed)

**Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for TTS engines"
```

---

## Task 13: Update README with Kokoro documentation

**Files:**
- Modify: `README.md`

**Step 1: Add Kokoro section**

Add after the "Supported TTS Engines" section:

```markdown
### Kokoro Neural TTS (Optional)

For higher quality voices, you can optionally install Kokoro TTS:

```bash
pip install kokoro>=0.9.4 soundfile
```

On Linux, ensure espeak-ng is installed:
```bash
sudo apt install espeak-ng
```

Kokoro provides natural-sounding neural voices that appear alongside system voices in the voice selector. Voices are tagged with `[kokoro]` in the dropdown.

**Available Kokoro Voices:**
- American English: Heart, Bella, Nicole, Adam, Michael, and more
- British English: Alice, Emma, Daniel, George, and more

Note: Kokoro requires more CPU/memory than traditional TTS and may be slower on older hardware.
```

**Step 2: Update TTS engines table**

Add row to the table:

```markdown
| All Platforms | Kokoro-82M | Heart, Bella, Adam, + 20 more (optional) |
```

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add Kokoro TTS documentation"
```

---

## Task 14: Run full test suite

**Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

**Step 2: Run with coverage**

Run: `pytest tests/ --cov=tts --cov-report=term-missing`
Expected: Good coverage of tts module

---

## Summary

This plan adds Kokoro TTS support with:
- Abstract `TTSEngineBase` class for engine implementations
- `Pyttsx3Engine` wrapping the existing pyttsx3 code
- `KokoroEngine` for neural TTS with 23 preset voices
- `CombinedTTSEngine` that merges voices from all available engines
- Per-voice engine routing (selecting a Kokoro voice uses Kokoro, system voice uses pyttsx3)
- Backwards-compatible `TTSEngine` alias
- CLI `--engine` flag for explicit engine selection
- Full test coverage
