# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ePub2Audiobook
Generates a standalone executable for Windows, macOS, and Linux.

Build commands:
    pyinstaller epub2audiobook.spec           # Build for current platform
    pyinstaller epub2audiobook.spec --onefile # Single executable (slower startup)
"""

import sys
from pathlib import Path

block_cipher = None

# Get the project root
PROJECT_ROOT = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        # Include any asset files
        # ('assets/*', 'assets'),
    ],
    hiddenimports=[
        # PyQt6 plugins
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        # pyttsx3 drivers
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'pyttsx3.drivers.nsss',
        'pyttsx3.drivers.espeak',
        # Audio processing
        'pydub',
        'mutagen',
        'mutagen.mp4',
        'mutagen.mp3',
        'mutagen.id3',
        # ePub parsing
        'ebooklib',
        'ebooklib.epub',
        # HTML parsing
        'bs4',
        'lxml',
        'lxml.etree',
        'html2text',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'unittest',
        'test',
        'tests',
        'numpy',
        'pandas',
        'matplotlib',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ePub2Audiobook',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here: 'assets/icon.ico' for Windows
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ePub2Audiobook',
)

# macOS app bundle (only on macOS)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='ePub2Audiobook.app',
        icon=None,  # Add icon: 'assets/icon.icns'
        bundle_identifier='com.epub2audiobook.app',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '10.15',
        },
    )
