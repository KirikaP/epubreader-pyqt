"""EPUB file loading module"""

import os
import base64
import re
from collections import OrderedDict
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
    """EPUB file loader with performance optimizations"""

    # Supported image MIME types
    _MIME_TYPES: Dict[str, str] = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "svg": "image/svg+xml",
        "webp": "image/webp",
    }

    # Maximum cache size to prevent memory bloat
    MAX_CACHE_SIZE = 10

    def __init__(self):
        self._book: Optional[epub.EpubBook] = None
        self._chapters: List[Any] = []
        # Use OrderedDict for LRU cache - order tracks access time
        self._chapter_cache: OrderedDict[int, str] = OrderedDict()
        self._image_index: Dict[str, Any] = {}
        self._show_images = True
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._chapter_map: Dict[str, int] = {}  # Mapping from chapter filename to index

    def load_file(self, filepath: str) -> Tuple[bool, str]:
        """
        Load an EPUB file

        Returns:
            (success, title) or (False, error_message)
        """
        try:
            self._book = epub.read_epub(filepath)
            
            # Order chapters by spine (reading order), fallback to original order if no spine
            if self._book.spine:
                self._chapters = []
                for spine_item in self._book.spine:
                    item = self._book.get_item_with_href(spine_item[0])
                    if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                        self._chapters.append(item)
            else:
                # Fallback: use get_items() order
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
        """Get chapter HTML content with LRU caching"""
        if not (0 <= index < len(self._chapters)):
            return None

        # Return cached content and update LRU order
        if index in self._chapter_cache:
            # Move to end to mark as recently used
            content = self._chapter_cache.pop(index)
            self._chapter_cache[index] = content
            return content

        try:
            content = self._chapters[index].get_content().decode("utf-8")
            content = self._embed_images(content)
            
            # Add to cache (at end for LRU)
            self._chapter_cache[index] = content
            
            # Evict old entries if cache is too large
            while len(self._chapter_cache) > self.MAX_CACHE_SIZE:
                self._chapter_cache.popitem(last=False)  # Remove oldest (first) item
            
            return content
        except Exception:
            return None

    def preload_chapters(self, current: int) -> None:
        """Asynchronously preload adjacent chapters (optimised to avoid redundant work)"""
        # Only preload chapters that aren't already cached
        preload_range = range(max(0, current - 1), min(len(self._chapters), current + 2))
        
        for i in preload_range:
            if i not in self._chapter_cache and i != current:
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
                    # Try to obtain title and href in a type-safe way
                    title = None
                    href = None

                    # Skip plain strings/bytes early to satisfy static checkers
                    if isinstance(item, (str, bytes)):
                        continue

                    if isinstance(item, epub.Link):
                        # Common case: epub.Link
                        title = item.title
                        href = item.href
                    elif isinstance(item, dict):
                        # Some TOC entries can be dict-like
                        title = item.get('title', '') or None
                        href = item.get('href', '') or None
                    else:
                        # Fallback to attribute access for other objects
                        title = getattr(item, 'title', None)
                        href = getattr(item, 'href', None)
                    
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
