"""
Converter Worker Module
Background worker for audio conversion to keep GUI responsive.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal

from core import EPubParser, TextCleaner, CleanerOptions
from tts import TTSEngine, TTSConfig
from audio import AudioProcessor, AudioFormat, M4BCreator, AudiobookMetadata, ChapterMarker


@dataclass
class ConversionSettings:
    """Settings for the conversion process."""
    epub_path: str
    output_path: str
    voice_id: str
    rate: int = 150
    volume: float = 1.0
    output_format: str = "m4b"  # m4b, mp3, or chapters (separate files)
    audio_quality: str = "medium"
    gap_between_chapters_ms: int = 1500
    normalize_audio: bool = True
    announce_chapters: bool = True


class ConverterWorker(QThread):
    """
    Background worker thread for converting ePub to audiobook.
    Emits progress signals to update the GUI.
    """

    # Signals
    progress = pyqtSignal(int, int, str)  # current, total, message
    chapter_complete = pyqtSignal(int, str)  # chapter_num, chapter_title
    finished = pyqtSignal(bool, str)  # success, message/path
    error = pyqtSignal(str)  # error message

    def __init__(self, settings: ConversionSettings):
        super().__init__()
        self.settings = settings
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of the conversion."""
        self._is_cancelled = True

    def run(self):
        """Run the conversion process."""
        temp_dir = None
        try:
            # Create temp directory for intermediate files
            temp_dir = tempfile.mkdtemp(prefix='epub2audio_')

            # Initialize components
            self.progress.emit(0, 100, "Initializing...")

            parser = EPubParser(self.settings.epub_path)
            cleaner = TextCleaner(CleanerOptions(
                add_chapter_announcement=self.settings.announce_chapters
            ))
            tts = TTSEngine()

            if not tts.initialize():
                self.error.emit("Failed to initialize TTS engine")
                return

            # Configure TTS
            tts.configure(TTSConfig(
                voice_id=self.settings.voice_id,
                rate=self.settings.rate,
                volume=self.settings.volume
            ))

            # Parse ePub
            self.progress.emit(5, 100, "Parsing ePub file...")
            parser.parse()

            if not parser.chapters:
                self.error.emit("No chapters found in ePub file")
                return

            metadata = parser.metadata
            total_chapters = len(parser.chapters)

            # Generate chapter audio files
            chapter_files = []
            chapter_markers = []

            for i, chapter in enumerate(parser.chapters):
                if self._is_cancelled:
                    self.error.emit("Conversion cancelled")
                    return

                progress_pct = 10 + int((i / total_chapters) * 70)
                self.progress.emit(
                    progress_pct, 100,
                    f"Converting chapter {i + 1}/{total_chapters}: {chapter.title}"
                )

                # Clean text
                cleaned_text = cleaner.clean(
                    chapter.content,
                    chapter_title=chapter.title if self.settings.announce_chapters else None
                )

                if not cleaned_text.strip():
                    continue

                # Generate audio file
                chapter_filename = f"chapter_{i + 1:03d}_{self._sanitize_filename(chapter.title)}.wav"
                chapter_path = os.path.join(temp_dir, chapter_filename)

                success = tts.synthesize_chapter(cleaned_text, chapter_path)

                if success and os.path.exists(chapter_path):
                    chapter_files.append(chapter_path)
                    self.chapter_complete.emit(i + 1, chapter.title)

            if not chapter_files:
                self.error.emit("No audio files were generated")
                return

            # Process based on output format
            if self.settings.output_format == "chapters":
                # Save individual chapter files
                output_dir = Path(self.settings.output_path)
                output_dir.mkdir(parents=True, exist_ok=True)

                processor = AudioProcessor(quality=self.settings.audio_quality)

                for i, chapter_file in enumerate(chapter_files):
                    self.progress.emit(
                        80 + int((i / len(chapter_files)) * 15), 100,
                        f"Exporting chapter {i + 1}..."
                    )

                    output_file = output_dir / f"chapter_{i + 1:03d}.mp3"
                    processor.convert_format(
                        chapter_file,
                        str(output_file),
                        AudioFormat.MP3
                    )

                self.progress.emit(100, 100, "Complete!")
                self.finished.emit(True, str(output_dir))

            else:
                # Merge into single file
                self.progress.emit(85, 100, "Merging chapters...")

                processor = AudioProcessor(quality=self.settings.audio_quality)
                merged_path = os.path.join(temp_dir, "merged.wav")

                success, markers = processor.merge_chapters(
                    chapter_files,
                    merged_path,
                    gap_ms=self.settings.gap_between_chapters_ms
                )

                if not success:
                    self.error.emit("Failed to merge chapter audio files")
                    return

                # Update chapter markers with titles
                for i, marker in enumerate(markers):
                    if i < len(parser.chapters):
                        marker.title = parser.chapters[i].title

                if self.settings.normalize_audio:
                    self.progress.emit(90, 100, "Normalizing audio...")
                    normalized_path = os.path.join(temp_dir, "normalized.wav")
                    processor.normalize_audio(merged_path, normalized_path)
                    merged_path = normalized_path

                # Create final output
                self.progress.emit(95, 100, "Creating audiobook file...")

                if self.settings.output_format == "m4b":
                    creator = M4BCreator()
                    audiobook_meta = AudiobookMetadata(
                        title=metadata.title,
                        author=metadata.author,
                        cover_image=metadata.cover_image,
                        cover_mime_type=metadata.cover_mime_type
                    )

                    success = creator.create_m4b(
                        merged_path,
                        self.settings.output_path,
                        markers,
                        audiobook_meta
                    )
                else:
                    # MP3 output
                    from audio.m4b_creator import MP3Tagger

                    processor.convert_format(
                        merged_path,
                        self.settings.output_path,
                        AudioProcessor.AudioFormat.MP3
                    )

                    tagger = MP3Tagger()
                    audiobook_meta = AudiobookMetadata(
                        title=metadata.title,
                        author=metadata.author,
                        cover_image=metadata.cover_image,
                        cover_mime_type=metadata.cover_mime_type
                    )
                    tagger.add_metadata(self.settings.output_path, audiobook_meta)

                    # Create CUE file for chapters
                    cue_path = self.settings.output_path.replace('.mp3', '.cue')
                    tagger.add_chapter_markers_cue(
                        self.settings.output_path,
                        markers,
                        cue_path
                    )

                    success = True

                if success:
                    self.progress.emit(100, 100, "Complete!")
                    self.finished.emit(True, self.settings.output_path)
                else:
                    self.error.emit("Failed to create final audiobook file")

        except Exception as e:
            self.error.emit(f"Conversion error: {str(e)}")

        finally:
            # Clean up temp files
            if temp_dir and os.path.exists(temp_dir):
                import shutil
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

            # Clean up TTS engine
            if 'tts' in locals():
                tts.cleanup()

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use in filename."""
        # Remove or replace problematic characters
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            name = name.replace(char, '_')
        # Limit length
        return name[:50].strip()
