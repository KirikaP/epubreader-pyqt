"""
EPUB Reader - PyQt6 version
Uses QWebEngineView for high-performance HTML rendering

Features:
- Supports EPUB format ebooks
- 12+ curated themes
- Custom fonts, font sizes, line spacing and paragraph spacing
- Reading mode (mouse-driven navigation)
- Table of contents navigation
- Toggle images on/off
- Save reading progress
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.main_window import MainWindow


def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("EPUB阅读器")
    app.setApplicationVersion("2.0.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
