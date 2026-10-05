import i18n
import customtkinter as ctk
import tkinter as tk
from PIL import ImageTk
import translation.gemini_provider as gemini_provider
from overlay.tooltip import TranslationTooltip
import threading

class ReaderView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="black")
        self.app = app
        
        self.series_title = None
        self.chapter = None
        self.current_page = 0
        self.current_image_pil = None
        self.current_image_tk = None
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Top bar
        self.top_bar = ctk.CTkFrame(self, height=40, corner_radius=0)
        self.top_bar.grid(row=0, column=0, sticky="ew")
        
        self.btn_back = ctk.CTkButton(self.top_bar, text=i18n.t("btn_back"), width=100, command=lambda: self.app.show_library(self.series_title))
        self.btn_back.pack(side="left", padx=10, pady=5)
        
        self.lbl_title = ctk.CTkLabel(self.top_bar, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_title.pack(side="left", padx=20, pady=5)
        
        self.lbl_page = ctk.CTkLabel(self.top_bar, text=f"{i18n.t('page')}: 0/0")
        self.lbl_page.pack(side="right", padx=20, pady=5)
        
        self.btn_translate = ctk.CTkButton(self.top_bar, text=i18n.t("translate_page"), width=120, 
                                           command=self.translate_current_page, fg_color="#FF9800", hover_color="#F57C00")
        self.btn_translate.place(relx=0.5, rely=0.5, anchor="center")
        
        # Canvas
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        
        self.btn_prev_ui = ctk.CTkButton(self, text="<", width=40, height=80, fg_color="#222222", hover_color="#444444", 
                                         text_color="white", font=ctk.CTkFont(size=24, weight="bold"), 
                                         command=self.prev_page, corner_radius=10)
        
        self.btn_next_ui = ctk.CTkButton(self, text=">", width=40, height=80, fg_color="#222222", hover_color="#444444", 
                                         text_color="white", font=ctk.CTkFont(size=24, weight="bold"), 
                                         command=self.next_page, corner_radius=10)
        
        # Bindings
        self.bind("<Configure>", self.on_resize)
        # Bind keys to the toplevel since the frame might not have focus
        app.bind("<Left>", lambda e: self.prev_page())
        app.bind("<Right>", lambda e: self.next_page())
        app.bind("<t>", lambda e: self.translate_current_page())
        app.bind("<T>", lambda e: self.translate_current_page())
        
        self.tooltip = TranslationTooltip(app)
        
    def load_chapter(self, series_title, chapter):
        self.series_title = series_title
        self.chapter = chapter
        self.current_page = 0
        self.lbl_title.configure(text=chapter.title)
        self.show_page()
        
    def show_page(self):
        if not self.chapter: return
        pages = self.chapter.load_pages()
        if not pages:
            self.lbl_page.configure(text=i18n.t("no_page"))
            self.btn_prev_ui.place_forget()
            self.btn_next_ui.place_forget()
            return
            
        self.lbl_page.configure(text=f"Sayfa: {self.current_page + 1} / {len(pages)}")
        
        if self.current_page > 0:
            self.btn_prev_ui.place(relx=0.02, rely=0.5, anchor="w")
        else:
            self.btn_prev_ui.place_forget()
            
        if self.current_page < len(pages) - 1:
            self.btn_next_ui.place(relx=0.98, rely=0.5, anchor="e")
        else:
            self.btn_next_ui.place_forget()
            
        self.current_image_pil = self.chapter.get_page_image(self.current_page)
        self.render_image()
        
    def next_page(self):
        if not self.chapter: return
        if self.current_page < len(self.chapter.load_pages()) - 1:
            self.current_page += 1
            self.show_page()
            
    def prev_page(self):
        if not self.chapter: return
        if self.current_page > 0:
            self.current_page -= 1
            self.show_page()
            
    def on_resize(self, event):
        # Debounce resize
        if hasattr(self, '_resize_job') and self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self.render_image)
            
    def render_image(self):
        if not self.current_image_pil: return
        
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width < 10 or canvas_height < 10:
            return # not fully rendered yet
            
        img_w, img_h = self.current_image_pil.size
        
        # Calculate scale to fit inside canvas
        scale = min(canvas_width / img_w, canvas_height / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        resized_img = self.current_image_pil.resize((new_w, new_h))
        self.current_image_tk = ImageTk.PhotoImage(resized_img)
        
        self.canvas.delete("all")
        x_center = canvas_width // 2
        y_center = canvas_height // 2
        self.canvas.create_image(x_center, y_center, image=self.current_image_tk, anchor="center")
        
    def translate_current_page(self):
        if not self.current_image_pil: return
        
        self.btn_translate.configure(state="disabled", text=i18n.t("translating"))
        
        def _worker():
            try:
                # Use the magic wand pipeline for full image if we just want a single translation bubble
                # or use full_page_fallback if it returns a list of boxes.
                # Since we want a simple translation:
                result = gemini_provider.translate_image(self.current_image_pil)
                self.after(0, lambda: self.show_translation(result))
            except Exception as e:
                self.after(0, lambda: self.show_translation(f"[Hata: {e}]"))
                
        threading.Thread(target=_worker, daemon=True).start()
        
    def show_translation(self, text):
        self.btn_translate.configure(state="normal", text=i18n.t("translate_page"))
        
        # Show tooltip in the center of the window
        x = self.winfo_rootx() + (self.winfo_width() // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2)
        
        self.tooltip.show(text, x, y)

    def refresh_ui_texts(self):
        self.btn_back.configure(text=i18n.t("btn_back"))
        self.btn_translate.configure(text=i18n.t("translate_page"))
        if not self.pages:
            self.lbl_page.configure(text=i18n.t("no_page"))
        else:
            self.lbl_page.configure(text=f"{i18n.t('page')}: {self.current_page_idx + 1}/{len(self.pages)}")
