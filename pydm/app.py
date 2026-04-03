"""PyDM Application — main orchestration class."""

import sys
import logging
import os

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QTimer, QObject
from PyQt6.QtGui import QFont, QFontDatabase

from pydm import __version__, __app_name__
from pydm.aria2_manager import Aria2Manager, IS_WINDOWS
from pydm.ytdlp_manager import YtDlpManager
from pydm.ui.main_window import MainWindow
from pydm.ui.styles import MAIN_STYLESHEET
from pydm.utils.settings import SettingsManager

logger = logging.getLogger(__name__)


class PyDMApp(QObject):
    """Main application class that ties everything together."""

    def __init__(self):
        super().__init__()
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName(__app_name__)
        self.qt_app.setApplicationVersion(__version__)
        self.qt_app.setQuitOnLastWindowClosed(False)

        # Apply stylesheet
        self.qt_app.setStyleSheet(MAIN_STYLESHEET)

        # Try to load Inter font
        self._load_fonts()

        # Load persistent settings
        self.settings = SettingsManager()

        # Initialize managers
        self.aria2_manager = Aria2Manager(settings=self.settings)
        self.ytdlp_manager = YtDlpManager()

        # Main window (created after daemon starts)
        self.main_window: MainWindow | None = None

        # Native messaging listener
        self.nm_listener = None

    def _load_fonts(self):
        """Try to load the Inter font from system or fallback."""
        families = ["Inter", "Segoe UI", "Roboto", "sans-serif"]
        font = QFont(families[0])
        if font.exactMatch():
            font.setPointSize(10)
        else:
            # Fallback to Segoe UI on Windows
            font = QFont("Segoe UI", 10)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        self.qt_app.setFont(font)

    def start(self) -> int:
        """Start the application. Returns exit code."""
        # Start aria2c daemon
        if not self.aria2_manager.start_daemon():
            if IS_WINDOWS:
                install_hint = (
                    "No se pudo iniciar el daemon aria2c.\n\n"
                    "Asegúrate de tener aria2c en el PATH o instálalo:\n"
                    "  • winget install aria2\n"
                    "  • scoop install aria2\n"
                    "  • Descarga desde https://github.com/aria2/aria2/releases"
                )
            else:
                install_hint = (
                    "No se pudo iniciar el daemon aria2c.\n\n"
                    "Asegúrate de tener aria2 instalado:\n"
                    "  • Arch: sudo pacman -S aria2\n"
                    "  • Debian/Ubuntu: sudo apt install aria2\n"
                    "  • Fedora: sudo dnf install aria2"
                )
            QMessageBox.critical(None, "Error — PyDM", install_hint)
            return 1

        # Create main window
        self.main_window = MainWindow(self.aria2_manager, self.ytdlp_manager, self.settings)
        self.main_window.show()

        # Start native messaging listener
        from pydm.native_messaging import create_listener
        self.nm_listener = create_listener()
        self.nm_listener.url_received.connect(self._on_url_received)
        self.nm_listener.start()

        logger.info("PyDM v%s started", __version__)

        # Run event loop
        exit_code = self.qt_app.exec()

        # Cleanup
        self._shutdown()
        return exit_code

    def _on_url_received(self, data: dict):
        """Handle a URL received from the browser extension."""
        if self.main_window:
            action = data.get("action", "download")
            url = data.get("url", "")
            
            if action == "extract_video":
                pageUrl = data.get("pageUrl", "")
                title = data.get("title", "")
                self.main_window.extract_video_from_browser(url, pageUrl, title)
            else:
                filename = data.get("filename", "")
                referer = data.get("referer", "")
                cookies = data.get("cookies", "")
                self.main_window.add_download_from_browser(url, filename, referer, cookies)

    def _shutdown(self):
        """Clean up all resources."""
        logger.info("Shutting down PyDM...")

        # Stop monitor thread FIRST (before stopping aria2c)
        if self.main_window:
            self.main_window._cleanup()

        if self.nm_listener:
            self.nm_listener.stop()

        # Brief pause to ensure threads have fully stopped
        import time
        time.sleep(0.3)

        # Now safe to stop aria2c
        self.aria2_manager.stop_daemon()
        logger.info("PyDM shut down cleanly")
