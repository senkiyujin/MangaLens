import os
import zipfile
from pathlib import Path
from PIL import Image
import io
import re
import logging

log = logging.getLogger("MangaLens.Library")

class Chapter:
    def __init__(self, path: str, title: str, is_archive: bool):
        self.path = path
        self.title = title
        self.is_archive = is_archive
        self._pages = []
    
    def load_pages(self):
        if self._pages: return self._pages
        valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
        
        if self.is_archive:
            try:
                with zipfile.ZipFile(self.path, 'r') as z:
                    self._pages = [f for f in z.namelist() if not f.endswith('/') and Path(f).suffix.lower() in valid_exts]
            except Exception as e:
                log.error(f"Error reading zip {self.path}: {e}")
        else:
            self._pages = [f for f in os.listdir(self.path) if Path(f).suffix.lower() in valid_exts]
            
        # Natural sort
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        self._pages.sort(key=natural_sort_key)
        return self._pages
        
    def get_page_image(self, index: int) -> Image.Image:
        pages = self.load_pages()
        if not pages or index < 0 or index >= len(pages):
            return None
            
        page_name = pages[index]
        if self.is_archive:
            with zipfile.ZipFile(self.path, 'r') as z:
                data = z.read(page_name)
                return Image.open(io.BytesIO(data))
        else:
            return Image.open(os.path.join(self.path, page_name))

class Series:
    def __init__(self, path: str, title: str):
        self.path = path
        self.title = title
        self.chapters = []
        self.cover_path = None
        
    def scan_chapters(self):
        self.chapters = []
        self.cover_path = None
        for item in os.listdir(self.path):
            full_path = os.path.join(self.path, item)
            
            if os.path.isdir(full_path):
                valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                has_imgs = any(Path(f).suffix.lower() in valid_exts for f in os.listdir(full_path))
                if has_imgs:
                    self.chapters.append(Chapter(full_path, item, is_archive=False))
                    
            elif os.path.isfile(full_path):
                ext = Path(full_path).suffix.lower()
                if ext in {'.zip', '.cbz'}:
                    self.chapters.append(Chapter(full_path, Path(full_path).stem, is_archive=True))
                elif item.lower().startswith('cover') and ext in {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}:
                    self.cover_path = full_path
        
        self.chapters.sort(key=lambda c: os.path.getctime(c.path))

class LibraryManager:
    def __init__(self):
        docs = Path.home() / "Documents"
        self.base_dir = docs / "MangaLensLibrary"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.series = []
        
    def scan_library(self):
        self.series = []
        if not self.base_dir.exists():
            return
            
        for item in os.listdir(self.base_dir):
            full_path = self.base_dir / item
            if full_path.is_dir():
                series_obj = Series(str(full_path), item)
                series_obj.scan_chapters()
                self.series.append(series_obj)
        self.series.sort(key=lambda s: os.path.getctime(s.path))

    def delete_series(self, title: str):
        import shutil
        target_dir = self.base_dir / title
        if target_dir.exists() and target_dir.is_dir():
            shutil.rmtree(target_dir)
        self.scan_library()

    def delete_chapter(self, series_title: str, chapter_path: str):
        import shutil
        import os
        from pathlib import Path
        
        path = Path(chapter_path)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                os.remove(path)
                
        self.scan_library()