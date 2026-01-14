#!/usr/bin/env python3
"""
Build script for ePub2Audiobook
Creates standalone executables for distribution.
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


def check_requirements():
    """Check that all build requirements are installed."""
    print("Checking requirements...")

    required = ['PyInstaller', 'PyQt6', 'pyttsx3', 'ebooklib', 'pydub', 'mutagen']
    missing = []

    for package in required:
        try:
            __import__(package.lower().replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print(f"Missing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False

    print("All requirements satisfied.")
    return True


def clean_build():
    """Clean previous build artifacts."""
    print("Cleaning previous builds...")

    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        path = PROJECT_ROOT / dir_name
        if path.exists():
            shutil.rmtree(path)
            print(f"  Removed {dir_name}/")

    # Clean .pyc files
    for pyc in PROJECT_ROOT.rglob('*.pyc'):
        pyc.unlink()

    for pycache in PROJECT_ROOT.rglob('__pycache__'):
        shutil.rmtree(pycache)


def build_executable(onefile=False):
    """Build the executable using PyInstaller."""
    print(f"\nBuilding executable ({'single file' if onefile else 'folder'} mode)...")

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        str(PROJECT_ROOT / 'epub2audiobook.spec')
    ]

    if onefile:
        cmd.append('--onefile')

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print("Build failed!")
        return False

    print("\nBuild completed successfully!")
    return True


def create_distribution():
    """Create a distribution package."""
    print("\nCreating distribution package...")

    dist_dir = PROJECT_ROOT / 'dist' / 'ePub2Audiobook'
    if not dist_dir.exists():
        print("Build artifacts not found. Run build first.")
        return False

    # Create README for distribution
    readme_content = """
ePub to Audiobook Converter
===========================

A free, offline tool to convert DRM-free ePub files to audiobooks.

GETTING STARTED
---------------
1. Run ePub2Audiobook (or ePub2Audiobook.exe on Windows)
2. Click "Browse" to select an ePub file
3. Choose your preferred voice and settings
4. Click "Convert to Audiobook"

REQUIREMENTS
------------
- Windows: No additional requirements (uses built-in SAPI5 voices)
- macOS: No additional requirements (uses built-in system voices)
- Linux: Install espeak-ng: sudo apt install espeak-ng

For M4B files with chapter markers, you also need ffmpeg installed.

COMMAND LINE USAGE
------------------
ePub2Audiobook book.epub output.m4b
ePub2Audiobook book.epub output.mp3 --voice "David" --speed 160
ePub2Audiobook --list-voices

LICENSE
-------
This software is provided free for personal use.

SUPPORT
-------
For issues, please report at: [your-repo-url]
"""

    readme_path = dist_dir / 'README.txt'
    readme_path.write_text(readme_content)
    print(f"  Created {readme_path}")

    # Create archive
    system = platform.system().lower()
    arch = platform.machine().lower()
    archive_name = f"epub2audiobook-{system}-{arch}"

    if system == 'windows':
        archive_path = PROJECT_ROOT / 'dist' / f'{archive_name}.zip'
        shutil.make_archive(str(archive_path.with_suffix('')), 'zip', dist_dir.parent, 'ePub2Audiobook')
    else:
        archive_path = PROJECT_ROOT / 'dist' / f'{archive_name}.tar.gz'
        shutil.make_archive(str(archive_path.with_suffix('').with_suffix('')), 'gztar', dist_dir.parent, 'ePub2Audiobook')

    print(f"  Created {archive_path}")
    print(f"\nDistribution package ready: {archive_path}")
    return True


def main():
    """Main build entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Build ePub2Audiobook')
    parser.add_argument('--clean', action='store_true', help='Clean build artifacts only')
    parser.add_argument('--onefile', action='store_true', help='Create single executable')
    parser.add_argument('--dist', action='store_true', help='Create distribution package')
    args = parser.parse_args()

    os.chdir(PROJECT_ROOT)

    if args.clean:
        clean_build()
        return

    if not check_requirements():
        sys.exit(1)

    clean_build()

    if not build_executable(onefile=args.onefile):
        sys.exit(1)

    if args.dist:
        create_distribution()

    print("\nDone!")


if __name__ == '__main__':
    main()
