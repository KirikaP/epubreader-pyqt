"""Web communication bridge module"""

from PyQt6.QtCore import QObject, pyqtSlot
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class WebBridge(QObject):
    """Bridge between JavaScript and Python"""

    def __init__(self, parent: "MainWindow"):
        super().__init__(parent)
        self._main_window = parent

    @pyqtSlot(str)
    def onMouseClick(self, button: str) -> None:
        """Handle mouse click events (in reading mode)"""
        if self._main_window.reading_mode:
            if button == "left":
                self._main_window.next_chapter()
            elif button == "right":
                self._main_window.prev_chapter()
