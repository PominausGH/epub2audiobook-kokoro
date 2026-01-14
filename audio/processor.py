"""
Audio Processor Module
Handles audio file operations, format conversion, and chapter merging.
"""

import os
import subprocess
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pathlib import Path

from pydub import AudioSegment


class AudioFormat(Enum):
    """Supported audio output formats."""
    MP3 = "mp3"
    M4B = "m4b"
    M4A = "m4a"
    WAV = "wav"
    OGG = "ogg"


@dataclass
class ChapterMarker:
    """Chapter marker for audiobook."""
    title: str
    start_ms: int  # Start time in milliseconds
    end_ms: int  # End time in milliseconds

    @property
    def start_seconds(self) -> float:
        return self.start_ms / 1000.0

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class AudioProcessor:
    """
    Processes audio files for audiobook creation.
    Handles format conversion, merging, and normalization.
    """

    # Quality presets
    QUALITY_PRESETS = {
        'low': {'bitrate': '64k', 'sample_rate': 22050},
        'medium': {'bitrate': '96k', 'sample_rate': 44100},
        'high': {'bitrate': '128k', 'sample_rate': 44100},
        'very_high': {'bitrate': '192k', 'sample_rate': 48000}
    }

    def __init__(self, quality: str = 'medium'):
        self.quality = self.QUALITY_PRESETS.get(quality, self.QUALITY_PRESETS['medium'])
        self._ffmpeg_available = self._check_ffmpeg()

    def _check_ffmpeg(self) -> bool:
        """Check if ffmpeg is available."""
        return shutil.which('ffmpeg') is not None

    def convert_format(
        self,
        input_path: str,
        output_path: str,
        output_format: AudioFormat
    ) -> bool:
        """
        Convert audio file to specified format.

        Args:
            input_path: Input audio file path
            output_path: Output file path
            output_format: Target format

        Returns:
            True if successful
        """
        try:
            audio = AudioSegment.from_file(input_path)

            export_params = {
                'format': output_format.value,
                'bitrate': self.quality['bitrate'],
            }

            # Add codec for specific formats
            if output_format in (AudioFormat.M4B, AudioFormat.M4A):
                export_params['codec'] = 'aac'

            audio.export(output_path, **export_params)
            return os.path.exists(output_path)

        except Exception as e:
            print(f"Conversion error: {e}")
            return False

    def merge_chapters(
        self,
        chapter_files: list[str],
        output_path: str,
        gap_ms: int = 1000
    ) -> tuple[bool, list[ChapterMarker]]:
        """
        Merge multiple chapter audio files into one.

        Args:
            chapter_files: List of chapter audio file paths
            output_path: Output file path
            gap_ms: Gap between chapters in milliseconds

        Returns:
            Tuple of (success, list of chapter markers)
        """
        if not chapter_files:
            return False, []

        try:
            combined = AudioSegment.empty()
            chapter_markers = []
            current_position = 0

            for i, file_path in enumerate(chapter_files):
                if not os.path.exists(file_path):
                    print(f"Warning: Chapter file not found: {file_path}")
                    continue

                # Load chapter audio
                chapter_audio = AudioSegment.from_file(file_path)

                # Get chapter name from filename
                chapter_name = Path(file_path).stem
                # Clean up the name (remove number prefix if present)
                if chapter_name.startswith(('chapter_', 'ch_')):
                    parts = chapter_name.split('_', 2)
                    if len(parts) > 2:
                        chapter_name = parts[2]

                # Create chapter marker
                marker = ChapterMarker(
                    title=chapter_name,
                    start_ms=current_position,
                    end_ms=current_position + len(chapter_audio)
                )
                chapter_markers.append(marker)

                # Add to combined audio
                combined += chapter_audio

                # Add gap between chapters (except after last)
                if i < len(chapter_files) - 1:
                    combined += AudioSegment.silent(duration=gap_ms)
                    current_position += len(chapter_audio) + gap_ms
                else:
                    current_position += len(chapter_audio)

            # Determine output format from extension
            ext = Path(output_path).suffix.lower().lstrip('.')
            format_map = {
                'mp3': 'mp3',
                'm4b': 'ipod',  # pydub uses 'ipod' for m4a/m4b
                'm4a': 'ipod',
                'wav': 'wav',
                'ogg': 'ogg'
            }

            export_format = format_map.get(ext, 'mp3')
            export_params = {'format': export_format}

            if ext in ('m4b', 'm4a'):
                export_params['codec'] = 'aac'
                export_params['bitrate'] = self.quality['bitrate']
            elif ext == 'mp3':
                export_params['bitrate'] = self.quality['bitrate']

            combined.export(output_path, **export_params)

            return os.path.exists(output_path), chapter_markers

        except Exception as e:
            print(f"Merge error: {e}")
            return False, []

    def normalize_audio(self, input_path: str, output_path: str, target_dbfs: float = -20.0) -> bool:
        """
        Normalize audio volume.

        Args:
            input_path: Input file path
            output_path: Output file path
            target_dbfs: Target volume in dBFS

        Returns:
            True if successful
        """
        try:
            audio = AudioSegment.from_file(input_path)
            change_in_dbfs = target_dbfs - audio.dBFS
            normalized = audio.apply_gain(change_in_dbfs)

            # Preserve format
            ext = Path(input_path).suffix.lower().lstrip('.')
            normalized.export(output_path, format=ext)

            return True
        except Exception as e:
            print(f"Normalization error: {e}")
            return False

    def get_audio_duration(self, file_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            audio = AudioSegment.from_file(file_path)
            return len(audio) / 1000.0
        except Exception:
            return 0.0

    def get_audio_info(self, file_path: str) -> dict:
        """Get information about an audio file."""
        try:
            audio = AudioSegment.from_file(file_path)
            return {
                'duration_seconds': len(audio) / 1000.0,
                'channels': audio.channels,
                'sample_rate': audio.frame_rate,
                'sample_width': audio.sample_width,
                'file_size_bytes': os.path.getsize(file_path)
            }
        except Exception as e:
            return {'error': str(e)}

    def add_silence(self, input_path: str, output_path: str,
                    start_ms: int = 0, end_ms: int = 500) -> bool:
        """Add silence at start and/or end of audio."""
        try:
            audio = AudioSegment.from_file(input_path)

            if start_ms > 0:
                audio = AudioSegment.silent(duration=start_ms) + audio
            if end_ms > 0:
                audio = audio + AudioSegment.silent(duration=end_ms)

            ext = Path(input_path).suffix.lower().lstrip('.')
            audio.export(output_path, format=ext)

            return True
        except Exception as e:
            print(f"Error adding silence: {e}")
            return False
