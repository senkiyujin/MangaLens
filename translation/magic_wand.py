import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, List


def find_bubble_bbox(image: Image.Image, click_x: int, click_y: int) -> Optional[Tuple[int, int, int, int]]:
    """
    Given a full screen image and a click coordinate, uses OpenCV floodFill
    to find the boundaries of the white manga bubble and returns a bounding box
    (left, top, width, height).
    Returns None if detection fails or region is too small/large.
    """
    img_gray = np.array(image.convert("L"))
    h, w = img_gray.shape

    if not (0 <= click_x < w and 0 <= click_y < h):
        return None

    seed_x, seed_y = click_x, click_y
    search_radius = 20
    y_min = max(0, click_y - search_radius)
    y_max = min(h, click_y + search_radius)
    x_min = max(0, click_x - search_radius)
    x_max = min(w, click_x + search_radius)

    region = img_gray[y_min:y_max, x_min:x_max]
    if region.size > 0:
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(region)
        seed_x = x_min + max_loc[0]
        seed_y = y_min + max_loc[1]

    mask = np.zeros((h + 2, w + 2), np.uint8)
    lo_diff = 40
    up_diff = 40
    flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY | cv2.FLOODFILL_FIXED_RANGE

    cv2.floodFill(img_gray, mask, (seed_x, seed_y), 0, lo_diff, up_diff, flags)
    active_pixels = cv2.findNonZero(mask[1:-1, 1:-1])

    if active_pixels is None:
        return None

    x, y, bw, bh = cv2.boundingRect(active_pixels)

    if bw * bh > (w * h * 0.8) or bw < 20 or bh < 20:
        return None

    padding = 15
    left = max(0, x - padding)
    top = max(0, y - padding)
    right = min(w, x + bw + padding)
    bottom = min(h, y + bh + padding)

    width = right - left
    height = bottom - top

    return (left, top, width, height)


def find_all_bubbles(image: Image.Image) -> List[Tuple[int, int, int, int]]:
    """
    Tam Sayfa Modu: Ekrandaki tüm konuşma balonlarını OpenCV RETR_LIST ile tespit eder.
    Fiziksel ekran pikselleri bazında %100 hassas koordinat döner.
    Manga okuma sırasına göre (Yukarıdan aşağıya, Sağdan sola) dizeler.
    """
    img_gray = np.array(image.convert("L"))
    h_img, w_img = img_gray.shape

    thresh = cv2.adaptiveThreshold(img_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    bboxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        # Çok daha esnek boyut filtrelemesi (küçük balonları da yakalar)
        if 1000 < area < (w_img * h_img * 0.40) and 25 < w < (w_img * 0.8) and 25 < h < (h_img * 0.8):
            roi = img_gray[y:y + h, x:x + w]
            # Balonun içi genellikle beyazdır (ortalama > 160)
            if np.mean(roi) > 160:
                bboxes.append((x, y, w, h))

    # Kapsayıcı kutuları büyüklüğüne göre sırala (Önce en büyükler)
    bboxes.sort(key=lambda b: b[2] * b[3], reverse=True)

    # Merkez bazlı overlap (iç içe geçenleri temizle)
    clean_bboxes = []
    for b in bboxes:
        bx, by, bw, bh = b
        overlap = False
        b_center = (bx + bw/2, by + bh/2)
        
        for cb in clean_bboxes:
            cx, cy, cw, ch = cb
            # Eğer b'nin merkezi, cb'nin (daha büyük kutu) içindeyse, b alt kutudur, yoksay.
            if cx < b_center[0] < cx + cw and cy < b_center[1] < cy + ch:
                overlap = True
                break
                
        if not overlap:
            clean_bboxes.append(b)

    # Manga okuma sırası: Yukarıdan aşağıya, sağdan sola
    clean_bboxes.sort(key=lambda b: (b[1] // 150, -b[0]))
    return clean_bboxes
