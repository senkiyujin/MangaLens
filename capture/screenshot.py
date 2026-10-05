"""
capture/screenshot.py — In-memory screen region capture.

Yöntem:
1. GDI tabanlı ctypes yakalama (Windows'ta %100 kararlı, App Control / BitBlt hataları yaşanmaz).
2. Fallback: PIL.ImageGrab.
Hiçbir şey diske yazılmaz — görüntü sadece bellekte tutulur.
"""

from __future__ import annotations

import ctypes
import struct
from typing import List, Tuple, Optional
from PIL import Image, ImageGrab

from translation.magic_wand import find_bubble_bbox


def _grab_screen_gdi(bbox: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
    """
    Windows GDI kullanarak ekran veya bölge görüntüsü alır.
    PIL.ImageGrab'ın 'screen grab failed' hatalarını %100 önler.
    """
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    if bbox is None:
        # Sanal ekran boyutları (tüm monitörler)
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        w = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        h = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        if w <= 0 or h <= 0:
            x, y = 0, 0
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
    else:
        left, top, right, bottom = bbox
        x, y = left, top
        w = max(1, right - left)
        h = max(1, bottom - top)

    hdcScreen = user32.GetDC(0)
    hdcMem = gdi32.CreateCompatibleDC(hdcScreen)
    hbmScreen = gdi32.CreateCompatibleBitmap(hdcScreen, w, h)
    oldBmp = gdi32.SelectObject(hdcMem, hbmScreen)

    # SRCCOPY = 0x00CC0020
    gdi32.BitBlt(hdcMem, 0, 0, w, h, hdcScreen, x, y, 0x00CC0020)

    header = struct.pack('<IiihhIIII', 40, w, -h, 1, 32, 0, 0, 0, 0)
    buffer = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdcScreen, hbmScreen, 0, h, buffer, header, 0)

    img = Image.frombytes('RGBA', (w, h), buffer.raw, 'raw', 'BGRA').convert('RGB')

    gdi32.SelectObject(hdcMem, oldBmp)
    gdi32.DeleteObject(hbmScreen)
    gdi32.DeleteDC(hdcMem)
    user32.ReleaseDC(0, hdcScreen)

    return img


def capture_region(x: int, y: int, width: int, height: int) -> Image.Image:
    """
    Ekranın belirtilen dikdörtgen bölgesini yakalar.
    Döndürülen PIL Image sadece bellektedir.
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Geçersiz bölge: {width}x{height}")

    bbox = (x, y, x + width, y + height)
    try:
        return _grab_screen_gdi(bbox)
    except Exception:
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        return img.convert("RGB")


def capture_bounding_box(
    points: List[Tuple[int, int]],
) -> Tuple[Image.Image, Tuple[int, int, int, int]]:
    """
    Lasso noktalarının bounding box'ını hesaplar ve o bölgeyi yakalar.
    Döndürür: (PIL Image, (left, top, width, height))
    """
    if not points:
        raise ValueError("Nokta listesi boş.")

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    left   = min(xs)
    top    = min(ys)
    right  = max(xs)
    bottom = max(ys)
    width  = right  - left
    height = bottom - top

    if width <= 0 or height <= 0:
        raise ValueError(f"Bounding box sıfır boyutlu: {width}x{height}")

    img = capture_region(left, top, width, height)
    return img, (left, top, width, height)


def capture_magic_wand(click_x: int, click_y: int) -> Tuple[Optional[Image.Image], Optional[Tuple[int, int, int, int]]]:
    """
    Sihirli Değnek: Hız optimizasyonu için tüm ekran yerine tıklanan noktanın etrafındaki
    1200x1200px'lik alanı yakalayarak ekran yakalama ve OpenCV hızını önemli ölçüde artırır.
    """
    REGION_SIZE = 1200
    half_size = REGION_SIZE // 2
    
    left = click_x - half_size
    top = click_y - half_size

    try:
        img_region = capture_region(left, top, REGION_SIZE, REGION_SIZE)
    except Exception:
        img_region = ImageGrab.grab(all_screens=True).convert("RGB")
        left, top = 0, 0  # Fallback to full screen coordinates

    local_click_x = click_x - left
    local_click_y = click_y - top

    bbox_local = find_bubble_bbox(img_region, local_click_x, local_click_y)
    
    if not bbox_local:
        return None, None
        
    l, t, w, h = bbox_local
    img_cropped = img_region.crop((l, t, l + w, t + h))
    
    bbox_abs = (left + l, top + t, w, h)
    return img_cropped, bbox_abs


def capture_full_page_and_bubbles() -> Tuple[Image.Image, List[Tuple[int, int, int, int]]]:
    """
    Tam Sayfa Modu: Tüm ekranı yakalar ve OpenCV ile içindeki tüm balonların bboxes listesini bulur.
    Döndürür: (Tam Ekran Görüntüsü, list[(left, top, width, height)])
    """
    from translation.magic_wand import find_all_bubbles
    try:
        img_full = _grab_screen_gdi(None)
    except Exception:
        img_full = ImageGrab.grab(all_screens=True).convert("RGB")

    bboxes = find_all_bubbles(img_full)
    return img_full, bboxes
