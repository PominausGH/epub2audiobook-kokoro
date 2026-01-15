# ePub to Audiobook Converter

A free, private, offline tool that converts DRM-free ePub files into high-quality audiobooks using **traditional (non-neural) text-to-speech engines**.

## Features

- **100% Offline** - No internet required after installation
- **Privacy-First** - Your books never leave your computer
- **Cross-Platform** - Works on Windows, macOS, and Linux
- **Traditional TTS** - Uses reliable, non-AI speech synthesis:
  - Windows: Microsoft SAPI5 voices
  - macOS: NSSpeechSynthesizer
  - Linux: espeak-ng
- **Chapter Support** - M4B files with proper chapter markers
- **Metadata Embedding** - Title, author, and cover image preserved
- **Simple GUI** - Easy-to-use interface, no technical knowledge required
- **Command-Line Mode** - For automation and scripting

## Screenshots

```
┌──────────────────────────────────────────────────────────┐
│         ePub to Audiobook Converter                      │
│              Using: SAPI5 (Windows)                      │
├──────────────────────────────────────────────────────────┤
│ ePub File                          │ Chapters Preview    │
│ [C:\Books\MyBook.epub] [Browse...] │ 1. Introduction     │
│                                    │ 2. Chapter One      │
│ Book Information                   │ 3. Chapter Two      │
│ Title:  My Great Book              │ ...                 │
│ Author: John Smith                 │                     │
│ Chapters: 15                       │                     │
│ Est. Duration: ~4h 30m             │                     │
│                                    │                     │
│ Voice Settings                     │                     │
│ Voice: [Microsoft David ▼] [Test]  │                     │
│ Speed: ████████░░ 150 WPM          │                     │
│ Volume: ██████████ 100%            │                     │
│                                    ├────────────────────┤
│ Output Settings                    │ Progress            │
│ Format: [M4B with chapters ▼]      │ ████████░░ 80%     │
│ Quality: [Medium (96 kbps) ▼]      │ Converting Ch.12... │
│ ☑ Announce chapter titles          │                     │
│ ☑ Normalize audio volume           │                     │
├──────────────────────────────────────────────────────────┤
│        [Convert to Audiobook]        [Cancel]            │
└──────────────────────────────────────────────────────────┘
```

## Installation

### Option 1: Docker (Recommended for Servers)

The easiest way to run as a web service:

```bash
# Clone and start
git clone https://github.com/yourusername/epub2audiobook.git
cd epub2audiobook

# Build and run
docker-compose up -d

# Open in browser
# http://localhost:5000
```

Or with make:
```bash
make build
make run
```

Docker provides:
- Web interface accessible from any device
- No local dependencies needed
- Works on any server, NAS, or VPS
- Uses espeak-ng + ffmpeg (pre-installed)

### Option 2: Download Pre-built Release

Download the latest release for your platform from the Releases page.

### Option 3: Run from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/epub2audiobook.git
   cd epub2audiobook
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install platform-specific TTS (Linux only):**
   ```bash
   # Debian/Ubuntu
   sudo apt install espeak-ng

   # Fedora
   sudo dnf install espeak-ng

   # Arch
   sudo pacman -S espeak-ng
   ```

5. **Install ffmpeg (optional, for M4B with chapters):**
   ```bash
   # Debian/Ubuntu
   sudo apt install ffmpeg

   # macOS
   brew install ffmpeg

   # Windows - download from https://ffmpeg.org/download.html
   ```

6. **Run the application:**
   ```bash
   python main.py
   ```

## Usage

### GUI Mode

Simply run the application without arguments:
```bash
python main.py
```

1. Click **Browse** to select an ePub file
2. Review the book information and chapters
3. Select a voice and adjust speed/volume
4. Choose output format (M4B recommended)
5. Click **Convert to Audiobook**
6. Wait for conversion to complete

### Command-Line Mode

```bash
# Basic conversion
python main.py book.epub output.m4b

# Specify voice and speed
python main.py book.epub output.m4b --voice "David" --speed 160

# List available voices
python main.py --list-voices

# Help
python main.py --help
```

### Output Formats

| Format | Description | Chapters | Best For |
|--------|-------------|----------|----------|
| **M4B** | Single file with embedded chapters | ✅ Native | Audiobook apps, iTunes |
| **MP3** | Single file + CUE sheet | ✅ Via CUE | General compatibility |
| **MP3 Chapters** | Separate file per chapter | ✅ Folders | Manual organization |

## Building Standalone Executables

To create a distributable executable:

```bash
# Install PyInstaller
pip install pyinstaller

# Build (folder mode - faster startup)
python build.py

# Build (single file mode - more portable)
python build.py --onefile

# Create distribution package
python build.py --dist
```

The built executable will be in the `dist/` folder.

## Project Structure

```
epub2audiobook/
├── main.py              # Desktop app entry point
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Docker deployment config
├── Makefile             # Convenience commands
├── core/
│   ├── epub_parser.py   # ePub parsing and text extraction
│   └── text_cleaner.py  # Text normalization for TTS
├── tts/
│   ├── base.py          # Abstract TTS engine base class
│   ├── pyttsx3_engine.py # System TTS (SAPI5/espeak/NSS)
│   ├── kokoro_engine.py # Kokoro neural TTS (optional)
│   └── factory.py       # Engine factory and combined engine
├── audio/
│   ├── processor.py     # Audio manipulation (pydub)
│   └── m4b_creator.py   # M4B creation with chapters
├── gui/                 # Desktop GUI (PyQt6)
│   ├── main_window.py
│   └── converter_worker.py
└── web/                 # Web interface (Flask)
    ├── app.py           # Flask application
    └── templates/
        └── index.html   # Web frontend
```

## Supported TTS Engines

| Platform | Engine | Voices |
|----------|--------|--------|
| Windows | Microsoft SAPI5 | David, Zira, + installed voices |
| macOS | NSSpeechSynthesizer | Alex, Samantha, + system voices |
| Linux | espeak-ng | Various languages/accents |
| All Platforms | Kokoro-82M (Neural) | Heart, Bella, Adam, + 20 more (optional) |

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

**CLI usage:**
```bash
# Use Kokoro voices specifically
python main.py book.epub output.m4b --engine kokoro --voice "Heart"

# List Kokoro voices
python main.py --list-voices --engine kokoro
```

Note: Kokoro requires more CPU/memory than traditional TTS and may be slower on older hardware.

### Adding More Voices

**Windows:**
- Install additional SAPI5 voices from Microsoft or third parties
- Some language packs include additional voices

**macOS:**
- System Preferences → Accessibility → Spoken Content → System Voice → Manage Voices

**Linux:**
- Install espeak-ng language data: `sudo apt install espeak-ng-data`

## Troubleshooting

### No voices found
- **Windows:** Ensure at least one SAPI5 voice is installed
- **Linux:** Install espeak-ng: `sudo apt install espeak-ng`
- **macOS:** System voices should be available by default

### M4B chapters not working
- Ensure ffmpeg is installed and in your PATH
- The app will fall back to M4A without chapters if ffmpeg is unavailable

### Audio quality issues
- Try a different voice
- Adjust the speed slider (150 WPM is typical for audiobooks)
- Enable "Normalize audio volume" for consistent levels

### Conversion is slow
- TTS synthesis is CPU-bound
- Longer books naturally take more time
- The estimated duration shown reflects actual reading time

## Technical Details

### Dependencies

- **ebooklib** - ePub parsing
- **pyttsx3** - Cross-platform TTS wrapper
- **pydub** - Audio processing
- **mutagen** - Audio metadata (ID3, MP4 tags)
- **PyQt6** - GUI framework
- **BeautifulSoup4** - HTML parsing
- **ffmpeg** (optional) - M4B chapter encoding

### Text Processing

The text cleaner handles:
- Abbreviation expansion (Mr. → Mister, etc.)
- Number to word conversion (123 → one hundred twenty three)
- Year pronunciation (1984 → nineteen eighty four)
- Currency formatting ($50 → fifty dollars)
- URL and email removal
- Footnote marker cleanup
- Smart quote normalization
- Punctuation handling for natural pauses

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

This project is open source and available for personal use. See LICENSE file for details.

## Acknowledgments

- **pyttsx3** for the excellent cross-platform TTS wrapper
- **ebooklib** for robust ePub parsing
- **pydub** for simple audio manipulation
- **PyQt6** for the modern GUI framework
