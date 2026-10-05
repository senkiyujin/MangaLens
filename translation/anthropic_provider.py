import io
import json
import logging
import re
import threading
from typing import Callable, List, Tuple
from PIL import Image
import base64

import anthropic
from storage.keystore import load_api_key
import i18n

log = logging.getLogger("MangaLens.anthropic")

_client = None
_client_lock = threading.Lock()

def _get_client():
    global _client
    with _client_lock:
        if _client is not None:
            return _client
        api_key = load_api_key("anthropic")
        if not api_key:
            raise RuntimeError("Anthropic API Key bulunamadı. Lütfen Ayarlar'dan girin.")
        _client = anthropic.Anthropic(api_key=api_key.strip())
        return _client

def _image_to_base64_and_type(image: Image.Image) -> Tuple[str, str]:
    img = image.convert("RGB")
    w, h = img.size
    max_dim = 1024
    if w > max_dim or h > max_dim:
        scale = min(max_dim / w, max_dim / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode('utf-8'), "image/jpeg"

def translate_image(image: Image.Image) -> str:
    try:
        client = _get_client()
        base64_image, media_type = _image_to_base64_and_type(image)
        
        from storage.keystore import load_manga_title, load_target_lang
        manga_title = load_manga_title()
        target_lang = load_target_lang()
        title_ctx = f" Bu sayfa '{manga_title}' mangasına aittir, terminolojiyi ona göre uyarla." if manga_title else ""
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=150,
            temperature=0.0,
            system=(
                "Sen profesyonel bir manga çevirmenisin. "
                f"Görseldeki metnin kaynak dilini otomatik algıla ve {target_lang} diline YERELLEŞTİR."
                f"{title_ctx} "
                "SADECE çevrilmiş metni yaz, açıklama ekleme."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": "Bu manga panelindeki metni çevir."
                        }
                    ]
                }
            ]
        )
        
        result = response.content[0].text.strip()
        if not result:
            return "[metin yok]"
        return result
    except Exception as e:
        err_str = str(e).lower()
        if "credit" in err_str or "429" in err_str or "balance" in err_str:
            msg = "Claude API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
            log.error(msg)
            return msg
        log.error(f"Anthropic çeviri hatası: {e}")
        return f"[Anthropic Hatası: {str(e)[:100]}]"

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
            
    t = threading.Thread(target=_worker, daemon=True, name="AnthropicTranslate")
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
            base64_image, media_type = _image_to_base64_and_type(image)
            
            from storage.keystore import load_manga_title, load_target_lang
            manga_title = load_manga_title()
            target_lang = load_target_lang()
            title_ctx = f" Bu sayfa '{manga_title}' mangasına aittir, terminolojiyi ona göre uyarla." if manga_title else ""
            
            prompt = (
                "Bu bir manga sayfası görüntüsüdür.\n"
                f"Görseldeki TÜM konuşma balonlarının yerini tespit et, kaynak dili otomatik algıla ve doğal bir şekilde {target_lang} diline yerelleştir.\n"
                "Yanıtı SADECE şu geçerli JSON dizisi olarak ver:\n"
                "[\n"
                f'  {{"box_2d": [ymin, xmin, ymax, xmax], "translation": "Çeviri Metni"}}\n'
                "]\n"
                "Koordinatlar 0 ile 1000 arasında oransal değerler olmalıdır (ymin, xmin, ymax, xmax)."
            )

            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                temperature=0.0,
                system=f"Sen profesyonel bir manga çevirmenisisin.{title_ctx}",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            
            response_text = response.content[0].text.strip()
            clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", response_text, flags=re.MULTILINE)
            items = json.loads(clean_json)
            
            cw, ch = image.size
            scale_x = (screen_w if screen_w > 0 else cw) / cw
            scale_y = (screen_h if screen_h > 0 else ch) / ch
            
            results = []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        text = item.get("translation") or item.get("turkish_translation") or item.get("text") or ""
                        box = item.get("box_2d") or []
                        if text and len(box) == 4:
                            ymin, xmin, ymax, xmax = box
                            img_left = int(xmin * cw / 1000)
                            img_top = int(ymin * ch / 1000)
                            crop_bw = int((xmax - xmin) * cw / 1000)
                            crop_bh = int((ymax - ymin) * ch / 1000)

                            screen_left = int(img_left * scale_x) + offset_x
                            screen_top = int(img_top * scale_y) + offset_y
                            screen_bw = max(40, int(crop_bw * scale_x))
                            screen_bh = max(25, int(crop_bh * scale_y))

                            results.append(((screen_left, screen_top, screen_bw, screen_bh), text))
            on_success(results)
        except Exception as exc:
            err_str = str(exc).lower()
            if "credit" in err_str or "429" in err_str or "balance" in err_str:
                msg = "Claude API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
                on_error(msg)
            else:
                on_error(f"[Anthropic FullPage Hatası: {exc}]")

    t = threading.Thread(target=_worker, daemon=True, name="AnthropicFullPage")
    t.start()

def test_api_key(api_key: str) -> Tuple[bool, str]:
    api_key = api_key.strip()
    if not api_key:
        return False, i18n.t("please_enter_api")
    try:
        test_client = anthropic.Anthropic(api_key=api_key)
        response = test_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}]
        )
        if response:
            global _client
            with _client_lock:
                _client = test_client
            return True, ""
        return False, i18n.t("failed")
    except Exception as e:
        err_str = str(e).lower()
        if "authentication" in err_str or "invalid" in err_str:
            return False, i18n.t("invalid_api_key")
        elif "credit" in err_str or "balance" in err_str or "quota" in err_str:
            return False, i18n.t("err_claude_limit")
        elif "connection" in err_str or "network" in err_str:
            return False, i18n.t("connection_failed")
        return False, f"Error:\n{str(e)}"
