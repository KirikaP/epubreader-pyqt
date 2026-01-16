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
        self._chapter_map: Dict[str, int] = {}  # 新增：章节文件名到索引的映射

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
            
            # 新增：构建章节文件名到索引的映射
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
        """获取目录（保持原接口）"""
        return self._book.toc if self._book else []

    def get_flat_toc(self) -> list:
        """获取扁平化的目录列表，每个元素为 (标题, 章节索引, 层级)"""
        if not self._book:
            return []
        
        flat_toc = []
        
        def process_items(items, level=0):
            for item in items:
                if hasattr(item, '__iter__') and not isinstance(item, (str, bytes)):
                    # 这是一个可迭代对象（如元组或列表），可能是嵌套结构
                    process_items(item, level)
                else:
                    # 尝试获取标题和链接
                    title = None
                    href = None
                    
                    # 检查不同类型
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
                    
                    # 如果是 Link 对象（最常见的类型）- 修正为 epub.Link
                    if isinstance(item, epub.Link):
                        title = title or item.title
                        href = href or item.href
                    
                    if title:
                        # 查找对应的章节索引
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
            print(f"解析目录时出错: {e}")
            # 返回空列表或基本目录作为后备
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
        """根据href查找章节索引"""
        if not href:
            return None
            
        # 提取文件名部分
        filename = os.path.basename(unquote(href))
        
        # 直接查找
        if filename in self._chapter_map:
            return self._chapter_map[filename]
        
        # 尝试不带查询参数
        if '?' in filename:
            base_name = filename.split('?')[0]
            if base_name in self._chapter_map:
                return self._chapter_map[base_name]
        
        # 尝试查找包含该文件名的章节
        for chapter_idx, chapter in enumerate(self._chapters):
            if filename in chapter.get_name():
                return chapter_idx
        
        return None

    def chapter_count(self) -> int:
        """获取章节数量"""
        return len(self._chapters)

    def __del__(self):
        """清理线程池"""
        self._executor.shutdown(wait=False)
