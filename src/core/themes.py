"""Theme configuration and stylesheet generation utilities."""

from typing import Dict

# Theme definitions (extensible color config dict)
THEMES: Dict[str, dict] = {
    "light": {
        "name": "DayDefault",
        "bg": "#f5f5f5",
        "fg": "#333333",
        "toolbar_bg": "#ffffff",
        "toolbar_border": "#e0e0e0",
        "select_bg": "#0078d7",
        "select_fg": "#ffffff",
        "hover_bg": "#e3f2fd",
        "hover_fg": "#0078d7",
        "treeview_bg": "#ffffff",
        "treeview_fg": "#333333",
        "content_bg": "#ffffff",
        "content_fg": "#333333",
        "heading_color": "#1565c0",
        "link_color": "#1976d2",
        "border_color": "#e0e0e0",
        "accent": "#0078d7",
        "shadow": "rgba(0,0,0,0.1)",
    },
    "dark": {
        "name": "NightDefault",
        "bg": "#1e1e1e",
        "fg": "#e0e0e0",
        "toolbar_bg": "#252526",
        "toolbar_border": "#3c3c3c",
        "select_bg": "#264f78",
        "select_fg": "#ffffff",
        "hover_bg": "#2a2d2e",
        "hover_fg": "#ffffff",
        "treeview_bg": "#252526",
        "treeview_fg": "#cccccc",
        "content_bg": "#1e1e1e",
        "content_fg": "#d4d4d4",
        "heading_color": "#569cd6",
        "link_color": "#4fc3f7",
        "border_color": "#3c3c3c",
        "accent": "#569cd6",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "sepia": {
        "name": "RetroBeige",
        "bg": "#f5f0e6",
        "fg": "#5c4b37",
        "toolbar_bg": "#faf6ed",
        "toolbar_border": "#e6dcc8",
        "select_bg": "#c9b896",
        "select_fg": "#3d3225",
        "hover_bg": "#ede4d3",
        "hover_fg": "#5c4b37",
        "treeview_bg": "#faf6ed",
        "treeview_fg": "#5c4b37",
        "content_bg": "#faf8f2",
        "content_fg": "#5c4b37",
        "heading_color": "#8b7355",
        "link_color": "#a0826d",
        "border_color": "#e6dcc8",
        "accent": "#a0826d",
        "shadow": "rgba(92,75,55,0.1)",
    },
    "green": {
        "name": "EyeComfortGreen",
        "bg": "#e8f5e9",
        "fg": "#1b5e20",
        "toolbar_bg": "#f1f8e9",
        "toolbar_border": "#c8e6c9",
        "select_bg": "#81c784",
        "select_fg": "#1b5e20",
        "hover_bg": "#c8e6c9",
        "hover_fg": "#2e7d32",
        "treeview_bg": "#f1f8e9",
        "treeview_fg": "#2e7d32",
        "content_bg": "#f9fbe7",
        "content_fg": "#33691e",
        "heading_color": "#388e3c",
        "link_color": "#43a047",
        "border_color": "#c8e6c9",
        "accent": "#4caf50",
        "shadow": "rgba(27,94,32,0.1)",
    },
    "monokai": {
        "name": "Monokai",
        "bg": "#272822",
        "fg": "#f8f8f2",
        "toolbar_bg": "#1e1f1c",
        "toolbar_border": "#3e3d32",
        "select_bg": "#49483e",
        "select_fg": "#f8f8f2",
        "hover_bg": "#3e3d32",
        "hover_fg": "#f8f8f2",
        "treeview_bg": "#1e1f1c",
        "treeview_fg": "#f8f8f2",
        "content_bg": "#272822",
        "content_fg": "#f8f8f2",
        "heading_color": "#f92672",
        "link_color": "#66d9ef",
        "border_color": "#3e3d32",
        "accent": "#a6e22e",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "nord": {
        "name": "Nord",
        "bg": "#2e3440",
        "fg": "#d8dee9",
        "toolbar_bg": "#3b4252",
        "toolbar_border": "#434c5e",
        "select_bg": "#5e81ac",
        "select_fg": "#eceff4",
        "hover_bg": "#434c5e",
        "hover_fg": "#eceff4",
        "treeview_bg": "#3b4252",
        "treeview_fg": "#d8dee9",
        "content_bg": "#2e3440",
        "content_fg": "#e5e9f0",
        "heading_color": "#88c0d0",
        "link_color": "#81a1c1",
        "border_color": "#434c5e",
        "accent": "#88c0d0",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "dracula": {
        "name": "Dracula",
        "bg": "#282a36",
        "fg": "#f8f8f2",
        "toolbar_bg": "#21222c",
        "toolbar_border": "#44475a",
        "select_bg": "#44475a",
        "select_fg": "#f8f8f2",
        "hover_bg": "#44475a",
        "hover_fg": "#ff79c6",
        "treeview_bg": "#21222c",
        "treeview_fg": "#f8f8f2",
        "content_bg": "#282a36",
        "content_fg": "#f8f8f2",
        "heading_color": "#ff79c6",
        "link_color": "#8be9fd",
        "border_color": "#44475a",
        "accent": "#bd93f9",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "one_dark": {
        "name": "One Dark",
        "bg": "#282c34",
        "fg": "#abb2bf",
        "toolbar_bg": "#21252b",
        "toolbar_border": "#181a1f",
        "select_bg": "#3e4451",
        "select_fg": "#d7dae0",
        "hover_bg": "#2c313a",
        "hover_fg": "#61afef",
        "treeview_bg": "#21252b",
        "treeview_fg": "#abb2bf",
        "content_bg": "#282c34",
        "content_fg": "#abb2bf",
        "heading_color": "#e06c75",
        "link_color": "#61afef",
        "border_color": "#181a1f",
        "accent": "#61afef",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "github_dark": {
        "name": "GitHub Dark",
        "bg": "#0d1117",
        "fg": "#c9d1d9",
        "toolbar_bg": "#161b22",
        "toolbar_border": "#30363d",
        "select_bg": "#238636",
        "select_fg": "#ffffff",
        "hover_bg": "#21262d",
        "hover_fg": "#58a6ff",
        "treeview_bg": "#161b22",
        "treeview_fg": "#c9d1d9",
        "content_bg": "#0d1117",
        "content_fg": "#c9d1d9",
        "heading_color": "#58a6ff",
        "link_color": "#58a6ff",
        "border_color": "#30363d",
        "accent": "#238636",
        "shadow": "rgba(0,0,0,0.4)",
    },
    "gruvbox": {
        "name": "Gruvbox",
        "bg": "#282828",
        "fg": "#ebdbb2",
        "toolbar_bg": "#1d2021",
        "toolbar_border": "#3c3836",
        "select_bg": "#504945",
        "select_fg": "#fbf1c7",
        "hover_bg": "#3c3836",
        "hover_fg": "#fe8019",
        "treeview_bg": "#1d2021",
        "treeview_fg": "#ebdbb2",
        "content_bg": "#282828",
        "content_fg": "#ebdbb2",
        "heading_color": "#fabd2f",
        "link_color": "#83a598",
        "border_color": "#3c3836",
        "accent": "#b8bb26",
        "shadow": "rgba(0,0,0,0.3)",
    },
    "tokyo_night": {
        "name": "Tokyo Night",
        "bg": "#1a1b26",
        "fg": "#a9b1d6",
        "toolbar_bg": "#16161e",
        "toolbar_border": "#2f3549",
        "select_bg": "#364a82",
        "select_fg": "#c0caf5",
        "hover_bg": "#292e42",
        "hover_fg": "#7aa2f7",
        "treeview_bg": "#16161e",
        "treeview_fg": "#a9b1d6",
        "content_bg": "#1a1b26",
        "content_fg": "#a9b1d6",
        "heading_color": "#7aa2f7",
        "link_color": "#7dcfff",
        "border_color": "#2f3549",
        "accent": "#bb9af7",
        "shadow": "rgba(0,0,0,0.4)",
    },
    "catppuccin": {
        "name": "Catppuccin",
        "bg": "#1e1e2e",
        "fg": "#cdd6f4",
        "toolbar_bg": "#181825",
        "toolbar_border": "#313244",
        "select_bg": "#45475a",
        "select_fg": "#cdd6f4",
        "hover_bg": "#313244",
        "hover_fg": "#f5c2e7",
        "treeview_bg": "#181825",
        "treeview_fg": "#cdd6f4",
        "content_bg": "#1e1e2e",
        "content_fg": "#cdd6f4",
        "heading_color": "#cba6f7",
        "link_color": "#89b4fa",
        "border_color": "#313244",
        "accent": "#f5c2e7",
        "shadow": "rgba(0,0,0,0.4)",
    },
}


def get_stylesheet(colors: dict) -> str:
    """Generate a modern Qt stylesheet"""
    return f"""
        /* ========== Main window ========== */
        QMainWindow {{
            background-color: {colors['bg']};
            color: {colors['fg']};
        }}
        
        /* ========== Toolbar ========== */
        QToolBar {{
            background-color: {colors['toolbar_bg']};
            border: none;
            border-bottom: 1px solid {colors['toolbar_border']};
            padding: 2px 4px;
            spacing: 2px;
        }}
        QToolBar::separator {{
            background-color: {colors['border_color']};
            width: 1px;
            margin: 4px 4px;
        }}
        QToolBar QToolButton {{
            background-color: transparent;
            color: {colors['fg']};
            border: none;
            border-radius: 4px;
            padding: 4px 6px;
            min-width: 24px;
        }}
        QToolBar QToolButton:hover {{
            background-color: {colors['hover_bg']};
            color: {colors['hover_fg']};
        }}
        QToolBar QToolButton:pressed {{
            background-color: {colors['select_bg']};
            color: {colors['select_fg']};
        }}
        QToolBar QToolButton:checked {{
            background-color: {colors['select_bg']};
            color: {colors['select_fg']};
        }}
        QToolBar QLabel {{
            color: {colors['fg']};
            padding: 0 4px;
            opacity: 0.7;
        }}
        
        /* ========== Treeview ========== */
        QTreeWidget {{
            background-color: {colors['treeview_bg']};
            color: {colors['treeview_fg']};
            border: none;
            border-right: 1px solid {colors['border_color']};
            outline: none;
            padding: 4px;
        }}
        QTreeWidget::item {{
            padding: 4px 8px;
            border-radius: 3px;
            margin: 1px 2px;
        }}
        QTreeWidget::item:selected {{
            background-color: {colors['select_bg']};
            color: {colors['select_fg']};
        }}
        QTreeWidget::item:hover:!selected {{
            background-color: {colors['hover_bg']};
            color: {colors['hover_fg']};
        }}
        QTreeWidget::branch {{
            background-color: transparent;
        }}
        
        /* ========== Scrollbar ========== */
        QScrollBar:vertical {{
            background-color: transparent;
            width: 10px;
            border: none;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background-color: {colors['accent']};
            min-height: 28px;
            border-radius: 6px;
            margin: 4px;
            border: 2px solid {colors['treeview_bg']};
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {colors['select_bg']};
            border-color: {colors['accent']};
        }}
        QScrollBar::sub-page:vertical, QScrollBar::add-page:vertical {{
            background: rgba(0,0,0,0); /* transparent */
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background-color: transparent;
            height: 10px;
            border: none;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {colors['accent']};
            min-width: 28px;
            border-radius: 6px;
            margin: 4px;
            border: 2px solid {colors['treeview_bg']};
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {colors['select_bg']};
            border-color: {colors['accent']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        
        /* ========== Menu ========== */
        QMenu {{
            background-color: {colors['toolbar_bg']};
            color: {colors['fg']};
            border: 1px solid {colors['border_color']};
            border-radius: 8px;
            padding: 8px 4px;
        }}
        QMenu::item {{
            padding: 8px 32px 8px 16px;
            border-radius: 4px;
            margin: 2px 4px;
        }}
        QMenu::item:selected {{
            background-color: {colors['hover_bg']};
            color: {colors['hover_fg']};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {colors['border_color']};
            margin: 6px 12px;
        }}
        
        /* ========== Status bar ========== */
        QStatusBar {{
            background-color: {colors['toolbar_bg']};
            color: {colors['fg']};
            border-top: 1px solid {colors['toolbar_border']};
            padding: 4px 12px;
        }}
        QStatusBar QLabel {{
            color: {colors['fg']};
            padding: 0 8px;
        }}
        
        /* ========== Splitter ========== */
        QSplitter::handle {{
            background-color: {colors['border_color']};
            width: 1px;
        }}
        QSplitter::handle:hover {{
            background-color: {colors['accent']};
        }}
        
        /* ========== Dialog ========== */
        QDialog {{
            background-color: {colors['bg']};
            color: {colors['fg']};
        }}
        
        /* ========== Input ========== */
        QLineEdit {{
            background-color: {colors['treeview_bg']};
            color: {colors['treeview_fg']};
            border: 1px solid {colors['border_color']};
            border-radius: 6px;
            padding: 8px 12px;
            selection-background-color: {colors['select_bg']};
        }}
        QLineEdit:focus {{
            border-color: {colors['accent']};
        }}
        
        /* ========== List ========== */
        QListWidget {{
            background-color: {colors['treeview_bg']};
            color: {colors['treeview_fg']};
            border: 1px solid {colors['border_color']};
            border-radius: 6px;
            outline: none;
            padding: 4px;
        }}
        QListWidget::item {{
            padding: 8px 12px;
            border-radius: 4px;
            margin: 2px;
        }}
        QListWidget::item:selected {{
            background-color: {colors['select_bg']};
            color: {colors['select_fg']};
        }}
        QListWidget::item:hover:!selected {{
            background-color: {colors['hover_bg']};
        }}
        
        /* ========== Buttons ========== */
        QPushButton {{
            background-color: {colors['toolbar_bg']};
            color: {colors['fg']};
            border: 1px solid {colors['border_color']};
            border-radius: 6px;
            padding: 8px 20px;
            min-width: 80px;
        }}
        QPushButton:hover {{
            background-color: {colors['hover_bg']};
            border-color: {colors['accent']};
        }}
        QPushButton:pressed {{
            background-color: {colors['select_bg']};
            color: {colors['select_fg']};
        }}
        QPushButton:default {{
            background-color: {colors['accent']};
            color: {colors['select_fg']};
            border-color: {colors['accent']};
        }}
        QPushButton:default:hover {{
            background-color: {colors['select_bg']};
        }}
        
        /* ========== Dialog buttons ========== */
        QDialogButtonBox QPushButton {{
            min-width: 90px;
        }}
        
        /* ========== Labels ========== */
        QLabel {{
            color: {colors['fg']};
        }}
        
        /* ========== Common component background ========== */
        QWidget {{
            background-color: {colors['bg']};
            color: {colors['fg']};
        }}
    """


def generate_html_style(
    colors: dict,
    font_family: str,
    font_size: int,
    line_spacing: float,
    paragraph_spacing: float,
) -> str:
    """Generate HTML content styles"""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
* {{
    box-sizing: border-box;
}}
body {{
    font-family: "{font_family}", "Microsoft YaHei", "PingFang SC", sans-serif;
    line-height: {line_spacing};
    margin: 0;
    padding: 16px 24px;
    background-color: {colors['content_bg']};
    color: {colors['content_fg']};
    font-size: {font_size}px;
}}
h1, h2, h3, h4, h5, h6 {{
    color: {colors['heading_color']};
    margin-top: 1.5em;
    margin-bottom: 0.8em;
    font-weight: 600;
}}
h1 {{ font-size: 1.8em; border-bottom: 2px solid {colors['border_color']}; padding-bottom: 0.3em; }}
h2 {{ font-size: 1.5em; }}
h3 {{ font-size: 1.3em; }}
p {{
    text-indent: 2em;
    margin: {paragraph_spacing}em 0;
    text-align: justify;
}}
a {{
    color: {colors['link_color']};
    text-decoration: none;
}}
a:hover {{
    text-decoration: underline;
}}
img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1.5em auto;
    border-radius: 8px;
    box-shadow: 0 4px 12px {colors.get('shadow', 'rgba(0,0,0,0.1)')};
}}
blockquote {{
    border-left: 4px solid {colors['accent']};
    margin: 1.5em 0;
    padding: 0.5em 1.5em;
    background-color: {colors['hover_bg']};
    border-radius: 0 8px 8px 0;
}}
/* ========== Web content scrollbar (WebKit) ========== */
::-webkit-scrollbar {{
    width: 10px;
    height: 10px;
}}
::-webkit-scrollbar-track {{
    background: {colors['content_bg']};
    border-radius: 6px;
}}
::-webkit-scrollbar-thumb {{
    background: {colors['accent']};
    border-radius: 6px;
    border: 2px solid {colors['content_bg']};
}}
::-webkit-scrollbar-thumb:hover {{
    background: {colors['select_bg']};
}}
code {{
    background-color: {colors['hover_bg']};
    padding: 2px 6px;
    border-radius: 4px;
    font-family: "Consolas", "Monaco", monospace;
    font-size: 0.9em;
}}
pre {{
    background-color: {colors['toolbar_bg']};
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    border: 1px solid {colors['border_color']};
}}
pre code {{
    background: none;
    padding: 0;
}}
hr {{
    border: none;
    height: 1px;
    background: linear-gradient(to right, transparent, {colors['border_color']}, transparent);
    margin: 2em 0;
}}
table {{
    border-collapse: collapse;
    width: 100%;
    margin: 1.5em 0;
}}
th, td {{
    border: 1px solid {colors['border_color']};
    padding: 10px 14px;
    text-align: left;
}}
th {{
    background-color: {colors['hover_bg']};
    font-weight: 600;
}}
::selection {{
    background-color: {colors['select_bg']};
    color: {colors['select_fg']};
}}
</style></head><body>"""
