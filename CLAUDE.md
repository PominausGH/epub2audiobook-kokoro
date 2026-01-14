# epub2audiobook

Convert EPUB books to audiobooks using TTS.

## Tech Stack
- Language: Python
- TTS: Text-to-speech engines
- GUI: Desktop interface available
- Web: Web interface available

## Commands
- `pip install -r requirements.txt` - Install dependencies
- `python main.py` - Run CLI
- `python -m gui` - Run GUI
- `python -m web` - Run web interface
- `docker-compose up` - Run in Docker
- `make` - Build targets (see Makefile)

## Structure
- `main.py` - CLI entry point
- `core/` - Core conversion logic
- `tts/` - TTS engine integrations
- `gui/` - Desktop GUI
- `web/` - Web interface
- `audio/` - Audio output
- `assets/` - Static assets

## Building
- `python build.py` - Build application
- See `epub2audiobook.spec` for PyInstaller config

## Superpowers
Use these skills when working on this project:
- `/brainstorming` - Before adding new TTS engines or features
- `/writing-plans` - For multi-step implementations
- `/test-driven-development` - Write tests for conversion logic
- `/systematic-debugging` - When fixing TTS/audio issues
- `/requesting-code-review` - After completing features
- `/verification-before-completion` - Test conversion output before done
- `/finishing-a-development-branch` - When ready to merge
