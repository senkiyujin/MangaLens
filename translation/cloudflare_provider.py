import io
import json
import logging
import re
import threading
from typing import Callable, List, Tuple
from PIL import Image
import urllib.request
import urllib.error

from storage.keystore import load_api_key
import i18n

log = logging.getLogger("MangaLens.cloudflare")

def _get_auth() -> Tuple[str, str]:
    api_key = load_api_key("cloudflare")
    if not api_key:
        raise RuntimeError(i18n.t("err_cloudflare_no_key"))
    parts = api_key.strip().split(":", 1)
    if len(parts) != 2:
        raise RuntimeError(i18n.t("err_cloudflare_no_key"))
    return parts[0].strip(), parts[1].strip()

def _image_to_byte_array(image: Image.Image) -> list:
    img = image.convert("RGB")
    w, h = img.size
    max_dim = 1024
    if w > max_dim or h > max_dim:
        scale = min(max_dim / w, max_dim / h)
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
    
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return list(buf.getvalue())

def translate_image(image: Image.Image) -> str:
    try:
        account_id, token = _get_auth()
        image_bytes = _image_to_byte_array(image)
        
        from storage.keystore import load_manga_title, load_target_lang
        manga_title = load_manga_title()
        target_lang = load_target_lang()
        title_ctx = f" Bu sayfa/görsel '{manga_title}' mangasına aittir, terminolojiyi ona göre uyarla." if manga_title else ""
        
        prompt = (
            "You are an expert manga translator. "
            f"Context: {manga_title if manga_title else 'Manga page'}. "
            f"Translate the text in the image to {target_lang}.\n"
            "CRITICAL: Output ONLY the translated text. DO NOT add any explanations, notes, image descriptions, or conversational text. "
            "Just output the exact translation and nothing else."
        )

        payload = {
            "prompt": prompt,
            "image": image_bytes,
            "max_tokens": 250
        }
        
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        data = json.dumps(payload).encode("utf-8")
        
        with urllib.request.urlopen(req, data=data, timeout=30.0) as resp:
            resp_body = resp.read().decode("utf-8")
            resp_json = json.loads(resp_body)
            
            if "result" in resp_json and "response" in resp_json["result"]:
                response_obj = resp_json["result"]["response"]
                if isinstance(response_obj, (list, dict)):
                    result = json.dumps(response_obj, ensure_ascii=False)
                else:
                    result = str(response_obj).strip()
                    
                if not result:
                    return "[metin yok]"
                return result
            else:
                log.error(f"Cloudflare unexpected response: {resp_json}")
                return "[Beklenmeyen Yanıt Formatı]"
                
    except urllib.error.HTTPError as e:
        err_str = str(e).lower()
        if e.code == 429:
            msg = i18n.t("err_cloudflare_limit")
            log.error(msg)
            return msg
        body = e.read().decode('utf-8', errors='ignore')
        log.error(f"Cloudflare Hatası: HTTP {e.code} - {body}")
        return f"[Cloudflare Hatası: HTTP {e.code} - {body[:150]}]"
    except Exception as e:
        log.error(f"Cloudflare Hatası: {e}")
        return f"[Cloudflare Hatası: {str(e)[:100]}]"

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
            
    t = threading.Thread(target=_worker, daemon=True, name="CloudflareTranslate")
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
            account_id, token = _get_auth()
            image_bytes = _image_to_byte_array(image)
            
            from storage.keystore import load_manga_title, load_target_lang
            manga_title = load_manga_title()
            target_lang = load_target_lang()
            title_ctx = f" Bu sayfa '{manga_title}' mangasına aittir, terminolojiyi ona göre uyarla." if manga_title else ""
            
            prompt = (
                "You are an expert manga translator API. "
                f"Context: {manga_title if manga_title else 'Manga page'}. "
                f"Translate all speech bubbles in the image to {target_lang}.\n"
                "CRITICAL: You must output ONLY a valid JSON array. DO NOT include any conversational text, greetings, image descriptions, or explanations. "
                "The response must start with '[' and end with ']'.\n\n"
                "EXAMPLE OUTPUT:\n"
                "[\n"
                f'  {{"box_2d": [100, 150, 200, 250], "translation": "Example translation"}}\n'
                "]\n\n"
                "NOW PROCESS THE IMAGE AND OUTPUT ONLY THE JSON ARRAY:"
            )
            
            payload = {
                "prompt": prompt,
                "image": image_bytes,
                "max_tokens": 2048
            }
            
            url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
            req = urllib.request.Request(url, method="POST")
            req.add_header("Authorization", f"Bearer {token}")
            req.add_header("Content-Type", "application/json")
            data = json.dumps(payload).encode("utf-8")
            
            with urllib.request.urlopen(req, data=data, timeout=30.0) as resp:
                resp_body = resp.read().decode("utf-8")
                resp_json = json.loads(resp_body)
                
                if "result" in resp_json and "response" in resp_json["result"]:
                    response_obj = resp_json["result"]["response"]
                    if isinstance(response_obj, (list, dict)):
                        response_text = json.dumps(response_obj, ensure_ascii=False)
                    else:
                        response_text = str(response_obj).strip()
                else:
                    raise RuntimeError("Beklenmeyen yanıt formatı")
                
            # JSON bloğunu daha sağlam bir şekilde ayıkla
            clean_json = response_text.strip()
            
            # Markdown code bloğu içindeyse temizle
            if "```" in clean_json:
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', clean_json)
                if json_match:
                    clean_json = json_match.group(1).strip()
                    
            # Köşeli parantez sayacı ile tam olarak tek bir JSON dizisi çıkar (Başı ve sonundaki sohbetleri at)
            start_idx = clean_json.find('[')
            if start_idx != -1:
                bracket_count = 0
                for i in range(start_idx, len(clean_json)):
                    if clean_json[i] == '[':
                        bracket_count += 1
                    elif clean_json[i] == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            clean_json = clean_json[start_idx:i+1]
                            break
            else:
                raise ValueError(f"JSON dizisi bulunamadı. Yanıt: {response_text[:100]}...")

            try:
                items = json.loads(clean_json)
            except json.JSONDecodeError as je:
                raise ValueError(f"JSON parse hatası: {je}. Raw: {clean_json[:200]}")
            
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
        except urllib.error.HTTPError as e:
            if e.code == 429:
                on_error(i18n.t("err_cloudflare_limit"))
            else:
                body = e.read().decode('utf-8', errors='ignore')
                on_error(f"[Cloudflare FullPage Hatası: HTTP {e.code} - {body[:150]}]")
        except Exception as exc:
            on_error(f"[Cloudflare FullPage Hatası: {exc}]")

    t = threading.Thread(target=_worker, daemon=True, name="CloudflareFullPage")
    t.start()

def test_api_key(api_key: str, _is_retry: bool = False) -> Tuple[bool, str]:
    api_key = api_key.strip()
    if not api_key:
        return False, i18n.t("please_enter_api")
        
    parts = api_key.split(":", 1)
    if len(parts) != 2:
        return False, i18n.t("err_cloudflare_no_key")
        
    account_id, token = parts
    
    try:
        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id.strip()}/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
        req = urllib.request.Request(url, method="POST")
        req.add_header("Authorization", f"Bearer {token.strip()}")
        req.add_header("Content-Type", "application/json")
        data = json.dumps({"prompt": "agree"}).encode("utf-8")
        
        with urllib.request.urlopen(req, data=data, timeout=10.0) as resp:
            return True, ""
            
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            return False, i18n.t("invalid_api_key")
        elif e.code == 429:
            return False, i18n.t("err_cloudflare_limit")
        return False, f"CLOUDFLARE_RAW_ERROR: HTTP {e.code}"
    except Exception as e:
        return False, f"CLOUDFLARE_RAW_ERROR: {str(e)}"
