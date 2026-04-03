"""Settings dialog for PyDM."""

import sys
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
)

from pydm.utils.settings import SettingsManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """Application settings dialog."""

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings = settings

        self.setWindowTitle("Settings — PyDM")
        self.setMinimumWidth(440)
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
        general_inner = QVBoxLayout(general_group)
        general_inner.setSpacing(12)
        general_inner.setContentsMargins(4, 4, 4, 4)

        self.autostart_check = QCheckBox("Start PyDM with Windows")
        if sys.platform != "win32":
            self.autostart_check.setText("Start PyDM on login")
        self.autostart_check.setToolTip(
            "Automatically launch PyDM when you log in."
        )
        general_inner.addWidget(self.autostart_check)

        layout.addWidget(general_group)

        # ── Behavior section ─────────────────────────────────────────
        behavior_group = QGroupBox("Behavior")
        behavior_inner = QVBoxLayout(behavior_group)
        behavior_inner.setSpacing(10)
        behavior_inner.setContentsMargins(4, 4, 4, 4)

        close_label = QLabel("When closing the window:")
        close_label.setMinimumHeight(20)
        behavior_inner.addWidget(close_label)

        self.close_combo = QComboBox()
        self.close_combo.addItem("Minimize to system tray", "minimize_to_tray")
        self.close_combo.addItem("Close the application", "close")
        self.close_combo.setMinimumHeight(36)
        behavior_inner.addWidget(self.close_combo)

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
        self.autostart_check.setChecked(
            self.settings.get_autostart()
        )

        close_behavior = self.settings.get("close_behavior", "minimize_to_tray")
        idx = self.close_combo.findData(close_behavior)
        if idx >= 0:
            self.close_combo.setCurrentIndex(idx)

    def _on_save(self):
        """Save settings and close."""
        self.settings.set(
            "close_behavior",
            self.close_combo.currentData()
        )

        new_autostart = self.autostart_check.isChecked()
        old_autostart = self.settings.get_autostart()
        if new_autostart != old_autostart:
            self.settings.set_autostart(new_autostart)

        self.accept()
