"""UI 对话框组件：字体选择等。"""

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
    """字体选择对话框（支持搜索与双击选择）。"""

    def __init__(self, parent, current_font: str):
        super().__init__(parent)
        self.setWindowTitle("选择字体")
        self.resize(400, 500)
        self._selected_font = current_font

        layout = QVBoxLayout(self)

        # 搜索输入：实时过滤字体列表
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索字体...")
        self.search.textChanged.connect(self._filter_fonts)
        layout.addWidget(self.search)

# 字体列表：显示系统字体，支持双击确认
        self.font_list = QListWidget()
        self._fonts = sorted(
            [f for f in QFontDatabase.families() if not f.startswith("@")]
        )
        self.font_list.addItems(self._fonts)
        self.font_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.font_list)

        # 设置列表当前项为传入的当前字体
        for i, f in enumerate(self._fonts):
            if f == current_font:
                self.font_list.setCurrentRow(i)
                break

        # 确认/取消 按钮
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


# 主题选择逻辑已迁移到工具栏下拉菜单（MainWindow）；保留 FontDialog，移除已弃用的 ThemeDialog 类以清理遗留代码
