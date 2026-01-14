"""
Main Window Module
PyQt6-based GUI for ePub to Audiobook converter.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSlider, QSpinBox, QProgressBar,
    QFileDialog, QGroupBox, QTextEdit, QMessageBox, QStatusBar,
    QApplication, QFrame, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QFont, QPixmap, QIcon

from core import EPubParser
from tts import TTSEngine, TTSConfig
from .converter_worker import ConverterWorker, ConversionSettings


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ePub to Audiobook Converter")
        self.setMinimumSize(800, 600)

        # State
        self.current_epub: Optional[EPubParser] = None
        self.tts_engine = TTSEngine()
        self.worker: Optional[ConverterWorker] = None
        self.settings = QSettings('ePub2Audiobook', 'Converter')

        # Initialize TTS
        if not self.tts_engine.initialize():
            QMessageBox.critical(
                self, "Error",
                "Failed to initialize Text-to-Speech engine.\n"
                "Please ensure you have TTS support installed on your system."
            )

        self._setup_ui()
        self._load_settings()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Title
        title_label = QLabel("ePub to Audiobook Converter")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtitle showing TTS engine
        engine_label = QLabel(f"Using: {self.tts_engine.get_engine_name()}")
        engine_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        engine_label.setStyleSheet("color: gray; font-style: italic;")
        main_layout.addWidget(engine_label)

        # Splitter for two-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Left panel - File and Settings
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 5, 0)

        # File Selection Group
        file_group = QGroupBox("ePub File")
        file_layout = QGridLayout(file_group)

        self.epub_path_label = QLabel("No file selected")
        self.epub_path_label.setWordWrap(True)
        self.epub_path_label.setStyleSheet("padding: 5px; background: #f0f0f0; border-radius: 3px;")
        file_layout.addWidget(self.epub_path_label, 0, 0)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setMinimumWidth(100)
        file_layout.addWidget(self.browse_btn, 0, 1)

        left_layout.addWidget(file_group)

        # Book Info Group
        info_group = QGroupBox("Book Information")
        info_layout = QGridLayout(info_group)

        info_layout.addWidget(QLabel("Title:"), 0, 0)
        self.title_label = QLabel("-")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label, 0, 1)

        info_layout.addWidget(QLabel("Author:"), 1, 0)
        self.author_label = QLabel("-")
        info_layout.addWidget(self.author_label, 1, 1)

        info_layout.addWidget(QLabel("Chapters:"), 2, 0)
        self.chapters_label = QLabel("-")
        info_layout.addWidget(self.chapters_label, 2, 1)

        info_layout.addWidget(QLabel("Est. Duration:"), 3, 0)
        self.duration_label = QLabel("-")
        info_layout.addWidget(self.duration_label, 3, 1)

        info_layout.setColumnStretch(1, 1)
        left_layout.addWidget(info_group)

        # Voice Settings Group
        voice_group = QGroupBox("Voice Settings")
        voice_layout = QGridLayout(voice_group)

        voice_layout.addWidget(QLabel("Voice:"), 0, 0)
        self.voice_combo = QComboBox()
        self.voice_combo.setMinimumWidth(200)
        self._populate_voices()
        voice_layout.addWidget(self.voice_combo, 0, 1)

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setMaximumWidth(80)
        voice_layout.addWidget(self.preview_btn, 0, 2)

        voice_layout.addWidget(QLabel("Speed:"), 1, 0)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(80, 250)
        self.speed_slider.setValue(150)
        voice_layout.addWidget(self.speed_slider, 1, 1)

        self.speed_label = QLabel("150 WPM")
        self.speed_label.setMinimumWidth(70)
        voice_layout.addWidget(self.speed_label, 1, 2)

        voice_layout.addWidget(QLabel("Volume:"), 2, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        voice_layout.addWidget(self.volume_slider, 2, 1)

        self.volume_label = QLabel("100%")
        self.volume_label.setMinimumWidth(70)
        voice_layout.addWidget(self.volume_label, 2, 2)

        left_layout.addWidget(voice_group)

        # Output Settings Group
        output_group = QGroupBox("Output Settings")
        output_layout = QGridLayout(output_group)

        output_layout.addWidget(QLabel("Format:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "M4B (Single file with chapters)",
            "MP3 (Single file with CUE)",
            "MP3 Chapters (Separate files)"
        ])
        output_layout.addWidget(self.format_combo, 0, 1)

        output_layout.addWidget(QLabel("Quality:"), 1, 0)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low (64 kbps)", "Medium (96 kbps)", "High (128 kbps)", "Very High (192 kbps)"])
        self.quality_combo.setCurrentIndex(1)
        output_layout.addWidget(self.quality_combo, 1, 1)

        self.announce_chapters_cb = QCheckBox("Announce chapter titles")
        self.announce_chapters_cb.setChecked(True)
        output_layout.addWidget(self.announce_chapters_cb, 2, 0, 1, 2)

        self.normalize_cb = QCheckBox("Normalize audio volume")
        self.normalize_cb.setChecked(True)
        output_layout.addWidget(self.normalize_cb, 3, 0, 1, 2)

        left_layout.addWidget(output_group)
        left_layout.addStretch()

        splitter.addWidget(left_panel)

        # Right panel - Chapters and Progress
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 0, 0, 0)

        # Chapters Preview
        chapters_group = QGroupBox("Chapters Preview")
        chapters_layout = QVBoxLayout(chapters_group)

        self.chapters_text = QTextEdit()
        self.chapters_text.setReadOnly(True)
        self.chapters_text.setPlaceholderText("Load an ePub file to see chapters...")
        chapters_layout.addWidget(self.chapters_text)

        right_layout.addWidget(chapters_group, 1)

        # Progress Group
        progress_group = QGroupBox("Conversion Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)

        right_layout.addWidget(progress_group)

        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.convert_btn = QPushButton("Convert to Audiobook")
        self.convert_btn.setMinimumSize(180, 40)
        self.convert_btn.setEnabled(False)
        convert_font = QFont()
        convert_font.setBold(True)
        self.convert_btn.setFont(convert_font)
        button_layout.addWidget(self.convert_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumSize(100, 40)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        # Status bar
        self.statusBar().showMessage("Ready - Select an ePub file to begin")

    def _populate_voices(self):
        """Populate voice combo box."""
        self.voice_combo.clear()
        voices = self.tts_engine.get_voices()

        for voice in voices:
            self.voice_combo.addItem(str(voice), voice.id)

        # Try to select a good default voice
        for i in range(self.voice_combo.count()):
            voice_name = self.voice_combo.itemText(i).lower()
            if 'david' in voice_name or 'zira' in voice_name or 'english' in voice_name:
                self.voice_combo.setCurrentIndex(i)
                break

    def _connect_signals(self):
        """Connect UI signals to slots."""
        self.browse_btn.clicked.connect(self._browse_epub)
        self.preview_btn.clicked.connect(self._preview_voice)
        self.convert_btn.clicked.connect(self._start_conversion)
        self.cancel_btn.clicked.connect(self._cancel_conversion)

        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v} WPM")
        )
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_label.setText(f"{v}%")
        )

    def _browse_epub(self):
        """Open file dialog to select ePub."""
        last_dir = self.settings.value('last_directory', '')

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ePub File",
            last_dir,
            "ePub Files (*.epub);;All Files (*)"
        )

        if file_path:
            self.settings.setValue('last_directory', str(Path(file_path).parent))
            self._load_epub(file_path)

    def _load_epub(self, file_path: str):
        """Load and parse an ePub file."""
        try:
            self.statusBar().showMessage("Loading ePub...")
            QApplication.processEvents()

            self.current_epub = EPubParser(file_path)
            self.current_epub.parse()

            # Update UI
            self.epub_path_label.setText(file_path)
            self.title_label.setText(self.current_epub.metadata.title)
            self.author_label.setText(self.current_epub.metadata.author)
            self.chapters_label.setText(str(len(self.current_epub.chapters)))

            # Estimate duration
            duration_sec = self.current_epub.get_estimated_duration()
            hours = duration_sec // 3600
            minutes = (duration_sec % 3600) // 60
            self.duration_label.setText(f"~{hours}h {minutes}m")

            # Populate chapters preview
            chapters_text = []
            for ch in self.current_epub.chapters:
                word_info = f"({ch.word_count:,} words)"
                chapters_text.append(f"{ch.number}. {ch.title} {word_info}")
            self.chapters_text.setPlainText('\n'.join(chapters_text))

            self.convert_btn.setEnabled(True)
            self.statusBar().showMessage(f"Loaded: {self.current_epub.metadata.title}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load ePub:\n{str(e)}")
            self.statusBar().showMessage("Error loading file")

    def _preview_voice(self):
        """Preview the selected voice."""
        voice_id = self.voice_combo.currentData()
        if not voice_id:
            return

        self.tts_engine.configure(TTSConfig(
            voice_id=voice_id,
            rate=self.speed_slider.value(),
            volume=self.volume_slider.value() / 100.0
        ))

        preview_text = "This is a preview of the selected voice. "
        if self.current_epub:
            preview_text += f"The book '{self.current_epub.metadata.title}' "
            preview_text += f"by {self.current_epub.metadata.author} "
            preview_text += f"has {len(self.current_epub.chapters)} chapters."
        else:
            preview_text += "Load an ePub file to convert it to an audiobook."

        # Run in background to keep UI responsive
        self.preview_btn.setEnabled(False)
        self.statusBar().showMessage("Playing preview...")

        try:
            self.tts_engine.speak(preview_text)
        finally:
            self.preview_btn.setEnabled(True)
            self.statusBar().showMessage("Ready")

    def _start_conversion(self):
        """Start the conversion process."""
        if not self.current_epub:
            return

        # Get output format
        format_idx = self.format_combo.currentIndex()
        if format_idx == 0:
            output_format = "m4b"
            filter_str = "M4B Audiobook (*.m4b)"
            default_ext = ".m4b"
        elif format_idx == 1:
            output_format = "mp3"
            filter_str = "MP3 Audio (*.mp3)"
            default_ext = ".mp3"
        else:
            output_format = "chapters"
            filter_str = ""
            default_ext = ""

        # Get output path
        default_name = f"{self.current_epub.metadata.title}{default_ext}"
        last_dir = self.settings.value('last_output_directory', '')

        if output_format == "chapters":
            output_path = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory",
                last_dir
            )
        else:
            output_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Audiobook As",
                os.path.join(last_dir, default_name),
                filter_str
            )

        if not output_path:
            return

        self.settings.setValue('last_output_directory', str(Path(output_path).parent))

        # Quality mapping
        quality_map = {0: 'low', 1: 'medium', 2: 'high', 3: 'very_high'}

        # Create settings
        settings = ConversionSettings(
            epub_path=self.epub_path_label.text(),
            output_path=output_path,
            voice_id=self.voice_combo.currentData(),
            rate=self.speed_slider.value(),
            volume=self.volume_slider.value() / 100.0,
            output_format=output_format,
            audio_quality=quality_map.get(self.quality_combo.currentIndex(), 'medium'),
            announce_chapters=self.announce_chapters_cb.isChecked(),
            normalize_audio=self.normalize_cb.isChecked()
        )

        # Create and start worker
        self.worker = ConverterWorker(settings)
        self.worker.progress.connect(self._on_progress)
        self.worker.chapter_complete.connect(self._on_chapter_complete)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)

        # Update UI state
        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setValue(0)

        self.worker.start()

    def _cancel_conversion(self):
        """Cancel the ongoing conversion."""
        if self.worker:
            self.worker.cancel()
            self.status_label.setText("Cancelling...")
            self.cancel_btn.setEnabled(False)

    def _on_progress(self, current: int, total: int, message: str):
        """Handle progress updates."""
        self.progress_bar.setValue(current)
        self.status_label.setText(message)
        self.statusBar().showMessage(message)

    def _on_chapter_complete(self, chapter_num: int, title: str):
        """Handle chapter completion."""
        self.status_label.setText(f"Completed: Chapter {chapter_num} - {title}")

    def _on_finished(self, success: bool, path: str):
        """Handle conversion completion."""
        self._reset_ui_state()

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText("Conversion complete!")
            self.statusBar().showMessage(f"Saved to: {path}")

            QMessageBox.information(
                self,
                "Conversion Complete",
                f"Audiobook created successfully!\n\nSaved to:\n{path}"
            )
        else:
            self.status_label.setText("Conversion failed")

    def _on_error(self, error_msg: str):
        """Handle conversion errors."""
        self._reset_ui_state()
        self.status_label.setText("Error occurred")
        self.statusBar().showMessage("Conversion failed")

        QMessageBox.critical(
            self,
            "Conversion Error",
            f"An error occurred during conversion:\n\n{error_msg}"
        )

    def _reset_ui_state(self):
        """Reset UI to ready state."""
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.worker = None

    def _load_settings(self):
        """Load saved settings."""
        # Restore voice selection
        saved_voice = self.settings.value('voice_id')
        if saved_voice:
            idx = self.voice_combo.findData(saved_voice)
            if idx >= 0:
                self.voice_combo.setCurrentIndex(idx)

        # Restore other settings
        self.speed_slider.setValue(int(self.settings.value('speed', 150)))
        self.volume_slider.setValue(int(self.settings.value('volume', 100)))
        self.format_combo.setCurrentIndex(int(self.settings.value('format', 0)))
        self.quality_combo.setCurrentIndex(int(self.settings.value('quality', 1)))

    def closeEvent(self, event):
        """Save settings on close."""
        self.settings.setValue('voice_id', self.voice_combo.currentData())
        self.settings.setValue('speed', self.speed_slider.value())
        self.settings.setValue('volume', self.volume_slider.value())
        self.settings.setValue('format', self.format_combo.currentIndex())
        self.settings.setValue('quality', self.quality_combo.currentIndex())

        # Cancel any ongoing conversion
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(5000)

        self.tts_engine.cleanup()
        event.accept()
