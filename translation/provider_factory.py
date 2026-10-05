from typing import Callable, List, Tuple
from PIL import Image
import logging

log = logging.getLogger("MangaLens.factory")

# Global provider modules will be loaded lazily
_gemini = None
_openai = None
_anthropic = None
_nvidia = None
_deepl = None
_deepseek = None
_cloudflare = None

def _get_provider_module(provider_name: str):
    global _gemini, _openai, _anthropic, _nvidia, _deepl, _deepseek, _cloudflare
    if provider_name == "gemini":
        if _gemini is None:
            import translation.gemini_provider as gemini_provider
            _gemini = gemini_provider
        return _gemini
    elif provider_name == "openai":
        if _openai is None:
            import translation.openai_provider as openai_provider
            _openai = openai_provider
        return _openai
    elif provider_name == "anthropic":
        if _anthropic is None:
            import translation.anthropic_provider as anthropic_provider
            _anthropic = anthropic_provider
        return _anthropic
    elif provider_name == "nvidia":
        if _nvidia is None:
            import translation.nvidia_provider as nvidia_provider
            _nvidia = nvidia_provider
        return _nvidia
    elif provider_name == "deepl":
        if _deepl is None:
            import translation.deepl_provider as deepl_provider
            _deepl = deepl_provider
        return _deepl
    elif provider_name == "deepseek":
        if _deepseek is None:
            import translation.deepseek_provider as deepseek_provider
            _deepseek = deepseek_provider
        return _deepseek

    elif provider_name == "cloudflare":
        if _cloudflare is None:
            import translation.cloudflare_provider as cloudflare_provider
            _cloudflare = cloudflare_provider
        return _cloudflare
    
    else:
        # fallback
        if _gemini is None:
            import translation.gemini_provider as gemini_provider
            _gemini = gemini_provider
        return _gemini

def translate_image_async(
    provider_name: str,
    image: Image.Image,
    on_success: Callable[[str], None],
    on_error: Callable[[str], None],
    on_status: Callable[[str], None] = None,
) -> None:
    try:
        module = _get_provider_module(provider_name)
        if hasattr(module, "translate_image_async"):
            import inspect
            sig = inspect.signature(module.translate_image_async)
            if "on_status" in sig.parameters:
                module.translate_image_async(image, on_success, on_error, on_status=on_status)
            else:
                module.translate_image_async(image, on_success, on_error)
        else:
            on_error(f"{provider_name} does not support standard translation yet.")
    except Exception as e:
        on_error(f"Sağlayıcı yüklenirken hata: {e}")

def translate_full_page_async(
    provider_name: str,
    image: Image.Image,
    screen_w: int,
    screen_h: int,
    offset_x: int,
    offset_y: int,
    is_panel: bool,
    on_success: Callable[[List[Tuple[Tuple[int, int, int, int], str]]], None],
    on_error: Callable[[str], None],
    on_status: Callable[[str], None] = None,
) -> None:
    try:
        module = _get_provider_module(provider_name)
        if hasattr(module, "translate_full_page_async"):
            import inspect
            sig = inspect.signature(module.translate_full_page_async)
            if "on_status" in sig.parameters:
                module.translate_full_page_async(image, screen_w, screen_h, offset_x, offset_y, is_panel, on_success, on_error, on_status=on_status)
            else:
                module.translate_full_page_async(image, screen_w, screen_h, offset_x, offset_y, is_panel, on_success, on_error)
        else:
            on_error(f"{provider_name} does not support full page translation yet.")
    except Exception as e:
        on_error(f"Sağlayıcı yüklenirken hata: {e}")

def test_api_key(provider_name: str, api_key: str) -> Tuple[bool, str]:
    import i18n
    try:
        module = _get_provider_module(provider_name)
    except Exception as e:
        return False, f"Modül Yükleme Hatası:\n{e}"
        
    ok = False
    err = i18n.t("no_test_infra")
    
    if hasattr(module, "test_api_key"):
        ok, err = module.test_api_key(api_key)
        
    if not ok and err:
        if "CLOUDFLARE_RAW_ERROR" in err:
            pass # Do not mask raw cloudflare debug error
        else:
            err_lower = err.lower()
            if "401" in err_lower or "unauthorized" in err_lower or "invalid x-api-key" in err_lower or "authentication" in err_lower or "api key not valid" in err_lower:
                err = i18n.t("invalid_api_key")
            elif "403" in err_lower or "forbidden" in err_lower:
                err = i18n.t("access_denied")
            elif "429" in err_lower or "too many requests" in err_lower or "quota" in err_lower or "billing" in err_lower or "insufficient" in err_lower or "out of credits" in err_lower:
                err = i18n.t("quota_exceeded")
            elif "connection" in err_lower or "timeout" in err_lower or "network" in err_lower:
                err = i18n.t("connection_failed")
    return ok, err
