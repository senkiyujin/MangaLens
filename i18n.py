import sys
from storage.keystore import load_language

# A global state for current language, loaded on startup.
CURRENT_LANG = load_language()

def set_language(lang: str):
    global CURRENT_LANG
    CURRENT_LANG = lang

# Dictionary containing all translations.
TRANSLATIONS = {
    "settings_title": {
        "en": "MangaLens — Settings",
        "tr": "MangaLens — Ayarlar"
    },
    "tab_general": {
        "en": "General",
        "tr": "Genel"
    },
    "tab_advanced": {
        "en": "Advanced",
        "tr": "Gelişmiş"
    },
    "tab_how_it_works": {
        "en": "How it Works?",
        "tr": "Nasıl Çalışır?"
    },
    "translating_osd": {
        "en": "Translating...",
        "tr": "Çevriliyor..."
    },
    "magic_wand_osd": {
        "en": "Magic Wand Working...",
        "tr": "Sihirli Değnek Çalışıyor..."
    },
    "full_page_osd": {
        "en": "Scanning Full Page...",
        "tr": "Tam Sayfa Taranıyor..."
    },
    "tab_licenses": {
        "en": "Licenses",
        "tr": "Lisanslar"
    },
    "language": {
        "en": "Language / Dil:",
        "tr": "Dil / Language:"
    },
    "auth": {
        "en": "Authentication",
        "tr": "Kimlik Doğrulama"
    },
    "ai_model": {
        "en": "AI Model",
        "tr": "Yapay Zeka Modeli"
    },
    "api_key": {
        "en": "API Key:",
        "tr": "API Anahtarı:"
    },
    "api_key_desc": {
        "en": "Sent only to the API. Encrypted in Credential Manager.",
        "tr": "Yalnızca API'ye gönderilir. Credential Manager'da şifrelenir."
    },
    "manga_title": {
        "en": "Manga Title (Optional):",
        "tr": "Manga Adı (Opsiyonel):"
    },
    "manga_title_desc": {
        "en": "AI adapts its tone and character language to this manga.",
        "tr": "Yapay zeka tonlama ve karakter dilini bu mangaya adapte eder."
    },
    "appearance": {
        "en": "Appearance",
        "tr": "Görünüm"
    },
    "dark_mode": {
        "en": "Dark Mode",
        "tr": "Koyu Tema (Dark Mode)"
    },
    "panel_mode": {
        "en": "Panel Finder Tool (Translate only inside the purple frame)",
        "tr": "Panel Bulma Aracı (Sadece mor çerçevenin içini çevir)"
    },
    "panel_mode_title": {
        "en": "Panel Mode",
        "tr": "Panel Modu"
    },
    "data_management": {
        "en": "Data Management",
        "tr": "Veri Yönetimi"
    },
    "clear_data": {
        "en": "Clear Key and Data",
        "tr": "Anahtarı ve Verileri Sil"
    },
    "test_connection": {
        "en": "Test Connection",
        "tr": "Bağlantıyı Test Et"
    },
    "start_app": {
        "en": "Start Application",
        "tr": "Uygulamayı Başlat"
    },
    "stop_app": {
        "en": "Stop Application",
        "tr": "Uygulamayı Durdur"
    },
    "testing": {
        "en": "Testing...",
        "tr": "Test ediliyor…"
    },
    "create_new_series_title": {
        "en": "Create New Series",
        "tr": "Yeni Seri Oluştur"
    },
    "add_new_chapter_title": {
        "en": "Add New Chapter",
        "tr": "Yeni Bölüm Ekle"
    },
    "select_chapter_file": {
        "en": "Select Chapter File (ZIP/CBZ)",
        "tr": "Bölüm Dosyası Seç (ZIP/CBZ)"
    },
    "manga_archives": {
        "en": "Manga Archives",
        "tr": "Manga Arşivleri"
    },
    "select_chapter_folder": {
        "en": "Select Chapter Folder",
        "tr": "Bölüm Klasörünü Seç"
    },
    "error_title": {
        "en": "Error",
        "tr": "Hata"
    },
    "file_exists": {
        "en": "A file or folder with this name already exists!",
        "tr": "Bu isimde bir dosya veya klasör zaten var!"
    },
    "select_cover_image": {
        "en": "Select Cover Image",
        "tr": "Kapak Resmi Seç"
    },
    "image_files": {
        "en": "Image Files",
        "tr": "Resim Dosyaları"
    }
,
    "open_library": {
        "en": "Open Library",
        "tr": "Kütüphaneyi Aç"
    },
    "tab_library": {
        "en": "Library",
        "tr": "Kütüphane"
    },
    "screen_translation": {
        "en": "Screen Translation",
        "tr": "Ekran Çevirisi"
    },
    "close_translation": {
        "en": "Close Translation",
        "tr": "Çeviriyi Kapat"
    },
    "manga_series_name": {
        "en": "Manga Series Name:",
        "tr": "Manga Serisi Adı:"
    },
    "manga_series_placeholder": {
        "en": "e.g. One Piece",
        "tr": "Örn: One Piece"
    },
    "create": {
        "en": "Create",
        "tr": "Oluştur"
    },
    "manga_exists": {
        "en": "A manga with this name already exists!",
        "tr": "Bu isimde bir manga zaten mevcut!"
    },
    "select_chapter_to_add": {
        "en": "Select the chapter to add. (The next number will be assigned automatically)",
        "tr": "Eklenecek bölümü seçin. (Sıradaki numara otomatik verilecek)"
    },
    "add_chapter_zip": {
        "en": "Add Chapter (ZIP / CBZ)",
        "tr": "Bölüm Ekle (ZIP / CBZ)"
    },
    "add_chapter_folder": {
        "en": "Add Chapter (Folder)",
        "tr": "Bölüm Ekle (Klasör)"
    },
    "wait_translating": {
        "en": "Please Wait: Translating...",
        "tr": "Lütfen Bekleyin: Çeviri Yapılıyor..."
    },
    "copying_preparing": {
        "en": "Copying and Preparing...",
        "tr": "Kopyalanıyor ve Hazırlanıyor..."
    },
    "translating_page": {
        "en": "Translating Page",
        "tr": "Sayfa Çevriliyor"
    },
    "create_new_series": {
        "en": "+ Create New Series",
        "tr": "+ Yeni Seri Oluştur"
    },
    "library_empty": {
        "en": "Library is empty. You can add a series with the '+ Create New Series' button on the top right.",
        "tr": "Kütüphane boş. Sağ üstteki '+ Yeni Seri Oluştur' butonuyla seri ekleyebilirsiniz."
    },
    "select_cover": {
        "en": "Select Cover",
        "tr": "Kapak Seç"
    },
    "delete": {
        "en": "Delete",
        "tr": "Sil"
    },
    "btn_back_short": {
        "en": "< Back",
        "tr": "< Geri"
    },
    "add_chapter": {
        "en": "+ Add Chapter",
        "tr": "+ Bölüm Ekle"
    },
    "series_empty": {
        "en": "There are no chapters in this series yet.",
        "tr": "Bu seride henüz bölüm yok."
    },
    "rename": {
        "en": "Rename",
        "tr": "Adlandır"
    },
    "enter_new_chapter_name": {
        "en": "Enter new chapter name:",
        "tr": "Yeni bölüm adını girin:"
    },
    "rename_title": {
        "en": "Rename",
        "tr": "Yeniden Adlandır"
    },
    "btn_back": {
        "en": "← Go Back",
        "tr": "← Geri Dön"
    },
    "page": {
        "en": "Page",
        "tr": "Sayfa"
    },
    "translate_page": {
        "en": "Translate Page (T)",
        "tr": "Sayfayı Çevir (T)"
    },
    "no_page": {
        "en": "No page",
        "tr": "Sayfa yok"
    },
    "translating": {
        "en": "Translating...",
        "tr": "Çevriliyor..."
    }
,
    "success": {
        "en": "✓ Success",
        "tr": "✓ Başarılı"
    },
    "failed": {
        "en": "✗ Failed",
        "tr": "✗ Başarısız"
    },
    "api_test_error": {
        "en": "API Test Error",
        "tr": "API Test Hatası"
    },
    "connection_failed": {
        "en": "Connection failed:\n",
        "tr": "Bağlantı başarısız oldu:\n"
    },
    "missing_info": {
        "en": "Missing Information",
        "tr": "Eksik Bilgi"
    },
    "please_enter_api": {
        "en": "Please enter an API key.",
        "tr": "Lütfen bir API anahtarı girin."
    },
    "tray_settings": {
        "en": "Settings",
        "tr": "Ayarlar"
    },
    "tray_quit": {
        "en": "Quit MangaLens",
        "tr": "Çıkış (MangaLens)"
    },
    "sleep_on": {
        "en": "Sleep Mode ON",
        "tr": "Uyku Modu AÇIK"
    },
    "sleep_off": {
        "en": "Sleep Mode OFF",
        "tr": "Uyku Modu KAPALI"
    },
    "tab_general": {
        "en": "General",
        "tr": "Genel"
    },
    "language": {
        "en": "UI Language",
        "tr": "Arayüz Dili"
    },
    "target_language": {
        "en": "Target Language",
        "tr": "Çeviri Dili"
    },
    "auth": {
        "en": "Authentication",
        "tr": "Kimlik Doğrulama"
    },
    "ai_model": {
        "en": "AI Model",
        "tr": "Yapay Zeka Modeli"
    },
    "api_key": {
        "en": "API Key:",
        "tr": "API Anahtarı:"
    },
    "api_key_desc": {
        "en": "Sent only to the API. Encrypted in Credential Manager.",
        "tr": "Yalnızca API'ye gönderilir. Credential Manager'da şifrelenir."
    },
    "manga_title": {
        "en": "Manga Title (Optional):",
        "tr": "Manga Adı (Opsiyonel):"
    },
    "manga_title_desc": {
        "en": "AI adapts its tone and character language to this manga.",
        "tr": "Yapay zeka tonlama ve karakter dilini bu mangaya adapte eder."
    },
    "tab_advanced": {
        "en": "Advanced",
        "tr": "Gelişmiş"
    },
    "appearance": {
        "en": "Appearance",
        "tr": "Görünüm"
    },
    "dark_mode": {
        "en": "Dark Mode",
        "tr": "Koyu Tema (Dark Mode)"
    },
    "panel_mode_title": {
        "en": "Panel Mode",
        "tr": "Panel Modu"
    },
    "panel_mode_desc": {
        "en": "Panel Finder Tool (Translate only inside the purple box)",
        "tr": "Panel Bulma Aracı (Sadece mor çerçevenin içini çevir)"
    },
    "data_management": {
        "en": "Data Management",
        "tr": "Veri Yönetimi"
    },
    "clear_data": {
        "en": "Clear Key and Data",
        "tr": "Anahtarı ve Verileri Sil"
    },
    "tab_how_it_works": {
        "en": "How it Works?",
        "tr": "Nasıl Çalışır?"
    },
    "test_connection": {
        "en": "Test Connection",
        "tr": "Bağlantıyı Test Et"
    },
    "stop_app": {
        "en": "Stop Application",
        "tr": "Uygulamayı Durdur"
    },
    "start_app": {
        "en": "Start Application",
        "tr": "Uygulamayı Başlat"
    },
    "missing_info": {
        "en": "Missing Information",
        "tr": "Eksik Bilgi"
    },
    "how_it_works_text": {
        "en": (
            "1. Setup:\n"
            "MangaLens requires one of the Google Gemini, Chat GPT, Claude, NVIDIA, DeepL, DeepSeek, or Cloudflare APIs to work. "
            "You can select your preferred model from the 'General' tab and enter your API key.\n\n"
            "2. Usage:\n"
            "• Hold down the CTRL key and drag your mouse to draw around the area you want to translate (Lasso Tool).\n"
            "• To translate a single speech bubble, hold down the CTRL key and Left Click inside the bubble (Magic Wand).\n"
            "• Press CTRL + SHIFT together to translate the entire screen or the panel at once.\n"
            "• Press the ESC key or click on an empty space on the screen to close the translation result.\n\n"
            "3. Shortcuts:\n"
            "• CTRL + Mouse Drag: Translates the drawn area (Lasso Tool)\n"
            "• CTRL + Left Click: Automatically finds and translates the bubble at the clicked location (Magic Wand)\n"
            "• CTRL + SHIFT: Translates the whole screen (or inside the purple box if Panel Mode is active)\n"
            "• ALT + Mouse Drag: Moves or resizes the purple panel box\n"
            "• CTRL + Enter: Puts MangaLens to sleep / wakes it up\n"
            "• ESC: Closes the open translation box on the screen\n"
        ),
        "tr": (
            "1. Kurulum:\n"
            "MangaLens'in çalışabilmesi için Google Gemini, Chat GPT, Claude, NVIDIA, DeepL, DeepSeek, veya Cloudflare API'lerinden birine ihtiyacı vardır. "
            "Genel sekmesinden istediğiniz modeli seçip API anahtarınızı girebilirsiniz.\n\n"
            "2. Kullanım:\n"
            "• Çeviri yapmak istediğiniz alanın etrafını CTRL tuşuna basılı tutarak farenizle çizin.\n"
            "• Sadece tek bir konuşma balonunu çevirmek istiyorsanız, CTRL tuşuna basılı tutarken baloncuğun içine Sol Tıklayın.\n"
            "• Tüm ekranı veya paneli tek seferde çevirmek için CTRL + SHIFT tuşlarına birlikte basın.\n"
            "• Çeviri sonucunu kapatmak için ESC tuşuna basın veya ekranda boş bir yere tıklayın.\n\n"
            "3. Kısayollar:\n"
            "• CTRL + Fare Hareketi: Etrafı çizilen alanı çevirir (Serbest Seçim - Lasso)\n"
            "• CTRL + Sol Tık: Tıklanan yerdeki baloncuğu otomatik bulup çevirir (Sihirli Değnek)\n"
            "• CTRL + SHIFT: Tüm ekranı veya Panel Modu açıksa mor kutunun içini tek seferde çevirir\n"
            "• ALT + Fare Sürükle: Mor renkli panel kutusunu taşır veya boyutlandırır\n"
            "• CTRL + Enter: MangaLens'i uyku moduna alır / uyandırır\n"
            "• ESC: Ekranda açık olan çeviri kutucuğunu kapatır\n"
        )
    },
    "licenses_prefix": {
        "en": (
            "MangaLens\n"
            "Universal AI Manga Translator\n\n"
            "MangaLens is an open-source project licensed under the MIT License.\n\n"
            "=========================================\n\n"
            "DISCLAIMER\n\n"
            "MangaLens is a neutral translation tool that solely functions as a screen reader and API forwarder. "
            "The developer cannot be held responsible for the user's actions on copyrighted materials or violations "
            "of the terms of service (TOS) of API providers (Google, OpenAI, Anthropic, DeepL, DeepSeek, Cloudflare, etc.). By using this "
            "software, you acknowledge that you assume all legal responsibilities.\n\n"
            "=========================================\n\n"
            "ACKNOWLEDGEMENTS\n\n"
            "Special thanks to the open-source community. MangaLens uses the following libraries:\n"
            "- Google GenAI, OpenAI, Anthropic, DeepL, DeepSeek, Cloudflare\n"
            "- OpenCV, NumPy, EasyOCR, Pillow\n"
            "- pynput, pystray, pywin32, keyring, google-auth"
        ),
        "tr": (
            "MangaLens\n"
            "Universal AI Manga Translator\n\n"
            "MangaLens, MIT Lisansı altında açık kaynaklı bir projedir.\n\n"
            "=========================================\n\n"
            "SORUMLULUK REDDİ (DISCLAIMER)\n\n"
            "MangaLens yalnızca ekran okuma ve API yönlendirme işlevi gören tarafsız "
            "bir çeviri aracıdır. Kullanıcıların telif hakkıyla korunan materyaller "
            "üzerinde yaptığı işlemlerden veya API sağlayıcılarının (Google, OpenAI, "
            "Anthropic, DeepL, DeepSeek, Cloudflare vb.) kullanım koşullarının (TOS) ihlalinden araç "
            "geliştiricisi sorumlu tutulamaz. Bu yazılımı kullanarak tüm yasal "
            "sorumlulukları üstlendiğinizi kabul etmiş olursunuz.\n\n"
            "=========================================\n\n"
            "TEŞEKKÜRLER\n\n"
            "Açık kaynak topluluğuna özel teşekkürler. MangaLens şu kütüphaneleri kullanır:\n"
            "- Google GenAI, OpenAI, Anthropic, DeepL, DeepSeek, Cloudflare\n"
            "- OpenCV, NumPy, EasyOCR, Pillow\n"
            "- pynput, pystray, pywin32, keyring, google-auth"
        )
    },
    
    # Provider error messages
    "err_openai_no_key": {
        "en": "OpenAI API Key not found. Please enter it in Settings.",
        "tr": "OpenAI API Key bulunamadı. Lütfen Ayarlar'dan girin."
    },
    "err_openai_limit": {
        "en": "Chat GPT API limit/budget exceeded!\nPlease renew your key in Settings or select a different AI model.",
        "tr": "Chat GPT API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
    },
    "err_nvidia_no_key": {
        "en": "NVIDIA API Key not found. Please enter it in Settings.",
        "tr": "NVIDIA API Key bulunamadı. Lütfen Ayarlar'dan girin."
    },
    "err_nvidia_limit": {
        "en": "NVIDIA API limit/budget exceeded!\nPlease renew your key in Settings or select a different AI model.",
        "tr": "NVIDIA API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
    },
    "err_gemini_no_key": {
        "en": "Please enter a Gemini API Key in Settings (aistudio.google.com/apikey).",
        "tr": "Lütfen Ayarlar'dan Gemini API Key girin (aistudio.google.com/apikey)."
    },
    "err_gemini_invalid_key": {
        "en": "[❌ Invalid API Key! Enter a new Gemini API Key in Settings.]",
        "tr": "[❌ Geçersiz API Key! Ayarlar'dan yeni Gemini API Key girin.]"
    },
    "err_gemini_auth": {
        "en": "[❌ Authentication error. Please check your API Key in Settings.]",
        "tr": "[❌ Kimlik hatası. Ayarlar'dan API Key kontrol edin.]"
    },
    "err_gemini_limit": {
        "en": "[⏸ Gemini API limit/budget exceeded! Please renew your key in Settings or select a different AI model.]",
        "tr": "[⏸ Gemini API limitiniz/bütçeniz doldu! Lütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin.]"
    },
    "err_gemini_limit_newline": {
        "en": "Gemini API limit/budget exceeded!\nPlease renew your key in Settings or select a different AI model.",
        "tr": "Gemini API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
    },
    "err_deepl_no_key": {
        "en": "DeepL API Key not found. Please enter it in Settings.",
        "tr": "DeepL API Key bulunamadı. Lütfen Ayarlar'dan girin."
    },
    "err_deepl_limit": {
        "en": "DeepL API limit/budget exceeded!\nPlease renew your key in Settings or select a different AI model.",
        "tr": "DeepL API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
    },
    "err_claude_no_key": {
        "en": "Anthropic API Key not found. Please enter it in Settings.",
        "tr": "Anthropic API Key bulunamadı. Lütfen Ayarlar'dan girin."
    },
    "err_claude_limit": {
        "en": "Claude API limit/budget exceeded!\nPlease renew your key in Settings or select a different AI model.",
        "tr": "Claude API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
    },
    "err_deepseek_no_key": {
        "en": "DeepSeek API Key not found. Please enter it in Settings.",
        "tr": "DeepSeek API Key bulunamadı. Lütfen Ayarlar'dan girin."
    },
    "err_deepseek_limit": {
        "en": "DeepSeek API limit/budget exceeded!\nPlease renew your key in Settings or select a different AI model.",
        "tr": "DeepSeek API limitiniz/bütçeniz doldu!\nLütfen Ayarlar'dan anahtarınızı yenileyin veya farklı bir yapay zeka modeli seçin."
    },

    "err_cloudflare_no_key": {
        "en": "To use Cloudflare, you must enter AccountID:APIKey.",
        "tr": "Cloudflare kullanabilmek için Hesap_ID:API_Anahtarı şeklinde girmelisiniz."
    },
    "err_cloudflare_limit": {
        "en": "Cloudflare Workers AI quota exceeded or rate limited.",
        "tr": "Cloudflare Workers AI kotanız dolmuş veya limitlere takıldınız."
    },
    "no_test_infra": {
        "en": "Test infrastructure for this AI provider is not ready yet.",
        "tr": "Bu yapay zeka sağlayıcısı için test altyapısı henüz hazır değil."
    },
    "invalid_api_key": {
        "en": "Invalid API Key! Please make sure you copied the key completely and didn't enter a key belonging to another model (e.g. Claude instead of ChatGPT).",
        "tr": "Geçersiz API Anahtarı! Lütfen anahtarı eksiksiz kopyaladığınızdan ve başka bir modele ait (örn. ChatGPT yerine Claude) anahtar girmediğinizden emin olun."
    },
    "access_denied": {
        "en": "Access Denied! Your API key is not authorized to perform this action, or this service may be blocked in your region.",
        "tr": "Erişim Reddedildi! API anahtarınızın bu işlemi yapmaya yetkisi yok veya bulunduğunuz bölgede bu servis engellenmiş olabilir."
    },
    "quota_exceeded": {
        "en": "Quota Exceeded or Insufficient Balance! The free usage limit of this API key has been reached or your account has insufficient balance.",
        "tr": "Kota Aşımı veya Yetersiz Bakiye! Bu API anahtarının ücretsiz kullanım limiti dolmuş veya hesabınızda yeterli bakiye bulunmuyor."
    },
    "connection_failed": {
        "en": "Connection Error! Check your internet connection or you may be experiencing a VPN/DNS issue.\n\n",
        "tr": "Bağlantı Hatası! İnternet bağlantınızı kontrol edin veya bir VPN/DNS sorunu yaşıyor olabilirsiniz.\n\n"
    },
    "api_test_error": {
        "en": "API Test Error",
        "tr": "API Test Hatası"
    },
    "success": {
        "en": "✓ Success",
        "tr": "✓ Başarılı"
    },
    "failed": {
        "en": "✗ Failed",
        "tr": "✗ Başarısız"
    },
    "testing": {
        "en": "Testing...",
        "tr": "Test ediliyor..."
    }
}

def t(key: str) -> str:
    """Returns the translation for the given key based on CURRENT_LANG."""
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(CURRENT_LANG, TRANSLATIONS[key].get("en", key))
    return key
