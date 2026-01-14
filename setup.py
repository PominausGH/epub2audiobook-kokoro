#!/usr/bin/env python3
"""
Setup script for ePub2Audiobook
Allows installation via pip install -e .
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / 'README.md'
long_description = readme_path.read_text(encoding='utf-8') if readme_path.exists() else ''

setup(
    name='epub2audiobook',
    version='1.0.0',
    description='Convert DRM-free ePub files to audiobooks using traditional TTS',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/epub2audiobook',
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.10',
    install_requires=[
        'ebooklib>=0.18',
        'pyttsx3>=2.90',
        'pydub>=0.25.1',
        'mutagen>=1.47.0',
        'PyQt6>=6.6.0',
        'beautifulsoup4>=4.12.0',
        'lxml>=5.0.0',
        'html2text>=2024.2.26',
    ],
    extras_require={
        'dev': [
            'pyinstaller>=6.0.0',
            'pytest>=7.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'epub2audiobook=main:main',
        ],
        'gui_scripts': [
            'epub2audiobook-gui=main:run_gui',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Multimedia :: Sound/Audio :: Speech',
        'Topic :: Text Processing :: Markup',
    ],
    keywords='epub audiobook tts text-to-speech ebook converter',
    project_urls={
        'Bug Reports': 'https://github.com/yourusername/epub2audiobook/issues',
        'Source': 'https://github.com/yourusername/epub2audiobook',
    },
)
