"""Download monitor thread for PyDM.

Polls aria2c daemon at regular intervals and emits
signals with updated download status for the GUI.
"""

import logging
from dataclasses import dataclass, field

from PyQt6.QtCore import QThread, pyqtSignal

from pydm.aria2_manager import Aria2Manager

logger = logging.getLogger(__name__)


@dataclass
class DownloadInfo:
    """Data class representing the state of a single download."""

    gid: str = ""
    name: str = ""
    url: str = ""
    total_size: int = 0
    completed_size: int = 0
    progress: float = 0.0
    download_speed: float = 0.0
    upload_speed: float = 0.0
    status: str = ""  # active, waiting, paused, error, complete, removed
    eta: float = 0.0
    connections: int = 0
    dir: str = ""
    error_message: str = ""


class DownloadMonitor(QThread):
    """Thread that monitors all aria2c downloads and emits updates.

    Signals:
        downloads_updated(list): Emitted with a list of DownloadInfo dicts.
        stats_updated(dict): Emitted with global stats.
    """

    downloads_updated = pyqtSignal(list)
    stats_updated = pyqtSignal(dict)

    def __init__(self, aria2_manager: Aria2Manager, ytdlp_manager, poll_interval_ms: int = 500):
        super().__init__()
        self.aria2_manager = aria2_manager
        self.ytdlp_manager = ytdlp_manager
        self.poll_interval_ms = poll_interval_ms
        self._running = True

    def run(self):
        """Main monitoring loop."""
        while self._running:
            try:
                downloads = self.aria2_manager.get_downloads()
                vt_dl = self.ytdlp_manager.get_downloads() if self.ytdlp_manager else []
                download_infos = []

                # Merge aria2c and ytdlp_manager downloads
                for dl in downloads + vt_dl:
                    try:
                        eta = 0.0
                        if dl.download_speed > 0 and dl.total_length > 0:
                            remaining = dl.total_length - dl.completed_length
                            eta = remaining / dl.download_speed

                        # Extract the original URI for fallback purposes
                        download_uri = ""
                        try:
                            uris = dl.files[0].uris if dl.files else []
                            if uris:
                                download_uri = uris[0].get("uri", "") if isinstance(uris[0], dict) else str(uris[0])
                        except Exception:
                            pass

                        # Extract a reasonable display name
                        display_name = dl.name or ""
                        # Reject names that are URLs, too short, or just a scheme
                        if not display_name or "://" in display_name or display_name.endswith(":") or len(display_name) < 3:
                            if download_uri:
                                try:
                                    from urllib.parse import urlparse, unquote
                                    parsed = urlparse(download_uri)
                                    path_name = unquote(parsed.path.rstrip("/").split("/")[-1])
                                    # Strip query params from filename
                                    path_name = path_name.split("?")[0]
                                    if path_name and "." in path_name:
                                        display_name = path_name
                                except Exception:
                                    pass
                        if not display_name or "://" in display_name or display_name.endswith(":"):
                            display_name = "Unknown"

                        status = dl.status
                        
                        # Check if completed file still exists
                        if status == "complete" and dl.files:
                            try:
                                import os
                                # Getting the first file path natively
                                file_path = str(dl.files[0].path)
                                
                                # Clean up .aria2 file that is kept by force-save
                                aria2_path = file_path + ".aria2"
                                if os.path.exists(aria2_path):
                                    try:
                                        os.remove(aria2_path)
                                    except OSError:
                                        pass
                                
                                if file_path and not os.path.exists(file_path):
                                    status = "missing"
                            except Exception:
                                pass

                        info = DownloadInfo(
                            gid=dl.gid,
                            name=display_name,
                            url=download_uri,
                            total_size=dl.total_length,
                            completed_size=dl.completed_length,
                            progress=dl.progress,
                            download_speed=dl.download_speed,
                            upload_speed=dl.upload_speed,
                            status=status,
                            eta=eta,
                            connections=dl.connections,
                            dir=dl.dir.as_posix() if hasattr(dl.dir, "as_posix") else str(dl.dir),
                            error_message=dl.error_message or "",
                        )
                        download_infos.append(info)
                    except Exception as e:
                        logger.debug("Error processing download %s: %s", dl.gid, e)

                self.downloads_updated.emit(download_infos)

                # Also emit global stats
                stats = self.aria2_manager.get_global_stats()
                self.stats_updated.emit(stats)

            except Exception as e:
                logger.debug("Monitor poll error: %s", e)

            self.msleep(self.poll_interval_ms)

    def stop(self):
        """Signal the thread to stop and wait for it to finish."""
        self._running = False
        self.wait(2000)
