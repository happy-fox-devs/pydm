"""Main window for PyDM."""

import logging
import os
import sys
import subprocess

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QColor
from PyQt6.QtWidgets import (
    QMainWindow,
    QToolBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QProgressBar,
    QStatusBar,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QMenu,
    QSystemTrayIcon,
    QApplication,
    QCheckBox,
)

from pydm.aria2_manager import Aria2Manager
from pydm.download_monitor import DownloadMonitor, DownloadInfo
from pydm.ui.add_download_dialog import AddDownloadDialog
from pydm.ui.video_extraction_dialog import VideoExtractionDialog
from pydm.ui.settings_dialog import SettingsDialog
from pydm.ui.styles import STATUS_COLORS, STATUS_TEXT, COLORS
from pydm.utils.helpers import format_size, format_speed, format_eta, truncate_filename

logger = logging.getLogger(__name__)

# Column indices
COL_NAME = 0
COL_SIZE = 1
COL_PROGRESS = 2
COL_SPEED = 3
COL_ETA = 4
COL_STATUS = 5
COL_GID = 6  # Hidden column for GID


class MainWindow(QMainWindow):
    """PyDM main application window."""

    def __init__(self, aria2_manager: Aria2Manager, ytdlp_manager, settings):
        super().__init__()
        self.aria2_manager = aria2_manager
        self.ytdlp_manager = ytdlp_manager
        self.settings = settings
        self._download_rows: dict[str, int] = {}  # GID -> row index
        self._previous_states: dict[str, str] = {}  # GID -> status string

        self.setWindowTitle("PyDM — Download Manager")
        self.setMinimumSize(900, 550)
        self.resize(1050, 650)

        self._setup_ui()
        self._setup_tray_icon()
        self._setup_monitor()

    # ------------------------------------------------------------------
    # UI Setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        """Build the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar
        self._setup_toolbar()

        # Download table
        self._setup_table()
        main_layout.addWidget(self.table)

        # Status bar
        self._setup_status_bar()

    def _setup_toolbar(self):
        """Create the main toolbar."""
        toolbar = QToolBar("Actions")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(toolbar)

        # Add Download
        self.action_add = QAction("➕  Add", self)
        self.action_add.setShortcut("Ctrl+N")
        self.action_add.setToolTip("Add new download (Ctrl+N)")
        self.action_add.triggered.connect(self._on_add_download)
        toolbar.addAction(self.action_add)

        toolbar.addSeparator()

        # Pause
        self.action_pause = QAction("⏸  Pause", self)
        self.action_pause.setShortcut("Ctrl+P")
        self.action_pause.setToolTip("Pause selected download (Ctrl+P)")
        self.action_pause.triggered.connect(self._on_pause)
        toolbar.addAction(self.action_pause)

        # Resume
        self.action_resume = QAction("▶  Resume", self)
        self.action_resume.setShortcut("Ctrl+R")
        self.action_resume.setToolTip("Resume selected download (Ctrl+R)")
        self.action_resume.triggered.connect(self._on_resume)
        toolbar.addAction(self.action_resume)

        toolbar.addSeparator()

        # Remove
        self.action_remove = QAction("🗑  Delete", self)
        self.action_remove.setShortcut("Delete")
        self.action_remove.setToolTip("Delete selected download (Delete)")
        self.action_remove.triggered.connect(self._on_remove)
        toolbar.addAction(self.action_remove)

        toolbar.addSeparator()

        # Clear errors/missing
        self.action_clear = QAction("🧹  Clear", self)
        self.action_clear.setToolTip("Clear missing and error downloads")
        self.action_clear.triggered.connect(self._on_clear_errors)
        toolbar.addAction(self.action_clear)

        # Clear all
        self.action_clear_all = QAction("✨  Clear All", self)
        self.action_clear_all.setToolTip("Clear all inactive downloads (Completed, Missing, Error)")
        self.action_clear_all.triggered.connect(self._on_clear_all)
        toolbar.addAction(self.action_clear_all)

        # Spacer to push Settings to the right
        spacer = QWidget()
        from PyQt6.QtWidgets import QSizePolicy
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Settings
        self.action_settings = QAction("⚙  Settings", self)
        self.action_settings.setToolTip("Open application settings")
        self.action_settings.triggered.connect(self._on_settings)
        toolbar.addAction(self.action_settings)

    def _setup_table(self):
        """Create the download list table."""
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Size", "Progress", "Speed", "ETA", "Status", "GID"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSortingEnabled(False)

        # Column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(COL_SIZE, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_PROGRESS, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_SPEED, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_ETA, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(COL_STATUS, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(COL_SIZE, 100)
        self.table.setColumnWidth(COL_PROGRESS, 180)
        self.table.setColumnWidth(COL_SPEED, 110)
        self.table.setColumnWidth(COL_ETA, 90)
        self.table.setColumnWidth(COL_STATUS, 140)

        # Hide GID column
        self.table.setColumnHidden(COL_GID, True)

        # Row height
        self.table.verticalHeader().setDefaultSectionSize(44)

        # Context menu
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_status_bar(self):
        """Create the status bar with speed and count info."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        self.speed_label = QLabel("⬇ 0 B/s")
        self.speed_label.setObjectName("statusLabel")
        self.speed_label.setMinimumWidth(150)

        self.active_label = QLabel("Activas: 0")
        self.active_label.setObjectName("statusLabel")

        self.total_label = QLabel("Total: 0")
        self.total_label.setObjectName("statusLabel")

        status_bar.addPermanentWidget(self.speed_label)
        status_bar.addPermanentWidget(self.active_label)
        status_bar.addPermanentWidget(self.total_label)

    def _setup_tray_icon(self):
        """Create system tray icon."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = None
            return

        self._tray = QSystemTrayIcon(self)
        self._tray.setToolTip("PyDM — Download Manager")

        # Try to use a system icon, fallback to default
        icon = QIcon.fromTheme("download")
        if icon.isNull():
            icon = self.style().standardIcon(
                self.style().StandardPixmap.SP_ArrowDown
            )
        self._tray.setIcon(icon)
        self.setWindowIcon(icon)

        # Tray menu
        tray_menu = QMenu()
        tray_menu.setObjectName("trayMenu")

        show_action = QAction("Show PyDM", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _setup_monitor(self):
        """Start the download monitor thread."""
        self.monitor = DownloadMonitor(self.aria2_manager, self.ytdlp_manager, poll_interval_ms=500)
        self.monitor.downloads_updated.connect(self._update_downloads)
        self.monitor.stats_updated.connect(self._update_stats)
        self.monitor.start()

    # ------------------------------------------------------------------
    # Download table updates
    # ------------------------------------------------------------------

    def _update_downloads(self, downloads: list[DownloadInfo]):
        """Update the table with current download status."""
        current_gids = set()

        for info in downloads:
            current_gids.add(info.gid)

            if info.gid in self._download_rows:
                row = self._download_rows[info.gid]
                self._update_row(row, info)
            else:
                row = self.table.rowCount()
                self.table.insertRow(row)
                self._download_rows[info.gid] = row
                self._create_row(row, info)

            # Auto-fallback to browser if download fails
            old_status = self._previous_states.get(info.gid, "")
            if info.status == "error" and old_status != "error":
                if info.url and info.url.startswith("http"):
                    logger.info(f"Download error, auto-fallback to browser: {info.url}")
                    logger.info(f"Error message: {info.error_message}")
                    import webbrowser
                    webbrowser.open(info.url)
            
            self._previous_states[info.gid] = info.status

        # Remove rows for downloads that no longer exist
        gids_to_remove = set(self._download_rows.keys()) - current_gids
        for gid in gids_to_remove:
            row = self._download_rows.pop(gid)
            self.table.removeRow(row)
            # Rebuild row index mapping
            self._rebuild_row_map()

    def _create_row(self, row: int, info: DownloadInfo):
        """Create a new row with all widgets."""
        # Name
        name_item = QTableWidgetItem(truncate_filename(info.name))
        name_item.setToolTip(info.name)
        self.table.setItem(row, COL_NAME, name_item)

        # Size
        size_item = QTableWidgetItem(format_size(info.total_size))
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, COL_SIZE, size_item)

        # Progress bar
        progress = QProgressBar()
        progress.setRange(0, 1000)
        progress.setValue(int(info.progress * 10))
        progress.setFormat(f"{info.progress:.1f}%")
        progress.setFixedHeight(18)
        # Wrap in a container for centering
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(progress)
        self.table.setCellWidget(row, COL_PROGRESS, container)

        # Speed
        speed_item = QTableWidgetItem(format_speed(info.download_speed))
        speed_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, COL_SPEED, speed_item)

        # ETA
        eta_item = QTableWidgetItem(format_eta(info.eta))
        eta_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, COL_ETA, eta_item)

        # Status
        status_text = STATUS_TEXT.get(info.status, info.status)
        status_item = QTableWidgetItem(status_text)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_color = STATUS_COLORS.get(info.status, COLORS["text_secondary"])
        status_item.setForeground(QColor(status_color))
        self.table.setItem(row, COL_STATUS, status_item)

        # GID (hidden)
        gid_item = QTableWidgetItem(info.gid)
        self.table.setItem(row, COL_GID, gid_item)

    def _update_row(self, row: int, info: DownloadInfo):
        """Update an existing row with new data."""
        if row >= self.table.rowCount():
            return

        # Name
        name_item = self.table.item(row, COL_NAME)
        if name_item:
            display_name = truncate_filename(info.name)
            if name_item.text() != display_name:
                name_item.setText(display_name)
                name_item.setToolTip(info.name)

        # Size
        size_item = self.table.item(row, COL_SIZE)
        if size_item:
            size_item.setText(format_size(info.total_size))

        # Progress bar
        container = self.table.cellWidget(row, COL_PROGRESS)
        if container:
            progress_bar = container.findChild(QProgressBar)
            if progress_bar:
                progress_bar.setValue(int(info.progress * 10))
                progress_bar.setFormat(f"{info.progress:.1f}%")

        # Speed
        speed_item = self.table.item(row, COL_SPEED)
        if speed_item:
            speed_item.setText(
                format_speed(info.download_speed) if info.status == "active" else ""
            )

        # ETA
        eta_item = self.table.item(row, COL_ETA)
        if eta_item:
            eta_item.setText(
                format_eta(info.eta) if info.status == "active" else ""
            )

        # Status
        status_item = self.table.item(row, COL_STATUS)
        if status_item:
            status_text = STATUS_TEXT.get(info.status, info.status)
            status_item.setText(status_text)
            status_color = STATUS_COLORS.get(info.status, COLORS["text_secondary"])
            status_item.setForeground(QColor(status_color))

    def _rebuild_row_map(self):
        """Rebuild the GID->row mapping after row removal."""
        self._download_rows.clear()
        for row in range(self.table.rowCount()):
            gid_item = self.table.item(row, COL_GID)
            if gid_item:
                self._download_rows[gid_item.text()] = row

    def _update_stats(self, stats: dict):
        """Update the status bar with global stats."""
        speed = stats.get("download_speed", 0)
        active = stats.get("num_active", 0)
        waiting = stats.get("num_waiting", 0)
        stopped = stats.get("num_stopped", 0)
        total = active + waiting + stopped

        self.speed_label.setText(f"⬇ {format_speed(speed)}")
        self.active_label.setText(f"Active: {active}")
        self.total_label.setText(f"Total: {total}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _get_selected_gid(self) -> str | None:
        """Get the GID of the currently selected row."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return None
        row = rows[0].row()
        gid_item = self.table.item(row, COL_GID)
        return gid_item.text() if gid_item else None

    def _on_add_download(self):
        """Show the Add Download dialog."""
        dialog = AddDownloadDialog(
            aria2_manager=self.aria2_manager,
            settings=self.settings,
            parent=self,
        )
        if dialog.exec():
            info = dialog.get_download_info()
            custom_dir = info["directory"]
            
            computed_category = self.aria2_manager.get_category_for_filename(info["filename"] or "")
            computed_dir = self.aria2_manager.get_category_dir(computed_category)

            if custom_dir == computed_dir or custom_dir == self.aria2_manager.download_dir:
                custom_dir = None
                
            dl = self.aria2_manager.add_download(
                url=info["url"],
                directory=custom_dir,
                filename=info["filename"] or None,
                max_connections=info["max_connections"],
            )
            if dl is None:
                QMessageBox.warning(
                    self,
                    "Error",
                    "No se pudo añadir la descarga. Verifica la URL e intenta de nuevo.",
                )

    def add_download_from_url(self, url: str):
        """Add a download from a captured browser URL.

        Shows the dialog pre-filled with the URL.
        """
        self._show_window()
        dialog = AddDownloadDialog(
            aria2_manager=self.aria2_manager,
            settings=self.settings,
            parent=self,
        )
        dialog.set_url(url)
        if dialog.exec():
            info = dialog.get_download_info()
            custom_dir = info["directory"]
            computed_category = self.aria2_manager.get_category_for_filename(info["filename"] or "")
            computed_dir = self.aria2_manager.get_category_dir(computed_category)
            if custom_dir == computed_dir or custom_dir == self.aria2_manager.download_dir:
                custom_dir = None
            self.aria2_manager.add_download(
                url=info["url"],
                directory=custom_dir,
                filename=info["filename"] or None,
                max_connections=info["max_connections"],
            )

    def add_download_from_browser(self, url: str, filename: str = "", referer: str = "", cookies: str = ""):
        """Add a download captured from the browser extension.

        Automatically starts the download with cookies and referer from the browser.
        Shows the window and the dialog pre-filled.
        """
        self._show_window()
        dialog = AddDownloadDialog(
            aria2_manager=self.aria2_manager,
            settings=self.settings,
            parent=self,
        )
        dialog.set_url(url)
        # Sanitize filename: some browsers report the referrer URL as filename
        if filename and "://" in filename:
            filename = ""
        if filename:
            dialog.filename_input.setText(filename)
        if dialog.exec():
            info = dialog.get_download_info()
            custom_dir = info["directory"]
            computed_category = self.aria2_manager.get_category_for_filename(info["filename"] or filename or url.split("/")[-1])
            computed_dir = self.aria2_manager.get_category_dir(computed_category)
            
            if custom_dir == computed_dir or custom_dir == self.aria2_manager.download_dir:
                custom_dir = None
                
            self.aria2_manager.add_download(
                url=info["url"],
                directory=custom_dir,
                filename=info["filename"] or None,
                max_connections=info["max_connections"],
                referer=referer or None,
                cookies=cookies or None,
            )

    def extract_video_from_browser(self, url: str, pageUrl: str, title: str):
        """Handle a video extraction request from the browser extension.
        
        Shows the video processing dialog with yt-dlp format extraction.
        """
        self._show_window()
        dialog = VideoExtractionDialog(
            aria2_manager=self.aria2_manager,
            ytdlp_manager=self.ytdlp_manager,
            settings=self.settings,
            url=url,
            title=title,
            parent=self
        )
        if dialog.exec():
            info = dialog.get_download_info()
            self.ytdlp_manager.add_download(
                url=info["url"],
                directory=info["directory"],
                filename=info["filename"],
                format_id=info["format_id"],
            )

    def _on_pause(self):
        """Pause the selected download."""
        gid = self._get_selected_gid()
        if gid:
            if not self.aria2_manager.pause_download(gid):
                self.ytdlp_manager.pause_download(gid)

    def _on_resume(self):
        """Resume the selected download."""
        gid = self._get_selected_gid()
        if gid:
            if not self.aria2_manager.resume_download(gid):
                self.ytdlp_manager.resume_download(gid)

    def _on_remove(self):
        """Remove the selected download and optionally delete its file."""
        gid = self._get_selected_gid()
        if not gid:
            return

        is_complete = self._previous_states.get(gid) in ("complete", "missing")
        file_path = None
        if is_complete:
            # Try to figure out file path to offer deletion
            try:
                dl = self.aria2_manager.api.get_download(gid)
                if dl and dl.files:
                    path = str(dl.files[0].path)
                    import os
                    if os.path.exists(path):
                        file_path = path
            except Exception:
                pass

        if file_path:
            behavior = self.settings.get("delete_file_behavior", "ask")
            if behavior == "ask":
                msg = QMessageBox(self)
                msg.setWindowTitle("Confirm Deletion")
                msg.setText("Do you want to remove this download from the list?")
                msg.setInformativeText("You can also remove the downloaded file from your PC.")
                
                keep_btn = msg.addButton("Keep file", QMessageBox.ButtonRole.AcceptRole)
                trash_btn = msg.addButton("Move to Trash", QMessageBox.ButtonRole.DestructiveRole)
                delete_btn = msg.addButton("Delete Permanently", QMessageBox.ButtonRole.DestructiveRole)
                cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
                
                check = QCheckBox("Remember my choice")
                msg.setCheckBox(check)
                msg.setDefaultButton(keep_btn)
                msg.exec()

                clicked = msg.clickedButton()
                if clicked == cancel_btn:
                    return
                
                if check.isChecked():
                    if clicked == keep_btn: self.settings.set("delete_file_behavior", "keep")
                    elif clicked == trash_btn: self.settings.set("delete_file_behavior", "trash")
                    elif clicked == delete_btn: self.settings.set("delete_file_behavior", "delete")

                self._execute_removal(gid, file_path, action="keep" if clicked == keep_btn else "trash" if clicked == trash_btn else "delete")
            else:
                self._execute_removal(gid, file_path, action=behavior)
        else:
            # Not complete or file doesn't exist, just confirm list removal
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                "Are you sure you want to delete this download?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self._execute_removal(gid, None, "keep")

    def _execute_removal(self, gid: str, file_path: str | None, action: str):
        """Execute the removal from memory and file deletion if applicable."""
        # Remove from list
        if not self.aria2_manager.remove_download(gid, force=True):
            self.ytdlp_manager.remove_download(gid)

        # Delete file
        if file_path and action in ("trash", "delete"):
            import os
            import time
            
            aria2_path = file_path + ".aria2"

            def _delete_file(path_to_delete):
                if not os.path.exists(path_to_delete):
                    return
                for _ in range(10):  # Retry up to 1 second
                    try:
                        if action == "trash":
                            try:
                                from send2trash import send2trash
                                send2trash(path_to_delete)
                            except ImportError:
                                os.remove(path_to_delete)
                        else:
                            os.remove(path_to_delete)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    logger.error("Failed to delete file after retries: %s", path_to_delete)

            _delete_file(file_path)
            
            # Also clean up the aria2 control file if it was left behind
            if os.path.exists(aria2_path):
                try:
                    os.remove(aria2_path)
                except OSError:
                    pass

    def _on_clear_errors(self):
        """Remove missing and error downloads from the list."""
        try:
            for gid, status in list(self._previous_states.items()):
                if status in ("error", "missing"):
                    self.aria2_manager.remove_download(gid)
                    self.ytdlp_manager.remove_download(gid)
        except Exception as e:
            logger.error("Failed to clear errors: %s", e)

    def _on_clear_all(self):
        """Remove ALL inactive downloads from the list."""
        try:
            for gid, status in list(self._previous_states.items()):
                if status in ("error", "missing", "complete", "removed"):
                    self.aria2_manager.remove_download(gid)
                    self.ytdlp_manager.remove_download(gid)
        except Exception as e:
            logger.error("Failed to clear all inactive: %s", e)

    def _show_context_menu(self, pos):
        """Show right-click context menu on the table."""
        menu = QMenu(self)

        gid = self._get_selected_gid()
        if not gid:
            return

        pause_action = menu.addAction("⏸  Pause")
        pause_action.triggered.connect(self._on_pause)

        resume_action = menu.addAction("▶  Resume")
        resume_action.triggered.connect(self._on_resume)

        menu.addSeparator()

        # Open folder
        open_folder_action = menu.addAction("📂  Open folder")
        open_folder_action.triggered.connect(lambda: self._open_download_folder(gid))

        menu.addSeparator()

        remove_action = menu.addAction("🗑  Delete")
        remove_action.triggered.connect(self._on_remove)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _open_download_folder(self, gid: str):
        """Open the download folder in the file manager."""
        path = self.aria2_manager.download_dir
        try:
            downloads = self.aria2_manager.get_downloads()
            for dl in downloads:
                if dl.gid == gid:
                    dl_dir = dl.dir
                    path = str(dl_dir) if dl_dir else path
                    break
        except Exception:
            pass
        self._open_folder(path)

    @staticmethod
    def _open_folder(path: str):
        """Open a folder in the native file manager."""
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    # ------------------------------------------------------------------
    # Tray icon
    # ------------------------------------------------------------------

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()

    def _show_window(self):
        """Show and raise the main window."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self):
        """Quit the application."""
        self._cleanup()
        QApplication.quit()

    # ------------------------------------------------------------------
    # Window events
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        """Handle window close based on user preference."""
        close_behavior = self.settings.get("close_behavior", "minimize_to_tray")

        if close_behavior == "minimize_to_tray" and self._tray and self._tray.isVisible():
            self.hide()
            self._tray.showMessage(
                "PyDM",
                "PyDM sigue ejecutándose en la bandeja del sistema.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            event.ignore()
        else:
            # Fully quit the app (not just close the window)
            event.ignore()
            self._quit_app()

    def _on_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.settings, parent=self)
        dialog.exec()

    def _cleanup(self):
        """Clean up resources before quitting."""
        if hasattr(self, "monitor"):
            self.monitor._running = False
            self.monitor.wait(1500)
