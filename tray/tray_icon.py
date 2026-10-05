"""
tray/tray_icon.py — System tray icon using pystray.

Runs in a separate daemon thread.  The icon is a simple programmatically
generated dark-gold circle so no external image file is needed.

Menu:
  ● Settings   → opens the settings window
  ● Quit       → cleanly exits the entire app
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw

from config import APP_NAME, BORDER_COLOR, TRAY_TOOLTIP


import os
import i18n

def _make_icon_image(size: int = 64) -> Image.Image:
    """Generate or load the tray icon."""
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
    try:
        if os.path.exists(logo_path):
            img = Image.open(logo_path)
            # Ensure it's square and resized properly
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            return img
    except Exception as e:
        print(f"Failed to load logo: {e}")
        
    # Fallback if logo not found
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = 4
    draw.ellipse([margin, margin, size - margin, size - margin], fill=BORDER_COLOR)
    inner_margin = 14
    draw.ellipse([inner_margin, inner_margin, size - inner_margin, size - inner_margin], fill=(20, 20, 20, 255))
    center = size // 2
    r = 8
    draw.ellipse([center - r, center - r, center + r, center + r], fill=BORDER_COLOR)
    return img


class TrayIcon:
    """
    System tray icon manager.

    Parameters
    ----------
    on_settings : callback invoked when user clicks "Settings"
    on_quit     : callback invoked when user clicks "Quit"
    """

    def __init__(
        self,
        on_show_app: Callable[[], None],
        on_settings: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_show_app = on_show_app
        self._on_settings = on_settings
        self._on_quit     = on_quit
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the tray icon in a background thread."""
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="TrayIcon",
        )
        self._thread.start()

    def stop(self) -> None:
        """Remove the tray icon."""
        if self._icon:
            self._icon.stop()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        menu = pystray.Menu(
            pystray.MenuItem(i18n.t("open_library"), self._show_app_clicked, default=True),
            pystray.MenuItem(i18n.t("tray_settings"), self._settings_clicked),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(i18n.t("tray_quit"), self._quit_clicked),
        )
        self._icon = pystray.Icon(
            name=APP_NAME,
            icon=_make_icon_image(),
            title=TRAY_TOOLTIP,
            menu=menu,
        )
        self._icon.run()

    def _show_app_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._on_show_app()
        
    def _settings_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._on_settings()

    def _quit_clicked(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self._on_quit()
