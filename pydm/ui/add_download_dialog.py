"""Add Download dialog for PyDM."""

import os
import urllib.parse

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QCheckBox,
)

from pydm.aria2_manager import Aria2Manager
from pydm.utils.settings import SettingsManager


class AddDownloadDialog(QDialog):
    """Dialog for adding a new download URL."""

    def __init__(self, aria2_manager: Aria2Manager, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.aria2_manager = aria2_manager
        self.settings = settings
        self.setWindowTitle("Add Download")
        self.setMinimumWidth(560)
        self.setModal(True)

        self._url = ""
        self._directory = self.aria2_manager.download_dir
        self._filename = ""
        self._max_connections = 16
        
        # State tracking for dynamic category
        self.current_category = "General"
        self.user_changed_dir = False

        self._setup_ui()
        self._update_category_path()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # --- Title ---
        title = QLabel("New Download")
        title.setStyleSheet(
            "font-size: 18px; font-weight: 700; color: #58a6ff; background: transparent;"
        )
        layout.addWidget(title)

        # --- URL input ---
        url_group = QGroupBox("URL")
        url_layout = QVBoxLayout(url_group)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://ejemplo.com/archivo.zip")
        self.url_input.setMinimumHeight(40)
        self.url_input.textChanged.connect(self._on_input_changed)
        url_layout.addWidget(self.url_input)
        layout.addWidget(url_group)

        # --- Options ---
        options_group = QGroupBox("Options")
        options_form = QFormLayout(options_group)
        options_form.setSpacing(12)

        # Directory
        dir_layout = QVBoxLayout()
        dir_input_layout = QHBoxLayout()
        self.dir_input = QLineEdit(self._directory)
        self.dir_input.setMinimumHeight(36)
        dir_browse_btn = QPushButton("📂 Browse...")
        dir_browse_btn.setFixedWidth(120)
        dir_browse_btn.clicked.connect(self._browse_directory)
        dir_input_layout.addWidget(self.dir_input)
        dir_input_layout.addWidget(dir_browse_btn)
        
        # Category save checkbox (hidden by default)
        self.save_category_cb = QCheckBox("Use this folder as default for the 'General' category")
        self.save_category_cb.setVisible(False)
        self.save_category_cb.setStyleSheet("color: #8b949e; font-size: 13px;")
        
        dir_layout.addLayout(dir_input_layout)
        dir_layout.addWidget(self.save_category_cb)
        
        options_form.addRow("Save to:", dir_layout)

        # Filename override
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("(Auto)")
        self.filename_input.setMinimumHeight(36)
        self.filename_input.textChanged.connect(self._on_input_changed)
        options_form.addRow("Name:", self.filename_input)

        # Max connections
        self.connections_spin = QSpinBox()
        self.connections_spin.setRange(1, 32)
        self.connections_spin.setValue(self._max_connections)
        self.connections_spin.setMinimumHeight(36)
        options_form.addRow("Connections:", self.connections_spin)

        layout.addWidget(options_group)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedWidth(120)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)

        download_btn = QPushButton("⬇ Download")
        download_btn.setObjectName("primaryButton")
        download_btn.setFixedWidth(140)
        download_btn.setMinimumHeight(40)
        download_btn.clicked.connect(self._on_download)
        download_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(download_btn)
        layout.addLayout(button_layout)

        # Focus on URL input
        self.url_input.setFocus()

    def _on_input_changed(self):
        """Called when URL or filename changes to update category."""
        if not self.user_changed_dir:
            self._update_category_path()

    def _update_category_path(self):
        """Calculate the category from URL or filename and update the path."""
        url = self.url_input.text().strip()
        filename = self.filename_input.text().strip()
        
        # Determine the name we should base our category check on
        check_name = ""
        if filename:
            check_name = filename
        elif url:
            try:
                parsed = urllib.parse.urlparse(url)
                check_name = urllib.parse.unquote(parsed.path.split("/")[-1])
            except Exception:
                pass
                
        # Get category
        self.current_category = self.aria2_manager.get_category_for_filename(check_name)
        
        # Get appropriate directory for this category
        new_dir = self.aria2_manager.get_category_dir(self.current_category)
        
        # Only update if user hasn't browsed manually
        if not self.user_changed_dir:
            self.dir_input.setText(new_dir)
            self.save_category_cb.setVisible(False)
            
        # Update the checkbox text in case user did browse manually and is modifying the extension now
        self.save_category_cb.setText(f"Utilizar esta carpeta por defecto para la categoría '{self.current_category}'")

    def _browse_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Seleccionar directorio de descarga",
            self.dir_input.text(),
        )
        if directory:
            self.dir_input.setText(directory)
            self.user_changed_dir = True
            self.save_category_cb.setText(f"Utilizar esta carpeta por defecto para la categoría '{self.current_category}'")
            self.save_category_cb.setVisible(True)

    def _on_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.url_input.setStyleSheet("border-color: #f85149;")
            self.url_input.setPlaceholderText("⚠ Ingresa una URL válida")
            return

        self._url = url
        self._directory = self.dir_input.text().strip()
        self._filename = self.filename_input.text().strip()
        self._max_connections = self.connections_spin.value()

        # If no explicit filename, extract from URL for the existence check
        check_filename = self._filename
        if not check_filename:
            try:
                parsed = urllib.parse.urlparse(url)
                check_filename = urllib.parse.unquote(parsed.path.rstrip("/").split("/")[-1])
                check_filename = check_filename.split("?")[0]
            except Exception:
                check_filename = ""

        # Check if file already exists
        if check_filename and self._directory:
            target_path = os.path.join(self._directory, check_filename)
            if os.path.exists(target_path):
                from PyQt6.QtWidgets import QMessageBox
                msg = QMessageBox(self)
                msg.setWindowTitle("File already exists")
                msg.setText(f"'{check_filename}' already exists in the download folder.")
                msg.setInformativeText("What would you like to do?")
                overwrite_btn = msg.addButton("Overwrite", QMessageBox.ButtonRole.DestructiveRole)
                duplicate_btn = msg.addButton("Duplicate", QMessageBox.ButtonRole.AcceptRole)
                cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                msg.setDefaultButton(duplicate_btn)
                msg.exec()

                clicked = msg.clickedButton()
                if clicked == cancel_btn:
                    return
                elif clicked == duplicate_btn:
                    # Find next available name: file (1).ext, file (2).ext, ...
                    base, ext = os.path.splitext(check_filename)
                    counter = 1
                    while os.path.exists(os.path.join(self._directory, f"{base} ({counter}){ext}")):
                        counter += 1
                    self._filename = f"{base} ({counter}){ext}"
                elif clicked == overwrite_btn:
                    # Remove existing file so aria2c can write to it
                    try:
                        os.remove(target_path)
                    except OSError:
                        pass
                    self._filename = check_filename

        # Save custom category path if user requested it
        if self.save_category_cb.isChecked() and self.user_changed_dir:
            self.settings.set_category_path(self.current_category, self._directory)

        self.accept()

    def get_download_info(self) -> dict:
        """Return the download info entered by the user."""
        return {
            "url": self._url,
            "directory": self._directory,
            "filename": self._filename,
            "max_connections": self._max_connections,
        }

    def set_url(self, url: str):
        """Pre-fill the URL field (used when capturing from browser)."""
        self.url_input.setText(url)
