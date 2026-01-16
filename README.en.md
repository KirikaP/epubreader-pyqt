# EPUB Reader

A modern EPUB reader built with PyQt6, rendering chapters using an embedded web engine and providing friendly typography and theme support.

> Note: Parts of this project were generated with AI (GitHub Copilot). The current maintainer has limited experience with PyQt. If you find UI issues or interaction improvements, please open an issue or submit a pull request, or collaborate with a contributor experienced in PyQt.

## Key Features ✅

- 📖 Support for EPUB format
- 🎨 Multiple themes (light / dark / eye-friendly)
- 🔤 Adjustable font, font size, line spacing, and paragraph spacing
- 📑 Table of contents navigation and chapter jumps
- 🖼️ Toggle image display
- 📕 Reading mode with mouse click page navigation
- 💾 Auto-save reading progress and user settings

## Quick Start 🚀

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python main.py
```

## Usage

- Open file: `Ctrl+O`
- Toggle table of contents: `Ctrl+T`
- Toggle reading mode: `Ctrl+M`
- Increase / decrease font size: `Ctrl++` / `Ctrl+-`

(See in-app hints and the status bar for the full list of shortcuts.)

## Interface & Interaction

- The toolbar contains quick actions (Open, Font, Theme, Format, Reading Mode, etc.).
- You can change fonts and themes from the toolbar and preview them immediately.
- Formatting options (line spacing / paragraph spacing / scale) are available via the format menu.

## Project Structure

```
epub-python/
├── main.py              # Application entry point
├── requirements.txt
├── README.en.md         # English README
├── README.zh-CN.md      # Simplified Chinese README
└── src/
    ├── core/            # Core logic (loader, settings, themes)
    └── ui/              # UI components (main window, dialogs, bridge)
```

## Contribution & Feedback

All contributions are welcome. Because parts of the repository were AI-assisted, **we encourage PyQt-experienced reviewers** to participate in code review and improvements.

---

## Run

```bash
python main.py
```

## Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open file |
| `Ctrl+R` | Reopen last file |
| `Ctrl+Q` | Quit |
| `←` / `→` | Previous / Next chapter |
| `Ctrl+T` | Toggle TOC |
| `Ctrl+I` | Toggle images |
| `Ctrl++` / `Ctrl+-` | Increase / decrease font size |
| `Ctrl+M` | Toggle reading mode |

## Reading Mode

When reading mode is enabled:
- **Left click** → next chapter
- **Right click** → previous chapter

## Themes

- Light / Dark
- Eye-friendly (beige / green)
- Monokai / Nord / Dracula
- One Dark / GitHub Dark
- Gruvbox / Tokyo Night / Catppuccin

## Tech Stack

- Python 3.8+
- PyQt6 + QWebEngineView (Chromium)
- ebooklib (EPUB parser)
