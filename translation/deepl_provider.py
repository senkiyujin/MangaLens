import logging
import threading
from typing import Callable, List, Tuple
from PIL import Image
import numpy as np

import deepl
from storage.keystore import load_api_key
import i18n

log = logging.getLogger("MangaLens.deepl")

_client = None
_client_lock = threading.Lock()

def _get_client():
    global _client
    with _client_lock:
        if _client is not None:
            return _client
        api_key = load_api_key("deepl")
        if not api_key:
            raise RuntimeError("DeepL API Key bulunamadı. Lütfen Ayarlar'dan girin.")
        _client = deepl.Translator(api_key.strip())
        return _client

_DEEPL_LANG_MAP = {
    "Türkçe": "TR",
    "English": "EN-US",
    "Español": "ES",
    "Français": "FR",
    "Deutsch": "DE",
    "Italiano": "IT",
    "Português": "PT-PT",
    "Русский": "RU",
    "日本語": "JA",
    "한국어": "KO",
    "中文": "ZH"
}

def translate_image(image: Image.Image) -> str:
    try:
        client = _get_client()
        from translation.gemini_provider import _get_ocr_reader
        reader = _get_ocr_reader()
        if not reader:
            return "[OCR Motoru Başlatılamadı]"
        
        img_rgb = image.convert("RGB")
        img_np = np.array(img_rgb)
        
        ocr_results = reader.readtext(img_np)
        if not ocr_results:
            return "[metin yok]"
            
        texts = [res[1] for res in ocr_results if res[2] >= 0.3 and len(res[1].strip()) > 1]
        if not texts:
            return "[metin yok]"
            
        combined_text = "\n\n".join(texts)
        
        from storage.keystore import load_target_lang
        target_lang = load_target_lang()
        deepl_lang_code = _DEEPL_LANG_MAP.get(target_lang, "TR")
        
        response = client.translate_text(combined_text, target_lang=deepl_lang_code)
        
        result = response.text.strip()
        if not result:
            return "[metin yok]"
        return result
    except Exception as e:
        err_str = str(e).lower()
        if "quota" in err_str or "limit" in err_str or "429" in err_str or "456" in err_str:
            msg = "DeepL API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
            log.error(msg)
            return msg
        log.error(f"DeepL çeviri hatası: {e}")
        return f"[DeepL Hatası: {str(e)[:100]}]"

def translate_image_async(
    image: Image.Image,
    on_success: Callable[[str], None],
    on_error: Callable[[str], None],
) -> None:
    def _worker():
        try:
            result = translate_image(image)
            on_success(result)
        except Exception as exc:
            on_error(f"[Hata: {exc}]")
            
    t = threading.Thread(target=_worker, daemon=True, name="DeepLTranslate")
    t.start()

def translate_full_page_async(
    image: Image.Image,
    screen_w: int,
    screen_h: int,
    offset_x: int,
    offset_y: int,
    is_panel: bool,
    on_success: Callable[[List[Tuple[Tuple[int, int, int, int], str]]], None],
    on_error: Callable[[str], None],
) -> None:
    def _worker():
        try:
            client = _get_client()
            
            from translation.gemini_provider import _get_ocr_reader
            reader = _get_ocr_reader()
            if not reader:
                on_error("[OCR Motoru Başlatılamadı]")
                return
                
            img_rgb = image.convert("RGB")
            real_w, real_h = img_rgb.size
            sw = screen_w if screen_w > 0 else real_w
            sh = screen_h if screen_h > 0 else real_h

            scale_x = sw / real_w
            scale_y = sh / real_h

            max_ocr_dim = 800 if is_panel else 1200
            cw, ch = img_rgb.size
            ocr_scale = min(max_ocr_dim / cw, max_ocr_dim / ch)
            if ocr_scale < 1.0:
                ocr_w, ocr_h = int(cw * ocr_scale), int(ch * ocr_scale)
                img_ocr = img_rgb.resize((ocr_w, ocr_h), Image.Resampling.LANCZOS)
            else:
                ocr_scale = 1.0
                img_ocr = img_rgb

            img_np = np.array(img_ocr)
            ocr_results = reader.readtext(img_np)

            if not ocr_results:
                on_success([])
                return

            blocks = []
            for res in ocr_results:
                bbox, text, conf = res
                if conf < 0.30 or len(text.strip()) < 2:
                    continue
                    
                xs = [int((pt[0] / ocr_scale) * scale_x) for pt in bbox]
                ys = [int((pt[1] / ocr_scale) * scale_y) for pt in bbox]
                l, t, r, b = min(xs), min(ys), max(xs), max(ys)
                
                merged = False
                for block in blocks:
                    bl, bt, br, bb = block['bbox']
                    btext = block['text']
                    
                    if abs(t - bb) < 50 and not (r < bl - 20 or l > br + 20):
                        new_l = min(bl, l)
                        new_t = min(bt, t)
                        new_r = max(br, r)
                        new_b = max(bb, b)
                        block['bbox'] = (new_l, new_t, new_r, new_b)
                        block['text'] = btext + " " + text
                        merged = True
                        break
                        
                if not merged:
                    blocks.append({'bbox': (l, t, r, b), 'text': text})

            if not blocks:
                on_success([])
                return
                
            from storage.keystore import load_manga_title
            manga_title = load_manga_title()

            # Batch translation with DeepL using ThreadPoolExecutor for concurrency
            import concurrent.futures
            
            results = []
            
            def translate_single_block(block):
                text = block['text']
                from storage.keystore import load_target_lang
                target_lang = load_target_lang()
                deepl_lang_code = _DEEPL_LANG_MAP.get(target_lang, "TR")
                
                # DeepL call - context parametresine Manga Adını vererek daha iyi çeviri al
                kwargs = {"target_lang": deepl_lang_code}
                if manga_title:
                    kwargs["context"] = f"Translating lines from the manga series '{manga_title}'"
                    
                res = client.translate_text(text, **kwargs)
                tr_text = res.text.strip()
                if tr_text:
                    l, t, r, b = block['bbox']
                    w = r - l
                    h = b - t
                    
                    screen_left = int(l) + offset_x
                    screen_top = int(t) + offset_y
                    screen_bw = max(40, int(w))
                    screen_bh = max(25, int(h))
                    
                    padding_x = 5
                    padding_y = 5
                    
                    return (
                        (max(0, screen_left - padding_x), 
                         max(0, screen_top - padding_y), 
                         screen_bw + padding_x*2, 
                         screen_bh + padding_y*2), 
                        str(tr_text)
                    )
                return None

            log.info(f"DeepL ile {len(blocks)} adet balon paralel (eşzamanlı) olarak çevriliyor...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(translate_single_block, b) for b in blocks]
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        results.append(res)
            
            on_success(results)
        except Exception as exc:
            err_str = str(exc).lower()
            if "quota" in err_str or "limit" in err_str or "429" in err_str or "456" in err_str:
                msg = "DeepL API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
                on_error(msg)
            else:
                on_error(f"[DeepL FullPage Hatası: {exc}]")

    t = threading.Thread(target=_worker, daemon=True, name="DeepLFullPage")
    t.start()

def test_api_key(api_key: str) -> Tuple[bool, str]:
    api_key = api_key.strip()
    if not api_key:
        return False, i18n.t("please_enter_api")
    try:
        test_client = deepl.Translator(api_key)
        usage = test_client.get_usage()
        if usage.any_limit_reached:
            return False, i18n.t("err_deepl_limit")
            
        global _client
        with _client_lock:
            _client = test_client
            
        return True, ""
    except Exception as e:
        err_str = str(e).lower()
        if "authorization" in err_str or "invalid" in err_str:
            return False, i18n.t("invalid_api_key")
        elif "connection" in err_str or "network" in err_str:
            return False, i18n.t("connection_failed")
        return False, f"Error:\n{str(e)}"
