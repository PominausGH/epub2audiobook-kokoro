"""
M4B Creator Module
Creates M4B audiobook files with chapter markers and metadata.
"""

import os
import subprocess
import shutil
import tempfile
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from mutagen.mp4 import MP4, MP4Cover

from .processor import ChapterMarker


@dataclass
class AudiobookMetadata:
    """Metadata for audiobook."""
    title: str = "Unknown Title"
    author: str = "Unknown Author"
    narrator: str = ""
    album: str = ""  # Often same as title for audiobooks
    year: str = ""
    genre: str = "Audiobook"
    description: str = ""
    cover_image: Optional[bytes] = None
    cover_mime_type: str = "image/jpeg"


class M4BCreator:
    """
    Creates M4B audiobook files with proper chapter markers and metadata.
    Uses ffmpeg for chapter embedding and mutagen for metadata.
    """

    def __init__(self):
        self._ffmpeg_path = shutil.which('ffmpeg')
        self._ffprobe_path = shutil.which('ffprobe')

    @property
    def ffmpeg_available(self) -> bool:
        """Check if ffmpeg is available."""
        return self._ffmpeg_path is not None

    def create_m4b(
        self,
        input_audio: str,
        output_path: str,
        chapters: list[ChapterMarker],
        metadata: AudiobookMetadata
    ) -> bool:
        """
        Create M4B file with chapters and metadata.

        Args:
            input_audio: Input audio file (any format ffmpeg supports)
            output_path: Output M4B file path
            chapters: List of chapter markers
            metadata: Audiobook metadata

        Returns:
            True if successful
        """
        if not self.ffmpeg_available:
            print("ffmpeg not available, creating simple M4A instead")
            return self._create_simple_m4a(input_audio, output_path, metadata)

        try:
            # Create chapter metadata file
            chapter_file = self._create_chapter_metadata(chapters)

            # Build ffmpeg command
            cmd = [
                self._ffmpeg_path,
                '-y',  # Overwrite output
                '-i', input_audio,
                '-i', chapter_file,
                '-map_metadata', '1',
                '-c', 'copy',  # Copy audio without re-encoding if possible
                '-f', 'ipod',  # M4B format
                output_path
            ]

            # Try to copy codec first, fall back to re-encoding
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                # Re-encode with AAC
                cmd = [
                    self._ffmpeg_path,
                    '-y',
                    '-i', input_audio,
                    '-i', chapter_file,
                    '-map_metadata', '1',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    '-f', 'ipod',
                    output_path
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up chapter file
            os.unlink(chapter_file)

            if result.returncode != 0:
                print(f"ffmpeg error: {result.stderr}")
                return False

            # Add metadata with mutagen
            self._apply_metadata(output_path, metadata)

            return os.path.exists(output_path)

        except Exception as e:
            print(f"M4B creation error: {e}")
            return False

    def _create_chapter_metadata(self, chapters: list[ChapterMarker]) -> str:
        """Create ffmpeg chapter metadata file."""
        lines = [";FFMETADATA1"]

        for chapter in chapters:
            lines.extend([
                "",
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={chapter.start_ms}",
                f"END={chapter.end_ms}",
                f"title={chapter.title}"
            ])

        # Write to temp file
        fd, path = tempfile.mkstemp(suffix='.txt')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return path

    def _apply_metadata(self, file_path: str, metadata: AudiobookMetadata) -> None:
        """Apply metadata to M4B file using mutagen."""
        try:
            audio = MP4(file_path)

            # Standard iTunes tags
            if metadata.title:
                audio['\xa9nam'] = metadata.title  # Title
            if metadata.author:
                audio['\xa9ART'] = metadata.author  # Artist
            if metadata.album or metadata.title:
                audio['\xa9alb'] = metadata.album or metadata.title  # Album
            if metadata.year:
                audio['\xa9day'] = metadata.year  # Year
            if metadata.genre:
                audio['\xa9gen'] = metadata.genre  # Genre
            if metadata.description:
                audio['desc'] = metadata.description  # Description
            if metadata.narrator:
                audio['----:com.apple.iTunes:NARRATOR'] = metadata.narrator.encode('utf-8')

            # Cover image
            if metadata.cover_image:
                # Determine cover format
                if metadata.cover_mime_type == 'image/png':
                    cover_format = MP4Cover.FORMAT_PNG
                else:
                    cover_format = MP4Cover.FORMAT_JPEG

                audio['covr'] = [MP4Cover(metadata.cover_image, imageformat=cover_format)]

            audio.save()

        except Exception as e:
            print(f"Metadata error: {e}")

    def _create_simple_m4a(
        self,
        input_audio: str,
        output_path: str,
        metadata: AudiobookMetadata
    ) -> bool:
        """Create simple M4A without chapters (fallback when ffmpeg unavailable)."""
        try:
            from pydub import AudioSegment

            # Load and convert
            audio = AudioSegment.from_file(input_audio)
            audio.export(output_path, format='ipod', codec='aac', bitrate='128k')

            # Add metadata
            self._apply_metadata(output_path, metadata)

            return os.path.exists(output_path)

        except Exception as e:
            print(f"Simple M4A creation error: {e}")
            return False

    def add_cover_image(self, audio_path: str, cover_image: bytes, mime_type: str = "image/jpeg") -> bool:
        """Add or replace cover image in M4B/M4A file."""
        try:
            audio = MP4(audio_path)

            if mime_type == 'image/png':
                cover_format = MP4Cover.FORMAT_PNG
            else:
                cover_format = MP4Cover.FORMAT_JPEG

            audio['covr'] = [MP4Cover(cover_image, imageformat=cover_format)]
            audio.save()

            return True
        except Exception as e:
            print(f"Cover image error: {e}")
            return False


class MP3Tagger:
    """Add metadata and chapter markers to MP3 files."""

    def __init__(self):
        pass

    def add_metadata(
        self,
        file_path: str,
        metadata: AudiobookMetadata
    ) -> bool:
        """Add metadata to MP3 file."""
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TYER, TCON, COMM, APIC

            audio = MP3(file_path, ID3=ID3)

            # Add ID3 tag if not present
            try:
                audio.add_tags()
            except Exception:
                pass  # Tags already exist

            if metadata.title:
                audio.tags.add(TIT2(encoding=3, text=metadata.title))
            if metadata.author:
                audio.tags.add(TPE1(encoding=3, text=metadata.author))
            if metadata.album or metadata.title:
                audio.tags.add(TALB(encoding=3, text=metadata.album or metadata.title))
            if metadata.year:
                audio.tags.add(TYER(encoding=3, text=metadata.year))
            if metadata.genre:
                audio.tags.add(TCON(encoding=3, text=metadata.genre))
            if metadata.description:
                audio.tags.add(COMM(encoding=3, lang='eng', desc='', text=metadata.description))

            # Cover image
            if metadata.cover_image:
                audio.tags.add(APIC(
                    encoding=3,
                    mime=metadata.cover_mime_type,
                    type=3,  # Cover (front)
                    desc='Cover',
                    data=metadata.cover_image
                ))

            audio.save()
            return True

        except Exception as e:
            print(f"MP3 metadata error: {e}")
            return False

    def add_chapter_markers_cue(
        self,
        audio_path: str,
        chapters: list[ChapterMarker],
        cue_output_path: str
    ) -> bool:
        """
        Create a CUE file for chapter markers.
        MP3 doesn't natively support chapters, but CUE files work with many players.
        """
        try:
            lines = [
                f'FILE "{Path(audio_path).name}" MP3'
            ]

            for i, chapter in enumerate(chapters, 1):
                # Convert ms to MM:SS:FF format (FF = frames, 75 per second)
                total_seconds = chapter.start_ms // 1000
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                frames = int((chapter.start_ms % 1000) / 1000 * 75)

                lines.extend([
                    f'  TRACK {i:02d} AUDIO',
                    f'    TITLE "{chapter.title}"',
                    f'    INDEX 01 {minutes:02d}:{seconds:02d}:{frames:02d}'
                ])

            with open(cue_output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            return True

        except Exception as e:
            print(f"CUE file error: {e}")
            return False
