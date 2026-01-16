"""EPUB文件加载模块"""

import os
import base64
import re
from urllib.parse import unquote
from typing import Optional, List, Any, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor

try:
    import ebooklib
    from ebooklib import epub
except ImportError:
    print("请先安装依赖库: pip install ebooklib")
    exit(1)


class EpubLoader:
    """EPUB文件加载器"""

    # 支持的图片格式
    _MIME_TYPES: Dict[str, str] = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "svg": "image/svg+xml",
        "webp": "image/webp",
    }

    def __init__(self):
        self._book: Optional[epub.EpubBook] = None
        self._chapters: List[Any] = []
        self._chapter_cache: Dict[int, str] = {}
        self._image_index: Dict[str, Any] = {}
        self._show_images = True
        self._executor = ThreadPoolExecutor(max_workers=2)

    def load_file(self, filepath: str) -> Tuple[bool, str]:
        """
        加载EPUB文件

        Returns:
            (成功, 标题) 或 (失败, 错误信息)
        """
        try:
            self._book = epub.read_epub(filepath)
            self._chapters = [
                item
                for item in self._book.get_items()
                if item.get_type() == ebooklib.ITEM_DOCUMENT
            ]
            self._chapter_cache.clear()
            self._build_image_index()

            title_meta = self._book.get_metadata("DC", "title")
            title = title_meta[0][0] if title_meta else os.path.basename(filepath)
            return True, title
        except Exception as e:
            return False, str(e)

    def _build_image_index(self) -> None:
        """构建图片索引，加速查找"""
        self._image_index.clear()
        if not self._book:
            return

        for item in self._book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                name = item.get_name()
                # 多种路径形式索引
                self._image_index[name] = item
                self._image_index[name.split("/")[-1]] = item
                self._image_index[os.path.basename(name)] = item

    def set_image_visibility(self, visible: bool) -> None:
        """设置图片显示状态"""
        if self._show_images != visible:
            self._show_images = visible
            self._chapter_cache.clear()

    def get_chapter_content(self, index: int) -> Optional[str]:
        """获取章节HTML内容"""
        if not (0 <= index < len(self._chapters)):
            return None

        if index in self._chapter_cache:
            return self._chapter_cache[index]

        try:
            content = self._chapters[index].get_content().decode("utf-8")
            content = self._embed_images(content)
            self._chapter_cache[index] = content
            return content
        except Exception:
            return None

    def preload_chapters(self, current: int) -> None:
        """异步预加载相邻章节"""
        for i in range(max(0, current - 1), min(len(self._chapters), current + 2)):
            if i not in self._chapter_cache:
                self._executor.submit(self.get_chapter_content, i)

    def _embed_images(self, html: str) -> str:
        """将图片引用转换为base64内嵌"""
        if not self._book:
            return html

        pattern = re.compile(r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*>', re.IGNORECASE)
        return pattern.sub(self._replace_image, html)

    def _replace_image(self, match: re.Match) -> str:
        """替换单个图片标签"""
        tag, src = match.group(0), match.group(1)

        # 隐藏图片时显示占位符
        if not self._show_images:
            filename = os.path.basename(unquote(src))
            return (
                f'<div style="border:1px dashed #999;padding:10px;'
                f'margin:10px 0;text-align:center;color:#666;">'
                f"[图片: {filename}]</div>"
            )

        try:
            src_decoded = unquote(src)
            item = self._image_index.get(src_decoded) or self._image_index.get(
                src_decoded.split("/")[-1]
            )

            if item:
                data = item.get_content()
                ext = item.get_name().lower().split(".")[-1]
                mime_type = self._MIME_TYPES.get(ext, "image/jpeg")
                b64 = base64.b64encode(data).decode("utf-8")
                return re.sub(
                    r'src=["\'][^"\'>]+["\']',
                    f'src="data:{mime_type};base64,{b64}"',
                    tag,
                    flags=re.IGNORECASE,
                )
        except Exception:
            pass
        return tag

    def get_toc(self) -> list:
        """获取目录"""
        return self._book.toc if self._book else []

    def chapter_count(self) -> int:
        """获取章节数量"""
        return len(self._chapters)

    def __del__(self):
        """清理线程池"""
        self._executor.shutdown(wait=False)
