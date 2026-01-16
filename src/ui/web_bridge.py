"""Web通信桥接模块"""

from PyQt6.QtCore import QObject, pyqtSlot
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class WebBridge(QObject):
    """JavaScript 与 Python 通信桥接"""

    def __init__(self, parent: "MainWindow"):
        super().__init__(parent)
        self._main_window = parent

    @pyqtSlot(str)
    def onMouseClick(self, button: str) -> None:
        """处理鼠标点击事件 (阅读模式下)"""
        if self._main_window.reading_mode:
            if button == "left":
                self._main_window.next_chapter()
            elif button == "right":
                self._main_window.prev_chapter()
