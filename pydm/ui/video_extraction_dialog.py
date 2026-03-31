"""Video Extraction dialog for PyDM."""

import os

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QWidget,
)

from pydm.aria2_manager import Aria2Manager
from pydm.utils.settings import SettingsManager
from pydm.video_extractor import VideoExtractor


class ExtractionThread(QThread):
    """Background thread to run yt-dlp without freezing UI."""
    formats_ready = pyqtSignal(list, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        info = VideoExtractor.get_video_info(self.url)
        if "error" in info:
            self.error_occurred.emit(info["error"])
        else:
            title = info.get("title", "Video")
            formats = VideoExtractor.parse_formats(info)
            self.formats_ready.emit(formats, title)


class VideoExtractionDialog(QDialog):
    """Dialog for extracting and selecting video qualities."""

    def __init__(self, aria2_manager: Aria2Manager, ytdlp_manager, settings: SettingsManager, url: str, title: str, parent=None):
        super().__init__(parent)
        self.aria2_manager = aria2_manager
        self.ytdlp_manager = ytdlp_manager
        self.settings = settings
        self.url = url
        self.video_title = title
        
        self.setWindowTitle("Processing Video...")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._selected_url = ""
        self._format_id = ""
        self._filename = ""
        self._directory = self.aria2_manager.get_category_dir("Video")
        self.formats_data = []

        self._setup_ui()
        self._start_extraction()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Title
        self.title_label = QLabel(self.video_title or "Extracting Video...")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #58a6ff;")
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Loading State
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setContentsMargins(0,0,0,0)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate spinning
        self.progress_bar.setFixedHeight(6)
        
        self.status_label = QLabel("Connecting and fetching formats...")
        self.status_label.setStyleSheet("color: #8b949e;")
        
        loading_layout.addWidget(self.progress_bar)
        loading_layout.addWidget(self.status_label)
        layout.addWidget(self.loading_widget)

        # Result State (Hidden initially)
        self.result_widget = QWidget()
        self.result_widget.setVisible(False)
        result_layout = QFormLayout(self.result_widget)
        result_layout.setContentsMargins(0,0,0,0)

        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumHeight(36)
        result_layout.addRow("Quality:", self.quality_combo)
        
        self.name_input = QLineEdit()
        self.name_input.setMinimumHeight(32)
        result_layout.addRow("Name:", self.name_input)

        layout.addWidget(self.result_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.clicked.connect(self.reject)

        self.download_btn = QPushButton("⬇ Download")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.setMinimumHeight(36)
        self.download_btn.clicked.connect(self._on_download)
        self.download_btn.setEnabled(False)

        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.download_btn)
        layout.addLayout(button_layout)

    def _start_extraction(self):
        self.thread = ExtractionThread(self.url)
        self.thread.formats_ready.connect(self._on_formats_ready)
        self.thread.error_occurred.connect(self._on_error)
        self.thread.start()

    def _on_formats_ready(self, formats: list, title: str):
        if not formats:
            self._on_error("No direct downloadable formats found.")
            return
            
        self.formats_data = formats
        self.video_title = title
        
        # Clean title for filename
        safe_title = "".join(c for c in title if c.isalnum() or c in " .-_()").strip()
        self.name_input.setText(f"{safe_title}")

        # Populate combo box
        for f in formats:
            size_mb = f['filesize'] / (1024*1024) if f['filesize'] else 0
            size_str = f" - {size_mb:.1f} MB" if size_mb else ""
            display_text = f"[{f['type']}] {f['resolution']} ({f['ext']}){size_str} {f['note']}"
            self.quality_combo.addItem(display_text)
            
        self.loading_widget.setVisible(False)
        self.title_label.setText(self.video_title)
        self.result_widget.setVisible(True)
        self.download_btn.setEnabled(True)
        self.setWindowTitle("Prepare Download")

    def _on_error(self, err: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {err}")
        self.status_label.setStyleSheet("color: #f85149;")

    def _on_download(self):
        idx = self.quality_combo.currentIndex()
        if idx >= 0 and idx < len(self.formats_data):
            selected_format = self.formats_data[idx]
            self._selected_url = selected_format["url"]
            self._format_id = selected_format["format_id"]
            ext = selected_format["ext"]
            
            # Ensure filename has extension
            filename = self.name_input.text().strip()
            if not filename.endswith(f".{ext}"):
                filename = f"{filename}.{ext}"
                
            self._filename = filename
            self.accept()
            
    def get_download_info(self) -> dict:
        return {
            "url": self._selected_url,
            "directory": self._directory,
            "filename": self._filename,
            "format_id": self._format_id,
        }
