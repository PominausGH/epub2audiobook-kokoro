#!/usr/bin/env python3
"""
ePub to Audiobook Converter
Main application entry point.

Converts DRM-free ePub files to audiobooks using traditional TTS engines:
- Windows: SAPI5
- macOS: NSSpeechSynthesizer
- Linux: espeak-ng

Usage:
    python main.py              # Launch GUI
    python main.py --cli file.epub output.m4b  # Command-line mode
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_gui():
    """Run the graphical user interface."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from gui import MainWindow

    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ePub2Audiobook")
    app.setOrganizationName("ePub2Audiobook")
    app.setApplicationVersion("1.0.0")

    # Apply a clean style
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def run_cli(args):
    """Run in command-line mode."""
    from core import EPubParser, TextCleaner, CleanerOptions
    from tts import TTSEngine, TTSConfig
    from audio import AudioProcessor, M4BCreator, AudiobookMetadata

    print(f"ePub to Audiobook Converter (CLI Mode)")
    print(f"=" * 40)

    # Parse ePub
    print(f"\nLoading: {args.input}")
    parser = EPubParser(args.input)
    parser.parse()

    print(f"  Title: {parser.metadata.title}")
    print(f"  Author: {parser.metadata.author}")
    print(f"  Chapters: {len(parser.chapters)}")

    # Initialize TTS
    print(f"\nInitializing TTS engine...")
    tts = TTSEngine()
    if not tts.initialize():
        print("ERROR: Failed to initialize TTS engine")
        sys.exit(1)

    print(f"  Engine: {tts.get_engine_name()}")
    voices = tts.get_voices()
    print(f"  Available voices: {len(voices)}")

    # Select voice
    voice_id = None
    if args.voice:
        for v in voices:
            if args.voice.lower() in v.name.lower():
                voice_id = v.id
                print(f"  Selected voice: {v.name}")
                break
        if not voice_id:
            print(f"  Warning: Voice '{args.voice}' not found, using default")

    if not voice_id and voices:
        voice_id = voices[0].id
        print(f"  Using default voice: {voices[0].name}")

    # Configure TTS
    tts.configure(TTSConfig(
        voice_id=voice_id,
        rate=args.speed,
        volume=args.volume / 100.0
    ))

    # Text cleaner
    cleaner = TextCleaner(CleanerOptions(add_chapter_announcement=True))

    # Process chapters
    import tempfile
    temp_dir = tempfile.mkdtemp(prefix='epub2audio_')
    chapter_files = []

    print(f"\nConverting chapters...")
    for i, chapter in enumerate(parser.chapters):
        print(f"  [{i+1}/{len(parser.chapters)}] {chapter.title}...", end=' ', flush=True)

        cleaned_text = cleaner.clean(chapter.content, chapter.title)
        if not cleaned_text.strip():
            print("(empty, skipped)")
            continue

        chapter_path = os.path.join(temp_dir, f"ch_{i+1:03d}.wav")
        if tts.synthesize_chapter(cleaned_text, chapter_path):
            chapter_files.append(chapter_path)
            print("done")
        else:
            print("failed")

    if not chapter_files:
        print("ERROR: No chapters were converted")
        sys.exit(1)

    # Merge and create output
    print(f"\nMerging {len(chapter_files)} chapters...")
    processor = AudioProcessor(quality='medium')

    merged_path = os.path.join(temp_dir, "merged.wav")
    success, markers = processor.merge_chapters(chapter_files, merged_path)

    if not success:
        print("ERROR: Failed to merge chapters")
        sys.exit(1)

    # Update markers with titles
    for i, marker in enumerate(markers):
        if i < len(parser.chapters):
            marker.title = parser.chapters[i].title

    # Create final output
    output_ext = Path(args.output).suffix.lower()

    print(f"Creating output file: {args.output}")

    if output_ext == '.m4b':
        creator = M4BCreator()
        meta = AudiobookMetadata(
            title=parser.metadata.title,
            author=parser.metadata.author,
            cover_image=parser.metadata.cover_image,
            cover_mime_type=parser.metadata.cover_mime_type
        )
        success = creator.create_m4b(merged_path, args.output, markers, meta)
    else:
        from audio import AudioFormat
        from audio.m4b_creator import MP3Tagger

        processor.convert_format(merged_path, args.output, AudioFormat.MP3)

        tagger = MP3Tagger()
        meta = AudiobookMetadata(
            title=parser.metadata.title,
            author=parser.metadata.author,
            cover_image=parser.metadata.cover_image,
            cover_mime_type=parser.metadata.cover_mime_type
        )
        tagger.add_metadata(args.output, meta)
        success = True

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    tts.cleanup()

    if success:
        print(f"\nSuccess! Audiobook saved to: {args.output}")
    else:
        print(f"\nERROR: Failed to create output file")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Convert ePub files to audiobooks using traditional TTS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           Launch GUI
  %(prog)s book.epub output.m4b      Convert to M4B
  %(prog)s book.epub output.mp3      Convert to MP3
  %(prog)s book.epub out.m4b -v "David" -s 160

Supported TTS Engines:
  Windows: Microsoft SAPI5 voices
  macOS:   NSSpeechSynthesizer voices
  Linux:   espeak-ng

Note: For M4B with chapters, ffmpeg must be installed.
        """
    )

    parser.add_argument('input', nargs='?', help='Input ePub file')
    parser.add_argument('output', nargs='?', help='Output audiobook file (m4b or mp3)')
    parser.add_argument('-v', '--voice', help='Voice name (partial match)')
    parser.add_argument('-s', '--speed', type=int, default=150,
                        help='Speech rate in words per minute (default: 150)')
    parser.add_argument('--volume', type=int, default=100,
                        help='Volume 0-100 (default: 100)')
    parser.add_argument('--list-voices', action='store_true',
                        help='List available voices and exit')
    parser.add_argument('--gui', action='store_true',
                        help='Force GUI mode even with arguments')

    args = parser.parse_args()

    # List voices mode
    if args.list_voices:
        from tts import TTSEngine
        tts = TTSEngine()
        if tts.initialize():
            print(f"TTS Engine: {tts.get_engine_name()}")
            print(f"\nAvailable voices:")
            for v in tts.get_voices():
                print(f"  - {v.name} ({v.gender})")
            tts.cleanup()
        else:
            print("ERROR: Failed to initialize TTS engine")
        sys.exit(0)

    # GUI mode
    if args.gui or (not args.input and not args.output):
        run_gui()
    else:
        # CLI mode - validate args
        if not args.input or not args.output:
            parser.error("Both input and output files are required for CLI mode")
        if not os.path.exists(args.input):
            parser.error(f"Input file not found: {args.input}")
        run_cli(args)


if __name__ == '__main__':
    main()
