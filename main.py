"""
EPUB阅读器 - PyQt6版本
使用 QWebEngineView 实现高性能 HTML 渲染

功能特性:
- 支持 EPUB 格式电子书
- 12+ 精选主题
- 自定义字体、字号、行距、段距
- 阅读模式（鼠标左右键翻页）
- 目录导航
- 图片显示/隐藏
- 阅读进度保存
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from src.ui.main_window import MainWindow


def main():
    # 高DPI支持
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
