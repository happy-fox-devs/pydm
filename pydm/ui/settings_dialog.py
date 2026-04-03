"""Settings dialog for PyDM."""

import sys
import os
import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QComboBox,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)

from pydm.utils.settings import SettingsManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings
        self._needs_restart = False

        self.setWindowTitle("Settings — PyDM")
        self.setFixedSize(440, 340)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 20)

        # ── General section ──────────────────────────────────────────
        general_group = QGroupBox("General")
        general_layout = QFormLayout(general_group)
        general_layout.setSpacing(14)
        general_layout.setContentsMargins(16, 24, 16, 16)

        # Show console
        self.console_check = QCheckBox("Show console window on startup")
        self.console_check.setToolTip(
            "Show the terminal/console when PyDM starts.\n"
            "Requires restart to take effect."
        )
        general_layout.addRow(self.console_check)

        # Start with OS
        self.autostart_check = QCheckBox("Start PyDM with Windows")
        if sys.platform != "win32":
            self.autostart_check.setText("Start PyDM on login")
        self.autostart_check.setToolTip(
            "Automatically launch PyDM when you log in."
        )
        general_layout.addRow(self.autostart_check)

        layout.addWidget(general_group)

        # ── Behavior section ─────────────────────────────────────────
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout(behavior_group)
        behavior_layout.setSpacing(14)
        behavior_layout.setContentsMargins(16, 24, 16, 16)

        # Close behavior
        close_label = QLabel("When closing the window:")
        self.close_combo = QComboBox()
        self.close_combo.addItem("Minimize to system tray", "minimize_to_tray")
        self.close_combo.addItem("Close the application", "close")
        behavior_layout.addRow(close_label, self.close_combo)

        layout.addWidget(behavior_group)

        # ── Spacer ───────────────────────────────────────────────────
        layout.addStretch()

        # ── Buttons ──────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _load_current_settings(self):
        """Load current settings into the UI widgets."""
        self.console_check.setChecked(
            self.settings.get("show_console", False)
        )
        self.autostart_check.setChecked(
            self.settings.get_autostart()
        )

        close_behavior = self.settings.get("close_behavior", "minimize_to_tray")
        idx = self.close_combo.findData(close_behavior)
        if idx >= 0:
            self.close_combo.setCurrentIndex(idx)

    def _on_save(self):
        """Save settings and close."""
        old_console = self.settings.get("show_console", False)
        new_console = self.console_check.isChecked()

        # Save console preference
        self.settings.set("show_console", new_console)

        # Save close behavior
        self.settings.set(
            "close_behavior",
            self.close_combo.currentData()
        )

        # Save autostart
        new_autostart = self.autostart_check.isChecked()
        old_autostart = self.settings.get_autostart()
        if new_autostart != old_autostart:
            self.settings.set_autostart(new_autostart)

        # Check if restart is needed
        if new_console != old_console:
            self._needs_restart = True
            QMessageBox.information(
                self,
                "Restart Required",
                "PyDM needs to restart for the console setting to take effect.\n\n"
                "Please restart the application manually.",
            )

        self.accept()

    @property
    def needs_restart(self) -> bool:
        """Whether the app needs a restart after saving."""
        return self._needs_restart
