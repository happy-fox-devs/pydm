"""Native Messaging Host for PyDM.

Listens for messages from the browser extension via stdin (Native Messaging protocol)
and forwards captured download URLs to the PyDM application.

The Native Messaging protocol uses:
- 4-byte little-endian length prefix
- Followed by UTF-8 JSON message

This module can run as:
1. A QThread inside the PyDM app (integrated mode)
2. A standalone script invoked by the browser (bridge mode)
"""

import json
import struct
import sys
import logging
import socket

logger = logging.getLogger(__name__)

# TCP port for native messaging bridge → app communication
SOCKET_PORT = 19876


def read_native_message() -> dict | None:
    """Read a single message from stdin using Native Messaging protocol."""
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length or len(raw_length) < 4:
            return None
        msg_length = struct.unpack("<I", raw_length)[0]
        if msg_length > 1024 * 1024:  # 1MB safety limit
            return None
        raw_msg = sys.stdin.buffer.read(msg_length)
        if len(raw_msg) < msg_length:
            return None
        return json.loads(raw_msg.decode("utf-8"))
    except Exception as e:
        logger.error("Error reading native message: %s", e)
        return None


def send_native_message(msg: dict):
    """Send a message to the browser extension via stdout."""
    try:
        encoded = json.dumps(msg).encode("utf-8")
        sys.stdout.buffer.write(struct.pack("<I", len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    except Exception as e:
        logger.error("Error sending native message: %s", e)


class NativeMessagingBridge:
    """Standalone bridge process invoked by the browser.

    Reads URLs from browser extension via stdin and forwards
    them to the PyDM app via a local TCP socket.
    """

    def run(self):
        """Main loop: read from browser, forward to PyDM."""
        while True:
            msg = read_native_message()
            if msg is None:
                break

            action = msg.get("action")
            if action == "download":
                url = msg.get("url", "")
                filename = msg.get("filename", "")
                referer = msg.get("referer", "")
                cookies = msg.get("cookies", "")
                if url:
                    self._forward_to_app(url, filename, referer, cookies)
                    send_native_message({"status": "ok", "url": url})
            elif action == "extract_video":
                url = msg.get("url", "")
                pageUrl = msg.get("pageUrl", "")
                title = msg.get("title", "")
                if url:
                    self._forward_to_app(url=url, action="extract_video", pageUrl=pageUrl, title=title)
                    send_native_message({"status": "ok", "url": url})
            elif action == "ping":
                send_native_message({"status": "pong"})

    def _forward_to_app(self, url: str, action: str = "download", filename: str = "", referer: str = "", cookies: str = "", pageUrl: str = "", title: str = ""):
        """Send the download URL to the running PyDM app via TCP."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect(("127.0.0.1", SOCKET_PORT))
            data = json.dumps({
                "action": action,
                "url": url,
                "filename": filename,
                "referer": referer,
                "cookies": cookies,
                "pageUrl": pageUrl,
                "title": title,
            }).encode("utf-8")
            sock.sendall(struct.pack("<I", len(data)) + data)
            sock.close()
        except Exception as e:
            logger.error("Failed to forward to PyDM app: %s", e)


# --- The following classes use PyQt6 and are only imported when running the app ---

def create_listener(port: int = SOCKET_PORT):
    """Factory function to create a NativeMessagingListener.

    Imports PyQt6 only when needed (not in bridge mode).
    """
    from PyQt6.QtCore import QThread, pyqtSignal

    class NativeMessagingListener(QThread):
        """QThread that runs a TCP server to receive URLs from the bridge process.

        Signals:
            url_received(dict): Emitted with download info dict when a URL is captured.
        """

        url_received = pyqtSignal(dict)

        def __init__(self, port: int = SOCKET_PORT):
            super().__init__()
            self.port = port
            self._running = True
            self._server: socket.socket | None = None

        def run(self):
            """Start TCP server and listen for incoming URLs."""
            try:
                self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._server.settimeout(1.0)
                self._server.bind(("127.0.0.1", self.port))
                self._server.listen(5)
                logger.info("Native messaging listener started on port %d", self.port)

                while self._running:
                    try:
                        conn, addr = self._server.accept()
                        conn.settimeout(5)
                        self._handle_connection(conn)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        if self._running:
                            logger.debug("Listener accept error: %s", e)
            except Exception as e:
                logger.error("Failed to start native messaging listener: %s", e)
            finally:
                if self._server:
                    self._server.close()

        def _handle_connection(self, conn: socket.socket):
            """Handle an incoming connection from the bridge."""
            try:
                raw_length = conn.recv(4)
                if len(raw_length) < 4:
                    return
                msg_length = struct.unpack("<I", raw_length)[0]
                if msg_length > 1024 * 1024:
                    return

                # Read all data (may come in chunks)
                raw_msg = b""
                while len(raw_msg) < msg_length:
                    chunk = conn.recv(msg_length - len(raw_msg))
                    if not chunk:
                        break
                    raw_msg += chunk

                data = json.loads(raw_msg.decode("utf-8"))

                url = data.get("url", "")
                if url:
                    logger.info("Received URL from browser: %s", url[:100])
                    self.url_received.emit(data)
            except Exception as e:
                logger.debug("Error handling connection: %s", e)
            finally:
                conn.close()

        def stop(self):
            """Stop the listener thread."""
            self._running = False
            if self._server:
                try:
                    self._server.close()
                except Exception:
                    pass
            self.wait(3000)

    return NativeMessagingListener(port)


# Entry point for standalone bridge mode
def main():
    """Run as native messaging host bridge (invoked by browser)."""
    bridge = NativeMessagingBridge()
    bridge.run()


if __name__ == "__main__":
    main()
