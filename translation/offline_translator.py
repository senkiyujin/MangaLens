import os
import json
import logging
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time
from pathlib import Path

log = logging.getLogger("MangaLens.OfflineTranslator")

_reader = None

def init_easyocr():
    global _reader
    if _reader is None:
        try:
            import easyocr
            # We use 'en' by default, since most scans are english before translation.
            _reader = easyocr.Reader(['en'], gpu=False)
        except Exception as e:
            log.error(f"Failed to initialize EasyOCR: {e}")
            raise e

def _get_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        # Try a manga-friendly default font or fallback to Arial
        return ImageFont.truetype("comic.ttf", size)
    except IOError:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except IOError:
            return ImageFont.load_default()

def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    lines = []
    words = text.split()
    current_line = []
    
    for word in words:
        current_line.append(word)
        # getbbox returns (left, top, right, bottom)
        bbox = font.getbbox(" ".join(current_line))
        line_w = bbox[2] - bbox[0] if bbox else 0
        if line_w > max_width:
            if len(current_line) > 1:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
                
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)

def process_page(img_path: str, manga_title: str, status_callback=None) -> bool:
    init_easyocr()
    
    # 1. Load image with OpenCV for inpainting and Pillow for drawing
    # Read using numpy to handle unicode paths in Windows just in case
    stream = open(img_path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img_cv = cv2.imdecode(numpyarray, cv2.IMREAD_COLOR)
    stream.close()
    
    if img_cv is None:
        log.error(f"Could not read image: {img_path}")
        return False
        
    img_pil = Image.open(img_path).convert("RGB")
    img_np = np.array(img_pil)
    
    # 2. Extract text blocks
    # Fix OCR: paragraph=True merges texts naturally. mag_ratio=1.0 is default and most stable.
    ocr_results = _reader.readtext(img_np, paragraph=True)
    blocks = []
    for res in ocr_results:
        if len(res) == 3:
            bbox, text, conf = res
        else:
            bbox, text = res
            conf = 1.0
            
        if len(text.strip()) < 2:
            continue
            
        xs = [int(pt[0]) for pt in bbox]
        ys = [int(pt[1]) for pt in bbox]
        l, t, r, b = min(xs), min(ys), max(xs), max(ys)
        
        merged = False
        for block in blocks:
            bl, bt, br, bb = block['bbox']
            btext = block['text']
            # If vertically close and horizontally overlapping
            if abs(t - bb) < 40 and not (r < bl or l > br):
                new_l, new_t = min(bl, l), min(bt, t)
                new_r, new_b = max(br, r), max(bb, b)
                block['bbox'] = (new_l, new_t, new_r, new_b)
                block['text'] = btext + " " + text
                merged = True
                break
                
        if not merged:
            blocks.append({'bbox': (l, t, r, b), 'text': text})
            
    if not blocks:
        return True # Nothing to translate
        
    # 3. Translate with Gemini
    text_dict = {str(i+1): b['text'] for i, b in enumerate(blocks)}
    
    from storage.keystore import load_api_key
    import google.generativeai as genai
    key = load_api_key("gemini")
    if not key:
        log.error("No Gemini API key found.")
        return False
        
    genai.configure(api_key=key)
    
    prompt = f"""Sen dünya çapında ödüllü bir Manga ve Çizgi Roman Çevirmenisin. Görevin '{manga_title}' mangasının sayfalarından çıkarılan metinleri Türkçe'ye mükemmel bir yerelleştirmeyle (localization) aktarmak.

ÇOK ÖNEMLİ KURAL: Sana verilen JSON'daki HİÇBİR ANAHTARI (KEY) SİLME VE EKSİLTME! Eğer 15 numara varsa, cevabında da tam 15 numara olmak ZORUNDA. Asla farklı numaralardaki metinleri birleştirip tek bir kutuya doldurmaya çalışma!

ALTIN KURALLAR:

1. BAĞIMSIZ AMA BAĞLAMLI ÇEVİRİ (HALÜSİNASYON YASAK!):
JSON'daki her bir numarayı KENDİ İÇİNDE bağımsız olarak çevir. Başka kutulardaki yazılarla birleştirip devasa, uydurma bir hikaye yazmaya kalkma (halüsinasyon yapma)! Diğer metinlere sadece "konuyu ve bağlamı anlamak" için göz at. Örneğin, bir kutuda sadece "SCARY" yazıyorsa, bunu sadece "KORKUNÇ" veya "ÜRKÜTÜCÜ" olarak çevir; "Seni yerin dibine soktu mu?" gibi kafandan asla yeni cümleler uydurma.

2. MANGA JARGONU VE EVRENİ:
Bu manga: '{manga_title}'. Çeviriyi yaparken o evrenin jargonunu KESİNLİKLE koru. "Underclassmen" kelimesini "Alt sınıflar" veya "Çömezler" olarak manga diline uyarla.

3. DOĞALLIK (ROBOTİK ÇEVİRİ YASAK!):
TRT dublajı veya Google Translate çevirilerinden kaçın. "Kendini daha iyi hissetmeni sağlar!" yerine "Bunu ye, iyi gelir!" de. Doğal, akıcı ve karaktere uygun sokak ağzı kullan.

İngilizce Metinler:
{json.dumps(text_dict, ensure_ascii=False)}
SADECE geçerli bir JSON döndür! Markdown OLMASIN! JSON'da sana verilen BÜTÜN numaralar EKSİKSİZ bulunsun!"""
    
    translated_dict = {}
    import time
    for attempt in range(2): # Up to 2 retries for rate limits
        try:
            model = genai.GenerativeModel('gemini-flash-lite-latest')
            res = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                )
            )
            time.sleep(4) # Base delay to prevent hitting 15 RPM
            text = res.text.strip()
            if text.startswith('```json'): text = text[7:]
            elif text.startswith('```'): text = text[3:]
            if text.endswith('```'): text = text[:-3]
            translated_dict = json.loads(text.strip())
            break # Success!
        except Exception as e:
            err_msg = str(e)
            # If it's a 429 or Quota error, wait 20 seconds and try again
            if "429" in err_msg or "Quota" in err_msg or "ResourceExhausted" in err_msg:
                msg = f"API Kotası (Rate Limit) Doldu! 20 saniye bekleniyor... (Deneme {attempt+1}/2)"
                print(msg)
                if status_callback:
                    status_callback(msg)
                time.sleep(20)
                continue
            else:
                print(f"Gemini translation failed with unrecoverable error: {e}")
                import traceback
                traceback.print_exc()
                return False
    else:
        print("Gemini API limit reached!")
        raise Exception("API Kotanız tamamen doldu (Günlük limit aşımı)! Lütfen uygulamanın Ayarlar sekmesinden yeni bir Gemini API Anahtarı girin.")

    # 4. Draw Dark Tooltip style boxes over original text
    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    final_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(final_img)
    
    # Load Arial Bold to match the UI style
    ui_font = "arialbd.ttf"
    if not os.path.exists("C:\\Windows\\Fonts\\arialbd.ttf"):
        ui_font = "arial.ttf"
        
    def get_ui_font(size):
        try:
            return ImageFont.truetype(ui_font, size)
        except:
            return ImageFont.load_default()
    
    for i, block in enumerate(blocks):
        idx_str = str(i+1)
        if idx_str not in translated_dict:
            continue
            
        # Clean AI glitches like hyphens or underscores
        translated_text = translated_dict[idx_str].replace("- ", "").replace("-", "").replace("_", "")
        
        l, t, r, b = block['bbox']
        
        # Base box size
        box_w = r - l
        box_h = b - t
        
        # We will use a classic Manga aesthetic: White background, Black text, Thin black outline
        bg_color = (255, 255, 255)
        text_color = (0, 0, 0)
        border_color = (0, 0, 0)
        
        # Strict padding to ensure we don't cover the manga art unnecessarily
        inner_pad = 8
        max_text_w = max(30, box_w)
        max_text_h = max(20, box_h + 10)
        
        font_size = 14
        font = get_ui_font(font_size)
        wrapped_text = ""
        
        # Find a font size that fits perfectly. Shrink aggressively if needed down to size 8.
        for sz in range(32, 7, -1):
            f = get_ui_font(sz)
            wt = wrap_text(translated_text, f, max_text_w)
            bbox = draw.textbbox((0, 0), wt, font=f)
            tw = bbox[2] - bbox[0] if bbox else 0
            th = bbox[3] - bbox[1] if bbox else 0
            
            # If it fits within the original width and height constraints
            if th <= max_text_h and tw <= max_text_w:
                font_size = sz
                font = f
                wrapped_text = wt
                break
        else:
            # If it STILL doesn't fit even at size 8, we just use size 10 and accept a slight overflow
            font_size = 10
            font = get_ui_font(font_size)
            wrapped_text = wrap_text(translated_text, font, max_text_w + 20)
            
        # Get exact dimensions of the finalized text
        bbox = draw.textbbox((0, 0), wrapped_text, font=font)
        final_tw = bbox[2] - bbox[0] if bbox else 0
        final_th = bbox[3] - bbox[1] if bbox else 0
        
        # Calculate the final sticker box. It should cover the original text, but expand slightly if the Turkish text is wider.
        final_box_w = max(box_w + 8, final_tw + inner_pad)
        final_box_h = max(box_h + 8, final_th + inner_pad)
        
        # Center the new box exactly where the original text was
        cx = l + box_w / 2
        cy = t + box_h / 2
        
        new_l = int(cx - final_box_w / 2)
        new_t = int(cy - final_box_h / 2)
        new_r = int(cx + final_box_w / 2)
        new_b = int(cy + final_box_h / 2)
        
        # 1. Draw the pristine white sticker box to cover the English text completely
        # width=2 for a subtle comic-book style balloon border
        draw.rectangle([new_l, new_t, new_r, new_b], fill=bg_color, outline=border_color, width=2)
        
        # 2. Draw text perfectly centered
        text_x = new_l + (final_box_w - final_tw) / 2
        text_y = new_t + (final_box_h - final_th) / 2
        
        draw.multiline_text(
            (text_x, text_y), 
            wrapped_text, 
            fill=text_color, 
            font=font, 
            align="center"
        )
        
    # 5. Save the image
    final_img.save(img_path)
    return True
