"""UI dialog components: font selection and helpers."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QListWidget,
    QLineEdit,
    QDialogButtonBox,
)
from PyQt6.QtGui import QFontDatabase

from src.core.themes import THEMES


class FontDialog(QDialog):
    """Font selection dialog (supports search and double-click selection)."""

    def __init__(self, parent, current_font: str):
        super().__init__(parent)
        self.setWindowTitle("选择字体")
        self.resize(400, 500)
        self._selected_font = current_font

        layout = QVBoxLayout(self)

        # Search input: live filter the font list
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索字体...")
        self.search.textChanged.connect(self._filter_fonts)
        layout.addWidget(self.search)

# Font list: display system fonts and support double-click to confirm
        self.font_list = QListWidget()
        self._fonts = sorted(
            [f for f in QFontDatabase.families() if not f.startswith("@")]
        )
        self.font_list.addItems(self._fonts)
        self.font_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.font_list)

        # Set current selection to the provided current font
        for i, f in enumerate(self._fonts):
            if f == current_font:
                self.font_list.setCurrentRow(i)
                break

        # OK/Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _filter_fonts(self, text: str) -> None:
        self.font_list.clear()
        filtered = [f for f in self._fonts if text.lower() in f.lower()]
        self.font_list.addItems(filtered)

    def get_font(self) -> str:
        item = self.font_list.currentItem()
        return item.text() if item else self._selected_font


# Theme selection logic moved to the toolbar menu (MainWindow); keep FontDialog and remove deprecated ThemeDialog to clean up legacy code
