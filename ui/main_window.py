import customtkinter as ctk
import tkinter as tk
from ui.library_view import LibraryView
from ui.reader_view import ReaderView
import i18n
import threading

class MainWindow(ctk.CTk):
    def __init__(self, overlay_callback, library_manager):
        super().__init__()
        
        self.title("MangaLens 2.0")
        self.geometry("1024x768")
        self.minsize(800, 600)
        
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.overlay_callback = overlay_callback
        self.library_manager = library_manager
        
        # Grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="MangaLens", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.btn_library = ctk.CTkButton(self.sidebar_frame, text=i18n.t("tab_library"), command=self.show_library)
        self.btn_library.grid(row=1, column=0, padx=20, pady=10)
        
        self.btn_overlay = ctk.CTkButton(self.sidebar_frame, text=i18n.t("screen_translation"), command=self.launch_overlay)
        self.btn_overlay.grid(row=2, column=0, padx=20, pady=10)
        
        self.btn_settings = ctk.CTkButton(self.sidebar_frame, text=i18n.t("tray_settings"), command=self.show_settings)
        self.btn_settings.grid(row=3, column=0, padx=20, pady=10)
        
        # Main View Area
        self.main_view = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_view.grid(row=0, column=1, sticky="nsew")
        self.main_view.grid_rowconfigure(0, weight=1)
        self.main_view.grid_columnconfigure(0, weight=1)
        
        # Initialize views
        self.library_view = LibraryView(self.main_view, self)
        self.reader_view = ReaderView(self.main_view, self)
        
        self.current_view = None
        self.show_library()

    def show_library(self, show_series_title=None):
        if self.current_view:
            self.current_view.grid_forget()
        
        self.library_manager.scan_library()
        self.library_view.refresh(self.library_manager.series)
        
        self.library_view.grid(row=0, column=0, sticky="nsew")
        self.current_view = self.library_view
        
        if show_series_title:
            for s in self.library_manager.series:
                if s.title == show_series_title:
                    self.library_view.show_series_detail(s)
                    break

    def open_reader(self, series_title, chapter):
        if self.current_view:
            self.current_view.grid_forget()
        self.reader_view.load_chapter(series_title, chapter)
        self.reader_view.grid(row=0, column=0, sticky="nsew")
        self.current_view = self.reader_view
        
    def launch_overlay(self):
        self.overlay_callback() # Trigger overlay mode
        
    def update_overlay_btn_state(self, is_running: bool):
        if is_running:
            self.btn_overlay.configure(text=i18n.t("close_translation"), fg_color="#dc3545", hover_color="#c82333")
        else:
            self.btn_overlay.configure(text=i18n.t("screen_translation"), fg_color=('#3B8ED0', '#1F6AA5'), hover_color=('#36719F', '#144870'))
        
    def show_settings(self):
        if getattr(self, 'settings_window', None) is not None:
            if self.settings_window._win and self.settings_window._win.winfo_exists():
                self.settings_window.show()
                return
                
        from settings.settings_window import SettingsWindow
        
        def on_saved(_key=None):
            pass
            
        def on_toggle():
            pass
            
        self.settings_window = SettingsWindow(self, is_running=True, on_toggle=on_toggle, on_saved=on_saved)
        self.settings_window.show()

    def refresh_ui_texts(self):
        self.btn_library.configure(text=i18n.t("tab_library"))
        self.btn_settings.configure(text=i18n.t("tray_settings"))
        # Preserve overlay state
        is_running = (self.btn_overlay.cget("text") not in [
            i18n.TRANSLATIONS.get("screen_translation", {}).get("en", "Screen Translation"),
            i18n.TRANSLATIONS.get("screen_translation", {}).get("tr", "Ekran Çevirisi")
        ])
        if is_running:
            self.btn_overlay.configure(text=i18n.t("close_translation"))
        else:
            self.btn_overlay.configure(text=i18n.t("screen_translation"))
            
        if hasattr(self, "library_view"):
            self.library_view.refresh_ui_texts()
        if hasattr(self, "reader_view"):
            self.reader_view.refresh_ui_texts()
