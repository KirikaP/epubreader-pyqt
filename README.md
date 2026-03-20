# EPUB Reader

A modern, cross-platform EPUB reader built with PyQt6 and QWebEngineView.

## Features

- **Full EPUB support**: Reads standard EPUB files
- **Multiple themes**: 12+ curated themes including light, dark, sepia, and programming editor themes
- **Customizable reading experience**: 
  - Adjustable font family, size, and scaling
  - Custom line spacing and paragraph spacing
  - Show/hide images with placeholder support
- **Reading mode**: Mouse-driven navigation (left click for next chapter, right click for previous)
- **Table of contents**: Flat TOC parsing with accurate selection and chapter mapping
- **Performance optimized**: 
  - LRU chapter caching
  - Async chapter preloading
  - Pre-compiled image indexing
- **Progress saving**: Automatically saves reading position and settings

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
python main.py
```

3. Use File → Open (Ctrl+O) to open an EPUB file.

## Keyboard Shortcuts

- **Ctrl+O**: Open EPUB file
- **Ctrl+T**: Toggle table of contents sidebar
- **Ctrl+M**: Toggle reading mode
- **Ctrl+I**: Toggle image visibility
- **← / →**: Navigate between chapters
- **Home / End**: Jump to first/last chapter
- **Ctrl+=**: Increase font size
- **Ctrl+-**: Decrease font size

## Theme Preview

The application includes 12 themes:
- Light, Dark, Sepia (for comfortable reading)
- Programming editor themes (Monokai, Nord, Dracula, One Dark, GitHub Dark, Gruvbox, Tokyo Night, Catppuccin)
- Eye-friendly green theme

## Project Structure

```
src/
├── core/           # Core functionality
│   ├── epub_loader.py      # EPUB parsing and caching
│   ├── settings.py         # User preferences management
│   └── themes.py           # Theme definitions and stylesheets
├── ui/             # User interface
│   ├── main_window.py      # Main application window
│   ├── web_bridge.py       # JavaScript-Python communication
│   └── js/                 # JavaScript utilities for web content
```

## Requirements

- Python 3.8+
- PyQt6 >= 6.4.0
- PyQt6-WebEngine >= 6.4.0
- ebooklib >= 0.18

## Recent Improvements

- Pre-compiled regex patterns for better performance
- Improved TOC selection algorithm for accurate chapter highlighting
- Enhanced error handling and type annotations
- Simplified UI with cleaner text labels

简体中文文档: [README.zh-CN.md](README.zh-CN.md)

