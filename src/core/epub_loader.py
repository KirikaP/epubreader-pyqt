"""EPUB file loading module"""

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
    """EPUB file loader"""

    # Supported image MIME types
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
        self._chapter_map: Dict[str, int] = {}  # Added: mapping from chapter filename to index

    def load_file(self, filepath: str) -> Tuple[bool, str]:
        """
        Load an EPUB file

        Returns:
            (success, title) or (False, error_message)
        """
        try:
            self._book = epub.read_epub(filepath)
            self._chapters = [
                item
                for item in self._book.get_items()
                if item.get_type() == ebooklib.ITEM_DOCUMENT
            ]
            
            # Build mapping from chapter filename to index
            self._chapter_map.clear()
            for i, chapter in enumerate(self._chapters):
                filename = os.path.basename(chapter.get_name())
                self._chapter_map[filename] = i
                
            self._chapter_cache.clear()
            self._build_image_index()

            title_meta = self._book.get_metadata("DC", "title")
            title = title_meta[0][0] if title_meta else os.path.basename(filepath)
            return True, title
        except Exception as e:
            return False, str(e)

    def _build_image_index(self) -> None:
        """Build image index for faster lookup"""
        self._image_index.clear()
        if not self._book:
            return

        for item in self._book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                name = item.get_name()
                # Index multiple path forms
                self._image_index[name] = item
                self._image_index[name.split("/")[-1]] = item
                self._image_index[os.path.basename(name)] = item

    def set_image_visibility(self, visible: bool) -> None:
        """Set image visibility state"""
        if self._show_images != visible:
            self._show_images = visible
            self._chapter_cache.clear()

    def get_chapter_content(self, index: int) -> Optional[str]:
        """Get chapter HTML content"""
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
        """Asynchronously preload adjacent chapters"""
        for i in range(max(0, current - 1), min(len(self._chapters), current + 2)):
            if i not in self._chapter_cache:
                self._executor.submit(self.get_chapter_content, i)

    def _embed_images(self, html: str) -> str:
        """Convert image references to base64 inline"""
        if not self._book:
            return html

        pattern = re.compile(r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*>', re.IGNORECASE)
        return pattern.sub(self._replace_image, html)

    def _replace_image(self, match: re.Match) -> str:
        """Replace a single image tag"""
        tag, src = match.group(0), match.group(1)

        # Show placeholder when images are hidden
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
        """Get table of contents (preserve original interface)"""
        return self._book.toc if self._book else []

    def get_flat_toc(self) -> list:
        """Get a flattened TOC list. Each item is a dict with title, chapter index and level"""
        if not self._book:
            return []
        
        flat_toc = []
        
        def process_items(items, level=0):
            for item in items:
                if hasattr(item, '__iter__') and not isinstance(item, (str, bytes)):
                    # This is an iterable (tuple/list), may be a nested structure
                    process_items(item, level)
                else:
                    # Try to obtain title and href
                    title = None
                    href = None
                    
                    # Check different attribute types
                    if hasattr(item, 'title'):
                        title = item.title
                    elif hasattr(item, 'get'):
                        try:
                            title = item.get('title', '')
                        except:
                            pass
                    
                    if hasattr(item, 'href'):
                        href = item.href
                    elif hasattr(item, 'get'):
                        try:
                            href = item.get('href', '')
                        except:
                            pass
                    
                    # If item is a Link (common case), normalize to epub.Link
                    if isinstance(item, epub.Link):
                        title = title or item.title
                        href = href or item.href
                    
                    if title:
                        # Find corresponding chapter index
                        chapter_idx = self._find_chapter_index(href) if href else None
                        flat_toc.append({
                            'title': title,
                            'level': level,
                            'href': href,
                            'chapter_idx': chapter_idx
                        })
        
        try:
            process_items(self._book.toc)
        except Exception as e:
            print(f"Error parsing TOC: {e}")
            # Fallback: return a basic list based on chapter filenames
            for i in range(self.chapter_count()):
                filename = self._chapters[i].get_name()
                flat_toc.append({
                    'title': f"章节 {i+1} ({os.path.basename(filename)})",
                    'level': 0,
                    'href': filename,
                    'chapter_idx': i
                })
        
        return flat_toc
    
    def _find_chapter_index(self, href: str) -> Optional[int]:
        """Find chapter index by href"""
        if not href:
            return None
            
        # Extract filename part
        filename = os.path.basename(unquote(href))
        
        # Direct lookup
        if filename in self._chapter_map:
            return self._chapter_map[filename]
        
        # Try without query parameters
        if '?' in filename:
            base_name = filename.split('?')[0]
            if base_name in self._chapter_map:
                return self._chapter_map[base_name]
        
        # Try searching chapters containing the filename
        for chapter_idx, chapter in enumerate(self._chapters):
            if filename in chapter.get_name():
                return chapter_idx
        
        return None

    def chapter_count(self) -> int:
        """Return the number of chapters"""
        return len(self._chapters)

    def __del__(self):
        """Shutdown the thread pool"""
        self._executor.shutdown(wait=False)
