"""
settings/settings_window.py — Gemini API key yapılandırma penceresi.
Standart Windows arayüzü, sekmeler, tema ve otomatik kayıt içerir.
"""
from __future__ import annotations

import os
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from PIL import Image, ImageTk

from config import APP_NAME
import i18n
from storage.keystore import (
    delete_api_key,
    delete_manga_title,
    has_api_key,
    load_api_key,
    load_manga_title,
    save_api_key,
    save_manga_title,
    load_panel_mode,
    save_panel_mode,
    load_theme_mode,
    save_theme_mode,
    load_active_provider,
    save_active_provider,
    load_language,
    save_language,
    load_target_lang,
    save_target_lang
)
import translation.provider_factory as provider_factory

class SettingsWindow:
    def __init__(
        self, 
        root: tk.Tk, 
        is_running: bool = False, 
        on_toggle: Optional[Callable[[], None]] = None,
        on_saved: Optional[Callable[[str], None]] = None
    ) -> None:
        self._root = root
        self._is_running = is_running
        self._on_toggle = on_toggle
        self._on_saved = on_saved
        self._win: Optional[tk.Toplevel] = None
        self._toggle_btn: Optional[ttk.Button] = None

        self._provider_var: Optional[tk.StringVar] = None
        self._api_var: Optional[tk.StringVar] = None
        self._manga_var: Optional[tk.StringVar] = None
        self._use_panel_var: Optional[tk.BooleanVar] = None
        self._dark_mode_var: Optional[tk.BooleanVar] = None
        self._lang_var: Optional[tk.StringVar] = None
        
        self._save_timer: Optional[str] = None
        self._entry: Optional[ttk.Entry] = None
        self._lisans_txt: Optional[tk.Text] = None

    def _on_language_changed(self, *args) -> None:
        if not self._lang_var or not self._win:
            return
        lang_str = self._lang_var.get()
        new_lang = "tr" if "Türkçe" in lang_str else "en"
        if new_lang != i18n.CURRENT_LANG:
            i18n.set_language(new_lang)
            save_language(new_lang)
            for widget in self._win.winfo_children():
                widget.destroy()
            self._apply_theme(self._win)
            self._build_ui(self._win)
            
            # Update main window dynamically
            if hasattr(self._root, "refresh_ui_texts"):
                self._root.refresh_ui_texts()


    def _on_target_language_changed(self, *args) -> None:
        if not self._target_lang_var:
            return
        val = self._target_lang_var.get()
        save_target_lang(val)

    def set_running_state(self, is_running: bool) -> None:
        self._is_running = is_running
        self._update_toggle_btn()

    def show(self) -> None:
        if self._win and self._win.winfo_exists():
            self._win.deiconify()
            self._win.lift()
            return
            
        win = tk.Toplevel(self._root)
        win.title(f"{APP_NAME} — Ayarlar")
        win.resizable(True, True)
        win.minsize(580, 620)
        
        w, h = 580, 680
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")
        
        self._win = win
        self._apply_theme(win)
        self._build_ui(win)
        win.protocol("WM_DELETE_WINDOW", win.destroy)

    def hide(self) -> None:
        if self._win and self._win.winfo_exists():
            self._win.withdraw()

    def _apply_theme(self, win: tk.Toplevel = None) -> None:
        target_win = win or self._win
        if not target_win:
            return
            
        is_dark = load_theme_mode()
        
        if is_dark:
            bg = "#2b2b2b"
            fg = "#f0f0f0"
            entry_bg = "#333333"
            tab_bg = "#3c3c3c"
            tab_sel = "#555555"
            btn_bg = "#3c3c3c"
            btn_act = "#4c4c4c"
            desc_fg = "#aaaaaa"
        else:
            bg = "#f0f0f0"
            fg = "#111111"
            entry_bg = "#ffffff"
            tab_bg = "#e0e0e0"
            tab_sel = "#ffffff"
            btn_bg = "#e1e1e1"
            btn_act = "#d1d1d1"
            desc_fg = "#555555"
            
        sel_bg = "#B8860B"
            
        target_win.configure(bg=bg)
        style = ttk.Style(target_win)
        if "clam" in style.theme_names():
            style.theme_use("clam")
            
        style.configure(".", background=bg, foreground=fg, selectbackground=sel_bg, selectforeground="white")
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg)
        style.configure("Header.TLabel", background=bg, foreground=fg, font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", background=bg, foreground=desc_fg, font=("Segoe UI", 9))
        style.configure("Bold.TLabel", background=bg, foreground=fg, font=("Segoe UI", 10, "bold"))
        style.configure("Desc.TLabel", background=bg, foreground=desc_fg, font=("Segoe UI", 8))
        
        style.configure("TCheckbutton", background=bg, foreground=fg)
        style.map("TCheckbutton", background=[("active", bg)])
        
        style.configure("TButton", background=btn_bg, foreground=fg, borderwidth=1, bordercolor=desc_fg)
        style.map("TButton", background=[("active", btn_act)])
        
        style.configure("Action.TButton", background="#28a745", foreground="white", font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Action.TButton", background=[("active", "#218838")])
        
        style.configure("Danger.TButton", background="#dc3545", foreground="white", font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#c82333")])
        
        style.configure("TEntry", fieldbackground=entry_bg, foreground=fg, insertcolor=fg, borderwidth=1)
        
        style.configure("TCombobox", fieldbackground=entry_bg, background=bg, foreground=fg, selectbackground=entry_bg, selectforeground=fg)
        style.map("TCombobox", fieldbackground=[("readonly", entry_bg)], selectbackground=[("readonly", entry_bg)], selectforeground=[("readonly", fg)])
        
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", background=tab_bg, foreground=fg, padding=[0, 8], width=14, anchor="center")
        style.map("TNotebook.Tab", background=[("selected", tab_sel)])

    def _build_ui(self, win: tk.Toplevel) -> None:
        main_frame = ttk.Frame(win, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        hdr_frame = ttk.Frame(main_frame)
        hdr_frame.pack(fill="x", pady=(0, 15))
        
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path).resize((48, 48), Image.Resampling.LANCZOS)
                self._logo_image = ImageTk.PhotoImage(img)
                ttk.Label(hdr_frame, image=self._logo_image).pack(side="left", padx=(0, 10))
            except Exception:
                pass
                
        title_frame = ttk.Frame(hdr_frame)
        title_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(title_frame, text="MangaLens", style="Header.TLabel").pack(anchor="w")
        ttk.Label(title_frame, text="Universal AI Manga Translator", style="Sub.TLabel").pack(anchor="w")
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(0, 15))
        
        # Tab 1
        genel_frame = ttk.Frame(notebook, padding=15)
        notebook.add(genel_frame, text=i18n.t("tab_general"))
        
        # Language Selector
        lang_frame = ttk.Frame(genel_frame)
        lang_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(lang_frame, text=i18n.t("language"), style="Bold.TLabel").pack(side="left")
        
        current_lang = "Türkçe (TR)" if i18n.CURRENT_LANG == "tr" else "English (EN)"
        self._lang_var = tk.StringVar(value=current_lang)
        self._lang_var.trace_add("write", self._on_language_changed)
        lang_combo = ttk.Combobox(lang_frame, textvariable=self._lang_var, state="readonly", font=("Segoe UI", 9), width=15)
        lang_combo['values'] = ("English (EN)", "Türkçe (TR)")
        lang_combo.pack(side="right")

        # Target Language Selector
        target_lang_frame = ttk.Frame(genel_frame)
        target_lang_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(target_lang_frame, text=i18n.t("target_language"), style="Bold.TLabel").pack(side="left")
        
        self._target_lang_var = tk.StringVar(value=load_target_lang())
        self._target_lang_var.trace_add("write", self._on_target_language_changed)
        target_lang_combo = ttk.Combobox(target_lang_frame, textvariable=self._target_lang_var, state="readonly", font=("Segoe UI", 9), width=15)
        target_lang_combo['values'] = (
            "Türkçe", "English", "Español", "Français", "Deutsch", 
            "Italiano", "Português", "Русский", "日本語", "한국어", "中文"
        )
        target_lang_combo.pack(side="right")

        ttk.Label(genel_frame, text=i18n.t("auth"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        
        ttk.Label(genel_frame, text=i18n.t("ai_model"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        
        self._provider_display_map = {
            "gemini": "Gemini",
            "openai": "Chat GPT",
            "anthropic": "Claude",
            "nvidia": "NVIDIA",
            "deepl": "DeepL",
            "deepseek": "DeepSeek",
            "cloudflare": "Cloudflare"
        }
        self._provider_name_map = {v: k for k, v in self._provider_display_map.items()}

        active_prov = load_active_provider()
        self._provider_var = tk.StringVar(value=self._provider_display_map.get(active_prov, "Gemini"))
        self._provider_var.trace_add("write", self._on_provider_changed)
        
        provider_combo = ttk.Combobox(genel_frame, textvariable=self._provider_var, state="readonly", font=("Segoe UI", 10))
        provider_combo['values'] = list(self._provider_display_map.values())
        provider_combo.pack(fill="x", padx=10, pady=(0, 15))
        
        ttk.Label(genel_frame, text=i18n.t("api_key"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        self._api_var = tk.StringVar(value=load_api_key(active_prov) or "")
        self._api_var.trace_add("write", self._on_text_changed)
        
        entry = ttk.Entry(genel_frame, textvariable=self._api_var, font=("Consolas", 10), show="•")
        entry.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(genel_frame, text=i18n.t("api_key_desc"), style="Desc.TLabel").pack(anchor="w", padx=10, pady=(0, 15))
        self._entry = entry
                     
        ttk.Label(genel_frame, text=i18n.t("manga_title"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        self._manga_var = tk.StringVar(value=load_manga_title() or "")
        self._manga_var.trace_add("write", self._on_text_changed)
        
        manga_entry = ttk.Entry(genel_frame, textvariable=self._manga_var, font=("Segoe UI", 10))
        manga_entry.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(genel_frame, text=i18n.t("manga_title_desc"), style="Desc.TLabel").pack(anchor="w", padx=10, pady=(0, 15))
                     
        # Tab 2
        gelismis_frame = ttk.Frame(notebook, padding=15)
        notebook.add(gelismis_frame, text=i18n.t("tab_advanced"))
        
        ttk.Label(gelismis_frame, text=i18n.t("appearance"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        self._dark_mode_var = tk.BooleanVar(value=load_theme_mode())
        ttk.Checkbutton(
            gelismis_frame, 
            text=i18n.t("dark_mode"), 
            variable=self._dark_mode_var,
            command=self._on_theme_toggle
        ).pack(anchor="w", padx=10, pady=(0, 20))
        
        ttk.Label(gelismis_frame, text=i18n.t("panel_mode_title"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        self._use_panel_var = tk.BooleanVar(value=load_panel_mode())
        ttk.Checkbutton(
            gelismis_frame, 
            text=i18n.t("panel_mode_desc"), 
            variable=self._use_panel_var,
            command=self._on_panel_toggle
        ).pack(anchor="w", padx=10, pady=(0, 20))
        
        ttk.Label(gelismis_frame, text=i18n.t("data_management"), style="Bold.TLabel").pack(anchor="w", pady=(0, 5))
        ttk.Button(gelismis_frame, text=i18n.t("clear_data"), command=self._clear_key).pack(anchor="w", padx=10)
        
        # Tab 3
        bilgi_frame = ttk.Frame(notebook, padding=15)
        notebook.add(bilgi_frame, text=i18n.t("tab_how_it_works"))
        
        info_text = i18n.t("how_it_works_text")
        info_label = tk.Label(bilgi_frame, text=info_text, justify="left", wraplength=480, font=("Segoe UI", 9))
        info_label.pack(anchor="w", fill="x")
        self._info_label = info_label
        
        # Tab 4: Lisanslar
        lisans_frame = ttk.Frame(notebook, padding=15)
        notebook.add(lisans_frame, text=i18n.t("tab_licenses"))
        
        lisans_text = i18n.t("licenses_prefix")
        txt = tk.Text(lisans_frame, wrap="word", font=("Consolas", 8), height=14)
        txt.insert("1.0", lisans_text)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)
        self._lisans_txt = txt
        self._update_info_label_colors()
        
        # Bottom
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill="x")
        
        self._test_btn = ttk.Button(bottom_frame, text=i18n.t("test_connection"), command=self._test_connection)
        self._test_btn.pack(side="left")
        
        self._toggle_btn = ttk.Button(bottom_frame, command=self._handle_toggle)
        self._toggle_btn.pack(side="right", ipadx=10, ipady=2)
        self._update_toggle_btn()
        
    def _update_info_label_colors(self) -> None:
        if not hasattr(self, '_info_label') or not self._info_label.winfo_exists():
            return
        is_dark = load_theme_mode()
        bg = "#2b2b2b" if is_dark else "#f0f0f0"
        fg = "#f0f0f0" if is_dark else "#111111"
        entry_bg = "#333333" if is_dark else "#ffffff"
        
        self._info_label.configure(bg=bg, fg=fg)
        if hasattr(self, '_lisans_txt') and self._lisans_txt:
            self._lisans_txt.configure(bg=entry_bg, fg=fg)

    def _update_toggle_btn(self) -> None:
        if not self._toggle_btn: return
        if self._is_running:
            self._toggle_btn.config(text=i18n.t("stop_app"), style="Danger.TButton")
        else:
            self._toggle_btn.config(text=i18n.t("start_app"), style="Action.TButton")

    def _handle_toggle(self) -> None:
        if not self._is_running:
            # Uygulamayı başlatmadan önce zorunlu test yap
            if self._test_btn and str(self._test_btn.cget("state")) == "disabled":
                return # Zaten test ediliyor
            self._test_connection(auto_start=True)
        else:
            # Uygulamayı durdururken test gerekmez
            if self._on_toggle:
                self._on_toggle()

    def _on_theme_toggle(self) -> None:
        is_dark = self._dark_mode_var.get()
        save_theme_mode(is_dark)
        self._apply_theme()
        self._update_info_label_colors()

    def _on_provider_changed(self, *args) -> None:
        display_prov = self._provider_var.get()
        provider = self._provider_name_map.get(display_prov, "gemini")
            
        key = load_api_key(provider) or ""
        self._api_var.set(key)
        self._save_settings()

    def _on_panel_toggle(self) -> None:
        self._save_settings()

    def _on_text_changed(self, *args) -> None:
        if self._save_timer is not None:
            self._win.after_cancel(self._save_timer)
        self._save_timer = self._win.after(800, self._save_settings)

    def _get_key(self) -> str:
        return (self._api_var.get() if self._api_var else "").strip()

    def _test_connection(self, auto_start: bool = False) -> None:
        key = self._get_key()
        if not key:
            import tkinter.messagebox as mb
            mb.showwarning(i18n.t("missing_info"), i18n.t("please_enter_api"), parent=self._win)
            return

        # Diğer ayarları (manga adı, seçili yapay zeka vb.) kaydet
        self._save_settings()

        if self._test_btn:
            self._test_btn.configure(state="disabled", text=i18n.t("testing"))

        def _run():
            try:
                display_prov = self._provider_var.get()
                provider = self._provider_name_map.get(display_prov, "gemini")
                ok, err = provider_factory.test_api_key(provider, key)
                if self._win and self._win.winfo_exists():
                    self._win.after(0, lambda: self._on_test_done(ok, err, auto_start))
            except Exception as e:
                if self._win and self._win.winfo_exists():
                    self._win.after(0, lambda: self._on_test_done(False, f"Altyapı Hatası: {e}", auto_start))

        threading.Thread(target=_run, daemon=True).start()

    def _on_test_done(self, ok: bool, err: str, auto_start: bool = False) -> None:
        if self._test_btn:
            self._test_btn.configure(state="normal", text=i18n.t("success") if ok else i18n.t("failed"))
        
        if ok:
            # Test başarılıysa API anahtarını güvenle kaydet
            key = self._get_key()
            display_prov = self._provider_var.get()
            provider = self._provider_name_map.get(display_prov, "gemini")
            save_api_key(provider, key)
            if self._on_saved:
                self._on_saved(key)
                
            if auto_start:
                self.hide()
                if self._on_toggle:
                    self._on_toggle()
        else:
            import tkinter.messagebox as mb
            mb.showerror(i18n.t("api_test_error"), err, parent=self._win)

    def _save_settings(self) -> None:
        if not self._win or not self._win.winfo_exists():
            return
            
        m_title = self._manga_var.get().strip() if self._manga_var else ""
        if m_title:
            save_manga_title(m_title)
        else:
            delete_manga_title()

        if self._use_panel_var:
            save_panel_mode(self._use_panel_var.get())

        display_prov = self._provider_var.get()
        provider = self._provider_name_map.get(display_prov, "gemini")
        save_active_provider(provider)

    def _clear_key(self) -> None:
        display_prov = self._provider_var.get() if self._provider_var else "Gemini"
        provider = self._provider_name_map.get(display_prov, "gemini")
        delete_api_key(provider)
        delete_manga_title()
        if self._api_var:
            self._api_var.set("")
        if self._manga_var:
            self._manga_var.set("")

