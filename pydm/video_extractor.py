import yt_dlp
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class VideoExtractor:
    """Handles extracting video formats from complex websites using yt-dlp."""

    @staticmethod
    def get_video_info(url: str) -> Dict[str, Any]:
        """
        Extract video information and supported formats.
        This is a blocking call and should be run in a background thread.
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info if info else {}
        except Exception as e:
            logger.error(f"Failed to extract video info for {url}: {e}")
            return {"error": str(e)}

    @staticmethod
    def parse_formats(info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses raw yt-dlp info into an easy-to-read list of formats for the UI.
        
        It groups formats into "Video+Audio", "Video Only" and "Audio Only",
        and drops formats without valid URLs.
        """
        if "formats" not in info:
            # Some raw URLs or simple videos might not have a formats list 
            # but provide the URL directly.
            if info.get("url"):
                return [{
                    "id": "default",
                    "ext": info.get("ext", "mp4"),
                    "resolution": "Default",
                    "note": "Original quality",
                    "filesize": info.get("filesize", 0),
                    "vcodec": info.get("vcodec", "none"),
                    "acodec": info.get("acodec", "none"),
                    "url": info.get("url"),
                    "type": "video+audio",
                    "merged_needed": False
                }]
            return []

        parsed = [{
            "format_id": "bestvideo+bestaudio/best",
            "ext": "mp4",
            "resolution": "Best Quality",
            "note": "Auto (Video + Audio)",
            "filesize": 0,
            "vcodec": "auto",
            "acodec": "auto",
            "url": info.get("webpage_url", info.get("url", "")),
            "type": "video+audio",
            "protocol": "https"
        }]

        for f in info.get("formats", []):
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            
            # Categorize the stream
            has_video = vcodec != "none"
            has_audio = acodec != "none"
            
            stream_type = "unknown"
            format_id = f.get("format_id", "")
            
            if has_video and has_audio:
                stream_type = "video+audio"
            elif has_video:
                stream_type = "video+audio"
                format_id = f"{format_id}+bestaudio"
            elif has_audio:
                stream_type = "audio_only"
                
            # Discard useless formats, like storyboards (mhtml)
            if f.get("ext") in ["mhtml", "jpg", "webp"]:
                continue

            note = f.get("format_note", "")
            if stream_type == "audio_only":
                res = f"Audio ({f.get('abr', 'N/A')}k)"
            else:
                height = f.get("height", 0)
                fps = f.get("fps", "")
                fps_str = f" {fps}fps" if fps and fps > 30 else ""
                res = f"{height}p{fps_str}" if height else "Unknown"
            
            parsed.append({
                "format_id": format_id,
                "ext": f.get("ext", "mp4"),
                "resolution": res,
                "note": note,
                "filesize": f.get("filesize") or f.get("filesize_approx", 0),
                "vcodec": vcodec,
                "acodec": acodec,
                "url": info.get("webpage_url", info.get("url", "")),
                "type": stream_type,
                "protocol": f.get("protocol", ""), 
            })
            
        def type_weight(t):
            return {"video+audio": 0, "video_only": 1, "audio_only": 2}.get(t, 3)

        # Skip the first element (the auto one) when sorting
        best_auto = parsed[0]
        rest = parsed[1:]
        rest.sort(key=lambda x: (type_weight(x["type"]), -(int(x["resolution"].split('p')[0]) if 'p' in x["resolution"] else 0)))
        
        return [best_auto] + rest
