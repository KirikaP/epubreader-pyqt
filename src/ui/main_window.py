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
    QLineEdit,
    QListWidget,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QAction, QFont, QShortcut, QKeySequence, QFontDatabase
from PyQt6.QtWebChannel import QWebChannel

from src.core.epub_loader import EpubLoader
from src.core.settings import SettingsManager
from src.core.themes import THEMES, get_stylesheet, generate_html_style
from src.ui.web_bridge import WebBridge


# JavaScript code: mouse click detection in reading mode (loaded from external file)
def _load_js(name: str) -> str:
    try:
        base = os.path.join(os.path.dirname(__file__), "js")
        path = os.path.join(base, name)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            # Wrap the JS in <script> tags so it is interpreted by the browser,
            # and include the qwebchannel loader script reference.
            return (
                '<script src="qrc:///qtwebchannel/qwebchannel.js"></script>\n'
                '<script>\n'
                f"{content}\n"
                '</script>\n'
            )
    except Exception:
        return ""

_MOUSE_HANDLER_JS = _load_js("mouse_handler.js")
_SCROLL_JS = _load_js("scroll_restore.js")


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
        self._toolbar_items: list[tuple] = []  # (item, label)
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
        self._menu_open = False

        # Temporarily save scroll info to restore reading position after display changes (per-chapter)
        self._pending_scroll_ratio: Optional[float] = None
        self._pending_scroll_chapter: Optional[int] = None

        # HTML style cache (to avoid regenerating on every chapter render)
        self._cached_html_style: Optional[str] = None
        self._cached_style_key: Optional[tuple] = None

        # Font list cache (lazy loading)
        self._all_fonts: Optional[list] = None

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

    @property
    def menu_open(self) -> bool:
        return self._menu_open

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
            toolbar, "打开", "打开文件 (Ctrl+O)", self._open_file_dialog
        )

        toolbar.addSeparator()

        # Navigation buttons group
        self._add_action(toolbar, "上一章", "上一章 (←)", self.prev_chapter)
        self._add_action(toolbar, "下一章", "下一章 (→)", self.next_chapter)

        toolbar.addSeparator()

        # View buttons group
        self._add_action(toolbar, "目录", "显示/隐藏目录 (Ctrl+T)", self._toggle_toc)
        self._add_action(
            toolbar, "图片", "显示/隐藏图片 (Ctrl+I)", self._toggle_images
        )

        toolbar.addSeparator()

        # Formatting (managed by QAction)
        self._format_action = self._add_action(
            toolbar, "排版", "排版", self._open_format_dialog
        )
        # Settings button - font selection becomes a dropdown
        self._font_action = self._add_action(
            toolbar, "字体", "选择字体", self._choose_font
        )
        # Theme (managed by QAction, labels support trailing arrow)
        self._theme_action = self._add_action(
            toolbar, "主题", "选择主题", self._open_theme_dialog
        )

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        # Reading mode button (right side)
        self._reading_btn = self._add_action(
            toolbar, "阅读模式", "切换阅读模式 (Ctrl+M)", self._toggle_reading_mode
        )

    def _add_action(self, toolbar: QToolBar, label: str, tip: str, callback) -> QAction:
        """Add a toolbar QAction. Returns QAction."""
        action = toolbar.addAction(label, callback)
        assert action is not None
        action.setToolTip(tip)
        # Save for display toggling (item, label)
        self._toolbar_items.append((action, label))
        return action

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
        """Refresh toolbar labels (handle compact mode)."""
        for item, label in self._toolbar_items:
            # Text handling
            if self._compact_mode:
                self._safe(getattr(item, "setText", lambda *_: None), "")
            else:
                if item is getattr(self, "_theme_action", None):
                    self._safe(getattr(item, "setText", lambda *_: None), "主题")
                elif item is getattr(self, "_reading_btn", None):
                    # Keep reading button label synchronized with reading state
                    self._safe(getattr(item, "setText", lambda *_: None), "阅读中" if self._reading_mode else label)
                else:
                    self._safe(getattr(item, "setText", lambda *_: None), label)
        # Ensure format action text aligns with compact mode
        fa = getattr(self, "_format_action", None)
        if fa is not None:
            self._safe(fa.setText, "排版" if not self._compact_mode else "")

    def _refresh_toolbar_labels(self) -> None:
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
        # Initially update toolbar - combine multiple delayed refreshes into one
        def _initial_refresh():
            self._maybe_update_toolbar_compact()
            self._refresh_toolbar_labels()
        
        QTimer.singleShot(250, _initial_refresh)

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
        
        # Clear HTML style cache as theme has changed
        self._cached_html_style = None
        self._cached_style_key = None
        
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
        # Refresh toolbar synchronously
        self._refresh_toolbar_labels()

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

    def _get_colors(self) -> dict:
        return THEMES.get(self._current_theme, THEMES["light"])

    def _get_html_style(self) -> str:
        """Get cached HTML style or generate new one if cache is invalid"""
        colors = self._get_colors()
        font_size = int(self._font_size * self._font_scale)
        
        # Create cache key
        style_key = (
            self._current_theme,
            self._font_family,
            font_size,
            self._line_spacing,
            self._paragraph_spacing,
        )
        
        # Return cached style if valid
        if self._cached_html_style and self._cached_style_key == style_key:
            return self._cached_html_style
        
        # Generate and cache new style
        self._cached_html_style = generate_html_style(
            colors,
            self._font_family,
            font_size,
            self._line_spacing,
            self._paragraph_spacing,
        )
        self._cached_style_key = style_key
        return self._cached_html_style

    def showEvent(self, event) -> None:
        """After window shows, refresh toolbar state to ensure labels render correctly"""
        super().showEvent(event)
        # Combine multiple UI refreshes into one delayed call
        def _refresh_all():
            self._maybe_update_toolbar_compact()
            self._refresh_toolbar_labels()
        
        QTimer.singleShot(50, _refresh_all)

    def _open_theme_dialog(self) -> None:
        # Show theme options using a menu anchored to the toolbar action
        menu = QMenu(self)
        for key, info in THEMES.items():
            name = info.get("name", key)
            act = QAction(name, self)
            act.setData(key)
            act.setCheckable(False)
            act.triggered.connect(lambda checked=False, k=key: self._set_theme(k))
            menu.addAction(act)
        menu.aboutToHide.connect(lambda: setattr(self, '_menu_open', False))
        self._menu_open = True
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
            ("增大字号", self._zoom_in),
            ("减小字号", self._zoom_out),
            ("增加行间距", self._increase_line_spacing),
            ("减小行间距", self._decrease_line_spacing),
            ("增加段间距", self._increase_paragraph_spacing),
            ("减小段间距", self._decrease_paragraph_spacing),
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
        menu.aboutToHide.connect(lambda: setattr(self, '_menu_open', False))
        self._menu_open = True
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
            self.setWindowTitle(f"EPUB 酷读器 - {result}")
            self._update_toc()
            if self._loader.chapter_count() > 0:
                # Ensure current chapter index is valid
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
            chapter_idx = item['chapter_idx']
            
            tree_item = QTreeWidgetItem(self._toc_tree, [title])
            tree_item.setToolTip(0, title)
            
            # Save chapter index to user data
            if chapter_idx is not None:
                tree_item.setData(0, Qt.ItemDataRole.UserRole, chapter_idx)
        
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
        match, fall back to selecting the nearest TOC item based on chapter_idx.
        """
        count = self._toc_tree.topLevelItemCount()
        found_item = None

        # Prefer items that store a chapter_idx matching the current chapter
        for i in range(count):
            it = self._toc_tree.topLevelItem(i)
            # Guard against possible None (pyqt API may return None)
            if it is None:
                continue

            chapter_idx = it.data(0, Qt.ItemDataRole.UserRole)
            if chapter_idx == self._current_chapter:
                found_item = it
                break

        # Fallback: find the nearest TOC item based on chapter_idx
        if not found_item and count > 0:
            best_item = None
            best_diff = float('inf')
            
            for i in range(count):
                it = self._toc_tree.topLevelItem(i)
                if it is None:
                    continue
                
                chapter_idx = it.data(0, Qt.ItemDataRole.UserRole)
                if chapter_idx is None:
                    continue
                
                # Find the TOC item with smallest positive difference (current >= chapter_idx)
                # This means: show the latest chapter that we've already passed
                if self._current_chapter >= chapter_idx:
                    diff = self._current_chapter - chapter_idx
                    if diff < best_diff:
                        best_diff = diff
                        best_item = it
            
            # If current chapter is before all TOC items, select the first TOC item
            if best_item is None:
                best_item = self._toc_tree.topLevelItem(0)
            
            found_item = best_item

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

        # If page is unavailable (rare environments or during init), render directly and return
        if page is None:
            html = self._get_html_style()
            html += _MOUSE_HANDLER_JS + _SCROLL_JS + (content or "") + "</body></html>"
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

            # Use cached HTML style
            html = self._get_html_style()
            html += _MOUSE_HANDLER_JS + _SCROLL_JS + (content or "") + "</body></html>"

            # Record whether to restore scroll (by ratio)
            if preserve_position:
                self._pending_scroll_ratio = ratio
                self._pending_scroll_chapter = self._current_chapter
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
                    page.runJavaScript(f"setScrollRatio({ratio_local})", lambda _: None)
                    QTimer.singleShot(60, lambda: page.runJavaScript(f"setScrollRatio({ratio_local})", lambda _: None))
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
            try:
                page.runJavaScript("getScrollRatio()", _set_html_and_restore)
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
            self._reading_btn.setText("阅读中" if self._reading_mode else "阅读模式")
            self._reading_btn.setToolTip(
                "关闭阅读模式" if self._reading_mode else "开启阅读模式 (Ctrl+M)"
            )

        status_bar = self.statusBar()
        if status_bar:
            if self._reading_mode:
                status_bar.showMessage("阅读模式已开启 - 左键下一章，右键上一章")
            else:
                status_bar.showMessage("阅读模式已关闭")
        self._save_settings()

    def _choose_font(self) -> None:
        # Implement font selection with a dropdown (includes search)
        if not hasattr(self, "_font_menu"):
            self._create_font_menu()
        self._menu_open = True
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
        self._font_menu.aboutToHide.connect(lambda: setattr(self, '_menu_open', False))
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
        
        # Load fonts asynchronously - only when menu is about to show
        self._all_fonts = None  # Cache font list for future uses
        
        def populate(names):
            font_list.clear()
            for name in names:
                it = QListWidgetItem(name)
                it.setFont(QFont(name, 14))
                it.setSizeHint(QSize(360, 26))
                font_list.addItem(it)
        
        def get_all_fonts():
            if self._all_fonts is None:
                # Load fonts only when needed (lazy loading)
                self._all_fonts = sorted(
                    [f for f in QFontDatabase.families() if not f.startswith("@")]
                )
            return self._all_fonts
        
        # Populate with initial set when menu is about to show
        def on_menu_about_to_show():
            fonts = get_all_fonts()
            populate(fonts)
            font_list.setFixedWidth(420)
            font_list.setMinimumHeight(min(800, 26 * len(fonts)))
        
        self._font_menu.aboutToShow.connect(on_menu_about_to_show)
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
            fonts = get_all_fonts()
            filtered = [f for f in fonts if text.lower() in f.lower()]
            populate(filtered)

        search.textChanged.connect(on_search)
        # Embed container into QMenu as QWidgetAction for complex dropdown layout
        action = QWidgetAction(self._font_menu)
        action.setDefaultWidget(container)
        self._font_menu.addAction(action)

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
            self._reading_btn.setText("阅读中" if self._reading_mode else "阅读模式")

        if "window_geometry" in data:
            from PyQt6.QtCore import QByteArray

            self.restoreGeometry(QByteArray.fromHex(data["window_geometry"].encode()))

    def resizeEvent(self, a0) -> None:
        super().resizeEvent(a0)
        self._maybe_update_toolbar_compact()

    def closeEvent(self, a0) -> None:
        self._save_settings()
        a0.accept()
