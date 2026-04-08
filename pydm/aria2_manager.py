"""aria2c daemon manager for PyDM.

Handles starting/stopping the aria2c daemon and provides
a high-level API for managing downloads via aria2p.
"""

import subprocess
import sys
import time
import os
import signal
import platform
import logging

import aria2p

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"

# Default aria2c configuration
DEFAULT_RPC_PORT = 6800
DEFAULT_RPC_SECRET = "pydm_secret_token"
DEFAULT_MAX_CONNECTIONS = 16
DEFAULT_SPLIT = 16


def _get_default_download_dir() -> str:
    """Detect the system's download directory.

    On Windows, uses SHGetKnownFolderPath via ctypes.
    On Linux, uses xdg-user-dir (respects locale, e.g. ~/Descargas).
    Falls back to ~/Downloads on all platforms.
    """
    if IS_WINDOWS:
        try:
            import ctypes
            from ctypes import wintypes
            # FOLDERID_Downloads = {374DE290-123F-4565-9164-39C4925E467B}
            FOLDERID_Downloads = ctypes.c_char_p(
                b"\x90\xe2\x4d\x37\x3f\x12\x65\x45\x91\x64\x39\xc4\x92\x5e\x46\x7b"
            )
            buf = ctypes.c_wchar_p()
            ctypes.windll.shell32.SHGetKnownFolderPath(
                FOLDERID_Downloads, 0, None, ctypes.byref(buf)
            )
            if buf.value:
                path = buf.value
                ctypes.windll.ole32.CoTaskMemFree(buf)
                return path
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["xdg-user-dir", "DOWNLOAD"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return os.path.expanduser("~/Downloads")


DEFAULT_DOWNLOAD_DIR = _get_default_download_dir()

# Download categories: extension → subfolder
# Files not matching any category go to "General"
DOWNLOAD_CATEGORIES = {
    "Compressed": [
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
        ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".zst",
    ],
    "Programs": [
        ".exe", ".msi", ".deb", ".rpm", ".AppImage", ".dmg",
        ".pkg", ".run", ".sh", ".bin", ".snap", ".flatpak",
    ],
    "Documents": [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".odt", ".ods", ".odp", ".txt", ".rtf", ".csv", ".epub",
    ],
    "Music": [
        ".mp3", ".flac", ".wav", ".aac", ".ogg", ".wma", ".m4a", ".opus",
    ],
    "Video": [
        ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
        ".m4v", ".mpg", ".mpeg", ".ts",
    ],
    "Images": [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
        ".ico", ".tiff", ".tif", ".raw",
    ],
    "APK": [".apk", ".xapk", ".apks"],
    "ISO": [".iso", ".img"],
    "Torrents": [".torrent", ".magnet"],
}


class Aria2Manager:
    """Manages the aria2c daemon process and provides download operations."""

    def __init__(
        self,
        rpc_port: int = DEFAULT_RPC_PORT,
        rpc_secret: str = DEFAULT_RPC_SECRET,
        download_dir: str = DEFAULT_DOWNLOAD_DIR,
        max_connections: int = DEFAULT_MAX_CONNECTIONS,
        split: int = DEFAULT_SPLIT,
        settings = None,
    ):
        self.rpc_port = rpc_port
        self.rpc_secret = rpc_secret
        self.download_dir = download_dir
        self.max_connections = max_connections
        self.split = split
        self.settings = settings
        self.categories_enabled = True
        self.categories = DOWNLOAD_CATEGORIES
        self._process: subprocess.Popen | None = None
        self._api: aria2p.API | None = None

    @property
    def api(self) -> aria2p.API:
        """Get the aria2p API instance, creating it if needed."""
        if self._api is None:
            self._api = aria2p.API(
                aria2p.Client(
                    host="http://localhost",
                    port=self.rpc_port,
                    secret=self.rpc_secret,
                )
            )
        return self._api

    def is_daemon_running(self) -> bool:
        """Check if the aria2c daemon is responding."""
        try:
            self.api.get_stats()
            return True
        except Exception:
            return False

    def start_daemon(self) -> bool:
        """Start the aria2c daemon process.

        Returns True if daemon started successfully.
        """
        if self.is_daemon_running():
            logger.info("aria2c daemon is already running")
            return True

        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)

        # falloc is not supported on NTFS (Windows)
        file_alloc = "none" if IS_WINDOWS else "falloc"

        # Configure session saving
        session_file = os.path.join(self.settings.config_dir, "aria2.session")
        if not os.path.exists(session_file):
            try:
                open(session_file, 'a').close()
            except OSError:
                pass

        cmd = [
            "aria2c",
            "--enable-rpc",
            f"--rpc-listen-port={self.rpc_port}",
            f"--rpc-secret={self.rpc_secret}",
            "--rpc-listen-all=false",
            f"--dir={self.download_dir}",
            f"--max-connection-per-server={self.max_connections}",
            f"--split={self.split}",
            f"--min-split-size=1M",
            "--max-concurrent-downloads=5",
            "--continue=true",
            "--auto-file-renaming=true",
            "--allow-overwrite=false",
            f"--file-allocation={file_alloc}",
            "--summary-interval=0",
            "--disk-cache=64M",
            "--max-overall-download-limit=0",
            "--max-download-limit=0",
            f"--save-session={session_file}",
            f"--input-file={session_file}",
            "--save-session-interval=10",
            "--force-save=true",
            "--max-download-result=500",
        ]

        try:
            popen_kwargs = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.PIPE,
            }
            # Hide console window on Windows
            if IS_WINDOWS:
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

            self._process = subprocess.Popen(cmd, **popen_kwargs)
            # Wait for daemon to be ready
            for _ in range(20):
                time.sleep(0.25)
                if self.is_daemon_running():
                    logger.info("aria2c daemon started on port %d", self.rpc_port)
                    return True
            logger.error("aria2c daemon failed to start within timeout")
            return False
        except FileNotFoundError:
            logger.error(
                "aria2c not found. Install it: sudo pacman -S aria2 (Arch) "
                "or sudo apt install aria2 (Debian/Ubuntu)"
            )
            return False
        except Exception as e:
            logger.error("Failed to start aria2c: %s", e)
            return False

    def stop_daemon(self):
        """Stop the aria2c daemon process."""
        if self._process is not None:
            try:
                # Force save session before terminating since Windows terminate() is forceful
                if self._api:
                    try:
                        self._api.client.save_session()
                        logger.info("aria2c session saved successfully")
                    except Exception as e:
                        logger.warning("Failed to save aria2c session: %s", e)

                self._process.terminate()
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception as e:
                logger.warning("Error stopping aria2c: %s", e)
            finally:
                self._process = None
                self._api = None
            logger.info("aria2c daemon stopped")

    def add_download(
        self,
        url: str,
        directory: str | None = None,
        filename: str | None = None,
        max_connections: int | None = None,
        referer: str | None = None,
        cookies: str | None = None,
    ) -> aria2p.Download | None:
        """Add a new download.

        Args:
            url: The URL to download.
            directory: Override download directory for this download.
            filename: Override filename for this download.
            max_connections: Override max connections per server.
            referer: HTTP Referer header for the download.
            cookies: Cookies string for the download.

        Returns:
            aria2p.Download object or None on failure.
        """
        if IS_WINDOWS:
            ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        else:
            ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

        options = {
            "user-agent": ua,
        }

        # Determine filename: use provided, extract from URL, or generate fallback
        # Reject filenames that look like URLs (some browsers report the referrer
        # page URL as the filename for certain downloads)
        if filename and "://" not in filename:
            options["out"] = filename
        else:
            extracted = self._extract_filename_from_url(url)
            if extracted:
                options["out"] = extracted

        # Determine the final filename for category detection
        final_filename = options.get("out", "")

        # Auto-categorize into subfolder
        if directory:
            options["dir"] = directory
        else:
            category = self.get_category_for_filename(final_filename)
            category_dir = self.get_category_dir(category)
            os.makedirs(category_dir, exist_ok=True)
            options["dir"] = category_dir

        if max_connections:
            options["max-connection-per-server"] = str(max_connections)
            options["split"] = str(max_connections)
        # Detect if URL has a self-contained auth token in query string.
        # CDNs with verify tokens reject requests that also include browser
        # cookies/referer (session mismatch), so we skip those headers.
        from urllib.parse import urlparse, parse_qs
        qs = parse_qs(urlparse(url).query)
        has_token = any(k in qs for k in ("verify", "token", "key", "auth", "sig", "signature", "hash"))

        if referer and not has_token:
            options["referer"] = referer
        if cookies and not has_token:
            options["header"] = f"Cookie: {cookies}"

        try:
            downloads = self.api.add_uris([url], options=options)
            if downloads:
                dl = downloads[0] if isinstance(downloads, list) else downloads
                logger.info("Added download: %s → %s (GID: %s)",
                           final_filename or url[:60], options["dir"], dl.gid)
                return dl
        except Exception as e:
            logger.error("Failed to add download '%s': %s", url, e)
        return None

    def pause_download(self, gid: str) -> bool:
        """Pause a download by GID."""
        try:
            dl = self.api.get_download(gid)
            return dl.pause()
        except Exception as e:
            logger.error("Failed to pause download %s: %s", gid, e)
            return False

    def resume_download(self, gid: str) -> bool:
        """Resume a paused download by GID."""
        try:
            dl = self.api.get_download(gid)
            return dl.resume()
        except Exception as e:
            logger.error("Failed to resume download %s: %s", gid, e)
            return False

    def remove_download(self, gid: str, force: bool = False) -> bool:
        """Remove a download by GID."""
        try:
            dl = self.api.get_download(gid)
            return dl.remove(force=force)
        except Exception as e:
            logger.error("Failed to remove download %s: %s", gid, e)
            return False

    def get_downloads(self) -> list[aria2p.Download]:
        """Get all downloads."""
        try:
            return self.api.get_downloads()
        except Exception as e:
            logger.error("Failed to get downloads: %s", e)
            return []

    def get_global_stats(self) -> dict:
        """Get global download statistics."""
        try:
            stats = self.api.get_stats()
            return {
                "download_speed": stats.download_speed,
                "upload_speed": stats.upload_speed,
                "num_active": stats.num_active,
                "num_waiting": stats.num_waiting,
                "num_stopped": stats.num_stopped,
            }
        except Exception as e:
            logger.error("Failed to get stats: %s", e)
            return {
                "download_speed": 0,
                "upload_speed": 0,
                "num_active": 0,
                "num_waiting": 0,
                "num_stopped": 0,
            }

    @staticmethod
    def _extract_filename_from_url(url: str) -> str | None:
        """Try to extract a reasonable filename from a URL.

        Returns None if no filename can be determined.
        """
        from urllib.parse import urlparse, unquote
        import time as _time

        try:
            parsed = urlparse(url)
            path = unquote(parsed.path)
            # Get last segment of path
            parts = path.rstrip("/").split("/")
            last_part = parts[-1] if parts else ""

            # Reject if it looks like a URL or scheme prefix instead of a filename
            if last_part.startswith("http://") or last_part.startswith("https://"):
                last_part = ""

            # Check if it looks like a real filename (has extension, reasonable length)
            if last_part and "." in last_part and len(last_part) < 200:
                # Clean up common URL artifacts
                last_part = last_part.split("?")[0].split("#")[0]
                if last_part:
                    return last_part

            # Fallback: generate a timestamped name
            timestamp = _time.strftime("%Y%m%d_%H%M%S")
            return f"download_{timestamp}"
        except Exception:
            import time as _time
            timestamp = _time.strftime("%Y%m%d_%H%M%S")
            return f"download_{timestamp}"

    def get_category_for_filename(self, filename: str) -> str:
        """Determine the download category subfolder for a filename.

        Returns the category name (e.g. 'Compressed', 'Video') or 'General'.
        """
        if not self.categories_enabled or not filename:
            return "General"

        lower = filename.lower()
        for category, extensions in self.categories.items():
            for ext in extensions:
                if lower.endswith(ext):
                    return category

        return "General"

    def get_category_dir(self, category: str) -> str:
        """Get the absolute directory path for a specific category.
        
        Uses custom settings if provided, otherwise falls back to the default
        download directory + category name.
        """
        if self.settings:
            custom_path = self.settings.get_category_path(category)
            if custom_path:
                return custom_path
                
        return os.path.join(self.download_dir, category)
