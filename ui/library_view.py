import i18n
import re
import customtkinter as ctk
import tkinter.filedialog as fd
import shutil
from pathlib import Path
import os
import re
import threading

class CreateSeriesWindow(ctk.CTkToplevel):
    def __init__(self, master, library_manager, on_success):
        super().__init__(master)
        self.title(i18n.t("create_new_series_title"))
        self.geometry("350x150")
        self.library_manager = library_manager
        self.on_success = on_success
        
        # Center the window
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (350 // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (150 // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        
        self.grid_columnconfigure(0, weight=1)
        
        self.lbl_series = ctk.CTkLabel(self, text=i18n.t("manga_series_name"), font=ctk.CTkFont(weight="bold"))
        self.lbl_series.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.entry_series = ctk.CTkEntry(self, placeholder_text=i18n.t("manga_series_placeholder"))
        self.entry_series.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.btn_create = ctk.CTkButton(self, text=i18n.t("create"), command=self.create_series)
        self.btn_create.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.lbl_error = ctk.CTkLabel(self, text="", text_color="red", font=ctk.CTkFont(size=12))
        self.lbl_error.grid(row=3, column=0, padx=20, pady=(0, 5))
        
    def create_series(self):
        series_name = self.entry_series.get().strip()
        if not series_name: return
        
        dest_dir = self.library_manager.base_dir / series_name
        if dest_dir.exists():
            self.lbl_error.configure(text=i18n.t("manga_exists"))
            return
            
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        self.on_success()
        self.destroy()

class AddChapterWindow(ctk.CTkToplevel):
    def __init__(self, master, library_manager, series_name, on_success):
        super().__init__(master)
        self.title(f"{i18n.t('add_new_chapter_title')}: {series_name}")
        self.geometry("400x150")
        self.library_manager = library_manager
        self.series_name = series_name
        self.on_success = on_success
        
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - (400 // 2)
        y = master.winfo_y() + (master.winfo_height() // 2) - (150 // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        
        self.grid_columnconfigure(0, weight=1)
        
        self.lbl_info = ctk.CTkLabel(self, text=i18n.t("select_chapter_to_add"), wraplength=350)
        self.lbl_info.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.btn_file = ctk.CTkButton(self, text=i18n.t("add_chapter_zip"), command=self.add_file)
        self.btn_file.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        
        self.btn_folder = ctk.CTkButton(self, text=i18n.t("add_chapter_folder"), command=self.add_folder, fg_color="#555555", hover_color="#444444")
        self.btn_folder.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        
        self.lbl_status = ctk.CTkLabel(self, text="", text_color="gray")
        self.lbl_status.grid(row=3, column=0, padx=20, pady=5)
        
    def _get_next_chapter_name(self):
        series_dir = self.library_manager.base_dir / self.series_name
        if not series_dir.exists():
            return "Bolum 1"
            
        items = [x for x in series_dir.iterdir() if not x.name.lower().startswith('cover')]
        count = len(items)
        return f"Bolum {count + 1}"
        
    def add_file(self):
        file_path = fd.askopenfilename(
            title=i18n.t("select_chapter_file"),
            filetypes=[(i18n.t("manga_archives"), "*.zip *.cbz")]
        )
        if not file_path: return
        self._copy_to_library(file_path, is_folder=False)
        
    def add_folder(self):
        folder_path = fd.askdirectory(title=i18n.t("select_chapter_folder"))
        if not folder_path: return
        self._copy_to_library(folder_path, is_folder=True)
        
    def _copy_to_library(self, src_path, is_folder):
        self.btn_file.grid_forget()
        self.btn_folder.grid_forget()
        self.lbl_info.configure(text=i18n.t("wait_translating"))
        
        # Add Progressbar
        self.progress = ctk.CTkProgressBar(self, mode="determinate")
        self.progress.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.progress.set(0)
        
        self.lbl_status.configure(text=i18n.t("copying_preparing"), text_color="white")
        
        next_name = self._get_next_chapter_name()
        
        def worker():
            try:
                dest_dir = self.library_manager.base_dir / self.series_name
                dest_target = dest_dir / next_name
                
                if dest_target.exists():
                    shutil.rmtree(dest_target)
                
                import zipfile
                if is_folder:
                    shutil.copytree(src_path, dest_target)
                else:
                    # Extract zip/cbz directly into the folder
                    dest_target.mkdir(parents=True, exist_ok=True)
                    with zipfile.ZipFile(src_path, 'r') as z:
                        z.extractall(dest_target)
                        
                # --- Offline AI Translation Step ---
                try:
                    import importlib
                    import translation.offline_translator as offline_translator
                    importlib.reload(offline_translator)
                    
                    # Log to a text file for debugging in the UI thread
                    with open(dest_target / "translation_log.txt", "w", encoding="utf-8") as debug_file:
                        debug_file.write(f"Starting translation for {self.series_name}\n")
                    
                    # Gather all images
                    valid_exts = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                    images = []
                    for root, _, files in os.walk(dest_target):
                        for file in files:
                            if Path(file).suffix.lower() in valid_exts:
                                images.append(os.path.join(root, file))
                                
                    total = len(images)
                    if total > 0:
                        # Natural sort
                        def natural_sort_key(s):
                            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
                        images.sort(key=natural_sort_key)
                        
                        for i, img_path in enumerate(images):
                            def update_ui(curr=i, tot=total):
                                self.lbl_status.configure(text=f"{i18n.t('translating_page')}: {curr+1} / {tot}", text_color="yellow")
                                self.progress.set((curr) / tot)
                            self.after(0, update_ui)
                            
                            def cb(msg, curr=i, tot=total):
                                self.after(0, lambda: self.lbl_status.configure(text=f"[{curr+1}/{tot}] {msg}", text_color="orange"))
                                
                            # Check if process_page accepts status_callback (backward compatibility)
                            import inspect
                            sig = inspect.signature(offline_translator.process_page)
                            if 'status_callback' in sig.parameters:
                                offline_translator.process_page(img_path, self.series_name, status_callback=cb)
                            else:
                                offline_translator.process_page(img_path, self.series_name)
                            
                        self.after(0, lambda: self.progress.set(1.0))
                        self.after(0, self._on_copy_success)
                            
                except Exception as ex:
                    print(f"Translation step error: {ex}")
                    with open(dest_target / "translation_log.txt", "a", encoding="utf-8") as debug_file:
                        import traceback
                        debug_file.write(f"Translation loop error: {ex}\n{traceback.format_exc()}\n")
                    # SHOW error on UI instead of silently closing
                    self.after(0, lambda e=ex: self.lbl_status.configure(text=f"Hata: {str(e)}", text_color="red"))
                    self.after(0, lambda: self.btn_file.configure(state="normal"))
                    return # Stop here, do not call _on_copy_success
            except Exception as e:
                self.after(0, lambda: self.lbl_status.configure(text=f"Hata: {e}", text_color="red"))
                self.after(0, lambda: self.btn_file.configure(state="normal"))
                self.after(0, lambda: self.btn_folder.configure(state="normal"))
                
        threading.Thread(target=worker, daemon=True).start()
        
    def _on_copy_success(self):
        self.on_success()
        self.destroy()

class LibraryView(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.active_menu_closer = None
        self._init_ui()
        self.winfo_toplevel().bind("<Button-1>", self._on_global_click, add="+")
        
    def _on_global_click(self, event):
        if not getattr(self, 'active_menu_closer', None):
            return
            
        active_widgets = getattr(self, 'active_menu_widgets', [])
        is_inside_menu = False
        curr = event.widget
        while curr:
            if curr in active_widgets:
                is_inside_menu = True
                break
            try:
                curr = curr.master
            except AttributeError:
                break
                
        if is_inside_menu:
            return
            
        self.active_menu_closer()
        self.active_menu_closer = None
        self.active_menu_widgets = []
        
    def _init_ui(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.overview_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.overview_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.overview_frame.grid_rowconfigure(1, weight=1)
        self.overview_frame.grid_columnconfigure(0, weight=1)
        
        self.top_frame = ctk.CTkFrame(self.overview_frame, fg_color="transparent")
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        self.top_frame.grid_columnconfigure(0, weight=1)
        
        self.title_label = ctk.CTkLabel(self.top_frame, text=i18n.t("tab_library"), font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.grid(row=0, column=0, sticky="w")
        
        self.btn_add = ctk.CTkButton(self.top_frame, text=i18n.t("create_new_series"), command=self.create_series, fg_color="#2E7D32", hover_color="#1B5E20")
        self.btn_add.grid(row=0, column=1, sticky="e")
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.overview_frame, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.scroll_frame.bind("<Configure>", self._reflow_grid)
        
        self.detail_frame = None
        self.card_frames = []
        self._last_cols = 0
        
    def create_series(self):
        CreateSeriesWindow(self.winfo_toplevel(), self.app.library_manager, on_success=self.app.show_library)
        
    def add_chapter(self, series_name):
        AddChapterWindow(self.winfo_toplevel(), self.app.library_manager, series_name, on_success=lambda s=series_name: self.app.show_library(s))
        
    def refresh(self, series_list):
        if self.detail_frame:
            self.detail_frame.destroy()
            self.detail_frame = None
        
        self.overview_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        self.card_frames = []
        self._last_cols = 0
            
        if not series_list:
            lbl = ctk.CTkLabel(self.scroll_frame, text=i18n.t("library_empty"))
            lbl.pack(pady=20)
            return
            
        for i, series in enumerate(series_list):
            # Vertical Card
            series_frame = ctk.CTkFrame(self.scroll_frame, width=250, height=350, cursor="hand2")
            series_frame.pack_propagate(False)
            self.card_frames.append(series_frame)
            
            lbl_cover = None
            if getattr(series, 'cover_path', None):
                try:
                    from PIL import Image, ImageOps
                    img = Image.open(series.cover_path)
                    # Use ImageOps.fit to fill exactly 250x350 without distortion
                    img = ImageOps.fit(img, (250, 350), method=Image.Resampling.LANCZOS)
                    cover_img = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 350))
                    lbl_cover = ctk.CTkLabel(series_frame, text="", image=cover_img, cursor="hand2")
                    lbl_cover.place(x=0, y=0, relwidth=1, relheight=1)
                except Exception as e:
                    pass
            
            btn_add_cover = ctk.CTkButton(series_frame, text=i18n.t("select_cover"), width=60, fg_color="#2E7D32", hover_color="#1B5E20",
                                            command=lambda s=series.title: self.add_cover(s))
                                            
            btn_delete = ctk.CTkButton(series_frame, text=i18n.t("delete"), width=30, fg_color="#D32F2F", hover_color="#B71C1C", 
                                       command=lambda s=series.title: self.delete_series(s))
                                       
            def toggle_actions(b1=btn_add_cover, b2=btn_delete):
                is_open = b1.winfo_ismapped()
                if getattr(self, 'active_menu_closer', None):
                    self.active_menu_closer()
                    self.active_menu_closer = None
                
                if not is_open:
                    b1.place(x=40, y=10)
                    b2.place(x=110, y=10)
                    
                    def closer():
                        if b1.winfo_exists() and b1.winfo_ismapped():
                            b1.place_forget()
                        if b2.winfo_exists() and b2.winfo_ismapped():
                            b2.place_forget()
                    self.active_menu_closer = closer
            
            btn_dots = ctk.CTkButton(series_frame, text="⋮", width=25, fg_color="transparent", text_color="white", hover_color="#333333", command=toggle_actions)
            # monkey-patch active widgets logic inside toggle_actions by checking if we just opened it
            def toggle_actions_wrapped(b1=btn_add_cover, b2=btn_delete, d=btn_dots, f=toggle_actions):
                f(b1, b2)
                if getattr(self, 'active_menu_closer', None):
                    self.active_menu_widgets = [b1, b2, d]
            btn_dots.configure(command=toggle_actions_wrapped)
            btn_dots.place(x=10, y=10)
            
            # Title label at the bottom
            title_lbl = ctk.CTkLabel(series_frame, text=series.title, font=ctk.CTkFont(size=16, weight="bold"), wraplength=230, justify="center", cursor="hand2", fg_color="#111111", corner_radius=5)
            title_lbl.pack(side="bottom", fill="x", padx=5, pady=(0, 5))
            
            def on_click(event, s=series):
                self.show_series_detail(s)
                
            series_frame.bind("<Button-1>", on_click)
            title_lbl.bind("<Button-1>", on_click)
            if lbl_cover:
                lbl_cover.bind("<Button-1>", on_click)
            
        self._reflow_grid()
            
    def _reflow_grid(self, event=None):
        if not self.card_frames:
            return
            
        width = self.scroll_frame.winfo_width()
        if width <= 10: 
            width = self.app.winfo_width() - 250 # Fallback
            if width <= 10: return
            
        cols = max(1, width // 280)
        
        if cols == self._last_cols and event is not None:
            return
            
        self._last_cols = cols
        
        s_col = 0
        s_row = 0
        for frame in self.card_frames:
            frame.grid(row=s_row, column=s_col, padx=15, pady=15, sticky="n")
            s_col += 1
            if s_col >= cols:
                s_col = 0
                s_row += 1

    def show_series_detail(self, series):
        self.overview_frame.grid_forget()
        
        if self.detail_frame:
            self.detail_frame.destroy()
            
        self.detail_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.detail_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=20, pady=20)
        self.detail_frame.grid_rowconfigure(1, weight=1)
        self.detail_frame.grid_columnconfigure(0, weight=1)
        
        # Header
        top_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        top_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_frame.grid_columnconfigure(1, weight=1)
        
        btn_back = ctk.CTkButton(top_frame, text=i18n.t("btn_back_short"), width=60, command=self.close_detail, fg_color="#555555", hover_color="#333333")
        btn_back.grid(row=0, column=0, sticky="w", padx=(0, 20))
        
        title_lbl = ctk.CTkLabel(top_frame, text=series.title, font=ctk.CTkFont(size=24, weight="bold"))
        title_lbl.grid(row=0, column=1, sticky="w")
        
        btn_add = ctk.CTkButton(top_frame, text=i18n.t("add_chapter"), command=lambda s=series.title: self.add_chapter(s), fg_color="#2E7D32", hover_color="#1B5E20")
        btn_add.grid(row=0, column=2, sticky="e")
        
        # Chapters list
        chapters_frame = ctk.CTkScrollableFrame(self.detail_frame, fg_color="transparent")
        chapters_frame.grid(row=1, column=0, sticky="nsew")
        self.chapters_frame = chapters_frame
        self.chapter_frames = []
        self._last_chapter_cols = 0
        
        if not series.chapters:
            ctk.CTkLabel(chapters_frame, text=i18n.t("series_empty")).pack(pady=20)
        else:
            for ch in series.chapters:
                ch_frame = ctk.CTkFrame(chapters_frame, fg_color="transparent")
                self.chapter_frames.append(ch_frame)
                
                btn = ctk.CTkButton(ch_frame, text=ch.title, width=150, height=40,
                                    command=lambda s=series, c=ch: self.app.open_reader(s.title, c))
                btn.grid(row=0, column=0)
                
                btn_del = ctk.CTkButton(ch_frame, text=i18n.t("delete"), width=40, height=40, fg_color="#D32F2F", hover_color="#B71C1C",
                                        command=lambda s=series, c=ch: self.delete_chapter(s.title, c.path))
                                        
                btn_ren = ctk.CTkButton(ch_frame, text=i18n.t("rename"), width=60, height=40, fg_color="#1976D2", hover_color="#1565C0",
                                        command=lambda s=series, c=ch: self.rename_chapter(s.title, c.path, c.title))
                                        
                def toggle_ch_opts(b1=btn_del, b2=btn_ren):
                    is_open = b1.winfo_ismapped()
                    if getattr(self, 'active_menu_closer', None):
                        self.active_menu_closer()
                        self.active_menu_closer = None
                        
                    if not is_open:
                        b1.grid(row=0, column=2, padx=(5, 0))
                        b2.grid(row=0, column=3, padx=(5, 0))
                        
                        def closer():
                            if b1.winfo_exists() and b1.winfo_ismapped():
                                b1.grid_forget()
                            if b2.winfo_exists() and b2.winfo_ismapped():
                                b2.grid_forget()
                        self.active_menu_closer = closer
                
                btn_dots = ctk.CTkButton(ch_frame, text="⋮", width=25, height=40, fg_color="transparent", hover_color="#333333", command=toggle_ch_opts)
                def toggle_ch_opts_wrapped(b1=btn_del, b2=btn_ren, d=btn_dots, f=toggle_ch_opts):
                    f(b1, b2)
                    if getattr(self, 'active_menu_closer', None):
                        self.active_menu_widgets = [b1, b2, d]
                btn_dots.configure(command=toggle_ch_opts_wrapped)
                btn_dots.grid(row=0, column=1, padx=(2, 0))
                
            chapters_frame.bind("<Configure>", self._reflow_chapter_grid)
            self._reflow_chapter_grid()

    def _reflow_chapter_grid(self, event=None):
        if not hasattr(self, 'chapter_frames') or not self.chapter_frames:
            return
            
        width = self.chapters_frame.winfo_width()
        if width <= 10: 
            width = self.app.winfo_width() - 250
            if width <= 10: return
            
        cols = max(1, width // 200)
        
        if getattr(self, '_last_chapter_cols', 0) == cols and event is not None:
            return
            
        self._last_chapter_cols = cols
        
        c_col = 0
        c_row = 0
        for frame in self.chapter_frames:
            frame.grid(row=c_row, column=c_col, padx=10, pady=10, sticky="w")
            c_col += 1
            if c_col >= cols:
                c_col = 0
                c_row += 1

    def rename_chapter(self, series_title, chapter_path, old_title):
        dialog = ctk.CTkInputDialog(text=i18n.t("enter_new_chapter_name"), title=i18n.t("rename_title"))
        new_title = dialog.get_input()
        if not new_title or new_title.strip() == old_title:
            return
            
        import os
        from pathlib import Path
        
        new_title = new_title.strip()
        path = Path(chapter_path)
        new_path = path.parent / (new_title + path.suffix)
        
        if not new_path.exists():
            os.rename(path, new_path)
            self.app.library_manager.scan_library()
            for s in self.app.library_manager.series:
                if s.title == series_title:
                    self.show_series_detail(s)
                    break
        else:
            from tkinter import messagebox
            messagebox.showerror(i18n.t("error_title"), i18n.t("file_exists"))

    def delete_chapter(self, series_title, chapter_path):
        self.app.library_manager.delete_chapter(series_title, chapter_path)
        for s in self.app.library_manager.series:
            if s.title == series_title:
                self.show_series_detail(s)
                break
                
    def close_detail(self):
        if self.detail_frame:
            self.detail_frame.destroy()
            self.detail_frame = None
        self.app.show_library() # refresh overview

    def add_cover(self, series_name):
        import tkinter.filedialog as fd
        import shutil
        from pathlib import Path
        
        filepath = fd.askopenfilename(
            title=i18n.t("select_cover_image"), 
            filetypes=[(i18n.t("image_files"), "*.jpg *.jpeg *.png *.webp")]
        )
        if filepath:
            ext = Path(filepath).suffix
            dest = self.app.library_manager.base_dir / series_name / f"cover{ext}"
            # Remove old covers
            for old_ext in ['.jpg', '.jpeg', '.png', '.webp']:
                old_dest = self.app.library_manager.base_dir / series_name / f"cover{old_ext}"
                if old_dest.exists():
                    old_dest.unlink()
            
            shutil.copy2(filepath, dest)
            self.app.library_manager.scan_library()
            self.app.show_library()
            
    def delete_series(self, title):
        self.app.library_manager.delete_series(title)
        self.app.show_library()

    def refresh_ui_texts(self):
        self.lbl_series.configure(text=i18n.t("manga_series_name"))
        self.entry_series.configure(placeholder_text=i18n.t("manga_series_placeholder"))
        self.btn_create.configure(text=i18n.t("create"))
        self.lbl_info.configure(text=i18n.t("select_chapter_to_add"))
        self.btn_file.configure(text=i18n.t("add_chapter_zip"))
        self.btn_folder.configure(text=i18n.t("add_chapter_folder"))
        self.title_label.configure(text=i18n.t("tab_library"))
        self.btn_add.configure(text=i18n.t("create_new_series"))
        
        # Refresh current list
        if getattr(self, "current_series", None):
            self.show_series_detail(self.current_series)
        else:
            self.refresh(self.app.library_manager.series)
