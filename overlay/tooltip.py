"""
overlay/tooltip.py — Cursor-following floating translation label.

Creates a frameless, always-on-top, semi-transparent Tkinter Toplevel window
that displays the Turkish translation text and repositions itself in real time
as the mouse cursor moves.

Design notes
------------
- Uses a second Toplevel (not a Label widget on the main canvas) so it can be
  independently transparent and avoid interfering with the lasso canvas.
- The window has WS_EX_NOACTIVATE set via ctypes so it never steals keyboard
  focus from the user's active application.
- Mouse events on the tooltip window are forwarded through (click-through) so
  the dismiss click registers on the underlying overlay, not on the tooltip itself.
"""

from __future__ import annotations

import ctypes
import tkinter as tk
from tkinter import font as tkfont
from typing import Optional

from config import (
    TOOLTIP_ALPHA,
    TOOLTIP_BG,
    TOOLTIP_FG,
    TOOLTIP_FONT_FAMILY,
    TOOLTIP_FONT_SIZE,
    TOOLTIP_FONT_WEIGHT,
    TOOLTIP_MAX_CHARS,
    TOOLTIP_OFFSET_X,
    TOOLTIP_OFFSET_Y,
    TOOLTIP_PADDING_X,
    TOOLTIP_PADDING_Y,
)

# Win32 extended window style constants
GWL_EXSTYLE      = -20
WS_EX_LAYERED    = 0x00080000
WS_EX_TRANSPARENT= 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST    = 0x00000008

user32 = ctypes.windll.user32


def _set_click_through(hwnd: int) -> None:
    """Make a window click-through using Win32 extended styles."""
    style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    user32.SetWindowLongW(
        hwnd, GWL_EXSTYLE,
        style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    )


def _wrap_text(text: str, max_chars: int) -> str:
    """Wrap long text at word boundaries."""
    if len(text) <= max_chars:
        return text
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > max_chars:
            if current:
                lines.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        lines.append(current)
    return "\n".join(lines)


class TranslationTooltip:
    """
    A cursor-following floating label that shows the Turkish translation.

    Lifecycle
    ---------
    show(text)  → create/update and make visible
    update_position(x, y)  → called on every mouse move event
    hide()      → destroy the tooltip window
    """

    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._win: Optional[tk.Toplevel] = None
        self._label: Optional[tk.Label] = None
        self._multi_wins: list[tk.Toplevel] = []
        self.visible: bool = False
        # Re-usable Font instance to prevent Tcl font handle leakage!
        self._badge_font = tkfont.Font(
            family=TOOLTIP_FONT_FAMILY,
            size=10,
            weight="bold",
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def show(self, text: str, cursor_x: int, cursor_y: int) -> None:
        """Display (or refresh) the floating label with the given text."""
        wrapped = _wrap_text(text, TOOLTIP_MAX_CHARS)

        if self._win is None or not self._win.winfo_exists():
            self._build_window()

        self._label.config(text=wrapped)  # type: ignore[union-attr]
        self._reposition(cursor_x, cursor_y)
        self._win.deiconify()  # type: ignore[union-attr]
        self.visible = True

    def show_multi_badges(self, badge_list: list[tuple[tuple[int, int, int, int], str]]) -> None:
        """
        Tam Sayfa Modu: Her konuşma balonunun üzerine tam hizalanmış yüzen çeviri etiketi koyar.
        badge_list: list[((x, y, w, h), turkish_text)]
        """
        self.hide()

        for (x, y, w, h), text in badge_list:
            try:
                win = tk.Toplevel(self._root)
                win.overrideredirect(True)
                win.attributes("-topmost", True)
                win.attributes("-alpha", 0.96)
                win.configure(bg="#121215")

                hwnd = int(win.frame(), 16)
                style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)

                # Şık İnce Altın Çerçeve
                border_frame = tk.Frame(win, bg="#D4AF37", bd=1)
                border_frame.pack(fill="both", expand=True)

                inner_frame = tk.Frame(border_frame, bg="#18181B")
                inner_frame.pack(fill="both", expand=True, padx=1, pady=1)

                # Cover the original text completely
                tw, th = w, h
                
                # Dinamik font boyutu hesaplama (kutu alanı / karakter sayısına göre)
                import math
                area_per_char = (tw * th) / max(1, len(text))
                estimated_size = int(math.sqrt(area_per_char) * 0.7)
                font_size = max(7, min(12, estimated_size))  # 7 ile 12 punto arası sınırla
                
                if not hasattr(self, '_font_cache'):
                    self._font_cache = {}
                if font_size not in self._font_cache:
                    self._font_cache[font_size] = tkfont.Font(
                        family=TOOLTIP_FONT_FAMILY,
                        size=font_size,
                        weight="bold",
                    )
                
                wrap_len = max(10, tw - 4)

                lbl = tk.Label(
                    inner_frame,
                    text=text,
                    font=self._font_cache[font_size],
                    fg="#FFFFFF",
                    bg="#18181B",
                    padx=1,
                    pady=1,
                    justify=tk.CENTER,
                    wraplength=wrap_len,
                )
                lbl.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

                win.geometry(f"{tw}x{th}+{x}+{y}")
                win.deiconify()
                self._multi_wins.append(win)
            except Exception:
                pass

        self.visible = True

    def update_position(self, cursor_x: int, cursor_y: int) -> None:
        """Move the tooltip to follow the cursor.  Call this on mouse move."""
        if self._win and self._win.winfo_exists() and self.visible:
            self._reposition(cursor_x, cursor_y)

    def hide(self) -> None:
        """Remove single tooltip and all multi badges, destroying HWNDs and forcing GC."""
        if self._win and self._win.winfo_exists():
            try:
                self._win.destroy()
            except Exception:
                pass
        self._win = None
        self._label = None

        for w in self._multi_wins:
            if w and w.winfo_exists():
                try:
                    w.destroy()
                except Exception:
                    pass
        self._multi_wins = []
        self.visible = False
        import gc
        gc.collect()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", TOOLTIP_ALPHA)
        win.configure(bg=TOOLTIP_BG)

        # Prevent focus steal on Windows
        hwnd = int(win.frame(), 16)
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            hwnd, GWL_EXSTYLE,
            style | WS_EX_NOACTIVATE
        )

        f = tkfont.Font(
            family=TOOLTIP_FONT_FAMILY,
            size=TOOLTIP_FONT_SIZE,
            weight=TOOLTIP_FONT_WEIGHT,
        )

        lbl = tk.Label(
            win,
            text="",
            font=f,
            fg=TOOLTIP_FG,
            bg=TOOLTIP_BG,
            padx=TOOLTIP_PADDING_X,
            pady=TOOLTIP_PADDING_Y,
            justify=tk.LEFT,
            wraplength=500,
        )
        lbl.pack()

        self._win = win
        self._label = lbl

    def _reposition(self, cursor_x: int, cursor_y: int) -> None:
        if self._win is None:
            return

        # Force geometry update so winfo_width/height are current
        self._win.update_idletasks()

        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        tw = self._win.winfo_width()
        th = self._win.winfo_height()

        x = cursor_x + TOOLTIP_OFFSET_X
        y = cursor_y + TOOLTIP_OFFSET_Y

        # Clamp to screen so tooltip never goes off-edge
        if x + tw > sw:
            x = cursor_x - tw - TOOLTIP_OFFSET_X
        if y + th > sh:
            y = cursor_y - th - TOOLTIP_OFFSET_Y

        self._win.geometry(f"+{x}+{y}")
