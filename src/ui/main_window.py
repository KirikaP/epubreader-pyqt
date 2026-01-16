"""Main window (UI and interaction)"""

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


# JavaScript code: mouse click detection in reading mode
_MOUSE_HANDLER_JS = """
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {
    new QWebChannel(qt.webChannelTransport, function(channel) {
        window.bridge = channel.objects.bridge;
    });
});
// Ignore clicks on the scrollbar area (prevent page turning when the scrollbar is clicked)
document.addEventListener('mousedown', function(e) {
    try {
        var scrollbarWidth = window.innerWidth - (document.documentElement.clientWidth || document.body.clientWidth || 0);
        // If computed scrollbar width > 0 and click is within the scrollbar area on the right, ignore the event
        if (scrollbarWidth > 0 && e.clientX >= window.innerWidth - scrollbarWidth) {
            return;
        }
    } catch (err) {
        // On error, do not interfere with normal click handling
    }

    // Ignore clicks on editable input controls
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
    """EPUB Reader main window - modern design"""

    # Default settings
    DEFAULT_FONT = "Microsoft YaHei"
    DEFAULT_FONT_SIZE = 16
    DEFAULT_THEME = "light"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB 阅读器")
        self.resize(1280, 800)

        # Core services and resource initialization
        self._loader = EpubLoader()
        self._settings = SettingsManager()
        self._web_bridge = WebBridge(self)

        # Reading state
        self._current_chapter = 0
        self._last_opened: Optional[str] = None

        # Toolbar items tracking (for compact mode toggling)
        self._toolbar_items: list[tuple] = []  # (item, label, emoji)
        self._compact_threshold = 520
        self._compact_mode = False

        # Display and typography settings
        self._current_theme = self.DEFAULT_THEME
        self._font_family = self.DEFAULT_FONT
        self._font_size = self.DEFAULT_FONT_SIZE
        self._font_scale = 1.0
        self._line_spacing = 1.8
        self._paragraph_spacing = 1.2
        self._show_images = True
        self._reading_mode = False
        self._toc_visible = True

        # Temporarily save scroll info to restore reading position after display changes (per-chapter)
        self._pending_scroll_ratio: Optional[float] = None
        self._pending_scroll_chapter: Optional[int] = None

        # UI component references (handles for later updates)
        self._reading_btn: Optional[QAction] = None
        self._progress_label: Optional[QLabel] = None
        self._chapter_label: Optional[QLabel] = None
        self._toc_header: Optional[QLabel] = None

        self._setup_ui()
        self._setup_shortcuts()
        self._load_settings()
        self._apply_theme()

        # Auto-open last file
        if self._last_opened and os.path.exists(self._last_opened):
            file_path = self._last_opened
            QTimer.singleShot(100, lambda: self._open_file(file_path))

    # ==================== Properties ====================

    @property
    def reading_mode(self) -> bool:
        return self._reading_mode

    # ==================== UI Initialization ====================

    def _setup_ui(self) -> None:
        """Initialize main UI layout"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main splitter (left TOC / right content)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)
        layout.addWidget(self._splitter)

        # Left TOC panel
        self._toc_widget = self._create_toc_panel()
        self._splitter.addWidget(self._toc_widget)

        # Right content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._browser = QWebEngineView()
        content_layout.addWidget(self._browser)

        self._splitter.addWidget(content_widget)

        # WebChannel communication
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
        """Create the table of contents panel"""
        panel = QWidget()
        panel.setMinimumWidth(120)
        panel.setMaximumWidth(350)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # TOC header (display title and chapter count)
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

        # Divider line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFixedHeight(1)
        layout.addWidget(line)

        # TOC tree
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
        """Build and populate the toolbar"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._toolbar = toolbar
        self.addToolBar(toolbar)

        # File button - open directly
        self._add_action(
            toolbar, "📂 打开", "打开文件 (Ctrl+O)", self._open_file_dialog
        )

        toolbar.addSeparator()

        # Navigation buttons group
        self._add_action(toolbar, "⬅️ 上一章", "上一章 (←)", self.prev_chapter)
        self._add_action(toolbar, "➡️ 下一章", "下一章 (→)", self.next_chapter)

        toolbar.addSeparator()

        # View buttons group
        self._add_action(toolbar, "📑 目录", "显示/隐藏目录 (Ctrl+T)", self._toggle_toc)
        self._add_action(
            toolbar, "🖼️ 图片", "显示/隐藏图片 (Ctrl+I)", self._toggle_images
        )

        toolbar.addSeparator()

        # Formatting (managed by QAction)
        self._format_action = self._add_action(
            toolbar, "📐 排版", "排版", self._open_format_dialog
        )
        # Settings button - font selection becomes a dropdown
        self._font_action = self._add_action(
            toolbar, "🔤 字体", "选择字体", self._choose_font
        )
        # Theme (managed by QAction, labels support trailing arrow)
        self._theme_action = self._add_action(
            toolbar, "🎨 主题", "选择主题", self._open_theme_dialog
        )

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Reading mode button (right side)
        self._reading_btn = self._add_action(
            toolbar, "📖 阅读模式", "切换阅读模式 (Ctrl+M)", self._toggle_reading_mode
        )

    def _add_action(self, toolbar: QToolBar, full_text: str, tip: str, callback):
        """Add a toolbar QAction (supports emoji icon and text toggling). Returns QAction."""
        # Parse emoji (before the first space) and label (rest after emoji)
        parts = full_text.split(" ", 1)
        emoji = parts[0]
        label = parts[1] if len(parts) > 1 else ""
        # Create QAction and save base label and emoji for later refresh
        action = toolbar.addAction(label, callback)
        assert action is not None
        action.setToolTip(tip)
        try:
            icon = self._emoji_icon(emoji, size=18)
            action.setIcon(icon)
        except Exception:
            pass
        # Save for display toggling (item, label, emoji)
        self._toolbar_items.append((action, label, emoji))
        return action

    def _emoji_icon(self, emoji: str, size: int = 18) -> QIcon:
        """Render an emoji as QIcon for toolbar icons."""
        pix = QPixmap(size, size)
        # Transparent background
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
        """Add a QPushButton to a menu without closing it (for repeated actions)."""
        from PyQt6.QtWidgets import QPushButton

        parts = text.split(" ", 1)
        emoji = parts[0]
        label = parts[1] if len(parts) > 1 else ""
        btn = QPushButton(label)
        btn.setFlat(True)
        btn.setStyleSheet("text-align: left; padding: 6px 16px;")
        btn.clicked.connect(callback)
        # Set icon so compact mode shows icon only
        try:
            btn.setIcon(self._emoji_icon(emoji, size=18))
        except Exception:
            pass
        action = QWidgetAction(menu)
        action.setDefaultWidget(btn)
        menu.addAction(action)
        # Also record the button as part of toolbar items (for toggling text/icon)
        self._toolbar_items.append((btn, label, emoji))

    def _maybe_update_toolbar_compact(self) -> None:
        """Toggle toolbar display mode (icon only or icon+text) based on window width."""
        width = self.width()
        want_compact = width <= self._compact_threshold
        if want_compact == self._compact_mode:
            return
        self._compact_mode = want_compact
        if want_compact:
            # Icon only
            self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        else:
            # Icon + text
            self._toolbar.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextBesideIcon
            )
        # Refresh all labels; centralize text display management
        self._refresh_toolbar_labels()

    def _safe(self, fn, *args, **kwargs):
        """Safe call wrapper: catch exceptions and return None to simplify error handling."""
        try:
            return fn(*args, **kwargs)
        except Exception:
            return None

    def _refresh_toolbar_items(self) -> None:
        """Refresh toolbar icons and labels (handle compact mode and theme changes)."""
        for item, label, emoji in self._toolbar_items:
            # Text handling
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
            # Icon handling (always refresh to reflect theme colors)
            try:
                icon = self._emoji_icon(emoji, size=18)
            except Exception:
                icon = None
            if icon is not None:
                self._safe(getattr(item, "setIcon", lambda *_: None), icon)
        # Ensure format action text aligns with compact mode
        fa = getattr(self, "_format_action", None)
        if fa is not None:
            self._safe(fa.setText, "排版" if not self._compact_mode else "")

    # Backwards compatibility: keep old name but reuse unified implementation
    def _refresh_toolbar_labels(self) -> None:
        self._refresh_toolbar_items()

    def _refresh_toolbar_icons(self) -> None:
        self._refresh_toolbar_items()

    def _create_status_bar(self) -> None:
        """Initialize status bar and add progress display"""
        status_bar = self.statusBar()
        assert status_bar is not None

        # Progress label
        self._progress_label = QLabel(" 0/0 ")
        self._progress_label.setFont(QFont(self.DEFAULT_FONT, 9))
        status_bar.addPermanentWidget(self._progress_label)

        status_bar.showMessage("欢迎使用 EPUB 阅读器")
        # Initially update toolbar display mode (delayed to ensure window size is settled)
        QTimer.singleShot(200, self._maybe_update_toolbar_compact)
        # Initially refresh labels to ensure button text displays correctly (delayed to allow layout)
        QTimer.singleShot(250, self._refresh_toolbar_labels)
        # Initially generate icons to ensure theme colors apply
        QTimer.singleShot(
            250, lambda: getattr(self, "_refresh_toolbar_icons", lambda: None)()
        )

    def _setup_shortcuts(self) -> None:
        """Register global keyboard shortcuts."""
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
        # Toolbar display mode needs updating on window resize
        # Implemented by overriding resizeEvent

    # ==================== Theme ====================

    def _apply_theme(self) -> None:
        """Apply current theme to the application stylesheet and refresh the toolbar."""
        colors = THEMES.get(self._current_theme, THEMES["light"])
        self.setStyleSheet(get_stylesheet(colors))
        # Update theme action text to show current theme name (if present)
        try:
            if hasattr(self, "_theme_action"):
                name = THEMES.get(self._current_theme, THEMES["light"])["name"]
                # Strip possible leading emoji
                if name and ord(name[0]) > 255:
                    name = name[2:] if len(name) > 2 and name[1] == " " else name[1:]
                try:
                    self._theme_action.setText(name)
                except Exception:
                    self._theme_action.setText(name)
        except Exception:
            pass
        # Regenerate emoji icons to reflect theme colors/arrows and refresh labels
        try:
            self._refresh_toolbar_icons()
            self._refresh_toolbar_labels()
        except Exception:
            # If synchronous updates fail, use delayed updates to keep UI stable
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
        """Called when a theme menu item is selected"""
        key = action.data()
        if not key:
            return
        self._current_theme = key
        # Set action as checked (exclusive behavior handled by QActionGroup)
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
        """After window shows, refresh toolbar state to ensure labels render correctly"""
        super().showEvent(event)
        QTimer.singleShot(50, self._maybe_update_toolbar_compact)
        QTimer.singleShot(80, self._refresh_toolbar_labels)
        QTimer.singleShot(
            80, lambda: getattr(self, "_refresh_toolbar_icons", lambda: None)()
        )

    def _open_theme_dialog(self) -> None:
        # Show theme options using a menu anchored to the toolbar action
        menu = QMenu(self)
        for key, info in THEMES.items():
            name = info.get("name", key)
            # Remove leading emoji (if any) for menu display
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
        # Use a menu to present formatting operations; clicks do not close the menu (remain open)
        menu = QMenu(self)
        self._make_menu_compact(menu)
        from PyQt6.QtWidgets import QPushButton

        ops = [
            ("Increase font size", self._zoom_in),
            ("Decrease font size", self._zoom_out),
            ("Increase line spacing", self._increase_line_spacing),
            ("Decrease line spacing", self._decrease_line_spacing),
            ("Increase paragraph spacing", self._increase_paragraph_spacing),
            ("Decrease paragraph spacing", self._decrease_paragraph_spacing),
        ]
        for label, cb in ops:
            btn = QPushButton(label)
            btn.setFlat(True)
            btn.setStyleSheet("text-align: left; padding: 4px 12px;")
            btn.clicked.connect(cb)
            action = QWidgetAction(menu)
            action.setDefaultWidget(btn)
            menu.addAction(action)
        # Pop up menu under toolbar button
        try:
            widget = self._toolbar.widgetForAction(self._format_action)
            if widget:
                menu.exec(widget.mapToGlobal(widget.rect().bottomLeft()))
            else:
                menu.exec(self.mapToGlobal(self.rect().center()))
        except Exception:
            menu.exec(self.mapToGlobal(self.rect().center()))

    # ==================== File operations ====================

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

    # ==================== Table of Contents & Chapters ====================

    def _update_toc(self) -> None:
        """Update the TOC tree; supports nested structure"""
        self._toc_tree.clear()
        
        # Use the new flattened TOC
        toc_items = self._loader.get_flat_toc()
        
        for item in toc_items:
            title = item['title']
            level = item['level']
            chapter_idx = item['chapter_idx']
            
            tree_item = QTreeWidgetItem(self._toc_tree, [title])
            tree_item.setToolTip(0, title)
            
            # Save chapter index to user data
            if chapter_idx is not None:
                tree_item.setData(0, Qt.ItemDataRole.UserRole, chapter_idx)
            
            # Set indentation level
            #self._toc_tree.setIndentation(15 * max(0, level))  # Optional: automatic indentation
        
        self._update_toc_selection()
        
        # Update chapter count
        total = self._loader.chapter_count()
        if self._chapter_label:
            self._chapter_label.setText(f"{total} 章")

    def _on_toc_click(self, item: QTreeWidgetItem) -> None:
        """Handle TOC item click"""
        # Get chapter index from user data
        chapter_idx = item.data(0, Qt.ItemDataRole.UserRole)
        
        if chapter_idx is not None:
            idx = chapter_idx
        else:
            # Fallback to old method
            idx = self._toc_tree.indexOfTopLevelItem(item)
        
        if idx is not None and 0 <= idx < self._loader.chapter_count() and idx != self._current_chapter:
            self._current_chapter = idx
            # Treat click navigation as an explicit navigation; display from top of chapter
            self._display_chapter(preserve_position=False)

    def _update_toc_selection(self) -> None:
        """Select the TOC item that corresponds to the current chapter.

        For flattened TOCs the number of TOC entries may not match chapter count, so selecting by
        index alone can be misaligned. Prefer matching items that store a `chapter_idx`; if none
        match, fall back to selecting by index (or the nearest valid item).
        """
        count = self._toc_tree.topLevelItemCount()
        found_item = None

        # Prefer items that store a chapter_idx matching the current chapter
        for i in range(count):
            it = self._toc_tree.topLevelItem(i)
            try:
                chapter_idx = it.data(0, Qt.ItemDataRole.UserRole)
            except Exception:
                chapter_idx = None
            if chapter_idx == self._current_chapter:
                found_item = it
                break

        # Fallback strategy: if no matching item is found, try selecting by index (if in range), otherwise select the last item
        if not found_item and count > 0:
            if 0 <= self._current_chapter < count:
                found_item = self._toc_tree.topLevelItem(self._current_chapter)
            else:
                # Select the nearest valid item
                idx = max(0, min(count - 1, self._current_chapter))
                found_item = self._toc_tree.topLevelItem(idx)

        if found_item:
            self._toc_tree.setCurrentItem(found_item)
            self._toc_tree.scrollToItem(found_item)

    def _display_chapter(self, preserve_position: bool = True) -> None:
        """Render the current chapter.

        When preserve_position=True, attempt to restore the current page scroll position (as a proportion of document height)
        to avoid large jumps when changing font/theme/line spacing settings.
        When preserve_position=False (typically triggered by navigation), display from the top of the chapter.
        """
        content = self._loader.get_chapter_content(self._current_chapter)
        page = self._browser.page()
        chapter_idx = self._current_chapter

        # If page is unavailable (rare environments or during init), render directly and return
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

            # Record whether to restore scroll (by ratio)
            if preserve_position:
                self._pending_scroll_ratio = ratio
                self._pending_scroll_chapter = chapter_idx
            else:
                self._pending_scroll_ratio = None
                self._pending_scroll_chapter = None

            # Set content and preload adjacent chapters
            self._browser.setHtml(html)
            self._loader.preload_chapters(self._current_chapter)

            # Restore scroll position after page load (attempt once + slightly delayed repeat to improve success rate)
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
            # Even if content is missing, update progress and TOC selection
            total = self._loader.chapter_count()
            if self._progress_label:
                self._progress_label.setText(f" {self._current_chapter + 1}/{total} ")
            self._update_toc_selection()
            return

        if preserve_position:
            # First get current page scroll ratio, then render new content and try to restore
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

        # Update progress and TOC selection
        total = self._loader.chapter_count()
        if self._progress_label:
            self._progress_label.setText(f" {self._current_chapter + 1}/{total} ")
        self._update_toc_selection()

    def _goto_chapter(self, index: int) -> None:
        if 0 <= index < self._loader.chapter_count():
            self._current_chapter = index
            # Programmatic jumps also start from chapter top
            self._display_chapter(preserve_position=False)

    # ==================== 导航 ====================

    def prev_chapter(self) -> None:
        if self._current_chapter > 0:
            self._current_chapter -= 1
            # When navigating to previous chapter, display from chapter top
            self._display_chapter(preserve_position=False)

    def next_chapter(self) -> None:
        if self._current_chapter < self._loader.chapter_count() - 1:
            self._current_chapter += 1
            # When navigating to next chapter, display from chapter top
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
            # Toggle icon and label
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
        # Implement font selection with a dropdown (includes search)
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
        # Reduce container padding for compact display
        container.setStyleSheet("QWidget { padding: 0px; margin: 0px; }")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        # Small font to save space
        small_font = QFont(self.DEFAULT_FONT, 11)
        # Search box
        search = QLineEdit()
        search.setPlaceholderText("搜索字体...")
        search.setFixedHeight(26)
        search.setFont(small_font)
        layout.addWidget(search)
        # Font list (each item rendered in its own font for preview)
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

        # Click or double-click to select
        def on_select(item):
            name = item.text()
            self._font_family = name
            self._display_chapter()
            self._save_settings()
            self._font_menu.hide()

        font_list.itemClicked.connect(on_select)
        font_list.itemDoubleClicked.connect(on_select)

        # Filtering
        def on_search(text: str):
            filtered = [f for f in all_fonts if text.lower() in f.lower()]
            populate(filtered)

        search.textChanged.connect(on_search)
        # Embed container into QMenu as QWidgetAction for complex dropdown layout
        action = QWidgetAction(self._font_menu)
        action.setDefaultWidget(container)
        self._font_menu.addAction(action)

    def _choose_theme(self) -> None:
        # Open theme selector (using unified dialog/menu entry)
        try:
            self._open_theme_dialog()
        except Exception:
            pass

    # ==================== Settings persistence ====================

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
