# EPUB 阅读器

支持的功能

- EPUB 阅读
- 主题
- 字体与排版调整
- 目录导航
- 阅读模式
- 保存进度

由 AI（GitHub Copilot）生成。

# 安装

见 `requirements.txt`。

# 使用

运行：

```
python main.py
```

## 使用说明

- 打开文件：`Ctrl+O`
- 切换目录：`Ctrl+T`
- 切换阅读模式：`Ctrl+M`
- 放大/缩小字号：`Ctrl++` / `Ctrl+-`

（完整快捷键请查看程序内的帮助或状态栏提示）

## 界面与交互说明

- 工具栏包含 快速操作（打开、字体、主题、排版、阅读模式等）。
- 字体与主题支持在工具栏中快速选择并即时预览。
- 排版操作（行距/段距/缩放）可在菜单中连续操作，菜单保持打开以便多次调整。

## 项目结构

```
epub-python/
├── main.py              # 程序入口
├── requirements.txt
├── README.en.md         # 英文 README
├── README.zh-CN.md      # 简体中文 README
└── src/
    ├── core/            # 核心逻辑（加载、设置、主题）
    └── ui/              # 界面组件（主窗口、对话、桥接）
```

## 贡献与反馈

欢迎提交 Issue、Bug 报告或 PR。因为仓库有 AI 生成的部分实现，**建议有 PyQt 经验的贡献者参与代码审查与优化**。

---

## 运行

```bash
python main.py
```

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+O` | 打开文件 |
| `Ctrl+R` | 重新打开上次文件 |
| `Ctrl+Q` | 退出 |
| `←` / `→` | 上一章/下一章 |
| `Ctrl+T` | 显示/隐藏目录 |
| `Ctrl+I` | 显示/隐藏图片 |
| `Ctrl++` / `Ctrl+-` | 放大/缩小字号 |
| `Ctrl+M` | 切换阅读模式 |

## 阅读模式

开启阅读模式后：
- **左键点击** → 下一章
- **右键点击** → 上一章

## 主题列表

- 日间默认 / 夜间默认
- 护眼米黄 / 护眼绿
- Monokai / Nord / Dracula
- One Dark / GitHub Dark
- Gruvbox / Tokyo Night / Catppuccin

## 技术栈

- Python 3.8+
- PyQt6 + QWebEngineView（Chromium 内核）
- ebooklib（EPUB 解析）
