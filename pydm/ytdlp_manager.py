import threading
import uuid
import time
import logging
import os
import yt_dlp
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class VirtualDownload:
    """Mock object that mimics aria2p.Download for the UI Monitor."""
    def __init__(self, url: str, directory: str, filename: str, format_id: str):
        self.gid = uuid.uuid4().hex[:16]
        self.url = url
        self.directory = directory
        self.filename = filename
        self.format_id = format_id
        
        self.name = filename
        self.status = "waiting" # waiting, active, paused, complete, error
        self.completed_length = 0
        self.total_length = 1 # avoid division by zero
        self.download_speed = 0
        self.eta = 0
        self.error_message = ""
        self.upload_speed = 0
        self.connections = 1
        
        # Thread control
        self._thread = None
        self._abort_flag = False

    @property
    def progress(self):
        return (self.completed_length / self.total_length * 100) if self.total_length > 0 else 0.0

    @property
    def dir(self):
        return self.directory

class YtDlpManager:
    """Manages concurrent yt-dlp native downloads and simulates aria2p properties."""
    
    def __init__(self):
        self.downloads: Dict[str, VirtualDownload] = {}
        self._lock = threading.Lock()

    def add_download(self, url: str, directory: str, filename: str, format_id: str) -> str:
        """Adds a download and starts it."""
        dl = VirtualDownload(url, directory, filename, format_id)
        with self._lock:
            self.downloads[dl.gid] = dl
        
        self.resume_download(dl.gid)
        return dl.gid

    def get_downloads(self) -> List[VirtualDownload]:
        """Returns all virtual downloads."""
        with self._lock:
            return list(self.downloads.values())

    def pause_download(self, gid: str) -> bool:
        with self._lock:
            if gid in self.downloads:
                dl = self.downloads[gid]
                if dl.status == "active":
                    dl._abort_flag = True
                    dl.status = "paused"
                    dl.download_speed = 0
                    dl.eta = 0
                    return True
        return False

    def resume_download(self, gid: str) -> bool:
        with self._lock:
            if gid in self.downloads:
                dl = self.downloads[gid]
                if dl.status in ["paused", "error", "waiting"]:
                    dl._abort_flag = False
                    dl.status = "active"
                    if dl._thread is None or not dl._thread.is_alive():
                        dl._thread = threading.Thread(target=self._worker, args=(dl,), daemon=True)
                        dl._thread.start()
                    return True
        return False

    def remove_download(self, gid: str) -> bool:
        with self._lock:
            if gid in self.downloads:
                dl = self.downloads[gid]
                dl._abort_flag = True
                dl.status = "removed"
                # Wait, do we remove the file? To keep it simple, just remove from dict
                del self.downloads[gid]
                return True
        return False

    def _worker(self, dl: VirtualDownload):
        """Background thread executing yt-dlp."""
        
        def hook(d):
            if dl._abort_flag:
                raise KeyboardInterrupt("Aborted by user")
            
            if d['status'] == 'downloading':
                dl.completed_length = d.get('downloaded_bytes', dl.completed_length)
                dl.total_length = d.get('total_bytes') or d.get('total_bytes_estimate') or dl.total_length
                dl.download_speed = d.get('speed', 0) or 0
                dl.eta = d.get('eta', 0) or 0
                dl.status = "active"
                
            elif d['status'] == 'finished':
                dl.completed_length = dl.total_length  # 100%
                dl.download_speed = 0
                dl.eta = 0
                # Could be merging right after this
        
        ydl_opts = {
            'format': dl.format_id,
            'outtmpl': os.path.join(dl.directory, dl.filename),
            'progress_hooks': [hook],
            'quiet': True,
            'no_warnings': True,
            # Use aria2c for raw download chunks if available, but native ffmpeg for merging
            'external_downloader': 'aria2c',
            'external_downloader_args': ['-c', '-j', '16', '-s', '16', '-x', '16', '-k', '1M'],
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([dl.url])
            dl.status = "complete"
            dl.download_speed = 0
            dl.eta = 0
        except KeyboardInterrupt:
            # We triggered this intentionally via pause
            pass
        except Exception as e:
            if not dl._abort_flag:
                dl.status = "error"
                dl.error_message = str(e)
                logger.error(f"YtDlpManager Error for {dl.gid}: {e}")
