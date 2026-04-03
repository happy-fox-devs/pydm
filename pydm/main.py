#!/usr/bin/env python3
"""PyDM — Python Download Manager.

Entry point for the application.
"""

import sys
import signal
import logging

from pydm.app import PyDMApp


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    """Main entry point."""
    setup_logging()
    app = PyDMApp()

    # Handle SIGINT (Ctrl+C) gracefully
    def sigint_handler(*args):
        logging.getLogger(__name__).info("Received SIGINT, shutting down...")
        app._shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, sigint_handler)

    # Allow Python to handle signals while Qt event loop runs
    # by setting a timer that gives Python a chance to run
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(200)

    sys.exit(app.start())


if __name__ == "__main__":
    main()
