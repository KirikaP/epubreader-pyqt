"""主窗口（UI 与交互）"""

import os
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QToolBar,
    QFileDialog,
    QMessageBox,
    QLabel,
    QMenu,
    QFrame,
    QSizePolicy,
    QWidgetAction,
    QToolButton,
    QLineEdit,
    QListWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtGui import QAction, QFont, QShortcut, QKeySequence, QIcon, QFontDatabase
from PyQt6.QtWebChannel import QWebChannel

from src.core.epub_loader import EpubLoader
from src.core.settings import SettingsManager
from src.core.themes import THEMES, get_stylesheet, generate_html_style
from src.ui.dialogs import FontDialog
from src.ui.web_bridge import WebBridge


# JavaScript 代码：用于阅读模式下的鼠标点击检测
_MOUSE_HANDLER_JS = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.bridge = channel.objects.bridge;
    });
});
// 忽略发生在滚动条上的点击（避免滚动栏被点击时翻页）
document.addEventListener('mousedown', function(e) {
    try {
        var scrollbarWidth = window.innerWidth - (document.documentElement.clientWidth || document.body.clientWidth || 0);
        // 如果计算出的滚动条宽度大于 0 且点击位置在窗口右侧滚动条区域，则忽略该事件
        if (scrollbarWidth > 0 && e.clientX >= window.innerWidth - scrollbarWidth) {
            return;
        }
    } catch (err) {
        // 发生异常时不影响正常点击处理
    }

    // 忽略在可编辑输入控件上的点击
    var tgt = e.target;
    if (tgt && (tgt.tagName === 'INPUT' || tgt.tagName === 'TEXTAREA' || tgt.isContentEditable)) {
        return;
    }

    if (window.bridge) {
        if (e.button === 0) window.bridge.onMouseClick('left');
        else if (e.button === 2) window.bridge.onMouseClick('right');
    }
});
document.addEventListener('contextmenu', function(e) { e.preventDefault(); });
</script>
"""


class MainWindow(QMainWindow):
    """EPUB阅读器主窗口 - 现代化设计"""

    # 默认设置
    DEFAULT_FONT = "Microsoft YaHei"
    DEFAULT_FONT_SIZE = 16
    DEFAULT_THEME = "light"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB 阅读器")
        self.resize(1280, 800)

        # 核心服务与资源初始化
        self._loader = EpubLoader()
        self._settings = SettingsManager()
        self._web_bridge = WebBridge(self)

        # 阅读状态
        self._current_chapter = 0
        self._last_opened: Optional[str] = None

        # 工具栏项目跟踪（用于紧凑模式切换）
        self._toolbar_items: list[tuple] = []  # (item, label, emoji)
        self._compact_threshold = 520
        self._compact_mode = False

        # 显示与排版设置
        self._current_theme = self.DEFAULT_THEME
        self._font_family = self.DEFAULT_FONT
        self._font_size = self.DEFAULT_FONT_SIZE
        self._font_scale = 1.0
        self._line_spacing = 1.8
        self._paragraph_spacing = 1.2
        self._show_images = True
        self._reading_mode = False
        self._toc_visible = True

        # 临时保存滚动信息以便在修改显示设置时恢复阅读位置（以章节为粒度）
        self._pending_scroll_ratio: Optional[float] = None
        self._pending_scroll_chapter: Optional[int] = None

        # UI 组件引用（句柄用于后续更新）
        self._reading_btn: Optional[QAction] = None
        self._progress_label: Optional[QLabel] = None
        self._chapter_label: Optional[QLabel] = None
        self._toc_header: Optional[QLabel] = None

        self._setup_ui()
        self._setup_shortcuts()
        self._load_settings()
        self._apply_theme()

        # 自动打开上次文件
        if self._last_opened and os.path.exists(self._last_opened):
            file_path = self._last_opened
            QTimer.singleShot(100, lambda: self._open_file(file_path))

    # ==================== 属性 ====================

    @property
    def reading_mode(self) -> bool:
        return self._reading_mode

    # ==================== UI 初始化 ====================

    def _setup_ui(self) -> None:
        """初始化主界面布局"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主分割器（左侧目录 / 右侧内容）
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        layout.addWidget(self._splitter)

        # 左侧目录面板
        self._toc_widget = self._create_toc_panel()
        self._splitter.addWidget(self._toc_widget)

        # 右侧内容区
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._browser = QWebEngineView()
        content_layout.addWidget(self._browser)

        self._splitter.addWidget(content_widget)

        # WebChannel 通信
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._web_bridge)
        page = self._browser.page()
        assert page is not None
        page.setWebChannel(self._channel)

        self._splitter.setSizes([200, 1000])
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)

        self._create_toolbar()
        self._create_status_bar()

    def _create_toc_panel(self) -> QWidget:
        """创建目录面板"""
        panel = QWidget()
        panel.setMinimumWidth(120)
        panel.setMaximumWidth(350)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 目录头部（显示标题与章节计数）
        header = QWidget()
        header.setFixedHeight(36)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 8, 0)

        self._toc_header = QLabel("📚 目录")
        self._toc_header.setFont(QFont(self.DEFAULT_FONT, 11, QFont.Weight.Bold))
        header_layout.addWidget(self._toc_header)

        header_layout.addStretch()

        self._chapter_label = QLabel("")
        self._chapter_label.setFont(QFont(self.DEFAULT_FONT, 9))
        self._chapter_label.setStyleSheet("opacity: 0.7;")
        header_layout.addWidget(self._chapter_label)

        layout.addWidget(header)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        layout.addWidget(line)

        # 目录树
        self._toc_tree = QTreeWidget()
        self._toc_tree.setHeaderHidden(True)
        self._toc_tree.setIndentation(12)
        self._toc_tree.setAnimated(True)
        self._toc_tree.setExpandsOnDoubleClick(True)
        self._toc_tree.itemClicked.connect(self._on_toc_click)
        self._toc_tree.setFont(QFont(self.DEFAULT_FONT, 10))
        layout.addWidget(self._toc_tree)

        return panel

    def _create_toolbar(self) -> None:
        """构建并填充工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toolbar = toolbar
        self.addToolBar(toolbar)

        # 文件按钮 - 直接打开
        self._add_action(
            toolbar, "📂 打开", "打开文件 (Ctrl+O)", self._open_file_dialog
        )

        toolbar.addSeparator()

        # 导航按钮组
        self._add_action(toolbar, "⬅️ 上一章", "上一章 (←)", self.prev_chapter)
        self._add_action(toolbar, "➡️ 下一章", "下一章 (→)", self.next_chapter)

        toolbar.addSeparator()

        # 视图按钮组
        self._add_action(toolbar, "📑 目录", "显示/隐藏目录 (Ctrl+T)", self._toggle_toc)
        self._add_action(
            toolbar, "🖼️ 图片", "显示/隐藏图片 (Ctrl+I)", self._toggle_images
        )

        toolbar.addSeparator()

        # 排版（统一由 QAction 管理）
        self._format_action = self._add_action(
            toolbar, "📐 排版", "排版", self._open_format_dialog
        )
        # 设置按钮 - 字体选择变为下拉菜单
        self._font_action = self._add_action(
            toolbar, "🔤 字体", "选择字体", self._choose_font
        )
        # 主题（统一由 QAction 管理，标签支持尾部箭头）
        self._theme_action = self._add_action(
            toolbar, "🎨 主题", "选择主题", self._open_theme_dialog
        )

        # 弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # 阅读模式按钮（右侧）
        self._reading_btn = self._add_action(
            toolbar, "📖 阅读模式", "切换阅读模式 (Ctrl+M)", self._toggle_reading_mode
        )

    def _add_action(self, toolbar: QToolBar, full_text: str, tip: str, callback):
        """添加工具栏 QAction（支持 emoji 图标与文本切换）。返回 QAction。"""
        # 解析 emoji（第一个空格之前的部分）和标签（去掉 emoji 的剩余部分）
        parts = full_text.split(" ", 1)
        emoji = parts[0]
        label = parts[1] if len(parts) > 1 else ""
        # 解析并创建 QAction，保存基础标签与 emoji 用于后续刷新
        action = toolbar.addAction(label, callback)
        assert action is not None
        action.setToolTip(tip)
        try:
            icon = self._emoji_icon(emoji, size=18)
            action.setIcon(icon)
        except Exception:
            pass
        # 保存用于切换显示 (item, label, emoji)
        self._toolbar_items.append((action, label, emoji))
        return action

    def _emoji_icon(self, emoji: str, size: int = 18) -> QIcon:
        """以 emoji 文本绘制并返回 QIcon，用于工具栏图标。"""
        pix = QPixmap(size, size)
        # 透明背景
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        font = QFont(self.DEFAULT_FONT, max(1, int(size * 0.7)))
        painter.setFont(font)
        painter.setPen(QColor(self._get_colors().get("fg", "#000000")))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        return QIcon(pix)

    def _add_menu_button(self, menu: QMenu, text: str, callback) -> None:
        """在菜单中添加不关闭的 QPushButton（用于连续操作）。"""
        from PyQt6.QtWidgets import QPushButton

        parts = text.split(" ", 1)
        emoji = parts[0]
        label = parts[1] if len(parts) > 1 else ""
        btn = QPushButton(label)
        btn.setFlat(True)
        btn.setStyleSheet("text-align: left; padding: 6px 16px;")
        btn.clicked.connect(callback)
        # 设置图标以便紧凑模式仅显示图标
        try:
            btn.setIcon(self._emoji_icon(emoji, size=18))
        except Exception:
            pass
        action = QWidgetAction(menu)
        action.setDefaultWidget(btn)
        menu.addAction(action)
        # 将按钮也记录为 toolbar item 的一部分（便于切换文本/图标）
        self._toolbar_items.append((btn, label, emoji))

    def _maybe_update_toolbar_compact(self) -> None:
        """根据窗口宽度切换工具栏显示模式（图标或图标+文字）。"""
        width = self.width()
        want_compact = width <= self._compact_threshold
        if want_compact == self._compact_mode:
            return
        self._compact_mode = want_compact
        if want_compact:
            # 仅图标
            self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        else:
            # 图标 + 文字
            self._toolbar.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
        # 刷新所有标签，统一管理文本显示
        self._refresh_toolbar_labels()

    def _safe(self, fn, *args, **kwargs):
        """安全调用包装：捕获异常并返回 None，简化错误处理。"""
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None

    def _refresh_toolbar_items(self) -> None:
        """刷新工具栏图标与文本（处理紧凑模式与主题变更）。"""
        for item, label, emoji in self._toolbar_items:
            # 文本处理
            if self._compact_mode:
                self._safe(getattr(item, "setText", lambda *_: None), "")
            else:
                if item is getattr(self, "_theme_action", None):
                    name = THEMES.get(self._current_theme, THEMES["light"])["name"]
                    if name and ord(name[0]) > 255:
                        name = (
                            name[2:] if len(name) > 2 and name[1] == " " else name[1:]
                        )
                    self._safe(getattr(item, "setText", lambda *_: None), name)
                else:
                    self._safe(getattr(item, "setText", lambda *_: None), label)
            # 图标处理（始终刷新以反映主题颜色）
            try:
                icon = self._emoji_icon(emoji, size=18)
            except Exception:
                icon = None
            if icon is not None:
                self._safe(getattr(item, "setIcon", lambda *_: None), icon)
        # 确保格式 action 的文本与 compact 模式一致
        fa = getattr(self, "_format_action", None)
        if fa is not None:
            self._safe(fa.setText, "排版" if not self._compact_mode else "")

    # 兼容旧接口：保持名称但内部复用统一实现
    def _refresh_toolbar_labels(self) -> None:
        self._refresh_toolbar_items()

    def _refresh_toolbar_icons(self) -> None:
        self._refresh_toolbar_items()

    def _create_status_bar(self) -> None:
        """初始化状态栏并添加进度显示"""
        status_bar = self.statusBar()
        assert status_bar is not None

        # 进度标签
        self._progress_label = QLabel(" 0/0 ")
        self._progress_label.setFont(QFont(self.DEFAULT_FONT, 9))
        status_bar.addPermanentWidget(self._progress_label)

        status_bar.showMessage("欢迎使用 EPUB 阅读器")
        # 初始时更新工具栏显示模式（延迟以确保窗口尺寸已确定）
        QTimer.singleShot(200, self._maybe_update_toolbar_compact)
        # 初始时刷新标签，使按钮文本在首次显示时正确（延迟以保证组件已布局）
        QTimer.singleShot(250, self._refresh_toolbar_labels)
        # 初始时生成图标，确保主题色生效
        QTimer.singleShot(
            250, lambda: getattr(self, "_refresh_toolbar_icons", lambda: None)()
        )

    def _setup_shortcuts(self) -> None:
        """注册全局快捷键绑定。"""
        shortcuts = [
            ("Ctrl+O", self._open_file_dialog),
            ("Ctrl+R", self._reopen_last),
            ("Ctrl+Q", self.close),
            ("Ctrl+T", self._toggle_toc),
            ("Left", self.prev_chapter),
            ("Right", self.next_chapter),
            ("Ctrl+=", self._zoom_in),
            ("Ctrl+-", self._zoom_out),
            ("Ctrl+M", self._toggle_reading_mode),
            ("Ctrl+I", self._toggle_images),
            ("Home", lambda: self._goto_chapter(0)),
            ("End", lambda: self._goto_chapter(self._loader.chapter_count() - 1)),
        ]
        for key, func in shortcuts:
            QShortcut(QKeySequence(key), self).activated.connect(func)
        # 当窗口大小改变时需要更新 toolbar 的显示模式
        # 通过重载 resizeEvent 实现

    # ==================== 主题 ====================

    def _apply_theme(self) -> None:
        """将当前主题应用到应用样式表并刷新工具栏。"""
        colors = THEMES.get(self._current_theme, THEMES["light"])
        self.setStyleSheet(get_stylesheet(colors))
        # 更新主题 action 文本以显示当前主题名称（如果存在）
        try:
            if hasattr(self, "_theme_action"):
                name = THEMES.get(self._current_theme, THEMES["light"])["name"]
                # 去掉可能的开头 emoji
                if name and ord(name[0]) > 255:
                    name = name[2:] if len(name) > 2 and name[1] == " " else name[1:]
                try:
                    self._theme_action.setText(name)
                except Exception:
                    self._theme_action.setText(name)
        except Exception:
            pass
        # 重新生成 emoji 图标以反映主题颜色 / 箭头等，并刷新标签
        try:
            self._refresh_toolbar_icons()
            self._refresh_toolbar_labels()
        except Exception:
            # 如果同步更新失败，使用延迟更新保证 UI 稳定性
            QTimer.singleShot(0, self._refresh_toolbar_labels)
            QTimer.singleShot(
                50, lambda: getattr(self, "_refresh_toolbar_icons", lambda: None)()
            )

    def _make_menu_compact(self, menu: QMenu) -> None:
        """Apply compact styling to a QMenu to reduce padding and item height and use theme colors."""
        try:
            colors = self._get_colors()
            bg = colors.get("toolbar_bg", colors.get("bg", "#fff"))
            fg = colors.get("fg", "#000")
            item_bg = colors.get("content_bg", bg)
            item_fg = colors.get("fg", fg)
            select_bg = colors.get("select_bg", "#0078d7")
            select_fg = colors.get("select_fg", "#fff")
            menu.setStyleSheet(
                f"QMenu {{ background: {bg}; color: {fg}; padding: 4px; }}"
                f"QMenu::item {{ padding: 4px 8px; min-height: 20px; background: {item_bg}; color: {item_fg}; }}"
                f"QMenu::item:selected {{ background: {select_bg}; color: {select_fg}; }}"
                f"QLineEdit {{ padding: 4px; margin: 2px; background: {bg}; color: {fg}; }}"
            )
        except Exception:
            pass

    def _on_theme_selected(self, action) -> None:
        """主题菜单项被选中时调用"""
        key = action.data()
        if not key:
            return
        self._current_theme = key
        # 将动作设置为选中（单选行为由 QActionGroup 保证）
        try:
            action.setChecked(True)
        except Exception:
            pass
        self._apply_theme()
        self._display_chapter()
        self._save_settings()

    def _get_colors(self) -> dict:
        return THEMES.get(self._current_theme, THEMES["light"])

    def showEvent(self, event) -> None:
        """窗口显示后再刷新工具栏状态，确保标签显示正确"""
        super().showEvent(event)
        QTimer.singleShot(50, self._maybe_update_toolbar_compact)
        QTimer.singleShot(80, self._refresh_toolbar_labels)
        QTimer.singleShot(
            80, lambda: getattr(self, "_refresh_toolbar_icons", lambda: None)()
        )

    def _open_theme_dialog(self) -> None:
        # 使用菜单显示主题选项并锚定到工具栏对应 action
        menu = QMenu(self)
        for key, info in THEMES.items():
            name = info.get("name", key)
            # 去掉开头 emoji（如有）用于菜单显示
            if name and ord(name[0]) > 255:
                name = name[2:] if len(name) > 2 and name[1] == " " else name[1:]
            act = QAction(name, self)
            act.setData(key)
            act.setCheckable(False)
            act.triggered.connect(lambda checked=False, k=key: self._set_theme(k))
            menu.addAction(act)
        try:
            widget = self._toolbar.widgetForAction(self._theme_action)
            if widget:
                menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
            else:
                menu.exec(self.mapToGlobal(self.rect().center()))
        except Exception:
            menu.exec(self.mapToGlobal(self.rect().center()))

    def _set_theme(self, key: str) -> None:
        self._current_theme = key
        self._apply_theme()
        self._display_chapter()
        self._save_settings()

    def _open_format_dialog(self) -> None:
        # 使用菜单显示排版操作，点击不会关闭菜单（保持显示）
        menu = QMenu(self)
        self._make_menu_compact(menu)
        from PyQt6.QtWidgets import QPushButton

        ops = [
            ("放大字号", self._zoom_in),
            ("缩小字号", self._zoom_out),
            ("增大行距", self._increase_line_spacing),
            ("减小行距", self._decrease_line_spacing),
            ("增大段距", self._increase_paragraph_spacing),
            ("减小段距", self._decrease_paragraph_spacing),
        ]
        for label, cb in ops:
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setStyleSheet("text-align: left; padding: 4px 12px;")
            btn.clicked.connect(cb)
            action = QWidgetAction(menu)
            action.setDefaultWidget(btn)
            menu.addAction(action)
        # 在工具栏按钮下方弹出菜单
        try:
            widget = self._toolbar.widgetForAction(self._format_action)
            if widget:
                menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
            else:
                menu.exec(self.mapToGlobal(self.rect().center()))
        except Exception:
            menu.exec(self.mapToGlobal(self.rect().center()))

    # ==================== 文件操作 ====================

    def _open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 EPUB 文件", "", "EPUB 文件 (*.epub);;所有文件 (*.*)"
        )
        if path:
            self._open_file(path)

    def _open_file(self, path: str) -> None:
        status_bar = self.statusBar()
        assert status_bar is not None
        status_bar.showMessage("⏳ 正在加载...")

        success, result = self._loader.load_file(path)

        if success:
            self._last_opened = path
            self.setWindowTitle(f"EPUB 阅读器 - {result}")
            self._update_toc()
            if self._loader.chapter_count() > 0:
                self._current_chapter = min(
                    self._current_chapter, self._loader.chapter_count() - 1
                )
                self._display_chapter()
            status_bar.showMessage(f"✅ 已打开: {os.path.basename(path)}")
            self._save_settings()
        else:
            QMessageBox.critical(self, "打开失败", f"无法打开文件:\n{result}")
            status_bar.showMessage("❌ 打开失败")

    def _reopen_last(self) -> None:
        if self._last_opened and os.path.exists(self._last_opened):
            self._open_file(self._last_opened)

    # ==================== 目录与章节 ====================

    def _update_toc(self) -> None:
        """更新目录树，支持嵌套结构"""
        self._toc_tree.clear()
        
        # 使用新的扁平化目录
        toc_items = self._loader.get_flat_toc()
        
        for item in toc_items:
            title = item['title']
            level = item['level']
            chapter_idx = item['chapter_idx']
            
            tree_item = QTreeWidgetItem(self._toc_tree, [title])
            tree_item.setToolTip(0, title)
            
            # 保存章节索引到用户数据
            if chapter_idx is not None:
                tree_item.setData(0, Qt.ItemDataRole.UserRole, chapter_idx)
            
            # 设置缩进级别
            #self._toc_tree.setIndentation(15 * max(0, level))  # 可选：自动缩进
        
        self._update_toc_selection()
        
        # 更新章节计数
        total = self._loader.chapter_count()
        if self._chapter_label:
            self._chapter_label.setText(f"{total} 章")

    def _on_toc_click(self, item: QTreeWidgetItem) -> None:
        """目录项点击处理"""
        # 从用户数据获取章节索引
        chapter_idx = item.data(0, Qt.ItemDataRole.UserRole)
        
        if chapter_idx is not None:
            idx = chapter_idx
        else:
            # 回退到旧方法
            idx = self._toc_tree.indexOfTopLevelItem(item)
        
        if idx is not None and 0 <= idx < self._loader.chapter_count() and idx != self._current_chapter:
            self._current_chapter = idx
            # 由目录跳转视为导航操作，从章节顶部显示
            self._display_chapter(preserve_position=False)

    def _update_toc_selection(self) -> None:
        """在目录中选中与当前章节对应的项（优先匹配保存的 chapter_idx）。

        在使用扁平化目录时，TOC 项的数量与章节数量可能不一一对应，直接按索引选中会导致错位，
        因此先查找具有匹配 `chapter_idx` 的项；若未找到则尝试按索引回退到最接近的项。
        """
        count = self._toc_tree.topLevelItemCount()
        found_item = None

        # 优先查找存储了 chapter_idx 且等于当前章节的项
        for i in range(count):
            it = self._toc_tree.topLevelItem(i)
            try:
                chapter_idx = it.data(0, Qt.ItemDataRole.UserRole)
            except Exception:
                chapter_idx = None
            if chapter_idx == self._current_chapter:
                found_item = it
                break

        # 回退策略：如果没有找到匹配项，按索引尝试选中（如果索引在范围内），否则选中最后一项
        if not found_item and count > 0:
            if 0 <= self._current_chapter < count:
                found_item = self._toc_tree.topLevelItem(self._current_chapter)
            else:
                # 选中最接近的有效项
                idx = max(0, min(count - 1, self._current_chapter))
                found_item = self._toc_tree.topLevelItem(idx)

        if found_item:
            self._toc_tree.setCurrentItem(found_item)
            self._toc_tree.scrollToItem(found_item)

    def _display_chapter(self, preserve_position: bool = True) -> None:
        """渲染当前章节内容。

        preserve_position=True 时会尽量恢复当前页面的滚动位置（按文档高度的比例），
        以保证在修改字体/主题/行距等显示设置时用户的位置不发生明显跳转；
        当 preserve_position=False（通常由导航操作触发）时，从章节顶部开始显示。
        """
        content = self._loader.get_chapter_content(self._current_chapter)
        page = self._browser.page()
        chapter_idx = self._current_chapter

        # 如果无法获取 page（极少数环境或初始化阶段），直接渲染并返回
        if page is None:
            colors = self._get_colors()
            font_size = max(12, int(self._font_size * self._font_scale))
            html = generate_html_style(
                colors,
                self._font_family,
                font_size,
                self._line_spacing,
                self._paragraph_spacing,
            )
            html += _MOUSE_HANDLER_JS + (content or "") + "</body></html>"
            self._browser.setHtml(html)
            self._loader.preload_chapters(self._current_chapter)
            total = self._loader.chapter_count()
            if self._progress_label:
                self._progress_label.setText(f" {self._current_chapter + 1}/{total} ")
            self._update_toc_selection()
            return

        def _set_html_and_restore(ratio: float):
            try:
                ratio = float(ratio) if ratio is not None else 0.0
            except Exception:
                ratio = 0.0

            colors = self._get_colors()
            font_size = max(12, int(self._font_size * self._font_scale))
            html = generate_html_style(
                colors,
                self._font_family,
                font_size,
                self._line_spacing,
                self._paragraph_spacing,
            )
            html += _MOUSE_HANDLER_JS + (content or "") + "</body></html>"

            # 记录是否要恢复滚动（按比例）
            if preserve_position:
                self._pending_scroll_ratio = ratio
                self._pending_scroll_chapter = chapter_idx
            else:
                self._pending_scroll_ratio = None
                self._pending_scroll_chapter = None

            # 设置内容并预加载相邻章节
            self._browser.setHtml(html)
            self._loader.preload_chapters(self._current_chapter)

            # 页面加载完成后恢复滚动位置（一次性尝试 + 轻微延迟重复以提高成功率）
            def _on_load(ok: bool):
                try:
                    if not preserve_position or self._pending_scroll_ratio is None:
                        return
                    if self._pending_scroll_chapter != self._current_chapter:
                        return

                    ratio_local = max(0.0, min(1.0, float(self._pending_scroll_ratio)))
                    js_set = f"""
                    (function(){{
                        try {{
                            var h = document.documentElement.scrollHeight || document.body.scrollHeight;
                            var win = window.innerHeight || document.documentElement.clientHeight;
                            var y = 0;
                            if (h - win > 0) y = Math.round({ratio_local} * (h - win));
                            window.scrollTo(0, y);
                            return y;
                        }} catch(e) {{ return 0; }}
                    }})()
                    """

                    page.runJavaScript(js_set, lambda _: None)
                    QTimer.singleShot(60, lambda: page.runJavaScript(js_set, lambda _: None))
                finally:
                    try:
                        page.loadFinished.disconnect(_on_load)
                    except Exception:
                        pass

            page.loadFinished.connect(_on_load)

        if content is None:
            # 无内容时仍需更新进度和 TOC 选择
            total = self._loader.chapter_count()
            if self._progress_label:
                self._progress_label.setText(f" {self._current_chapter + 1}/{total} ")
            self._update_toc_selection()
            return

        if preserve_position:
            # 先获取当前页面的滚动比例，再渲染新内容并尝试恢复
            js_get = """
            (function(){
                try{
                    var h = document.documentElement.scrollHeight || document.body.scrollHeight;
                    var win = window.innerHeight || document.documentElement.clientHeight;
                    var y = window.scrollY || window.pageYOffset || 0;
                    var ratio = (h - win > 0) ? (y / (h - win)) : 0;
                    return ratio;
                } catch(e) { return 0; }
            })()
            """
            try:
                page.runJavaScript(js_get, _set_html_and_restore)
            except Exception:
                _set_html_and_restore(0.0)
        else:
            _set_html_and_restore(0.0)

        # 更新进度与 TOC 选择
        total = self._loader.chapter_count()
        if self._progress_label:
            self._progress_label.setText(f" {self._current_chapter + 1}/{total} ")
        self._update_toc_selection()

    def _goto_chapter(self, index: int) -> None:
        if 0 <= index < self._loader.chapter_count():
            self._current_chapter = index
            # 程序化跳转也从章节顶部开始
            self._display_chapter(preserve_position=False)

    # ==================== 导航 ====================

    def prev_chapter(self) -> None:
        if self._current_chapter > 0:
            self._current_chapter -= 1
            # 导航到上一章时从章节顶部开始显示
            self._display_chapter(preserve_position=False)

    def next_chapter(self) -> None:
        if self._current_chapter < self._loader.chapter_count() - 1:
            self._current_chapter += 1
            # 导航到下一章时从章节顶部开始显示
            self._display_chapter(preserve_position=False)

    def _toggle_toc(self) -> None:
        self._toc_visible = not self._toc_visible
        self._toc_widget.setVisible(self._toc_visible)

    # ==================== 显示设置 ====================

    def _zoom_in(self) -> None:
        self._font_scale = min(2.0, self._font_scale + 0.1)
        self._display_chapter()
        self._save_settings()

    def _zoom_out(self) -> None:
        self._font_scale = max(0.5, self._font_scale - 0.1)
        self._display_chapter()
        self._save_settings()

    def _increase_line_spacing(self) -> None:
        self._line_spacing = min(3.0, self._line_spacing + 0.1)
        self._display_chapter()
        self._save_settings()

    def _decrease_line_spacing(self) -> None:
        self._line_spacing = max(1.2, self._line_spacing - 0.1)
        self._display_chapter()
        self._save_settings()

    def _increase_paragraph_spacing(self) -> None:
        self._paragraph_spacing = min(3.0, self._paragraph_spacing + 0.2)
        self._display_chapter()
        self._save_settings()

    def _decrease_paragraph_spacing(self) -> None:
        self._paragraph_spacing = max(0.4, self._paragraph_spacing - 0.2)
        self._display_chapter()
        self._save_settings()

    def _toggle_images(self) -> None:
        self._show_images = not self._show_images
        self._loader.set_image_visibility(self._show_images)
        self._display_chapter()
        self._save_settings()

    def _toggle_reading_mode(self) -> None:
        self._reading_mode = not self._reading_mode
        if self._reading_btn:
            # 切换图标与标签
            try:
                icon = self._emoji_icon("📕" if self._reading_mode else "📖", size=18)
                self._reading_btn.setIcon(icon)
            except Exception:
                pass
            self._reading_btn.setText("阅读中" if self._reading_mode else "阅读模式")
            self._reading_btn.setToolTip(
                "关闭阅读模式" if self._reading_mode else "开启阅读模式 (Ctrl+M)"
            )

        status_bar = self.statusBar()
        if status_bar:
            if self._reading_mode:
                status_bar.showMessage("📖 阅读模式已开启 - 左键下一章，右键上一章")
            else:
                status_bar.showMessage("阅读模式已关闭")
        self._save_settings()

    def _choose_font(self) -> None:
        # 使用下拉菜单实现字体选择（包含搜索）
        if not hasattr(self, "_font_menu"):
            self._create_font_menu()
        try:
            widget = self._toolbar.widgetForAction(self._font_action)
            if widget:
                self._font_menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
            else:
                self._font_menu.exec(self.mapToGlobal(self.rect().center()))
        except Exception:
            self._font_menu.exec(self.mapToGlobal(self.rect().center()))

    def _create_font_menu(self) -> None:
        self._font_menu = QMenu(self)
        self._make_menu_compact(self._font_menu)
        container = QWidget()
        # 减少容器内间距以实现紧凑显示
        container.setStyleSheet("QWidget { padding: 0px; margin: 0px; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        # 小号字体以节省空间
        small_font = QFont(self.DEFAULT_FONT, 11)
        # 搜索框
        search = QLineEdit()
        search.setPlaceholderText("搜索字体...")
        search.setFixedHeight(26)
        search.setFont(small_font)
        layout.addWidget(search)
        # 字体列表（每项用自身字体渲染，变长一些以便预览）
        from PyQt6.QtWidgets import QListWidgetItem

        font_list = QListWidget()
        font_list.setFont(small_font)
        font_list.setSpacing(2)
        colors = self._get_colors()
        select_bg = colors.get("select_bg", "#0078d7")
        select_fg = colors.get("select_fg", "#ffffff")
        fg = colors.get("fg", "#000000")
        bg = colors.get("content_bg", "#ffffff")
        hover_bg = colors.get("hover_bg", select_bg)
        hover_fg = colors.get("hover_fg", select_fg)
        font_list.setStyleSheet(
            f"QListWidget::item {{ padding: 4px 8px; min-height: 22px; color: {fg}; background: {bg}; }}"
            f"QListWidget::item:selected {{ background: {select_bg}; color: {select_fg}; }}"
            f"QListWidget::item:hover {{ background: {hover_bg}; color: {hover_fg}; }}"
        )
        font_list.setMouseTracking(True)
        all_fonts = sorted(
            [f for f in QFontDatabase.families() if not f.startswith("@")]
        )

        def populate(names):
            font_list.clear()
            for name in names:
                it = QListWidgetItem(name)
                it.setFont(QFont(name, 14))
                it.setSizeHint(QSize(360, 26))
                font_list.addItem(it)

        populate(all_fonts)
        font_list.setFixedWidth(420)
        font_list.setMinimumHeight(min(800, 26 * len(all_fonts)))
        layout.addWidget(font_list)

        # 点击或双击选中
        def on_select(item):
            name = item.text()
            self._font_family = name
            self._display_chapter()
            self._save_settings()
            self._font_menu.hide()

        font_list.itemClicked.connect(on_select)
        font_list.itemDoubleClicked.connect(on_select)

        # 过滤
        def on_search(text: str):
            filtered = [f for f in all_fonts if text.lower() in f.lower()]
            populate(filtered)

        search.textChanged.connect(on_search)
        # 将容器嵌入 QMenu 作为 QWidgetAction，以实现复杂布局的下拉菜单
        action = QWidgetAction(self._font_menu)
        action.setDefaultWidget(container)
        self._font_menu.addAction(action)

    def _choose_theme(self) -> None:
        # 打开主题选择（使用统一的对话/菜单入口）
        try:
            self._open_theme_dialog()
        except Exception:
            pass

    # ==================== 设置持久化 ====================

    def _save_settings(self) -> None:
        self._settings.save(
            {
                "last_opened": self._last_opened,
                "current_chapter": self._current_chapter,
                "current_theme": self._current_theme,
                "font_family": self._font_family,
                "font_scale": self._font_scale,
                "line_spacing": self._line_spacing,
                "paragraph_spacing": self._paragraph_spacing,
                "show_images": self._show_images,
                "reading_mode": self._reading_mode,
                "toc_visible": self._toc_visible,
                "window_geometry": self.saveGeometry().toHex().data().decode(),
            }
        )

    def _load_settings(self) -> None:
        data = self._settings.load()
        if not data:
            return

        self._last_opened = data.get("last_opened")
        self._current_chapter = data.get("current_chapter", 0)
        self._current_theme = data.get("current_theme", self.DEFAULT_THEME)
        self._font_family = data.get("font_family", self.DEFAULT_FONT)
        self._font_scale = data.get("font_scale", 1.0)
        self._line_spacing = data.get("line_spacing", 1.8)
        self._paragraph_spacing = data.get("paragraph_spacing", 1.2)
        self._show_images = data.get("show_images", True)
        self._reading_mode = data.get("reading_mode", False)
        self._toc_visible = data.get("toc_visible", True)

        self._loader.set_image_visibility(self._show_images)
        self._toc_widget.setVisible(self._toc_visible)

        if self._reading_btn:
            try:
                icon = self._emoji_icon("📕" if self._reading_mode else "📖", size=18)
                self._reading_btn.setIcon(icon)
            except Exception:
                pass
            self._reading_btn.setText("阅读中" if self._reading_mode else "阅读模式")

        if "window_geometry" in data:
            from PyQt6.QtCore import QByteArray

            self.restoreGeometry(QByteArray.fromHex(data["window_geometry"].encode()))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._maybe_update_toolbar_compact()

    def closeEvent(self, event) -> None:
        self._save_settings()
        event.accept()
