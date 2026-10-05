"""
main.py — MangaLens entry point.

Wires all modules together:
  OverlayWindow ← LassoController ← screenshot capture ← NvidiaTranslation
                                              ↓
                                       TranslationTooltip
                                              ↑
                                        TrayIcon / SettingsWindow

Startup flow
────────────
1. Check for stored API key.
2. If none → show settings window first (blocks until key is saved or closed).
3. Create overlay window.
4. On window ready: create LassoController, TranslationTooltip, TrayIcon.
5. LassoController fires on_lasso_done → capture region → translate async.
6. Translation callback → tooltip.show() on Tk main thread.
7. Dismiss → tooltip.hide() + lasso.set_state_idle().
"""

from __future__ import annotations

import sys
import os
import logging
import threading
import i18n
import keyring
import keyring.errors

# ── Ensure the project root is on sys.path ────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

_LOG_FILE = os.path.join(os.path.dirname(__file__), "debug.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8", mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("MangaLens")

import tkinter as tk

from capture.screenshot import (
    capture_bounding_box,
    capture_full_page_and_bubbles,
    capture_magic_wand,
)
from config import MIN_CAPTURE_AREA_PX
from overlay.lasso import LassoController, LassoState
from overlay.tooltip import TranslationTooltip
from overlay.window import OverlayWindow
from settings.settings_window import SettingsWindow
from storage.keystore import has_api_key
from tray.tray_icon import TrayIcon
import translation.provider_factory as provider_factory
from storage.keystore import load_active_provider


class MangaLensApp:
    def __init__(self) -> None:
        self._overlay = None
        self._lasso = None
        self._tooltip = None
        self._tray = None
        self._settings = None
        self._is_running = False
        
        # New UI
        from library.library_manager import LibraryManager
        self.library_manager = LibraryManager()
        self.main_window = None

    def run(self) -> None:
        from storage.keystore import load_language
        import i18n
        i18n.set_language(load_language())
        
        from ui.main_window import MainWindow
        self.main_window = MainWindow(overlay_callback=self.launch_overlay, library_manager=self.library_manager)
        
        # Preload EasyOCR in background thread so full-page scan is instant!
        import translation.gemini_provider as gemini_provider
        import threading
        threading.Thread(target=gemini_provider._get_ocr_reader, daemon=True, name="OCRPreload").start()
        
        self.main_window.mainloop()

    def launch_overlay(self):
        from overlay.window import OverlayWindow
        
        if self._overlay:
            # Zaten çalışıyorsa / oluşturulmuşsa toggle yap (temizle ve kapat/aç)
            self._toggle_app()
            return
            
        log.info("Starting overlay window...")
        if self.main_window:
            self.main_window.iconify()
        self._overlay = OverlayWindow(on_ready=self._on_overlay_ready, master=self.main_window)
        self._overlay.run()
        
    def _on_overlay_ready(self) -> None:
        log.info("Overlay ready. Initialising components...")

        root   = self._overlay.root
        canvas = self._overlay.canvas

        # Tooltip
        from overlay.tooltip import TranslationTooltip
        self._tooltip = TranslationTooltip(root)

        from overlay.lasso import LassoController
        self._lasso = LassoController(
            overlay=self._overlay,
            on_lasso_done=self._on_lasso_done,
            on_magic_wand=self._on_magic_wand_done,
            on_full_page=self._on_full_page_done,
            on_dismiss=self._on_dismiss,
            on_set_clickthrough=self._overlay.set_click_through,
            on_sleep_toggle=self._on_sleep_toggle,
        )

        self._overlay.register_mouse_move(self._on_mouse_move)

        from tray.tray_icon import TrayIcon
        
        def show_main_app():
            if self.main_window:
                self.main_window.deiconify()
                self.main_window.lift()
                self.main_window.focus_force()
                
        self._tray = TrayIcon(
            on_show_app=show_main_app,
            on_settings=self._open_settings,
            on_quit=self._quit,
        )
        self._tray.start()
        self._is_running = True
        if self.main_window:
            self.main_window.update_overlay_btn_state(True)
        log.info("MangaLens running. Right-click anywhere to arm lasso.")

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_sleep_toggle(self, is_sleep: bool) -> None:
        log.info(f"Sleep mode toggled: {is_sleep}")
        self._sleep_mode = is_sleep
        
        if self._lasso:
            self._lasso.force_sleep(self._sleep_mode)
            
        if self._tooltip:
            import pynput.mouse
            c = pynput.mouse.Controller()
            mx, my = c.position
            if self._sleep_mode:
                self._tooltip.show(i18n.t("sleep_on"), mx, my)
            else:
                self._tooltip.show(i18n.t("sleep_off"), mx, my)
            
            # Auto-hide after 1.5 seconds message after a short delay
            self._overlay.root.after(2000, lambda: self._tooltip.hide() if self._tooltip else None)
            
        if hasattr(self._overlay, 'set_sleep_mode'):
            self._overlay.set_sleep_mode(is_sleep)

    def _on_mouse_move(self, x: int, y: int) -> None:
        """Called ~60fps from the overlay's mouse poll. Update tooltip position."""
        if self._tooltip and self._tooltip.visible:
            self._tooltip.update_position(x, y)

    def _on_lasso_done(self, points: list[tuple[int, int]]) -> None:
        """
        Called on the Tk main thread when the user completes a lasso.
        Captures the screen region and fires the async translation.
        """
        log.info(f"Lasso completed with {len(points)} points.")

        try:
            img, (left, top, w, h) = capture_bounding_box(points)
        except ValueError as exc:
            log.warning(f"Capture failed: {exc}")
            if self._lasso:
                self._lasso.set_state_idle()
            return

        area = w * h
        if area < MIN_CAPTURE_AREA_PX:
            log.info(f"Captured area {area}px² is below threshold — ignoring.")
            if self._lasso:
                self._lasso.set_state_idle()
            return

        log.info(f"Captured {w}×{h} region at ({left},{top}). Sending to Gemini 2.0 Flash…")
        # img is a PIL Image — stays in memory, passed directly to SDK

        # Show a "translating…" placeholder immediately
        root = self._overlay.root
        mx   = self._overlay.mouse_x
        my   = self._overlay.mouse_y
        if self._tooltip:
            self._tooltip.show(i18n.t("translating_osd"), mx, my)

        def on_success(translation: str) -> None:
            log.info(f"Translation received: {translation!r}")
            root.after(0, lambda: self._show_translation(translation))

        def on_error(msg: str) -> None:
            log.error(f"Translation error: {msg}")
            root.after(0, lambda: self._show_translation(msg))

        def on_status(msg: str) -> None:
            root.after(0, lambda: self._show_translation(msg))

        self._translate_image_async(img, on_success, on_error, on_status=on_status)

        if self._lasso:
            self._lasso.set_state_translating()

    def _on_magic_wand_done(self, pt: tuple[int, int]) -> None:
        """
        Called when the user clicks without dragging (or Ctrl+Left Click).
        Uses OpenCV to find the bubble boundaries automatically.
        """
        log.info(f"Magic wand triggered at {pt}.")
        root = self._overlay.root
        
        if self._tooltip:
            self._tooltip.show(i18n.t("magic_wand_osd"), pt[0], pt[1])
        if self._lasso:
            self._lasso.set_state_translating()

        def _worker():
            try:
                img, bbox = capture_magic_wand(pt[0], pt[1])
                if not img or not bbox:
                    log.info("Magic wand found no valid bubble.")
                    root.after(0, self._on_magic_wand_failed)
                    return

                left, top, w, h = bbox
                log.info(f"Magic wand captured {w}×{h} region at ({left},{top}). Sending to Gemini…")

                def on_success(translation: str) -> None:
                    log.info(f"Translation received: {translation!r}")
                    root.after(0, lambda: self._show_translation(translation))

                def on_error(msg: str) -> None:
                    log.error(f"Translation error: {msg}")
                    root.after(0, lambda: self._show_translation(msg))

                def on_status(msg: str) -> None:
                    root.after(0, lambda: self._show_translation(msg))

                self._translate_image_async(img, on_success, on_error, on_status=on_status)
            except Exception as exc:
                log.exception(f"Magic wand worker error: {exc}")
                root.after(0, self._on_magic_wand_failed)

        threading.Thread(target=_worker, daemon=True, name="MagicWandWorker").start()

    def _on_magic_wand_failed(self) -> None:
        """Called on Tk main thread when magic wand fails to find a bubble."""
        if self._tooltip:
            mx = self._overlay.mouse_x
            my = self._overlay.mouse_y
            self._tooltip.show("[Metin balonu bulunamadı]", mx, my)
            self._overlay.root.after(1500, lambda: self._tooltip.hide() if self._tooltip else None)
        if self._lasso:
            self._lasso.set_state_idle()

    def _on_full_page_done(self) -> None:
        """
        Called on Tk main thread when Ctrl+Shift is pressed (Full Page Mode).
        Uses Gemini Vision AI with strict timeout and thread guard.
        If panel mode is active, it only captures the purple panel box area.
        """
        if getattr(self, "_is_full_page_running", False):
            log.info("Full page scan already in progress — ignoring duplicate request.")
            return

        self._is_full_page_running = True
        log.info("Full Page translation triggered (Ctrl+Shift).")
        root = self._overlay.root
        
        is_panel = False
        # Check if panel mode is active
        panel_bounds = self._overlay.get_panel_bounds()
        if panel_bounds:
            is_panel = True
            x, y, sw, sh = panel_bounds
            log.info(f"Panel mode active, capturing region: {panel_bounds}")
            offset_x, offset_y = x, y
        else:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x, y = 0, 0
            offset_x, offset_y = 0, 0
            
        mx = self._overlay.mouse_x
        my = self._overlay.mouse_y

        if self._tooltip:
            self._tooltip.show(i18n.t("full_page_osd"), mx, my)
        if self._lasso:
            self._lasso.set_state_translating()

        def _worker():
            try:
                from capture.screenshot import capture_region
                img_full = capture_region(x, y, sw, sh)

                def on_success(badge_results: list[tuple[tuple[int, int, int, int], str]]) -> None:
                    self._is_full_page_running = False
                    log.info(f"Full page translation received {len(badge_results)} items.")
                    if not badge_results:
                        root.after(0, self._on_full_page_failed)
                    else:
                        root.after(0, lambda: self._show_full_page_badges(badge_results))

                def on_error(msg: str) -> None:
                    self._is_full_page_running = False
                    log.error(f"Full page error: {msg}")
                    root.after(0, lambda: self._show_translation(msg))

                def on_status(msg: str) -> None:
                    # Update tooltip position to center of screen or last mouse pos, here we just show it
                    root.after(0, lambda: self._show_translation(msg))

                provider = load_active_provider()
                provider_factory.translate_full_page_async(
                    provider, img_full, sw, sh, offset_x, offset_y, is_panel, on_success, on_error, on_status=on_status
                )
            except Exception as exc:
                self._is_full_page_running = False
                log.exception(f"Full page worker error: {exc}")
                root.after(0, self._on_full_page_failed)

        threading.Thread(target=_worker, daemon=True, name="FullPageWorker").start()

    def _show_full_page_badges(self, badge_results: list[tuple[tuple[int, int, int, int], str]]) -> None:
        """Displays translucent translation badges over each bubble location."""
        if self._tooltip:
            self._tooltip.show_multi_badges(badge_results)
        if self._lasso:
            self._lasso.set_state_showing()

    def _on_full_page_failed(self) -> None:
        """Called on Tk main thread when full page scan fails to detect bubbles."""
        if self._tooltip:
            mx = self._overlay.mouse_x
            my = self._overlay.mouse_y
            self._tooltip.show("[Balon bulunamadı]", mx, my)
            self._overlay.root.after(1500, lambda: self._tooltip.hide() if self._tooltip else None)
        if self._lasso:
            self._lasso.set_state_idle()

    def _translate_image_async(self, image, on_success, on_error, on_status=None):
        provider = load_active_provider()
        provider_factory.translate_image_async(provider, image, on_success, on_error, on_status=on_status)

    def _show_translation(self, text: str) -> None:
        """Display the translation tooltip (called on Tk main thread)."""
        mx = self._overlay.mouse_x
        my = self._overlay.mouse_y
        if self._tooltip:
            self._tooltip.show(text, mx, my)
        if self._lasso:
            self._lasso.set_state_showing()

    def _on_dismiss(self) -> None:
        """Hide the tooltip and return to idle."""
        log.info("Tooltip dismissed.")
        if self._tooltip:
            self._tooltip.hide()
        # LassoController calls set_state_idle() after this callback

    # ── Tray callbacks ────────────────────────────────────────────────────────

    def _open_settings(self) -> None:
        """Open the settings window from the tray (thread-safe via after)."""
        root = self._overlay.root
        root.after(0, self._open_settings_main)

    def _open_settings_main(self) -> None:
        if self._settings is None or (
            self._settings._win is not None
            and not self._settings._win.winfo_exists()
        ):
            def on_saved(_key=None):
                # Settings saved, reload UI state
                self._overlay.update_panel_mode()
                
            self._settings = SettingsWindow(
                self._overlay.root, 
                is_running=self._is_running,
                on_toggle=self._toggle_app,
                on_saved=on_saved
            )
        self._settings.show()

    def _toggle_app(self) -> None:
        if self._is_running:
            self._is_running = False
            self._overlay.root.withdraw()
            if self._tooltip:
                self._tooltip.hide()
            if self._lasso:
                self._lasso.force_sleep(True)
            if self._settings:
                self._settings.set_running_state(False)
            if self.main_window:
                self.main_window.update_overlay_btn_state(False)
        else:
            self._is_running = True
            self._overlay.root.deiconify()
            self._overlay.root.attributes("-alpha", 1.0)
            if self._lasso:
                self._lasso.force_sleep(False)
            if self._settings:
                self._settings.set_running_state(True)
            if self.main_window:
                self.main_window.update_overlay_btn_state(True)
                self.main_window.iconify()
                
    def _quit(self) -> None:
        """Clean shutdown from tray or Tk close."""
        log.info("Shutting down MangaLens…")
        if self._lasso:
            self._lasso.stop()
        if self._tray:
            self._tray.stop()
        if self._tooltip:
            self._tooltip.hide()
        self._overlay.quit()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # On Windows, DPI awareness ensures coordinates are physical pixels
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    app = MangaLensApp()
    app.run()
